import os

# WLED Configuration
WLED_IP = "192.168.1.8"  # TODO: Replace with your WLED IP
JSON_URL = f"http://{WLED_IP}/json/state"

# Logic Configuration
TIMEOUT_SECONDS = 8
CONFIDENCE_THRESHOLD = 0.65

# Camera Configuration
CAMERA_INDEX = 0

# Door Tracking Configuration
# [x1, y1, x2, y2] proportional coordinates (0.0 to 1.0)
# Example: Right 20% of the screen is the "Door"
DOOR_RECT = [0.8, 0.0, 1.0, 1.0] 
DEBUG_DRAW = False
# Telegram Configuration
TELEGRAM_TOKEN = "" 
TELEGRAM_CHAT_ID = ""

# Remote Access Configuration
CLOUDFLARED_PATH = r"C:\Users\MY PC\Documents\new\huamn\cloudflared.exe" # Assumes it's in PATH, or provide full path
STREAM_PORT = 5000
