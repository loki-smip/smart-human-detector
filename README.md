# 🕵️‍♂️ Smart Human Detector (WLED + Telegram)

**Automate your room lights and get security alerts using AI Computer Vision.**

This project uses a standard webcam and **YOLOv8** to detect humans entering or exiting a room. It controls **WLED** smart lights based on occupancy and sends **Telegram** notifications with photos and video streams.

## ✨ Features

*   **🧠 Intelligent Detection**: Uses YOLOv8 to distinguish humans from pets or objects.
*   **🚪 Smart Entry/Exit Logic**:
    *   **Instant Entry**: Lights turn ON immediately when you enter.
    *   **Smart Hysteresis**: Prevents flickering (false exits) if you linger in the doorway.
    *   **Occupancy Counting**: Keeps lights ON as long as someone is inside.
*   **💡 WLED Integration**: Automatically turns WLED strips ON/OFF.
*   **📱 Telegram Bot**:
    *   Receive **Photo Alerts** 📸 on entry.
    *   Receive **Duration Reports** ⏱️ on exit.
    *   **Remote Control**: Mute alerts, check status, or request a snapshot.
*   **🌍 Remote Access**:
    *   **Live Video Stream**: View your camera feed from anywhere using a secure Cloudflare Tunnel.
    *   **Headless Mode**: Runs silently in the background without a desktop window.

---

## 🛠️ Prerequisites

### Hardware
1.  **PC/Laptop**: Windows or Linux (with Python 3.10+).
2.  **Webcam**: Any USB or integrated camera.
3.  **WLED Device**: An ESP8266/ESP32 running [WLED](https://github.com/Aircoookie/WLED).

### Software Requirements
*   **Python 3.10+**
*   **Cloudflared** (Optional, for remote streaming): [Download Here](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)

---

## 🚀 Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/smart-human-detector.git
    cd smart-human-detector
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Cloudflared (Optional)**
    *   Download `cloudflared.exe` (Windows) or binary (Linux).
    *   Place it in the project folder OR add it to your system PATH.

---

## ⚙️ Configuration

Open `config.py` and update the settings:

```python
# WLED Configuration
WLED_IP = "192.168.1.X"  # Your WLED Device IP

# Logic
TIMEOUT_SECONDS = 5      # How long lights stay ON after last person leaves
CONFIDENCE_THRESHOLD = 0.65 # AI Confidence (0.5 - 0.7 recommended)

# Camera
CAMERA_INDEX = 0         # 0 for default webcam

# Door Zone (0.0 to 1.0)
# Use DEBUG_DRAW = True to set this up visually first!
DOOR_RECT = [0.8, 0.0, 1.0, 1.0] 
DEBUG_DRAW = False       # Set True to open window and draw door zone

# Telegram Bot
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# Remote Access
CLOUDFLARED_PATH = r"C:\path\to\cloudflared.exe"
STREAM_PORT = 5000
```

### 🚪 Setting up the Door Zone
1.  Set `DEBUG_DRAW = True` in `config.py`.
2.  Run the script: `python main.py`.
3.  A window will open. **Click and Drag** to draw a box around your doorway.
4.  The config is saved automatically to `door_config.json`.
5.  Set `DEBUG_DRAW = False` to run in headless mode.

---

## 🏃 Usage

Run the main script:

```bash
python main.py
```

### 🤖 Telegram Commands

Send these commands to your bot:

| Command | Description |
| :--- | :--- |
| `/status` | 📊 Check Room Count, Light Status, and Stream State. |
| `/snap` | 📸 Request an instant photo snapshot. |
| `/stream` | 📹 Start a secure Cloudflare Tunnel for live video. |
| `/stop` | 🛑 Stop the live stream tunnel. |
| `/slint` | 🔕 **Silent Mode**: Mute all notification alerts. |
| `/art` | 🔔 **Alert Mode**: Unmute notifications. |
| `/help` | ℹ️ Show command list. |

---

## 📝 File Structure

*   `main.py`: Core logic loop (Detection, Tracking, WLED control).
*   `detector.py`: YOLOv8 wrapper for human detection.
*   `notifier.py`: Handles Telegram messages and photos.
*   `streamer.py`: Flask-based MJPEG video streaming server.
*   `wled.py`: simple API client for WLED.
*   `config.py`: Configuration settings.

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

[MIT](https://choosealicense.com/licenses/mit/)
