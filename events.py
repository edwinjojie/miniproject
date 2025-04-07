import numpy as np
from collections import deque
from datetime import datetime
import cv2
from scipy.optimize import linear_sum_assignment

class EventDetector:
    def __init__(self, temporal_window=10, min_holding=15, min_disposal=20, min_throw=5, depth_threshold=50):
        """Initialize the EventDetector with event detection parameters."""
        self.events_data = []
        self.temporal_window = temporal_window
        self.min_holding = min_holding
        self.min_disposal = min_disposal
        self.min_throw = min_throw
        self.depth_threshold = depth_threshold
        self.max_depth = 255

    def process(self, tracking_data, detections, frame, flow=None):
        """Process tracking data to detect disposal events with improved association."""
        vehicle_tracks = {tid: t for tid, t in tracking_data.items() if t["type"] == "vehicle"}
        trash_detections = [d for d in detections if d["class_id"] == 1]
        
        # Feature 3: Improved Trash-Vehicle Association
        if vehicle_tracks and trash_detections:
            cost_matrix = np.zeros((len(trash_detections), len(vehicle_tracks)))
            for i, trash in enumerate(trash_detections):
                for j, (tid, vehicle) in enumerate(vehicle_tracks.items()):
                    cost_matrix[i, j] = self._calc_distance(trash["center"], vehicle["center"][-1])
            row_idx, col_idx = linear_sum_assignment(cost_matrix)
            for r, c in zip(row_idx, col_idx):
                if cost_matrix[r, c] < 150:
                    trash_detections[r]["assigned_vehicle"] = list(vehicle_tracks.keys())[c]
        
        # Feature 4: Update trash depth history
        for det in trash_detections:
            det["depth_history"].append(det["center"][2])
            if "trajectory" not in det:
                det["trajectory"] = deque(maxlen=10)
            det["trajectory"].append(det["center"][:2])
        
        for tid, track in vehicle_tracks.items():
            self._init_track_buffers(track)
            trash_near, nearest_trash = self._check_trash_proximity(track, trash_detections)
            track["proximity_buffer"].append(1 if trash_near else 0)
            track["throw_buffer"].append(1 if trash_near else 0)
            track["frames"].append(frame.copy())
            avg_vel = track.get('smoothed_velocity', 0)
            avg_area = np.mean(track["area_history"]) if track["area_history"] else 0
            stop_thresh, move_thresh = self._get_dynamic_thresholds(avg_area)
            self._update_vehicle_state(track, tid, avg_vel, stop_thresh, move_thresh, nearest_trash, flow)

    def _init_track_buffers(self, track):
        """Initialize buffers for tracking state and frames."""
        if "proximity_buffer" not in track:
            track.update({
                "proximity_buffer": deque([0] * self.temporal_window, maxlen=self.temporal_window),
                "throw_buffer": deque([0] * self.min_throw, maxlen=self.min_throw),
                "frames": deque(maxlen=30),
                "state": "IDLE",
                "no_trash_count": 0,
                "disposal_location": None
            })

    def _check_trash_proximity(self, track, detections):
        """Check if trash is near the vehicle with adaptive threshold."""
        nearest_trash = None
        min_distance = float('inf')
        vehicle_z = track["center"][-1][2]
        vehicle_area = (track['bbox'][2] - track['bbox'][0]) * (track['bbox'][3] - track['bbox'][1])
        adaptive_threshold = 150 * (vehicle_area / 100000) ** 0.5
        
        for det in detections:
            if det["class_id"] == 1 and (not det.get("assigned_vehicle") or det["assigned_vehicle"] == track.get("id")):
                distance = self._calc_distance(track["center"][-1], det["center"])
                trash_z = det["center"][2]
                depth_diff = abs(vehicle_z - trash_z)
                if distance < adaptive_threshold and depth_diff < self.depth_threshold:
                    if distance < min_distance:
                        min_distance = distance
                        nearest_trash = det
        return nearest_trash is not None, nearest_trash

    def _get_dynamic_thresholds(self, avg_area):
        """Get dynamic velocity thresholds based on vehicle size."""
        if avg_area > 100000:
            return 0.2, 1.0
        elif avg_area > 20000:
            return 0.4, 2.0
        else:
            return 0.8, 4.0

    def _analyze_velocity_trend(self, track):
        """Analyze velocity trend for behavior analysis."""
        if len(track["velocity"]) > 5:
            recent_velocities = list(track["velocity"])[-5:]
            return np.mean(np.diff(recent_velocities))
        return 0

    def _detect_disposal(self, trash):
        """Detect disposal based on depth change."""
        if len(trash["depth_history"]) > 3:
            depth_change = trash["depth_history"][-1] - trash["depth_history"][-3]
            return depth_change > 20
        return False

    def _update_vehicle_state(self, track, tid, avg_vel, stop_thresh, move_thresh, nearest_trash, flow):
        """Update vehicle state with enhanced analysis."""
        is_stopped = avg_vel < stop_thresh
        is_moving = avg_vel >= move_thresh
        is_slowed = not is_stopped and not is_moving
        velocity_trend = self._analyze_velocity_trend(track)
        
        if track["state"] == "IDLE":
            if is_stopped and sum(track["proximity_buffer"]) >= self.min_holding:
                track["state"] = "STOPPED_UNLOADING"
                track["disposal_location"] = track["center"][-1]
            elif is_slowed and sum(track["throw_buffer"]) >= self.min_throw:
                track["state"] = "SLOWING_THROW"
                track["disposal_location"] = track["center"][-1]
            elif velocity_trend < -0.1 and is_slowed and nearest_trash:
                track["state"] = "DECELERATING_NEAR_TRASH"
        elif track["state"] in ["STOPPED_UNLOADING", "SLOWING_THROW", "DECELERATING_NEAR_TRASH"]:
            if track["proximity_buffer"][-1]:
                track["no_trash_count"] = 0
                disposal_confirmed = nearest_trash and self._detect_disposal(nearest_trash)
                if nearest_trash and len(nearest_trash["trajectory"]) > 3:
                    if self._detect_throwing_motion(track, nearest_trash):
                        track["state"] = "POTENTIAL_THROW"
                        self._record_event(tid, track, "THROW_DETECTED")
                elif disposal_confirmed:
                    track["state"] = "TRASH_DISPOSED"
                    self._record_event(tid, track, "DEPTH_CONFIRMED_DISPOSAL")
                elif flow is not None and nearest_trash:
                    x, y = map(int, nearest_trash["center"][:2])
                    flow_region = flow[max(0, y-10):min(flow.shape[0], y+10), max(0, x-10):min(flow.shape[1], x+10)]
                    mag, _ = cv2.cartToPolar(flow_region[..., 0], flow_region[..., 1])
                    if np.mean(mag) > 1.0:
                        track["state"] = "POTENTIAL_THROW"
                        self._record_event(tid, track, "FLOW_DETECTED_THROW")
            else:
                track["no_trash_count"] += 1
                if track["no_trash_count"] >= self.min_disposal and is_moving:
                    event_type = "STOPPED_DISPOSAL" if track["state"] == "STOPPED_UNLOADING" else "MOVING_THROW"
                    self._record_event(tid, track, event_type)
                    track["state"] = "TRASH_DISPOSED"

    def _detect_throwing_motion(self, track, trash):
        """Detect if trash exhibits throwing motion."""
        if len(trash["trajectory"]) < 4:
            return False
        points = np.array(list(trash["trajectory"])[-4:])
        movement = points[-1] - points[0]
        vehicle_pos = np.array(track["center"][-1][:2])
        trash_pos = np.array(trash["center"][:2])
        direction = trash_pos - vehicle_pos
        return np.dot(movement, direction) > 0

    def _calc_distance(self, p1, p2):
        """Calculate 3D Euclidean distance between two points."""
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    def _record_event(self, tid, track, event_type):
        """Record a detected event."""
        event = {
            "timestamp": datetime.now(),
            "vehicle_id": tid,
            "event_type": event_type,
            "location": track["disposal_location"],
            "velocity": track.get('smoothed_velocity', 0),
            "frames": list(track["frames"]),
            "state": track["state"]
        }
        self.events_data.append(event)