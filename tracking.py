from collections import deque
import numpy as np
from scipy.optimize import linear_sum_assignment

class Tracker:
    def __init__(self, distance_threshold=150, max_inactive=30, frame_rate=30.0, fov_horizontal=60.0, resolution=(1280, 720)):
        self.tracking_data = {}
        self.next_id = 1
        self.dist_thresh = distance_threshold
        self.max_inactive = max_inactive
        self.frame_rate = frame_rate
        self.fov_horizontal = fov_horizontal
        self.resolution = resolution
        self.pixel_to_meter = self._calibrate_pixel_to_meter()

    def _calibrate_pixel_to_meter(self):
        """Calibrate pixel-to-meter conversion based on FOV."""
        focal_length = self.resolution[0] / (2 * np.tan(np.radians(self.fov_horizontal / 2)))
        return focal_length / 255.0

    def assign_ids(self, detections, current_frame):
        """Assign IDs to detections and update tracking data."""
        self._clean_inactive(current_frame)
        
        if not self.tracking_data:
            for det in detections:
                tid = self.next_id
                det['id'] = tid
                self._init_track(det, current_frame)
                self.next_id += 1
            return

        cost = np.zeros((len(detections), len(self.tracking_data)))
        for i, det in enumerate(detections):
            for j, (tid, track) in enumerate(self.tracking_data.items()):
                cost[i, j] = self._calc_distance(det['center'], track['center'][-1])
        
        row_idx, col_idx = linear_sum_assignment(cost)
        
        assigned_dets = []
        for r, c in zip(row_idx, col_idx):
            if cost[r, c] < self.dist_thresh:
                tid = list(self.tracking_data.keys())[c]
                detections[r]['id'] = tid
                self._update_track(tid, detections[r], current_frame)
                assigned_dets.append(r)

        for i, det in enumerate(detections):
            if i not in assigned_dets:
                tid = self.next_id
                det['id'] = tid
                self._init_track(det, current_frame)
                self.next_id += 1

    def _calc_distance(self, p1, p2):
        """Calculate 3D Euclidean distance between two points."""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2)

    def _init_track(self, det, frame):
        """Initialize a new track."""
        area = (det['bbox'][2] - det['bbox'][0]) * (det['bbox'][3] - det['bbox'][1])
        self.tracking_data[det['id']] = {
            'type': det['type'],
            'bbox': det['bbox'],
            'center': deque([det['center']], maxlen=30),
            'area_history': deque([area], maxlen=5),
            'velocity': deque([0.0], maxlen=5),
            'smoothed_velocity': 0.0,
            'last_seen': frame,
            'state': 'IDLE'
        }
        if det['type'] == 'trash':
            self.tracking_data[det['id']]['trajectory'] = deque([det['center'][:2]], maxlen=10)

    def _estimate_distance_from_area(self, depth, area):
        """Estimate distance using depth and area."""
        base_area = 10000
        base_depth = 255.0
        distance = np.sqrt(base_area * (base_depth / depth) / area)
        return distance * self.pixel_to_meter

    def _triangulate_position(self, center, area):
        """Triangulate 3D position."""
        depth = center[2]
        estimated_distance = self._estimate_distance_from_area(depth, area)
        x = (center[0] - self.resolution[0] / 2) * estimated_distance / (self.resolution[0] / 2)
        y = (center[1] - self.resolution[1] / 2) * estimated_distance / (self.resolution[1] / 2)
        z = depth * self.pixel_to_meter
        return np.array([x, y, z])

    def _update_track(self, tid, det, frame):
        """Update track with refined velocity and smoothing."""
        track = self.tracking_data[tid]
        prev_center = track['center'][-1]
        current_center = det['center']
        
        track['bbox'] = det['bbox']
        track['center'].append(current_center)
        area = (det['bbox'][2] - det['bbox'][0]) * (det['bbox'][3] - det['bbox'][1])
        track['area_history'].append(area)
        track['last_seen'] = frame
        
        if track['type'] == 'trash':
            track['trajectory'].append(current_center[:2])
        
        if len(track['center']) > 1:
            prev_pos = self._triangulate_position(prev_center, track['area_history'][-2])
            curr_pos = self._triangulate_position(current_center, area)
            displacement = curr_pos - prev_pos
            raw_velocity = np.linalg.norm(displacement) * self.frame_rate
            if np.abs(raw_velocity) < 0.1:
                velocity = 0.0
            else:
                velocity = raw_velocity
            # Temporal smoothing
            alpha = 0.3
            track['smoothed_velocity'] = alpha * velocity + (1 - alpha) * track.get('smoothed_velocity', 0.0)
            track['velocity'].append(track['smoothed_velocity'])

    def _clean_inactive(self, current_frame):
        """Remove inactive tracks."""
        inactive = [tid for tid, data in self.tracking_data.items()
                    if current_frame - data['last_seen'] > self.max_inactive]
        for tid in inactive:
            del self.tracking_data[tid]