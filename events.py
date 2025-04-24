import cv2
import numpy as np
from datetime import datetime

class EventDetector:
    def __init__(self, flow_threshold=2.0, depth_threshold=0.1):
        """Initialize event detector with thresholds."""
        self.flow_threshold = flow_threshold
        self.depth_threshold = depth_threshold
        self.prev_vehicle_tracks = {}
        self.prev_trash_counts = {}

    def process(self, tracking_data, detections, frame, flow=None, depth_map=None):
        """Detect disposal events based on tracking data and detections."""
        events = []
        trash_detections = [d for d in detections if d['type'] == 'trash']
        vehicle_tracks = {tid: track for tid, track in tracking_data.items() if track['type'] == 'vehicle'}
        trash_tracks = {tid: track for tid, track in tracking_data.items() if track['type'] == 'trash'}

        # Update depth history for trash tracks
        if depth_map is not None:
            for tid, track in trash_tracks.items():
                x, y = map(int, track['center'][-1])
                depth = depth_map[y, x] if 0 <= y < depth_map.shape[0] and 0 <= x < depth_map.shape[1] else 0
                track['depth_history'].append(depth)

        for tid, track in vehicle_tracks.items():
            vehicle_center = track['center'][-1]
            x1, y1, x2, y2 = map(int, track['bbox'][-1])
            expanded_bbox = (x1 - 50, y1 - 50, x2 + 50, y2 + 50)

            # Throwing event
            if flow is not None:
                for trash in trash_detections:
                    if trash['context'] == 'improper':
                        x, y = map(int, trash['center'])
                        if not (x1 < x < x2 and y1 < y < y2) and self.is_outward_motion(vehicle_center, flow, x, y):
                            events.append({
                                'timestamp': datetime.now(),
                                'vehicle_id': tid,
                                'event_type': 'throwing',
                                'location': vehicle_center,
                                'velocity': track['velocity'][-1],
                                'review_needed': trash['status'] == 'potential'
                            })

            # Unloading event
            curr_trash = [t for t in trash_detections if self.bbox_overlap(expanded_bbox, t['bbox']) and t['context'] == 'improper']
            prev_count = self.prev_trash_counts.get(tid, 0)
            if len(curr_trash) > prev_count and track['state'][-1] in ['slowing', 'stopped']:
                events.append({
                    'timestamp': datetime.now(),
                    'vehicle_id': tid,
                    'event_type': 'unloading',
                    'location': vehicle_center,
                    'velocity': track['velocity'][-1],
                    'review_needed': any(t['status'] == 'potential' for t in curr_trash)
                })
            self.prev_trash_counts[tid] = len(curr_trash)

            # Hidden disposal event
            occluded_area = (x1 - 100, y1 - 100, x2 + 100, y2 + 100)
            new_trash = [t for t in trash_detections if self.bbox_overlap(occluded_area, t['bbox']) and t['context'] == 'improper']
            prev_in_area = self.prev_vehicle_tracks.get(tid, {}).get('trash_count', 0)
            if len(new_trash) > prev_in_area and track['state'][-1] == 'stopped':
                events.append({
                    'timestamp': datetime.now(),
                    'vehicle_id': tid,
                    'event_type': 'hidden_disposal',
                    'location': vehicle_center,
                    'velocity': track['velocity'][-1],
                    'review_needed': any(t['status'] == 'potential' for t in new_trash)
                })

            # Confirmed disposal event using trash tracks
            if depth_map is not None and flow is not None:
                for trash_tid, trash_track in trash_tracks.items():
                    if len(trash_track['depth_history']) > 1:
                        depth_change = trash_track['depth_history'][-1] - trash_track['depth_history'][-2]
                        if abs(depth_change) > self.depth_threshold:
                            tx, ty = map(int, trash_track['center'][-1])
                            if not (x1 < tx < x2 and y1 < ty < y2) and self.is_outward_motion(vehicle_center, flow, tx, ty):
                                events.append({
                                    'timestamp': datetime.now(),
                                    'vehicle_id': tid,
                                    'trash_id': trash_tid,
                                    'event_type': 'confirmed_disposal',
                                    'location': vehicle_center,
                                    'velocity': track['velocity'][-1],
                                    'review_needed': trash_track['status'] == 'potential'
                                })

        self.prev_vehicle_tracks = vehicle_tracks
        return events

    def is_outward_motion(self, vehicle_center, flow, x, y):
        """Check if motion at (x, y) is outward from vehicle center."""
        if flow is None or not (0 <= y < flow.shape[0] and 0 <= x < flow.shape[1]):
            return False
        flow_u, flow_v = flow[y, x]
        mag = np.sqrt(flow_u**2 + flow_v**2)
        if mag < self.flow_threshold:
            return False
        dx, dy = x - vehicle_center[0], y - vehicle_center[1]
        dot_product = flow_u * dx + flow_v * dy
        return dot_product > 0

    def bbox_overlap(self, bbox1, bbox2):
        """Check if two bounding boxes overlap."""
        x1, y1, x2, y2 = bbox1[0], bbox1[1], bbox1[0] + bbox1[2], bbox1[1] + bbox1[3]
        tx1, ty1, tx2, ty2 = map(int, bbox2)
        return not (x2 < tx1 or tx2 < x1 or y2 < ty1 or ty2 < y1)