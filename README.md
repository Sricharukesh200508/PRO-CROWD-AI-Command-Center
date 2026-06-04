# Pro-Crowd AI Dashboard

A modern React dashboard for real-time crowd density analysis, powered by CSRNet.

## 🚀 Setup & Run

### 1. Backend (Python/Flask)
The backend handles the AI processing using `CSRNet` and streams video via MJPEG.

```bash
cd backend
pip install -r requirements.txt
python server.py
```
*Wait for "✅ Server active and model loaded." before using the frontend.*

### 2. Frontend (React/Vite)
The frontend provides the "Super Cool" dashboard interface.

```bash
cd frontend
npm install  # (If not already installed)
npm run dev
```
*Open the URL shown (usually `http://localhost:5173`) in your browser.*

## 🌟 Features
-   **Static Image Analysis**: Upload an image to get count and density map.
-   **Live Video Stream**: Upload a video file to simulate a live CCTV feed.
    -   The server processes the video frame-by-frame.
    -   The frontend displays the live processed stream with heatmap overlay.
    -   Real-time stats (count, density) are updated every second.
-   **Safety Alerts**: Visual warnings when crowd density exceeds the set threshold.
-   **Modern UI**: Glassmorphism design with smooth animations.

## ⚠️ Notes
-   Ensure `best_csrnet_shanghaiA.pth` is in the project root.
-   Video processing is CPU-intensive. Lower resolution videos (e.g., 640x480) recommended for smooth "live" playback without GPU.
