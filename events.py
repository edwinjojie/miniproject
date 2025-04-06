import numpy as np
from collections import deque
from datetime import datetime
import cv2

class EventDetector:
    def __init__(self, temporal_window=10, min_holding=15, min_disposal=20, min_throw=5, depth_threshold=50):
        """Initialize the EventDetector with event detection parameters."""
        self.events_data = []  # Moved here to reset per instance
        self.temporal_window = temporal_window
        self.min_holding = min_holding
        self.min_disposal = min_disposal
        self.min_throw = min_throw
        self.depth_threshold = depth_threshold  # Max allowable depth difference
        self.max_depth = 255  # Assuming normalized depth range 0-255 from MiDaS

    def process(self, tracking_data, detections, frame):
        """Process tracking data to detect disposal events."""
        for tid, track in list(tracking_data.items()):
            if track["type"] != "vehicle":
                continue
            self._init_track_buffers(track)
            trash_near, nearest_trash = self._check_trash_proximity(track, detections)
            track["proximity_buffer"].append(1 if trash_near else 0)
            track["throw_buffer"].append(1 if trash_near else 0)
            track["frames"].append(frame.copy())
            avg_vel = np.mean(track["velocity"]) if track["velocity"] else 0
            avg_area = np.mean(track["area_history"]) if track["area_history"] else 0
            stop_thresh, move_thresh = self._get_dynamic_thresholds(avg_area)
            self._update_vehicle_state(track, tid, avg_vel, stop_thresh, move_thresh, nearest_trash)

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
        """Check if trash is near the vehicle in 3D space."""
        nearest_trash = None
        min_distance = float('inf')
        vehicle_z = track["center"][-1][2]
        
        for det in detections:
            if det["class_id"] == 1:  # Trash
                distance = self._calc_distance(track["center"][-1], det["center"])
                trash_z = det["center"][2]
                depth_diff = abs(vehicle_z - trash_z)
                if distance < 150 and depth_diff < self.depth_threshold:
                    if distance < min_distance:
                        min_distance = distance
                        nearest_trash = det
        
        trash_near = nearest_trash is not None
        return trash_near, nearest_trash

    def _get_dynamic_thresholds(self, avg_area):
        """Get dynamic velocity thresholds based on vehicle size."""
        if avg_area > 100000:
            return 0.2, 1.0
        elif avg_area > 20000:
            return 0.4, 2.0
        else:
            return 0.8, 4.0

    def _update_vehicle_state(self, track, tid, avg_vel, stop_thresh, move_thresh, nearest_trash):
        """Update vehicle state based on velocity and trash proximity."""
        is_stopped = avg_vel < stop_thresh
        is_moving = avg_vel >= move_thresh
        is_slowed = not is_stopped and not is_moving
        if track["state"] == "IDLE":
            if is_stopped and sum(track["proximity_buffer"]) >= self.min_holding:
                track["state"] = "STOPPED_UNLOADING"
                track["disposal_location"] = track["center"][-1]
            elif is_slowed and sum(track["throw_buffer"]) >= self.min_throw:
                track["state"] = "SLOWING_THROW"
                track["disposal_location"] = track["center"][-1]
        elif track["state"] in ["STOPPED_UNLOADING", "SLOWING_THROW"]:
            if track["proximity_buffer"][-1]:
                track["no_trash_count"] = 0
                if nearest_trash and "trajectory" in nearest_trash and len(nearest_trash["trajectory"]) > 3:
                    if self._detect_throwing_motion(track, nearest_trash):
                        track["state"] = "POTENTIAL_THROW"
                        self._record_event(tid, track, "THROW_DETECTED")
            else:
                track["no_trash_count"] += 1
                if track["no_trash_count"] >= self.min_disposal and is_moving:
                    event_type = "STOPPED_DISPOSAL" if track["state"] == "STOPPED_UNLOADING" else "MOVING_THROW"
                    self._record_event(tid, track, event_type)
                    track["state"] = "TRASH_DISPOSED"

    def _detect_throwing_motion(self, track, trash):
        """Detect if trash exhibits throwing motion relative to the vehicle."""
        if len(trash.get("trajectory", [])) < 4:
            return False
        points = np.array(trash["trajectory"][-4:])
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
            "velocity": np.mean(track["velocity"]) if track["velocity"] else 0,
            "frames": list(track["frames"]),
            "state": track["state"]
        }
        self.events_data.append(event)  # Append to instance-specific list
        # No file logging here; handled by API
