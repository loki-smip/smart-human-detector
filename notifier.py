import requests
import threading
import time
import cv2
import os
import datetime
import logging
import config

class TelegramNotifier:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.snapshot_dir = "snapshots"
        self.muted = False # State for notification toggle
        
        if not os.path.exists(self.snapshot_dir):
            os.makedirs(self.snapshot_dir)

    def _send_photo_thread(self, frame, caption):
        """Internal method to send photo in a separate thread."""
        if self.muted: return
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.snapshot_dir, f"alert_{timestamp}.jpg")
            cv2.imwrite(filename, frame)
            
            with open(filename, 'rb') as photo:
                url = f"{self.base_url}/sendPhoto"
                payload = {'chat_id': self.chat_id, 'caption': caption}
                files = {'photo': photo}
                requests.post(url, data=payload, files=files, timeout=10)
                
            logging.info("Telegram photo sent.")
        except Exception as e:
            logging.error(f"Failed to send Telegram photo: {e}")

    def send_photo(self, frame, caption="Alert"):
        """Sends a photo asynchronously."""
        if self.token == "YOUR_BOT_TOKEN_HERE" or self.muted:
            return

        t = threading.Thread(target=self._send_photo_thread, args=(frame, caption))
        t.start()

    def _send_message_thread(self, text):
        """Internal method to send text in a separate thread."""
        if self.muted: return
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {'chat_id': self.chat_id, 'text': text}
            requests.post(url, json=payload, timeout=10)
            logging.info(f"Telegram message sent: {text}")
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {e}")

    def send_message(self, text):
        """Sends a text message asynchronously."""
        if self.token == "YOUR_BOT_TOKEN_HERE" or self.muted:
            return

        t = threading.Thread(target=self._send_message_thread, args=(text,))
        t.start()
        
    def start_listening(self, callback):
        """Starts a background thread to listen for Telegram commands."""
        if self.token == "YOUR_BOT_TOKEN_HERE":
            logging.warning("Telegram token missing. Listener disabled.")
            return

        self.callback = callback
        t = threading.Thread(target=self._listener_thread)
        t.daemon = True
        t.start()
        logging.info("Telegram command listener started.")

    def _listener_thread(self):
        """Polls for updates and triggers callback on valid commands."""
        offset = 0
        get_updates_url = f"{self.base_url}/getUpdates"
        
        while True:
            try:
                # Long polling
                params = {'offset': offset + 1, 'timeout': 30}
                response = requests.get(get_updates_url, params=params, timeout=35)
                data = response.json()
                
                if data.get('ok'):
                    for result in data['result']:
                        update_id = result['update_id']
                        offset = max(offset, update_id)
                        
                        message = result.get('message', {})
                        text = message.get('text', '').lower()
                        chat_id = str(message.get('chat', {}).get('id'))
                        
                        # Security Check: Only listen to OWNER
                        if chat_id != self.chat_id and self.chat_id != "YOUR_CHAT_ID_HERE":
                            logging.warning(f"Ignored command from unknown user: {chat_id}")
                            continue

                        if text.startswith('/'):
                            # Commands
                            if text == '/stream':
                                self.callback('start_stream')
                            elif text == '/stop':
                                self.callback('stop_stream')
                            elif text == '/slint':
                                self.muted = True
                                self._send_reply("Silent Mode Active 🔕\nAlerts paused.")
                            elif text == '/art':
                                self.muted = False
                                self._send_reply("Alert Mode Active 🔔\nSending alerts.")
                            elif text == '/status':
                                self.callback('status')
                            elif text == '/snap':
                                self.callback('snapshot')
                            elif text == '/help':
                                help_text = (
                                    "🤖 *Bot Commands*:\n"
                                    "/status - Check System Status\n"
                                    "/snap - Take a photo 📸\n"
                                    "/stream - Start Live Video\n"
                                    "/stop - Stop Live Video\n"
                                    "/slint - Mute Alerts 🔕\n"
                                    "/art - Unmute Alerts 🔔"
                                )
                                self._send_reply(help_text)
                        else:
                            # Ignored
                            pass
                            
            except Exception as e:
                logging.error(f"Telegram Listener Error: {e}")
                time.sleep(5)

    def _send_reply(self, text):
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {'chat_id': self.chat_id, 'text': text}
            requests.post(url, json=payload, timeout=10)
        except: pass
