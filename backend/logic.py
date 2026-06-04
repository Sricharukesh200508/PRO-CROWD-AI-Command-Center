import matplotlib
matplotlib.use('Agg') # ⚠️ CRITICAL: Must be before other matplotlib imports

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
import cv2
import io
import matplotlib.pyplot as plt
import base64
from ultralytics import YOLO

# ==========================================
# 🧠 MODEL ARCHITECTURE (Copied from app.py)
# ==========================================
class CSRNet(nn.Module):
    def __init__(self):
        super(CSRNet, self).__init__()
        vgg = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1)
        self.frontend = vgg.features[0:23]
        self.backend = nn.Sequential(
            nn.Conv2d(512, 512, 3, padding=2, dilation=2), nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, 3, padding=2, dilation=2), nn.ReLU(inplace=True),
            nn.Conv2d(512, 256, 3, padding=2, dilation=2), nn.ReLU(inplace=True),
            nn.Conv2d(256, 128, 3, padding=2, dilation=2), nn.ReLU(inplace=True),
            nn.Conv2d(128, 64, 3, padding=2, dilation=2), nn.ReLU(inplace=True)
        )
        self.output_layer = nn.Conv2d(64, 1, kernel_size=1)

    def forward(self, x):
        x = self.frontend(x)
        x = self.backend(x)
        x = self.output_layer(x)
        return x

def load_model():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Load CSRNet
    csr_model = CSRNet().to(device)
    try:
        csr_model.load_state_dict(torch.load('../best_csrnet_shanghaiA.pth', map_location=device))
        print("✅ CSRNet loaded.")
    except:
        print("⚠️ CSRNet weights not found. Demo mode active.")
    csr_model.eval()
    
    # Load YOLO
    try:
        yolo_model = YOLO('yolov8n.pt')
        print("✅ YOLO v8 loaded.")
    except Exception as e:
        print(f"⚠️ YOLO load failed: {e}")
        yolo_model = None
        
    return csr_model, yolo_model, device

def calculate_pressure_index(density_map):
    """
    Calculates a heuristic 'Pressure Index' from the density map.
    Scale: 0 - 100
    Logic: Peak local density normalized against a hypothetical safety threshold.
    """
    if density_map is None or density_map.size == 0:
        return 0
    
    # Identify high density areas (top 0.5% of pixels)
    peak_val = np.percentile(density_map, 99.5)
    
    # Heuristic normalization: 
    # For CSRNet on ShanghaiTech, a 'dangerous' local peak is typically around 0.1-0.2
    # We'll map 0.15 to a pressure of 80.
    pressure = int(min(100, (peak_val / 0.15) * 80))
    
    return max(0, pressure)

# ==========================================
# 🛠️ PROCESSING HELPERS
# ==========================================
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def process_image(img_pil, csr_model, yolo_model, device, threshold=30):
    """Processes a single image for static analysis using hybrid logic"""
    # Convert PIL to OpenCV for YOLO
    frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    # 1. Try YOLO first (Person class only)
    model_name = "YOLO v8 (Sparse)"
    results = yolo_model(frame, conf=0.4, verbose=False, classes=[0])[0]
    count = len(results.boxes)
    
    if count > threshold:
        # DENSE MODE: CSRNet + Heatmap
        model_name = "CSRNet (Dense)"
        img_tensor = transform(img_pil).unsqueeze(0).to(device)
        
        with torch.no_grad():
            output = csr_model(img_tensor)
            count = int(output.sum().item())
            density_map = output.squeeze().cpu().numpy()
            pressure = calculate_pressure_index(density_map)
            density_map_viz = cv2.GaussianBlur(density_map, (15, 15), 0)
        
        # Convert density map to base64 image
        fig, ax = plt.subplots()
        ax.imshow(density_map_viz, cmap='jet')
        ax.axis('off')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    else:
        # SPARSE MODE: YOLO Bounding Boxes
        pressure = int((count / max(1, threshold)) * 50) 
        viz_frame = results.plot()
        
        # Convert OpenCV image to base64
        _, buffer = cv2.imencode('.png', viz_frame)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        
    return count, img_b64, pressure, model_name

def get_inference_result(frame, csr_model, yolo_model, device, threshold=30, force_model=None):
    """
    Hybrid logic: Use YOLO for sparse crowds, CSRNet for dense crowds.
    Automatically switches based on YOLO detection count vs threshold.
    Or forces a specific model if force_model is provided ('CSRNet' or 'YOLO').
    """
    # 1. Handle Forced Mode
    if force_model == 'CSRNet':
        model_name = "CSRNet (Forced)"
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img_tensor = transform(img_pil).unsqueeze(0).to(device)
        with torch.no_grad():
            output = csr_model(img_tensor)
            count = int(output.sum().item())
            density_map = output.squeeze().cpu().numpy()
            pressure = calculate_pressure_index(density_map)
            density_map_viz = cv2.GaussianBlur(density_map, (15, 15), 0)
            density_map_norm = cv2.normalize(density_map_viz, None, 0, 255, cv2.NORM_MINMAX)
            viz_frame = cv2.applyColorMap(density_map_norm.astype(np.uint8), cv2.COLORMAP_JET)
        return count, viz_frame, pressure, model_name

    # 2. Hybrid logic (Default)
    model_name = "YOLO v8 (Sparse)"
    results = yolo_model(frame, conf=0.4, verbose=False, classes=[0])[0]
    count = len(results.boxes)
    
    if count > threshold:
        # DENSE MODE: CSRNet + Heatmap
        model_name = "CSRNet (Dense)"
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img_tensor = transform(img_pil).unsqueeze(0).to(device)
        
        with torch.no_grad():
            output = csr_model(img_tensor)
            count = int(output.sum().item())
            density_map = output.squeeze().cpu().numpy()
            pressure = calculate_pressure_index(density_map)
            density_map_viz = cv2.GaussianBlur(density_map, (15, 15), 0)
            density_map_norm = cv2.normalize(density_map_viz, None, 0, 255, cv2.NORM_MINMAX)
            viz_frame = cv2.applyColorMap(density_map_norm.astype(np.uint8), cv2.COLORMAP_JET)
    else:
        # SPARSE MODE: YOLO Bounding Boxes
        pressure = int((count / max(1, threshold)) * 50) # Heuristic for YOLO
        viz_frame = results.plot() # Draws bounding boxes
        
    return count, viz_frame, pressure, model_name

def apply_heatmap_overlay(frame, viz_frame, count, pressure, model_name="CSRNet"):
    """
    Combines visual feedback (Heatmap if CSRNet, Boxes if YOLO) with frame.
    Efficient for creating video frames.
    """
    # Resize viz_frame to match frame if needed (YOLO plot usually matches original)
    h, w, _ = frame.shape
    viz_resized = cv2.resize(viz_frame, (w, h))
    
    # If it's a heatmap (CSRNet), blend it. If it's YOLO plots, use directly.
    if "CSRNet" in model_name:
        overlay = cv2.addWeighted(frame, 0.6, viz_resized, 0.4, 0)
    else:
        overlay = viz_resized # YOLO plot() already contains the detections

    
    # Add count text to frame
    cv2.putText(overlay, f"Count: {count}", (30, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
    
    # Add Pressure Index
    p_color = (0, 255, 0) if pressure < 40 else (0, 255, 255) if pressure < 70 else (0, 0, 255)
    cv2.putText(overlay, f"Pressure: {pressure}%", (30, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, p_color, 2)
    
    # Add Active Model
    cv2.putText(overlay, f"Model: {model_name}", (30, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    return overlay

def get_safety_assessment(count, threshold, pressure):
    """
    Returns a safety tier and mitigation recommendation.
    Tiers: Safe, Elevated, Warning, Critical
    """
    cpi = count / max(1, threshold)
    
    if cpi >= 1.0 or pressure > 85:
        tier = "CRITICAL"
        recommendation = f"Immediate evacuation/diversion to Sector B required. Percentage over-capacity: {int((cpi-1)*100)}%."
    elif cpi >= 0.85 or pressure > 70:
        tier = "WARNING"
        recommendation = "Near capacity. Stop admissions immediately. Divert incoming crowd to Sector C."
    elif cpi >= 0.7 or pressure > 50:
        tier = "ELEVATED"
        recommendation = "Monitor gate 4 closely. Prepare for potential diversion. Deploy barrier 4 if needed."
    else:
        tier = "SAFE"
        recommendation = "Normal operations. Maintain standard monitoring."
        
    return tier, recommendation, cpi
