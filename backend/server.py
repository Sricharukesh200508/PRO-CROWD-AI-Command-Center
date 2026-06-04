from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
from PIL import Image
import io
import cv2
import time
import threading
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from logic import load_model, process_image, get_inference_result, apply_heatmap_overlay, get_safety_assessment
from database import init_db, log_image_analysis, start_video_session, log_video_frame, get_history, get_session_timeline, clear_all_history

app = Flask(__name__)
CORS(app)

# Load models once at startup
print("⏳ Loading models...")
csr_model, yolo_model, device = load_model()
print("✅ Server active and models loaded.")

# Initialize database
init_db()
print("✅ Database initialized.")

# Global state for video streaming
global_video_path = "temp_video.mp4"
is_webcam = False
current_count = 0
current_pressure = 0
current_threshold = 500
current_model_type = "CSRNet"
is_streaming = False
playback_speed = 1.0 # 1.0 = Normal, 0.5 = Slow, 2.0 = Fast

def generate_frames(speed=1.0):
    global current_count, current_pressure, current_model_type, is_streaming
    source = 0 if is_webcam else global_video_path
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print("❌ Could not open video file")
        return

    is_streaming = True
    
    # Start a new video session in DB
    session_id = start_video_session("Webcam" if is_webcam else global_video_path)
    
    # Processing variables
    frame_counter = 0
    start_time = time.time()
    process_interval = 10 # Run inference every 10 frames for better performance
    last_density_map = None
    last_count = 0
    last_pressure = 0
    last_model_name = "CSRNet"
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    delay = 1.0 / (fps * speed) # Adjust delay based on speed multiplier
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            # Loop video
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        # Resize frame for faster processing and standard display
        frame = cv2.resize(frame, (640, 480))
        
        # Determine if we should run inference
        if frame_counter % process_interval == 0:
            try:
                # 1. Skip accumulated frames if webcam to ensure smoothness
                if is_webcam:
                    # Clear buffer: only keep the last frame
                    for _ in range(5): # grab a few extra to be sure we are at peak
                        cap.grab()
                    ret, frame = cap.read()
                    if not ret: break
                    frame = cv2.resize(frame, (640, 480))

                # 2. Force CSRNet for video files, use hybrid for webcam
                force = 'CSRNet' if not is_webcam else None
                hybrid_thresh = 30
                
                count, viz_frame, pressure, model_name = get_inference_result(
                    frame, csr_model, yolo_model, device, 
                    threshold=hybrid_thresh, force_model=force
                )
                
                last_density_map = viz_frame
                last_count = count
                last_pressure = pressure
                last_model_name = model_name
                current_count = count
                current_pressure = pressure
                
                # Log frame to database
                elapsed = time.time() - start_time
                tier, _, cpi = get_safety_assessment(count, current_threshold, pressure)
                log_video_frame(session_id, elapsed, count, pressure, cpi, tier)
            except Exception as e:
                print(f"Inference error: {e}")
        
        # Apply overlay (using fresh or cached density map)
        if last_density_map is not None:
            processed_frame = apply_heatmap_overlay(frame, last_density_map, last_count, last_pressure, last_model_name)
        else:
            processed_frame = frame
            
        # Add visual indicator for "Live" status vs "Processing"
        if frame_counter % process_interval != 0:
             cv2.circle(processed_frame, (620, 20), 5, (0, 255, 255), -1) # Yellow dot = using cached map
        else:
             cv2.circle(processed_frame, (620, 20), 5, (0, 255, 0), -1)   # Green dot = fresh inference

        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame_bytes = buffer.tobytes()
        
        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        frame_counter += 1
        
        # Control playback speed
        time.sleep(delay) 
    
    cap.release()
    is_streaming = False

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    file = request.files['video']
    file.save(global_video_path)
    return jsonify({"message": "Video uploaded successfully", "path": global_video_path})

@app.route('/video_feed')
def video_feed():
    global current_threshold, current_model_type, is_webcam
    speed = request.args.get('speed', default=1.0, type=float)
    current_threshold = request.args.get('threshold', default=500, type=int)
    is_webcam = request.args.get('webcam', default='false').lower() == 'true'
    return Response(generate_frames(speed), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/current_count')
def get_current_count():
    tier, recommendation, cpi = get_safety_assessment(current_count, current_threshold, current_pressure)
    return jsonify({
        "count": current_count, 
        "pressure": current_pressure,
        "is_streaming": is_streaming,
        "threshold": current_threshold,
        "cpi": round(cpi, 2),
        "tier": tier,
        "recommendation": recommendation
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    threshold = request.form.get('threshold', default=500, type=int)
    model_type = request.form.get('model_type', default='CSRNet', type=str)
    try:
        img_pil = Image.open(file.stream).convert('RGB')
        # Hybrid logic: Automatically switches between CSRNet and YOLO
        count, density_map_b64, pressure, model_name = process_image(img_pil, csr_model, yolo_model, device, threshold)
        tier, recommendation, cpi = get_safety_assessment(count, threshold, pressure)
        
        # Log to database
        log_image_analysis(count, pressure, cpi, tier, model_name)
        
        return jsonify({
            "count": count,
            "pressure": pressure,
            "density_map": density_map_b64,
            "cpi": round(cpi, 2),
            "tier": tier,
            "recommendation": recommendation,
            "model_name": model_name
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download_report')
def download_report():
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(100, 750, "Pro-Crowd AI Analysis Report")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 700, f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(100, 680, "Analysis Mode: Video Stream")
    
    c.drawString(100, 650, f"Latest Crowd Count: {current_count}")
    c.drawString(100, 630, f"Capacity Threshold: {current_threshold}")
    
    tier, recommendation, cpi = get_safety_assessment(current_count, current_threshold, current_pressure)
    
    c.drawString(100, 610, f"Crowd Pressure Index (CPI): {round(cpi, 2)}")
    c.drawString(100, 590, f"Local Density Pressure: {current_pressure}%")
    
    assessment_y = 550
    if tier == "CRITICAL":
        c.setFillColorRGB(0.8, 0, 0)
    elif tier == "WARNING":
        c.setFillColorRGB(1, 0.4, 0)
    elif tier == "ELEVATED":
        c.setFillColorRGB(0.2, 0.2, 0.6)
    else:
        c.setFillColorRGB(0, 0.5, 0)
        
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, assessment_y, f"Safety Tier: {tier}")
    
    c.setFont("Helvetica-Oblique", 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(100, assessment_y - 20, "Mitigation Strategy:")
    
    # Text wrapping for recommendation
    text_object = c.beginText(100, assessment_y - 40)
    text_object.setFont("Helvetica", 11)
    for line in recommendation.split('. '):
        text_object.textLine(line + ('.' if not line.endswith('.') else ''))
    c.drawText(text_object)
        
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='analysis_report.pdf', mimetype='application/pdf')

@app.route('/history')
def history():
    return jsonify(get_history())

@app.route('/video_history/<int:session_id>')
def video_history(session_id):
    return jsonify(get_session_timeline(session_id))

@app.route('/clear_history', methods=['POST'])
def clear_history():
    clear_all_history()
    return jsonify({"message": "History cleared successfully"})

if __name__ == '__main__':
    # Use threaded=True for stream support
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
