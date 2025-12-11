import numpy as np
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional
import cv2

class DetectionValidator:
    """
    Multi-layer validation system to filter false positive trash detections.
    Designed to reject vehicles/humans misclassified as trash.
    """
    
    def __init__(self):
        # Track history for temporal analysis (keyed by track_id)
        self.track_histories = defaultdict(lambda: {
            'positions': deque(maxlen=15),
            'sizes': deque(maxlen=15),
            'confidences': deque(maxlen=15),
            'velocities': deque(maxlen=10),
            'first_seen': None,
            'frames_seen': 0,
            'frames_stationary': 0,
            'state': 'POTENTIAL',  # POTENTIAL -> SUSPICIOUS -> CONFIRMED
            'rejection_reasons': []
        })
        
        # Physical constraints (tunable)
        self.min_trash_size = 5      # pixels
        self.max_trash_size = 200    # pixels (anything larger is likely vehicle/human)
        self.trash_aspect_ratio_range = (0.2, 5.0)  # width/height ratio
        
        # Motion thresholds
        self.stationary_threshold = 5    # px/frame - trash should stop moving
        self.smooth_motion_threshold = 0.3  # velocity variance - vehicles move smoothly
        
        # Confirmation requirements
        self.suspicious_frames = 5   # frames to reach SUSPICIOUS
        self.confirmed_frames = 10   # frames to reach CONFIRMED
        
    def validate_detection(
        self, 
        detection: Dict,
        vehicle_detections: List[Dict],
        frame_count: int,
        flow: Optional[np.ndarray] = None,
        depth_map: Optional[np.ndarray] = None
    ) -> Tuple[bool, str, str]:
        """
        Validate if a detection is truly trash or a false positive.
        
        Returns:
            (is_valid, state, reason)
            - is_valid: True if detection passes validation
            - state: 'POTENTIAL', 'SUSPICIOUS', 'CONFIRMED', or 'REJECTED'
            - reason: explanation for decision
        """
        track_id = detection.get('id', None)
        if track_id is None:
            return False, 'REJECTED', 'No track ID assigned'
        
        bbox = detection['bbox']
        center = detection.get('center', self._bbox_center(bbox))
        confidence = detection.get('confidence', 0.5)
        
        # === LAYER 1: PHYSICAL PLAUSIBILITY ===
        valid, reason = self._check_physical_constraints(bbox, detection)
        if not valid:
            self.track_histories[track_id]['rejection_reasons'].append(reason)
            return False, 'REJECTED', reason
        
        # === LAYER 2: CROSS-MODEL CONFLICT RESOLUTION ===
        valid, reason = self._check_vehicle_overlap(bbox, vehicle_detections)
        if not valid:
            self.track_histories[track_id]['rejection_reasons'].append(reason)
            return False, 'REJECTED', reason
        
        # === LAYER 3: TEMPORAL STABILITY ANALYSIS ===
        self._update_track_history(track_id, center, bbox, confidence, frame_count)
        state, reason = self._evaluate_track_state(track_id, flow, depth_map)
        
        # Only accept CONFIRMED detections for downstream processing
        if state == 'CONFIRMED':
            return True, state, reason
        elif state == 'SUSPICIOUS':
            return False, state, reason  # Not ready yet, keep tracking
        else:
            return False, state, reason  # Still POTENTIAL or REJECTED
    
    def _check_physical_constraints(self, bbox: List[int], detection: Dict) -> Tuple[bool, str]:
        """Layer 1: Size and aspect ratio sanity checks"""
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        area = width * height
        
        # Size filter
        if area < self.min_trash_size:
            return False, f"Too small ({area}px) - likely noise"
        
        if area > self.max_trash_size ** 2:
            return False, f"Too large ({area}px) - likely vehicle/human"
        
        # Aspect ratio filter
        if height == 0:
            return False, "Invalid bbox (height=0)"
        
        aspect_ratio = width / height
        min_ar, max_ar = self.trash_aspect_ratio_range
        
        # Reject human-like vertical shapes (tall and narrow)
        if aspect_ratio < 0.4 and height > 80:
            return False, f"Human-like aspect ratio ({aspect_ratio:.2f}) with height {height}px"
        
        # Reject vehicle-like horizontal shapes (wide and flat)
        if aspect_ratio > 3.5 and width > 100:
            return False, f"Vehicle-like aspect ratio ({aspect_ratio:.2f}) with width {width}px"
        
        if not (min_ar <= aspect_ratio <= max_ar):
            return False, f"Aspect ratio {aspect_ratio:.2f} outside trash range [{min_ar}, {max_ar}]"
        
        return True, "Physical constraints passed"
    
    def _check_vehicle_overlap(self, trash_bbox: List[int], vehicle_detections: List[Dict]) -> Tuple[bool, str]:
        """Layer 2: Check if trash overlaps with vehicles/humans"""
        if not vehicle_detections:
            return True, "No vehicles to check"
        
        tx1, ty1, tx2, ty2 = trash_bbox
        trash_area = (tx2 - tx1) * (ty2 - ty1)
        
        for vehicle in vehicle_detections:
            vx1, vy1, vx2, vy2 = vehicle['bbox']
            
            # Compute intersection
            ix1 = max(tx1, vx1)
            iy1 = max(ty1, vy1)
            ix2 = min(tx2, vx2)
            iy2 = min(ty2, vy2)
            
            if ix1 < ix2 and iy1 < iy2:
                intersection = (ix2 - ix1) * (iy2 - iy1)
                iou = intersection / trash_area if trash_area > 0 else 0
                
                # High overlap = likely part of the vehicle
                if iou > 0.3:
                    return False, f"Overlaps vehicle by {iou*100:.1f}% - likely vehicle part misclassified"
                
                # Medium overlap near vehicle = suspicious
                if iou > 0.15:
                    vehicle_conf = vehicle.get('confidence', 0)
                    
                    # If vehicle confidence is lower, might be vehicle misdetected as trash
                    if vehicle_conf < 0.4:
                        return False, f"Overlaps low-confidence vehicle - likely misclassification"
        
        return True, "No vehicle conflicts"
    
    def _update_track_history(self, track_id: int, center: Tuple, bbox: List[int], confidence: float, frame_count: int):
        """Update tracking history for temporal analysis"""
        history = self.track_histories[track_id]
        
        if history['first_seen'] is None:
            history['first_seen'] = frame_count
        
        history['positions'].append(center)
        history['sizes'].append((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
        history['confidences'].append(confidence)
        history['frames_seen'] += 1
        
        # Calculate velocity if we have previous position
        if len(history['positions']) >= 2:
            prev_pos = history['positions'][-2]
            curr_pos = history['positions'][-1]
            velocity = np.sqrt((curr_pos[0] - prev_pos[0])**2 + (curr_pos[1] - prev_pos[1])**2)
            history['velocities'].append(velocity)
            
            # Count stationary frames
            if velocity < self.stationary_threshold:
                history['frames_stationary'] += 1
    
    def _evaluate_track_state(self, track_id: int, flow: Optional[np.ndarray], depth_map: Optional[np.ndarray]) -> Tuple[str, str]:
        """Layer 3: Evaluate track progression through state machine"""
        history = self.track_histories[track_id]
        
        # Not enough data yet
        if history['frames_seen'] < 3:
            return 'POTENTIAL', 'Insufficient tracking data'
        
        # === Motion Pattern Analysis ===
        velocities = list(history['velocities'])
        if len(velocities) >= 5:
            # Check for smooth, sustained motion (characteristic of vehicles/humans)
            velocity_variance = np.var(velocities[-5:])
            mean_velocity = np.mean(velocities[-5:])
            
            # Vehicles move smoothly at sustained speeds
            if mean_velocity > 15 and velocity_variance < self.smooth_motion_threshold * mean_velocity:
                return 'REJECTED', f"Smooth sustained motion (v={mean_velocity:.1f}, var={velocity_variance:.2f}) - likely vehicle/human"
            
            # Humans have periodic gait patterns (medium speed, medium variance)
            if 5 < mean_velocity < 20 and velocity_variance > 2:
                return 'REJECTED', f"Periodic motion pattern (v={mean_velocity:.1f}) - likely pedestrian"
        
        # === Size Stability ===
        sizes = list(history['sizes'])
        if len(sizes) >= 5:
            size_variance = np.var(sizes[-5:])
            mean_size = np.mean(sizes[-5:])
            size_cv = size_variance / mean_size if mean_size > 0 else 0
            
            # Objects changing size rapidly are moving toward/away from camera
            if size_cv > 0.3:
                return 'REJECTED', f"Rapidly changing size (CV={size_cv:.2f}) - likely moving object"
        
        # === Position Stability ===
        positions = list(history['positions'])
        if len(positions) >= 5:
            position_variance = np.var([p[0] for p in positions[-5:]]) + np.var([p[1] for p in positions[-5:]])
            
            # Trash should become stationary after appearing
            if history['frames_seen'] > 10 and position_variance > 100:
                return 'REJECTED', f"Never settled (pos_var={position_variance:.1f}) - not stationary trash"
        
        # === State Progression ===
        frames_seen = history['frames_seen']
        frames_stationary = history['frames_stationary']
        
        # POTENTIAL -> SUSPICIOUS: seen consistently, starting to settle
        if history['state'] == 'POTENTIAL':
            if frames_seen >= self.suspicious_frames and frames_stationary >= 2:
                history['state'] = 'SUSPICIOUS'
                return 'SUSPICIOUS', f"Tracked for {frames_seen} frames, stationary for {frames_stationary}"
            return 'POTENTIAL', f"Building confidence ({frames_seen}/{self.suspicious_frames} frames)"
        
        # SUSPICIOUS -> CONFIRMED: sustained presence, mostly stationary
        if history['state'] == 'SUSPICIOUS':
            if frames_seen >= self.confirmed_frames and frames_stationary >= 6:
                history['state'] = 'CONFIRMED'
                return 'CONFIRMED', f"Confirmed trash: {frames_seen} frames, {frames_stationary} stationary"
            return 'SUSPICIOUS', f"Validating ({frames_seen}/{self.confirmed_frames} frames, {frames_stationary} stationary)"
        
        # Already confirmed
        return 'CONFIRMED', "Previously confirmed"
    
    def _bbox_center(self, bbox: List[int]) -> Tuple[float, float]:
        """Calculate bbox center"""
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def get_track_summary(self, track_id: int) -> Dict:
        """Get summary of track for debugging"""
        if track_id not in self.track_histories:
            return {}
        
        history = self.track_histories[track_id]
        return {
            'state': history['state'],
            'frames_seen': history['frames_seen'],
            'frames_stationary': history['frames_stationary'],
            'mean_velocity': np.mean(history['velocities']) if history['velocities'] else 0,
            'rejection_reasons': history['rejection_reasons']
        }
    
    def cleanup_old_tracks(self, active_track_ids: List[int], max_age: int = 30):
        """Remove tracks that are no longer active"""
        current_tracks = set(self.track_histories.keys())
        active_set = set(active_track_ids)
        
        for track_id in current_tracks - active_set:
            # Keep track if recently seen
            if self.track_histories[track_id]['frames_seen'] < max_age:
                continue
            del self.track_histories[track_id]
