import cv2
import numpy as np
from collections import deque

class Tracker:
    def __init__(self, max_age=10, min_hits=3, iou_threshold=0.3):
        """Initialize tracker with SORT parameters."""
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracking_data = {}
        self.next_id = 0
        self.velocity_thresholds = {'slowing': 5.0, 'stopped': 1.0}

    def assign_ids(self, detections):
        """Assign tracking IDs to detections and update tracks."""
        updated_tracks = {}
        matched_ids = set()

        for det in detections:
            best_id, best_iou = None, -1
            det_bbox = det['bbox']
            for tid, track in self.tracking_data.items():
                if tid in matched_ids:
                    continue
                track_bbox = track['bbox'][-1]
                iou = self._compute_iou(det_bbox, track_bbox)
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_id = tid

            if best_id is not None:
                self._update_track(best_id, det)
                updated_tracks[best_id] = self.tracking_data[best_id]
                matched_ids.add(best_id)
            else:
                new_id = self.next_id
                self._init_track(new_id, det)
                updated_tracks[new_id] = self.tracking_data[new_id]
                self.next_id += 1

        self.tracking_data = {tid: track for tid, track in updated_tracks.items()
                              if len(track['bbox']) < self.max_age or tid in matched_ids}
        return self.tracking_data

    def _init_track(self, tid, det):
        """Initialize a new track."""
        self.tracking_data[tid] = {
            'bbox': deque([det['bbox']], maxlen=self.max_age),
            'center': deque([det['center']], maxlen=self.max_age),
            'velocity': deque([det.get('velocity', 0.0)], maxlen=self.max_age),  # Default to 0.0 if missing
            'type': det['type'],
            'state': deque(['moving'], maxlen=self.max_age)
        }
        if det['type'] == 'trash':
            self.tracking_data[tid]['status'] = det.get('status', 'potential')
            self.tracking_data[tid]['depth_history'] = deque(maxlen=10)

    def _update_track(self, tid, det):
        """Update an existing track."""
        track = self.tracking_data[tid]
        track['bbox'].append(det['bbox'])
        track['center'].append(det['center'])
        track['velocity'].append(det.get('velocity', 0.0))  # Default to 0.0 if missing
        if det['type'] == 'trash':
            track['status'] = det.get('status', 'potential')
        velocity = det.get('velocity', 0.0)
        state = 'moving'
        if velocity < self.velocity_thresholds['stopped']:
            state = 'stopped'
        elif velocity < self.velocity_thresholds['slowing']:
            state = 'slowing'
        track['state'].append(state)

    def _compute_iou(self, bbox1, bbox2):
        """Compute Intersection over Union between two bounding boxes."""
        x1, y1, x2, y2 = bbox1
        tx1, ty1, tx2, ty2 = bbox2
        xi1, yi1 = max(x1, tx1), max(y1, ty1)
        xi2, yi2 = min(x2, tx2), min(y2, ty2)
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        bbox1_area = (x2 - x1) * (y2 - y1)
        bbox2_area = (tx2 - tx1) * (ty2 - ty1)
        union_area = bbox1_area + bbox2_area - inter_area
        return inter_area / union_area if union_area > 0 else 0