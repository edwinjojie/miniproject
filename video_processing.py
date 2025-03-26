# video_processing.py

import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque
from scipy.optimize import linear_sum_assignment
import json
import os
import logging
from filterpy.kalman import KalmanFilter

# Configure logging (WARNING for production, adjust to DEBUG for development)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Track:
    """Class to manage individual object tracks with Kalman filter prediction."""
    def __init__(self, track_id, class_id, bbox, center, frame):
        self.track_id = track_id
        self.class_id = class_id
        self.bbox = bbox
        self.center = center
        self.last_seen = frame
        self.kalman = self._init_kalman(center)
        self.position_history = deque(maxlen=10)  # Limit history to 10 frames

    def _init_kalman(self, center):
        """Initialize Kalman filter for motion prediction."""
        kf = KalmanFilter(dim_x=4, dim_z=2)  # State: [x, y, vx, vy], Measurement: [x, y]
        kf.x = np.array([center[0], center[1], 0, 0])  # Initial position, zero velocity
        kf.F = np.array([[1, 0, 1, 0],  # State transition: x' = x + vx, y' = y + vy
                         [0, 1, 0, 1],
                         [0, 0, 1, 0],
                         [0, 0, 0, 1]])
        kf.H = np.array([[1, 0, 0, 0],  # Measurement function: observe x, y
                         [0, 1, 0, 0]])
        kf.P *= 10  # Initial uncertainty
        kf.R = np.array([[5, 0], [0, 5]])  # Measurement noise
        kf.Q = np.eye(4) * 0.01  # Process noise
        return kf

    def predict(self):
        """Predict next position using Kalman filter."""
        self.kalman.predict()
        self.center = (int(self.kalman.x[0]), int(self.kalman.x[1]))

    def update(self, bbox, center, frame):
        """Update track with new detection."""
        self.bbox = bbox
        self.center = center
        self.last_seen = frame
        self.kalman.update(np.array([center[0], center[1]]))
        self.position_history.append(center)

class VideoProcessor:
    def __init__(self, model_path="./models/yolov8m.pt", trash_model_path="./models/yolov8n.pt", 
                 video_path="./videos/videoplayback.mp4", output_path="./data/frame_data.json",
                 distance_threshold=150, max_inactive_frames=90, frame_skip=1):
        """
        Initialize VideoProcessor with paths and tracking parameters.

        Args:
            model_path (str): Path to general YOLOv8 model.
            trash_model_path (str): Path to trash-specific YOLO model.
            video_path (str): Path to input video.
            output_path (str): Path for JSON output.
            distance_threshold (int): Max distance for track association.
            max_inactive_frames (int): Frames before a track is dropped.
            frame_skip (int): Process every nth frame (default: 1).
        """
        try:
            self.model = YOLO(model_path)
            self.trash_model = YOLO(trash_model_path)
        except Exception as e:
            logger.error(f"Failed to load YOLO models: {e}")
            raise ValueError(f"Failed to load YOLO models: {e}")

        self.video_path = video_path
        self.output_path = output_path
        self.distance_threshold = distance_threshold
        self.max_inactive_frames = max_inactive_frames
        self.frame_skip = frame_skip
        self.tracking_data = {}  # {track_id: Track}
        self.next_id = 1
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    def calculate_center(self, bbox):
        """Calculate bounding box center."""
        x1, y1, x2, y2 = bbox
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    def compute_distance(self, center1, center2):
        """Compute Euclidean distance between two points."""
        return np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)

    def load_video(self):
        """Load video file."""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video: {self.video_path}")
            raise ValueError(f"Failed to open video: {self.video_path}")
        return cap

    def detect_objects(self, frame):
        """Detect objects using YOLO models."""
        detections = []
        try:
            # General model: humans (0), vehicles (2, 7)
            results = self.model(frame, conf=0.5, iou=0.4)
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0].cpu().numpy())
                    if class_id in [0, 2, 7]:
                        bbox = box.xyxy[0].cpu().numpy()
                        detections.append({'bbox': bbox, 'class_id': class_id})

            # Trash model: trash (1)
            trash_results = self.trash_model(frame, conf=0.5, iou=0.4)
            for result in trash_results:
                for box in result.boxes:
                    if int(box.cls[0].cpu().numpy()) == 1:
                        bbox = box.xyxy[0].cpu().numpy()
                        detections.append({'bbox': bbox, 'class_id': 1})
        except Exception as e:
            logger.error(f"Detection error: {e}")
        return detections

    def track_objects(self, detections, current_frame):
        """Track objects with Kalman filter and Hungarian algorithm."""
        # Predict positions for existing tracks
        for track in self.tracking_data.values():
            track.predict()

        if not detections:
            return

        # Initialize tracks if none exist
        if not self.tracking_data:
            for det in detections:
                center = self.calculate_center(det['bbox'])
                self.tracking_data[self.next_id] = Track(self.next_id, det['class_id'], det['bbox'], center, current_frame)
                det['id'] = self.next_id
                self.next_id += 1
            return

        # Distance matrix: detections vs predicted track centers
        distance_matrix = np.array([
            [self.compute_distance(self.calculate_center(det['bbox']), track.center)
             for track in self.tracking_data.values()]
            for det in detections
        ])

        # Hungarian assignment
        row_ind, col_ind = linear_sum_assignment(distance_matrix)
        assigned_ids = set()

        for row, col in zip(row_ind, col_ind):
            if distance_matrix[row, col] < self.distance_threshold:
                det = detections[row]
                track_id = list(self.tracking_data.keys())[col]
                if track_id not in assigned_ids:
                    center = self.calculate_center(det['bbox'])
                    self.tracking_data[track_id].update(det['bbox'], center, current_frame)
                    det['id'] = track_id
                    assigned_ids.add(track_id)

        # New tracks for unassigned detections
        for det in detections:
            if 'id' not in det:
                center = self.calculate_center(det['bbox'])
                self.tracking_data[self.next_id] = Track(self.next_id, det['class_id'], det['bbox'], center, current_frame)
                det['id'] = self.next_id
                self.next_id += 1

        # Remove inactive tracks
        inactive = [tid for tid, track in self.tracking_data.items()
                    if current_frame - track.last_seen > self.max_inactive_frames]
        for tid in inactive:
            del self.tracking_data[tid]

    def process_video(self):
        """Process video and save frame data."""
        cap = self.load_video()
        frame_data = []
        current_frame = 0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if current_frame % self.frame_skip == 0:
                    detections = self.detect_objects(frame)
                    self.track_objects(detections, current_frame)
                    frame_data.append({
                        'frame_id': current_frame,
                        'detections': [
                            {
                                'id': det.get('id'),
                                'type': 'vehicle' if det['class_id'] in [2, 7] else 'trash' if det['class_id'] == 1 else 'human',
                                'position': self.calculate_center(det['bbox'])
                            } for det in detections
                        ]
                    })
                current_frame += 1

            with open(self.output_path, 'w') as f:
                json.dump(frame_data, f)
            logger.info(f"Saved frame data to {self.output_path}")

        except Exception as e:
            logger.error(f"Video processing error: {e}")
            raise
        finally:
            cap.release()

        return frame_data

if __name__ == "__main__":
    processor = VideoProcessor(
        video_path="./videos/videoplayback.mp4",
        frame_skip=2  # Process every 2nd frame for efficiency
    )
    frame_data = processor.process_video()
    print(f"Processed {len(frame_data)} frames.")