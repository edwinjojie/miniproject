import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict
from detection_validator import DetectionValidator
import torch

class Detector:
    def __init__(self, vehicle_model_path, trash_model_path, confirmation_threshold=3, disposal_confirmation_threshold=3):
        """Initialize with vehicle and trash YOLO models and confirmation thresholds."""
        self.vehicle_model = YOLO(vehicle_model_path)
        self.trash_model = YOLO(trash_model_path)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.prev_frame = None
        self.trash_confirmation_threshold = confirmation_threshold  # Frames to confirm trash
        self.disposal_confirmation_threshold = disposal_confirmation_threshold  # Events to confirm disposal
        self.trash_sightings = defaultdict(int)  # Track sightings of potential trash
        self.disposal_sightings = defaultdict(int)  # Track potential disposal events
        self.video_writer = None  # For saving cropped clips
        self.frame_buffer = []  # Buffer to store frames for clips

        # Initialize detection validator
        self.validator = DetectionValidator()
        print("[VALIDATOR] Detection validator initialized")

    def detect(self, frame, prev_frame=None, flow=None, frame_count=0):
        """
        Run detection with initial validation filters.
        
        Args:
            frame: Current frame
            prev_frame: Previous frame for optical flow
            flow: Pre-computed optical flow (optional)
            frame_count: Current frame number
        
        Returns:
            tuple: (all_detections, vehicle_detections_only)
        """
        detections = []
        vehicle_detections = []
        
        # === STEP 1: RUN YOLO MODELS ===
        vehicle_results = self.vehicle_model(frame, conf=0.3, classes=[2, 3, 4, 6, 8], imgsz=640, device=self.device)
        trash_results = self.trash_model(frame, conf=0.2, classes=[0, 1, 2], imgsz=640, device=self.device)
        bin_results = self.trash_model(frame, conf=0.3, classes=[3], imgsz=640, device=self.device)
        
        # === STEP 2: PROCESS VEHICLE DETECTIONS (needed first for validation) ===
        for r in vehicle_results:
            boxes = r.boxes
            for box in boxes:
                bbox = box.xyxy[0].cpu().numpy().astype(int).tolist()
                x1, y1, x2, y2 = bbox
                center = ((x1 + x2) / 2, (y1 + y2) / 2)
                
                vehicle_det = {
                    'bbox': bbox,
                    'center': center,
                    'confidence': float(box.conf[0]),
                    'class': int(box.cls[0]),
                    'type': 'vehicle',
                    'id': None  # Will be assigned by tracker
                }
                
                vehicle_detections.append(vehicle_det)
                detections.append(vehicle_det)
        
        # === STEP 3: PROCESS TRASH DETECTIONS WITH INITIAL VALIDATION ===
        initial_trash_count = 0
        passed_physical = 0
        passed_overlap = 0
        
        for r in trash_results:
            boxes = r.boxes
            for box in boxes:
                initial_trash_count += 1
                bbox = box.xyxy[0].cpu().numpy().astype(int).tolist()
                x1, y1, x2, y2 = bbox
                center = ((x1 + x2) / 2, (y1 + y2) / 2)
                
                trash_det = {
                    'bbox': bbox,
                    'center': center,
                    'confidence': float(box.conf[0]),
                    'class': int(box.cls[0]),
                    'type': 'trash',
                    'id': None,  # Will be assigned by tracker
                    'status': 'potential'  # Will be updated by validator
                }
                
                # LAYER 1: Physical constraints check
                is_valid, reason = self.validator._check_physical_constraints(
                    trash_det['bbox'], trash_det
                )
                
                if not is_valid:
                    print(f"[FILTER-PHYSICAL] Frame {frame_count}: {reason}")
                    continue
                
                passed_physical += 1
                
                # LAYER 2: Vehicle overlap check
                is_valid, reason = self.validator._check_vehicle_overlap(
                    trash_det['bbox'], vehicle_detections
                )
                
                if not is_valid:
                    print(f"[FILTER-OVERLAP] Frame {frame_count}: {reason}")
                    continue
                
                passed_overlap += 1
                
                # Passed initial validation - add to detections
                detections.append(trash_det)
        
        # Log filtering stats
        if initial_trash_count > 0:
            print(f"[FILTER-STATS] Frame {frame_count}: "
                  f"{initial_trash_count} raw trash detections -> "
                  f"{passed_physical} passed physical -> "
                  f"{passed_overlap} passed overlap -> "
                  f"{passed_overlap} sent to tracking")
        
        # === STEP 4: PROCESS BIN DETECTIONS ===
        for r in bin_results:
            boxes = r.boxes
            for box in boxes:
                bbox = box.xyxy[0].cpu().numpy().astype(int).tolist()
                x1, y1, x2, y2 = bbox
                center = ((x1 + x2) / 2, (y1 + y2) / 2)
                
                detections.append({
                    'bbox': bbox,
                    'center': center,
                    'confidence': float(box.conf[0]),
                    'class': int(box.cls[0]),
                    'type': 'bin'
                })
        
        # === STEP 5: COMPUTE VELOCITIES (if flow available) ===
        if flow is not None:
            for det in detections:
                if det['type'] == 'vehicle':
                    bbox = det['bbox']
                    x1, y1, x2, y2 = bbox
                    
                    # Extract flow in bbox region
                    flow_region = flow[y1:y2, x1:x2]
                    if flow_region.size > 0:
                        # Calculate mean flow magnitude
                        magnitude = np.sqrt(flow_region[..., 0]**2 + flow_region[..., 1]**2)
                        det['velocity'] = float(np.mean(magnitude))
                    else:
                        det['velocity'] = 0.0
                else:
                    det['velocity'] = 0.0
        
        return detections, vehicle_detections

    def _estimate_velocity(self, bbox, frame):
        """Estimate object velocity using optical flow."""
        if self.prev_frame is None:
            return 0.0
        # Guard against shape mismatch between previous and current frame
        if self.prev_frame.shape != frame.shape:
            self.prev_frame = frame.copy()
            return 0.0
        prev_gray = cv2.cvtColor(self.prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        try:
            flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        except cv2.error:
            return 0.0
        x1, y1, x2, y2 = map(int, bbox)
        flow_region = flow[y1:y2, x1:x2]
        mag, _ = cv2.cartToPolar(flow_region[..., 0], flow_region[..., 1])
        return np.mean(mag) if mag.size > 0 else 0.0

    def compute_optical_flow(self, frame):
        """Compute optical flow for motion analysis."""
        if self.prev_frame is None:
            self.prev_frame = frame.copy()
            return None, None
        # Guard against shape mismatch
        if self.prev_frame.shape != frame.shape:
            self.prev_frame = frame.copy()
            return None, None
        prev_gray = cv2.cvtColor(cv2.GaussianBlur(self.prev_frame, (5, 5), 0), cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(cv2.GaussianBlur(frame, (5, 5), 0), cv2.COLOR_BGR2GRAY)
        try:
            flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        except cv2.error:
            self.prev_frame = frame.copy()
            return None, None
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        mag = cv2.medianBlur(mag, 3)
        self.prev_frame = frame.copy()
        return flow, mag

    def detect_disposal_motion(self, frame, detections, flow, tracking_data):
        """Detect and confirm disposal events, saving cropped video clips."""
        disposal_events = []
        if flow is None:
            return disposal_events

        vehicle_centers = {tid: track['center'] for tid, track in tracking_data.items() if track['type'] == 'vehicle'}
        for trash in [d for d in detections if d['type'] == 'trash' and d['context'] == 'improper']:
            tx, ty = map(int, trash['center'])
            if not (0 <= ty < flow.shape[0] and 0 <= tx < flow.shape[1]):
                continue
            flow_u, flow_v = flow[ty, tx]
            mag = np.sqrt(flow_u**2 + flow_v**2)
            if mag < 2.0:  # Threshold for significant motion
                continue

            # Check for outward motion from any vehicle
            for tid, vehicle_center in vehicle_centers.items():
                dx, dy = tx - vehicle_center[0], ty - vehicle_center[1]
                dot_product = flow_u * dx + flow_v * dy
                if dot_product > 0:  # Outward motion detected
                    event_key = (tuple(trash['center']), tid)  # Unique key for disposal event
                    event_type = 'potential_disposal'
                    if trash['status'] == 'confirmed':
                        self.disposal_sightings[event_key] += 1
                        if self.disposal_sightings[event_key] >= self.disposal_confirmation_threshold:
                            event_type = 'confirmed_disposal'

                    # Create disposal event
                    disposal_event = {
                        'type': event_type,
                        'trash_center': trash['center'],
                        'vehicle_id': tid,
                        'magnitude': mag,
                        'confidence': trash['confidence'],
                        'review_needed': event_type == 'potential_disposal'
                    }
                    disposal_events.append(disposal_event)

                    # Save cropped video clip
                    self._save_cropped_clip(frame, trash['bbox'], event_type, trash)
                    break

        return disposal_events

    def _save_cropped_clip(self, frame, bbox, event_type, trash):
        """Save a cropped video clip of the disposal incident."""
        x1, y1, x2, y2 = map(int, bbox)
        margin = 50  # Add margin around the detection
        x1, y1 = max(0, x1 - margin), max(0, y1 - margin)
        x2, y2 = min(frame.shape[1], x2 + margin), min(frame.shape[0], y2 + margin)
        cropped_frame = frame[y1:y2, x1:x2]

        # Buffer frames (e.g., 30 frames for a short clip)
        self.frame_buffer.append(cropped_frame)
        if len(self.frame_buffer) > 30:
            self.frame_buffer.pop(0)

        # Initialize video writer if a disposal event is detected
        if self.video_writer is None and len(self.frame_buffer) >= 10:  # Minimum frames to start clip
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            filename = f"{event_type}_{int(trash['center'][0])}_{int(trash['center'][1])}.mp4"
            self.video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (x2 - x1, y2 - y1))

        # Write buffered and current frames to video
        if self.video_writer is not None:
            for buffered_frame in self.frame_buffer[:-1]:
                self.video_writer.write(buffered_frame)
            self.video_writer.write(cropped_frame)

        # Stop writing after a certain number of frames (e.g., 30) and reset
        if len(self.frame_buffer) == 30:
            self.video_writer.release()
            self.video_writer = None
            self.frame_buffer = []

    def _calc_distance(self, p1, p2):
        """Calculate Euclidean distance between two points."""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
