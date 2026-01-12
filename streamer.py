from flask import Flask, Response
import threading
import cv2
import time
import logging

app = Flask(__name__)

# Global buffer for the latest frame
outputFrame = None
lock = threading.Lock()

def update_frame(frame):
    global outputFrame, lock
    with lock:
        outputFrame = frame.copy()

def get_frame():
    """Thread-safe frame getter for snapshots."""
    global outputFrame, lock
    with lock:
        if outputFrame is None: return None
        return outputFrame.copy()

def generate():
    global outputFrame, lock
    while True:
        with lock:
            if outputFrame is None:
                continue
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            if not flag:
                continue
        
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')
        time.sleep(0.05) # Limit to ~20 FPS

@app.route("/")
def index():
    return "<h1>Smart Human Detector Live Stream</h1><img src='/video_feed'>"

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype = "multipart/x-mixed-replace; boundary=frame")

def start_server(port=5000):
    # Disable Flask banner
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Run Flask in a thread
    t = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': port, 'debug': False, 'use_reloader': False})
    t.daemon = True
    t.start()
    logging.info(f"Streamer started on port {port}")
