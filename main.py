import cv2
import time
import logging
import json
import os
import math
import datetime
import subprocess
import threading
import re
import config
from detector import HumanDetector
from wled import WLEDController
from notifier import TelegramNotifier
import streamer

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

DOOR_CONFIG_FILE = "door_config.json"

class DoorConfig:
    def __init__(self):
        self.rect = config.DOOR_RECT
        self.dragging = False
        self.start_point = None
        self.current_drag_rect = None 

    def load(self):
        if os.path.exists(DOOR_CONFIG_FILE):
            try:
                with open(DOOR_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.rect = data.get("rect", config.DOOR_RECT)
            except Exception as e:
                logging.error(f"Failed to load door config: {e}")

    def save(self):
        try:
            with open(DOOR_CONFIG_FILE, 'w') as f:
                json.dump({"rect": self.rect}, f)
        except Exception as e:
            logging.error(f"Failed to save door config: {e}")

def get_absolute_rect(rect, width, height):
    dx1, dy1, dx2, dy2 = rect
    x1, y1 = int(dx1 * width), int(dy1 * height)
    x2, y2 = int(dx2 * width), int(dy2 * height)
    return x1, y1, x2, y2

def is_in_rect(center, rect, width, height):
    x, y = center
    x1, y1, x2, y2 = get_absolute_rect(rect, width, height)
    return x1 <= x <= x2 and y1 <= y <= y2

def mouse_callback(event, x, y, flags, param):
    cfg = param['config']
    width, height = param['size']
    if width == 0 or height == 0: return

    nx, ny = x / width, y / height
    nx = max(0.0, min(1.0, nx))
    ny = max(0.0, min(1.0, ny))

    if event == cv2.EVENT_LBUTTONDOWN:
        cfg.dragging = True
        cfg.start_point = (nx, ny)
        cfg.current_drag_rect = None
    elif event == cv2.EVENT_MOUSEMOVE:
        if cfg.dragging:
            sx, sy = cfg.start_point
            x1, x2 = sorted([sx, nx])
            y1, y2 = sorted([sy, ny])
            cfg.current_drag_rect = [x1, y1, x2, y2]
    elif event == cv2.EVENT_LBUTTONUP:
        if cfg.dragging:
            cfg.dragging = False
            sx, sy = cfg.start_point
            x1, x2 = sorted([sx, nx])
            y1, y2 = sorted([sy, ny])
            if (x2 - x1) > 0.01 and (y2 - y1) > 0.01:
                cfg.rect = [x1, y1, x2, y2]
                cfg.save()
            cfg.current_drag_rect = None

# Global state for tunnel
tunnel_process = None

def control_tunnel(action, notifier):
    global tunnel_process
    if action == 'start_stream':
        if tunnel_process:
            notifier.send_message("Tunnel already running.")
            return
            
        notifier.send_message("Starting Cloudflare Tunnel... 🚀")
        try:
            # Start cloudflared
            cmd = [config.CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{config.STREAM_PORT}"]
            tunnel_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Read stderr for the URL (cloudflared prints URL to stderr)
            threading.Thread(target=extract_url, args=(tunnel_process.stderr, notifier)).start()
            
        except FileNotFoundError:
            notifier.send_message("Error: 'cloudflared' not found in PATH.")
        except Exception as e:
            notifier.send_message(f"Error starting tunnel: {e}")
            
    elif action == 'stop_stream':
        if tunnel_process:
            tunnel_process.terminate()
            tunnel_process = None
            notifier.send_message("Tunnel Closed. 🛑")
        else:
            notifier.send_message("No tunnel running.")

def extract_url(pipe, notifier):
    """Reads stream output to find the *.trycloudflare.com URL"""
    for line in iter(pipe.readline, ''):
        if 'trycloudflare.com' in line:
            url_match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if url_match:
                url = url_match.group(0)
                notifier.send_message(f"🎥 Live Stream Ready:\n{url}")
                return

def main():
    detector = HumanDetector()
    wled = WLEDController()
    door_cfg = DoorConfig()
    door_cfg.load()
    notifier = TelegramNotifier()
    
    # Start Streamer App in Background
    streamer.start_server(config.STREAM_PORT)
    
    # Start Telegram Listener
    # Use a closure to capture local state (wled, door_cfg, etc.)
    # Note: room_count is an integer (immutable), so accessing strict 'current' value 
    # from a thread might be tricky if not using a mutable container.
    # We will use a mutable wrapper for state stats if needed, 
    # but strictly speaking Python function closures look up variables at call time.
    
    def telegram_command_handler(action):
        # Handle Tunnel
        if action in ['start_stream', 'stop_stream']:
            control_tunnel(action, notifier)
            return

        # Handle Status
        if action == 'status':
            wled_status = "ON 💡" if wled_is_active else "OFF ⚫"
            stream_status = "ON 🟢" if tunnel_process else "OFF 🔴"
            mute_status = "YES 🔕" if notifier.muted else "NO 🔔"
            stats = (
                f"📊 *System Status*\n"
                f"👥 Room Count: {room_count}\n"
                f"💡 Lights: {wled_status}\n"
                f"📹 Stream: {stream_status}\n"
                f"🔇 Muted: {mute_status}"
            )
            notifier.send_message(stats)

        # Handle Snapshot
        if action == 'snapshot':
            # Get latest frame from streamer (thread safe)
            frame = streamer.get_frame()
            if frame is not None:
                notifier.send_photo(frame, "📸 Snapshot requested")
            else:
                notifier.send_message("⚠️ Camera not ready.")

    notifier.start_listening(telegram_command_handler)

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        logging.error("Could not open video device.")
        return

    # Headless Mode vs Debug Mode
    WINDOW_NAME = "Smart Human Detector"
    callback_param = {'config': door_cfg, 'size': (0, 0)}

    if config.DEBUG_DRAW:
        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, mouse_callback, callback_param)
        logging.info("Debug Mode Enable: Local window created.")
    else:
        logging.info("Headless Mode: No local window.")

    # State
    tracked_history = {} 
    
    room_count = 0
    wled_is_active = False
    no_human_start_time = None
    
    delayed_alerts = [] # List of {'time': ts, 'tid': id}
    pending_exits = {} # {tid: {'time': ts, 'info': track_info}}

    print("Starting Intelligent Human Detector... (Headless/Silent Mode)")

    # Warmup
    for _ in range(10): cap.read()

    try:
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            height, width = frame.shape[:2]
            callback_param['size'] = (width, height)
            
            current_time = time.time()

            # 0. Process Delayed Alerts (Ensure light is definitely ON in frame)
            pending_alerts = []
            for alert in delayed_alerts:
                if current_time >= alert['time']:
                    # Trigger Alert
                    time_str = datetime.datetime.now().strftime("%I:%M %p")
                    notifier.send_photo(frame, f"🚪 Entry Detected at {time_str}\nID: {alert['tid']}")
                else:
                    pending_alerts.append(alert)
            delayed_alerts = pending_alerts

            # 1. Detection & Tracking
            tracks, annotated_frame = detector.track(frame)
            current_track_ids = set()

            # 2. Process Tracks (Active Humans)
            for trk in tracks:
                tid = trk['id']
                center = trk['center']
                current_track_ids.add(tid)
                
                if tid not in tracked_history:
                    # New ID detected
                    arrival_time = time.time()
                    
                    if is_in_rect(center, door_cfg.rect, width, height):
                        # In Door Zone - Check for Pending Exit (Flicker Merge)
                        if pending_exits:
                            # Reacquired! Pop one and treat as same person
                            old_tid, _ = pending_exits.popitem()
                            logging.info(f"Merged New ID {tid} with Pending Exit {old_tid}. Count remains {room_count}.")
                            # Inherit history? Or just start fresh tracker?
                            # Fresh tracker is safer for positions, but we skip Count increment.
                        else:
                            # Genuine New Entry
                            room_count += 1
                            # DELAYED TELEGRAM ALERT
                            delayed_alerts.append({'time': time.time() + 1.0, 'tid': tid})
                            logging.info(f"ID {tid} ENTERED. Count: {room_count}")
                        
                        tracked_history[tid] = {'center': center, 'first_seen': arrival_time, 'last_seen': arrival_time}

                    else:
                        # Reappearance (Inside Room)
                        logging.info(f"ID {tid} Appeared (Reappearance).")
                        arrival_time = time.time()
                        tracked_history[tid] = {'center': center, 'first_seen': arrival_time, 'last_seen': arrival_time}
                else:
                    # Existing ID
                    tracked_history[tid]['center'] = center
                    tracked_history[tid]['last_seen'] = time.time()


            # 3. Process Missing Tracks
            lost_ids = [tid for tid in tracked_history if tid not in current_track_ids]
            
            for tid in lost_ids:
                info = tracked_history[tid]
                last_center = info['center']
                
                del tracked_history[tid] # Remove from active tracking

                if is_in_rect(last_center, door_cfg.rect, width, height):
                    # Lost in Door Zone -> Buffer as Pending Exit
                    logging.info(f"ID {tid} pending exit (Buffer 1.5s)...")
                    pending_exits[tid] = {'time': time.time(), 'info': info}
                else:
                    # Lost elsewhere -> Occluded
                    pass

            # 4. Process Pending Exits (Timeout)
            expired_exits = []
            for tid, exit_data in pending_exits.items():
                if current_time - exit_data['time'] > 1.5:
                    expired_exits.append(tid)
            
            for tid in expired_exits:
                info = pending_exits.pop(tid)['info']
                room_count -= 1
                logging.info(f"ID {tid} EXIT CONFIRMED. Count: {room_count}")
                
                # TELEGRAM ALERT
                duration_sec = info['last_seen'] - info['first_seen']
                mins, secs = divmod(int(duration_sec), 60)
                duration_str = f"{mins}m {secs}s"
                notifier.send_message(f"🏃 Exit Detected.\nDuration: {duration_str}")

            # 5. Safety
            if room_count < 0: room_count = 0

            # 5. WLED Logic
            status_text = f"Count: {room_count} | "
            
            if room_count > 0:
                no_human_start_time = None
                if not wled_is_active:
                    wled.turn_on()
                    wled_is_active = True
                status_text += "ON"
            else:
                if wled_is_active:
                    if no_human_start_time is None: no_human_start_time = time.time()
                    elapsed = time.time() - no_human_start_time
                    remaining = config.TIMEOUT_SECONDS - elapsed
                    if elapsed >= config.TIMEOUT_SECONDS:
                        wled.turn_off()
                        wled_is_active = False
                        status_text += "OFF"
                    else:
                        status_text += f"Wait {remaining:.1f}s"
                else:
                    status_text += "OFF"

            # 6. Visualization
            # Draw Door
            x1, y1, x2, y2 = get_absolute_rect(door_cfg.rect, width, height)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(annotated_frame, "DOOR", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            # Draw drag rect (Legacy support for logic, though mouse off)
            if door_cfg.dragging and door_cfg.current_drag_rect:
                dx1, dy1, dx2, dy2 = get_absolute_rect(door_cfg.current_drag_rect, width, height)
                cv2.rectangle(annotated_frame, (dx1, dy1), (dx2, dy2), (0, 255, 255), 2)

            # Viz Pending Exits
            for tid in pending_exits:
                cv2.putText(annotated_frame, f"Wait Exit {tid}...", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 128, 255), 2)

            cv2.putText(annotated_frame, status_text, (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # STREAM UPDATE: Send the ANNOTATED frame to the stream
            # so remote user sees the boxes/door/status.
            streamer.update_frame(annotated_frame)

            # Local Window (Debug Mode)
            if config.DEBUG_DRAW:
                cv2.imshow(WINDOW_NAME, annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # Tiny sleep to prevent CPU hogging in headless mode since waitKey is gone
                time.sleep(0.01)

    except KeyboardInterrupt:
        logging.info("Interrupted.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
