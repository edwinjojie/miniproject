import cv2
import numpy as np
import config

class VisualizationManager:
    def __init__(self):
        """Initialize visualization parameters with larger and bolder fonts."""
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_size = 0.8  # Increased font size for better readability
        self.id_font_size = 0.8  # Increased for ID labels
        self.font_thickness = 2  # Increased thickness for bolder text
        self.colors = {
            'vehicle': (0, 128, 255),
            'trash': (0, 255, 0),
            'text': (255, 255, 255),
            'flow': (255, 0, 0)
        }
        self.state_colors = {
            'moving': (0, 128, 255),  # Orange
            'slowing': (0, 255, 255),  # Yellow
            'stopped': (255, 0, 0)    # Red
        }
        self.current_mode = 'normal'  # Modes: 'normal', 'optical_flow', 'depth'

    def visualize(self, frame, detections, tracking_data, events, flow=None, depth_map=None):
        """Visualize detections, tracks, and events based on the current mode."""
        vis_frame = frame.copy()

        if self.current_mode == 'normal':
            # Draw all detections, even those without IDs
            for d in detections:
                x1, y1, x2, y2 = map(int, d['bbox'])
                if d['type'] == 'trash':
                    if d['context'] == 'proper':
                        color = (255, 0, 0)  # Blue
                        label = 'Proper Disposal'
                    elif d['status'] == 'confirmed':
                        color = (0, 255, 0)  # Green
                        label = 'Confirmed Trash'
                    else:
                        color = (0, 165, 255)  # Orange
                        label = 'Potential Trash'
                    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(vis_frame, label, (x1, y1 - 10), self.font, self.id_font_size, self.colors['text'], self.font_thickness)
                elif d['type'] == 'vehicle':
                    # Draw vehicle even if it doesn't have an ID yet
                    state = tracking_data.get(d.get('id', -1), {}).get('state', ['moving'])[-1] if 'id' in d else 'moving'
                    color = self.state_colors.get(state, self.colors['vehicle'])
                    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
                    label = f"V{d.get('id', 'NoID')} {d.get('velocity', 0):.1f}px/s"
                    cv2.putText(vis_frame, label, (x1, y1 - 10), self.font, self.id_font_size, self.colors['text'], self.font_thickness)

            # Draw events
            for event in events:
                tid = event['vehicle_id']
                if tid in tracking_data:
                    x1, y1, x2, y2 = map(int, tracking_data[tid]['bbox'][-1])
                    expanded_bbox = (x1 - 50, y1 - 50, x2 - x1 + 100, y2 - y1 + 100)
                    color = (0, 0, 255) if event.get('review_needed', False) else (153, 50, 204)  # Red for review, purple otherwise
                    cv2.rectangle(vis_frame, (expanded_bbox[0], expanded_bbox[1]),
                                  (expanded_bbox[0] + expanded_bbox[2], expanded_bbox[1] + expanded_bbox[3]), color, 2)
                    decision_text = f"Decision: {event['event_type'].capitalize()}"
                    if event.get('review_needed', False):
                        decision_text += " - Review Needed"
                    cv2.putText(vis_frame, decision_text, (x1, y2 + 20), self.font, self.font_size, self.colors['text'], self.font_thickness)
                    velocity_text = f"Velocity: {event['velocity']:.1f}px/s"
                    cv2.putText(vis_frame, velocity_text, (x1, y2 + 40), self.font, self.font_size, self.colors['text'], self.font_thickness)

        elif self.current_mode == 'optical_flow':
            if flow is not None:
                step = 20
                h, w = flow.shape[:2]
                y, x = np.mgrid[step//2:h:step, step//2:w:step].reshape(2, -1).astype(int)
                fx, fy = flow[y, x].T
                lines = np.vstack([x, y, x + fx, y + fy]).T.reshape(-1, 2, 2)
                lines = np.int32(lines + 0.5)
                for (x1, y1), (x2, y2) in lines:
                    cv2.arrowedLine(vis_frame, (x1, y1), (x2, y2), self.colors['flow'], 1, tipLength=0.3)

        elif self.current_mode == 'depth':
            if depth_map is not None:
                vis_frame = cv2.addWeighted(vis_frame, 0.7, depth_map, 0.3, 0)

        return vis_frame

    def set_mode(self, mode):
        """Set the current visualization mode."""
        if mode in ['normal', 'optical_flow', 'depth']:
            self.current_mode = mode