from collections import deque
import numpy as np
from scipy.optimize import linear_sum_assignment

class Tracker:
    def __init__(self, distance_threshold=150, max_inactive=30):
        self.tracking_data = {}
        self.next_id = 1
        self.dist_thresh = distance_threshold
        self.max_inactive = max_inactive

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
        self.tracking_data[det['id']] = {
            'type': det['type'],
            'bbox': det['bbox'],
            'center': deque([det['center']], maxlen=30),  # Expecting [x, y, z]
            'area_history': deque([(det['bbox'][2] - det['bbox'][0]) * (det['bbox'][3] - det['bbox'][1])], maxlen=5),
            'velocity': deque([0], maxlen=5),
            'last_seen': frame,
            'state': 'IDLE'
        }

    def _update_track(self, tid, det, frame):
        track = self.tracking_data[tid]
        prev_center = track['center'][-1] if track['center'] else det['center']
        
        track['bbox'] = det['bbox']
        track['center'].append(det['center'])
        area = (det['bbox'][2] - det['bbox'][0]) * (det['bbox'][3] - det['bbox'][1])
        track['area_history'].append(area)
        track['last_seen'] = frame
        
        if len(track['center']) > 1:
            dx = track['center'][-1][0] - prev_center[0]
            dy = track['center'][-1][1] - prev_center[1]
            dz = track['center'][-1][2] - prev_center[2]
            velocity = np.sqrt(dx**2 + dy**2 + dz**2)
            norm_velocity = velocity / (np.mean(track['area_history'])**0.25)
            track['velocity'].append(norm_velocity)

    def _clean_inactive(self, current_frame):
        inactive = [tid for tid, data in self.tracking_data.items()
                    if current_frame - data['last_seen'] > self.max_inactive]
        for tid in inactive:
            del self.tracking_data[tid]