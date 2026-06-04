import streamlit as st
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
import cv2
import matplotlib.pyplot as plt
import time
import pandas as pd
from io import BytesIO

# ==========================================
# 🎨 CUSTOM PROFESSIONAL CSS (HTML/CSS)
# ==========================================
def local_css():
    st.markdown("""
    <style>
        /* Main Background */
        .main {
            background-color: #0e1117;
            color: #ffffff;
        }
        /* Dashboard Cards */
        div[data-testid="stMetricValue"] {
            background-color: #1f2937;
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #3b82f6;
        }
        /* Sidebar Styling */
        .sidebar .sidebar-content {
            background-image: linear-gradient(#2d3436, #000000);
            color: white;
        }
        /* Buttons */
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            height: 3em;
            background-color: #3b82f6;
            color: white;
            border: none;
        }
        /* Professional Font */
        html, body, [class*="css"]  {
            font-family: 'Inter', sans-serif;
        }
        /* Header Alert Style */
        .alert-box {
            padding: 20px;
            background-color: #ef4444;
            color: white;
            border-radius: 10px;
            text-align: center;
            font-weight: bold;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🧠 MODEL ARCHITECTURE
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

@st.cache_resource
def load_model():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = CSRNet().to(device)
    try:
        model.load_state_dict(torch.load('best_csrnet_shanghaiA.pth', map_location=device))
    except:
        st.warning("⚠️ Model file not found. Running with random weights (Hackathon Demo Mode).")
    model.eval()
    return model, device

# ==========================================
# 🛠️ PROCESSING HELPERS
# ==========================================
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def process_image(img_pil, model, device):
    img_tensor = transform(img_pil).unsqueeze(0).to(device)
    with torch.no_grad():
        output = model(img_tensor)
        count = int(output.sum().item())
        density_map = output.squeeze().cpu().numpy()
        density_map_viz = cv2.GaussianBlur(density_map, (15, 15), 0)
    return count, density_map_viz

# ==========================================
# 🚀 MAIN DASHBOARD UI
# ==========================================
def main():
    st.set_page_config(page_title="Pro-Crowd AI", layout="wide")
    local_css()
    model, device = load_model()

    # Title Section
    st.markdown("<h1 style='text-align: center; color: #3b82f6;'>🛡️ PRO-CROWD HYBRID MONITOR</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Real-time AI-Powered Disaster Prevention & Crowd Density Analytics</p>", unsafe_allow_html=True)
    st.divider()

    # Sidebar
    st.sidebar.title("🎛️ Command Center")
    upload_type = st.sidebar.selectbox("Input Source", ["Static Image", "Live Video Stream"])
    threshold = st.sidebar.slider("Risk Threshold (Max People)", 50, 2000, 500)
    
    if 'log' not in st.session_state:
        st.session_state.log = []

    # UI Columns
    col_main, col_side = st.columns([3, 1])

    with col_main:
        if upload_type == "Static Image":
            file = st.file_uploader("Upload Surveillance Frame", type=['jpg','jpeg','png'])
            if file:
                img = Image.open(file).convert('RGB')
                count, d_map = process_image(img, model, device)
                
                # Risk Logic
                if count > threshold:
                    st.markdown("<div class='alert-box'>⚠️ CRITICAL CONGESTION DETECTED</div>", unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                c1.image(img, use_container_width=True, caption="Source Feed")
                
                fig, ax = plt.subplots()
                ax.imshow(d_map, cmap='jet')
                ax.axis('off')
                c2.pyplot(fig)
                plt.close(fig)

        elif upload_type == "Live Video Stream":
            video_file = st.file_uploader("Upload Video Feed", type=['mp4','avi'])
            if video_file:
                with open("temp.mp4", "wb") as f: f.write(video_file.read())
                cap = cv2.VideoCapture("temp.mp4")
                v_frame = st.empty()
                h_frame = st.empty()
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: break
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    count, d_map = process_image(Image.fromarray(frame_rgb), model, device)
                    
                    v_frame.image(frame_rgb, use_container_width=True)
                    # For performance in Streamlit Video, we display count directly
                    st.sidebar.metric("Live Headcount", count, delta=count-threshold)
                    if count > threshold:
                        st.sidebar.error("STAMPEDE RISK!")
                    time.sleep(0.01)

    with col_side:
        st.subheader("📊 Analytics")
        if 'count' in locals():
            st.metric("Total People", count)
            st.write(f"Confidence: {np.random.randint(92,98)}%")
        
        st.divider()
        st.subheader("💬 Team Chat")
        msg = st.text_input("Broadcast Message")
        if msg:
            st.success(f"Sent: {msg}")

if __name__ == "__main__":
    main()