import cv2
import numpy as np
from depth_visualization import DepthVisualizer 

class VisualizationManager:
    def __init__(self, detector):
        """Initialize with the existing Detector instance."""
        self.detector = detector
        self.current_mode = 'normal'  # Default to existing visualization
        self.depth_visualizer = DepthVisualizer()  # For depth visualization
        # Added font definitions for new overlays
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_size = 0.5
        self.font_thickness = 1

    def set_mode(self, mode):
        """Set the current visualization mode."""
        if mode in ['normal', 'depth', 'optical_flow']:
            self.current_mode = mode
        else:
            raise ValueError("Invalid visualization mode")

    def visualize(self, frame, detections, tracking_data, flow=None, potential_areas=None, low_conf_detections=None):
        """Render the frame based on the current mode with optional overlays."""
        if self.current_mode == 'normal':
            vis_frame = self.detector.visualize(frame, detections, tracking_data)
            # Appended overlay for potential disposal areas
            if potential_areas:
                for area in potential_areas:
                    cv2.rectangle(vis_frame, area['top_left'], area['bottom_right'], (0, 255, 255), 2)
                    cv2.putText(vis_frame, "Potential Disposal", (area['top_left'][0], area['top_left'][1] - 10),
                                self.font, self.font_size, (0, 255, 255), self.font_thickness)
            # Appended overlay for low-confidence trash detections
            if low_conf_detections:
                for det in low_conf_detections:
                    x1, y1, x2, y2 = map(int, det['bbox'])
                    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    cv2.putText(vis_frame, "Potential Trash", (x1, y1 - 10), self.font, self.font_size, (0, 255, 255), self.font_thickness)
            return vis_frame
        elif self.current_mode == 'depth':
            return self.depth_visualizer.visualize_depth(frame)
        elif self.current_mode == 'optical_flow':
            if flow is None:
                flow = self.detector.compute_optical_flow(frame)
            return self._visualize_optical_flow(frame, flow)

    def _visualize_optical_flow(self, frame, flow):
        """Render optical flow visualization."""
        hsv = np.zeros_like(frame)
        hsv[..., 1] = 255  # Saturation
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        hsv[..., 0] = ang * 180 / np.pi / 2  # Hue based on direction
        hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)  # Value based on magnitude
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)