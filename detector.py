from ultralytics import YOLO
import cv2
import config

class HumanDetector:
    def __init__(self):
        # Load a pretrained YOLOv8n model
        self.model = YOLO('yolov8n.pt') 
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD

    def track(self, frame):
        """
        Tracks humans in a frame using YOLOv8 tracking.
        Returns:
            tracks (list): List of dicts {'id': int, 'box': [x1,y1,x2,y2], 'center': (x,y)}
            annotated_frame (numpy array): Frame with tracking info.
        """
        # Run tracking with Configured Confidence
        results = self.model.track(frame, classes=[0], persist=True, verbose=False, 
                                   tracker="bytetrack.yaml", conf=self.confidence_threshold)

        tracks = []
        annotated_frame = frame
        
        for result in results:
            annotated_frame = result.plot()
            if result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy().astype(int)
                ids = result.boxes.id.cpu().numpy().astype(int)
                
                for box, track_id in zip(boxes, ids):
                    x1, y1, x2, y2 = box
                    w = x2 - x1
                    h = y2 - y1
                    
                    # Filter small noise (must be at least 5% of frame width/height approx)
                    # Simple heuristic: ignore things smaller than 20x20 pixels
                    if w < 20 or h < 50: 
                        continue

                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    tracks.append({
                        'id': track_id,
                        'box': box,
                        'center': (center_x, center_y)
                    })
        
        return tracks, annotated_frame
