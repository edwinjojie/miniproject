import cv2
import numpy as np
import os
import time
from datetime import datetime

class VisualizationManager:
    def __init__(self, detector=None):
        """Initialize visualization parameters with larger and bolder fonts."""
        self.detector = detector  # Store detector reference for advanced visualizations
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_size = 0.8  # Increased font size for better readability
        self.id_font_size = 0.8  # Increased for ID labels
        self.font_thickness = 2  # Increased thickness for bolder text
        self.colors = {
            'vehicle': (0, 128, 255),  # Orange
            'trash': (0, 255, 0),      # Green
            'text': (255, 255, 255),   # White
            'flow': (255, 0, 0),       # Red
            'alert': (0, 0, 255),      # Red
            'bin': (255, 0, 255),      # Purple
            'confirmed': (0, 255, 0),  # Green
            'potential': (0, 165, 255), # Orange
            'proper': (255, 0, 0)      # Blue
        }
        self.state_colors = {
            'moving': (0, 128, 255),  # Orange
            'slowing': (0, 255, 255), # Yellow
            'stopped': (255, 0, 0)    # Red
        }
        self.current_mode = 'normal'  # Modes: 'normal', 'optical_flow', 'depth', 'combined'
        self.heatmap = None
        self.heatmap_decay = 0.95  # How fast the heatmap fades
        self.show_stats = True
        self.frame_count = 0
        self.fps_history = []
        self.last_frame_time = time.time()
        self.settings = {
            'show_ids': True,
            'show_confidence': True,
            'show_velocity': True,
            'show_stats': True,
            'show_heatmap': False,
            'show_areas_of_interest': True
        }
        
    def set_mode(self, mode):
        """Set the current visualization mode."""
        valid_modes = ['normal', 'optical_flow', 'depth', 'combined']
        if mode in valid_modes:
            self.current_mode = mode
            print(f"Visualization mode set to: {mode}")
            return True
        return False
        
    def toggle_setting(self, setting_name):
        """Toggle a specific visualization setting."""
        if setting_name in self.settings:
            self.settings[setting_name] = not self.settings[setting_name]
            return self.settings[setting_name]
        return None

    def visualize(self, frame, detections, tracking_data, events=None, flow=None, depth_map=None, 
                 potential_areas=None, low_conf_detections=None):
        """Visualize detections, tracks, and events based on the current mode."""
        self.frame_count += 1
        events = events or []
        potential_areas = potential_areas or []
        low_conf_detections = low_conf_detections or []
        
        # Calculate FPS
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_frame_time) if (current_time - self.last_frame_time) > 0 else 0
        self.last_frame_time = current_time
        self.fps_history.append(fps)
        if len(self.fps_history) > 30:
            self.fps_history.pop(0)
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        
        # Initialize/update heatmap
        if self.heatmap is None:
            self.heatmap = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.float32)
        else:
            # Decay existing heatmap
            self.heatmap *= self.heatmap_decay
        
        # Update heatmap based on current detections
        if self.settings['show_heatmap']:
            for d in detections:
                if d['type'] == 'trash' and d['context'] == 'improper':
                    x1, y1, x2, y2 = map(int, d['bbox'])
                    center_x, center_y = int((x1 + x2) / 2), int((y1 + y2) / 2)
                    cv2.circle(self.heatmap, (center_x, center_y), 20, 0.5, -1)
                    
            # Convert heatmap to colormap for visualization
            heatmap_colored = cv2.applyColorMap(
                np.uint8(255 * self.heatmap), cv2.COLORMAP_JET)
        
        # Choose base visualization based on mode
        if self.current_mode == 'depth' and depth_map is not None:
            vis_frame = cv2.addWeighted(frame, 0.7, depth_map, 0.3, 0)
        elif self.current_mode == 'optical_flow' and flow is not None:
            vis_frame = frame.copy()
            self._draw_optical_flow(vis_frame, flow)
        elif self.current_mode == 'combined':
            # Combined mode: normal visualization + optical flow arrows + semi-transparent depth
            vis_frame = frame.copy()
            if depth_map is not None:
                vis_frame = cv2.addWeighted(vis_frame, 0.8, depth_map, 0.2, 0)
            if flow is not None and self.frame_count % 3 == 0:  # Only draw flow every 3rd frame for clarity
                self._draw_optical_flow(vis_frame, flow, step=30)  # Larger step for cleaner visualization
        else:
            # Normal mode
            vis_frame = frame.copy()
        
        # If heatmap enabled, overlay it
        if self.settings['show_heatmap'] and self.heatmap is not None:
            vis_frame = cv2.addWeighted(
                vis_frame, 0.7, heatmap_colored, 0.3, 0)
        
        # Draw areas of interest (potential disposal areas)
        if self.settings['show_areas_of_interest'] and potential_areas:
            for area in potential_areas:
                p1 = area['top_left']
                p2 = area['bottom_right']
                cv2.rectangle(vis_frame, p1, p2, (0, 255, 255), 2)  # Yellow rectangle
                cv2.putText(vis_frame, "Potential disposal area", 
                          (p1[0], p1[1] - 10), self.font, self.font_size, 
                          (0, 255, 255), self.font_thickness)
        
        # Always draw detections
        if self.current_mode != 'optical_flow':  # Skip in pure optical flow mode
            self._draw_detections(vis_frame, detections, tracking_data, low_conf_detections)
        
        # Draw events if provided and not in pure optical flow mode
        if events and self.current_mode != 'optical_flow':
            self._draw_events(vis_frame, events, tracking_data)
        
        # Draw stats overlay
        if self.settings['show_stats']:
            self._draw_stats_overlay(vis_frame, avg_fps, len(detections), 
                                    len([d for d in detections if d['type'] == 'trash']), 
                                    len(events))
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(vis_frame, timestamp, (vis_frame.shape[1] - 230, 30), 
                   self.font, 0.7, (255, 255, 255), 2)
        
        return vis_frame
        
    def _draw_optical_flow(self, frame, flow, step=20):
        """Draw optical flow vectors on the frame."""
        h, w = flow.shape[:2]
        y, x = np.mgrid[step//2:h:step, step//2:w:step].reshape(2, -1).astype(int)
        fx, fy = flow[y, x].T
        
        # Filter out small movements
        mask = np.sqrt(fx*fx + fy*fy) > 1.0
        x, y, fx, fy = x[mask], y[mask], fx[mask], fy[mask]
        
        # Create line segments
        lines = np.vstack([x, y, x + fx, y + fy]).T.reshape(-1, 2, 2)
        lines = np.int32(lines)
        
        # Draw the flow arrows
        for (x1, y1), (x2, y2) in lines:
            # Color based on direction and magnitude
            mag = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            angle = np.arctan2(y2-y1, x2-x1)
            hue = ((angle + np.pi) / (2 * np.pi)) * 180
            color = tuple(int(c) for c in cv2.cvtColor(np.uint8([[[hue, 255, min(255, mag * 5)]]]), 
                                                      cv2.COLOR_HSV2BGR)[0, 0])
            cv2.arrowedLine(frame, (x1, y1), (x2, y2), color, 1, tipLength=0.3)
    
    def _draw_detections(self, frame, detections, tracking_data, low_conf_detections=None):
        """Draw detection bounding boxes and labels."""
        # First draw low confidence detections with dashed lines
        if low_conf_detections:
            for d in low_conf_detections:
                x1, y1, x2, y2 = map(int, d['bbox'])
                # Draw dashed rectangle
                dash_length = 10
                for i in range(0, int((x2-x1)*2 + (y2-y1)*2), dash_length*2):
                    if i < (x2-x1):
                        pt1 = (x1 + i, y1)
                        pt2 = (min(x1 + i + dash_length, x2), y1)
                    elif i < (x2-x1) + (y2-y1):
                        pt1 = (x2, y1 + i - (x2-x1))
                        pt2 = (x2, min(y1 + i - (x2-x1) + dash_length, y2))
                    elif i < (x2-x1)*2 + (y2-y1):
                        pt1 = (x2 - (i - (x2-x1) - (y2-y1)), y2)
                        pt2 = (max(x2 - (i - (x2-x1) - (y2-y1)) - dash_length, x1), y2)
                    else:
                        pt1 = (x1, y2 - (i - (x2-x1)*2 - (y2-y1)))
                        pt2 = (x1, max(y2 - (i - (x2-x1)*2 - (y2-y1)) - dash_length, y1))
                    cv2.line(frame, pt1, pt2, self.colors['potential'], 1)
                
                # Add low confidence label
                confidence_text = f"Low conf: {d['confidence']:.2f}"
                cv2.putText(frame, confidence_text, (x1, y1 - 10), self.font, 
                          0.5, self.colors['potential'], 1)
        
        # Draw all main detections
        for d in detections:
            x1, y1, x2, y2 = map(int, d['bbox'])
            
            if d['type'] == 'trash':
                # Determine trash color and label based on its status
                if d['context'] == 'proper':
                    color = self.colors['proper']
                    label = 'Proper Disposal'
                elif d.get('status', 'potential') == 'confirmed':
                    color = self.colors['confirmed']
                    label = 'Confirmed Trash'
                else:
                    color = self.colors['potential']
                    label = 'Potential Trash'
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                if self.settings['show_ids']:
                    # Display trash label with ID if available
                    trash_id = d.get('id', '')
                    id_text = f"{label} #{trash_id}" if trash_id else label
                    cv2.putText(frame, id_text, (x1, y1 - 10), self.font, 
                              self.id_font_size, self.colors['text'], self.font_thickness)
                
                # Show confidence if enabled
                if self.settings['show_confidence'] and 'confidence' in d:
                    conf_text = f"Conf: {d['confidence']:.2f}"
                    cv2.putText(frame, conf_text, (x1, y1 - 30), self.font, 
                              0.6, self.colors['text'], 1)
            
            elif d['type'] == 'vehicle':
                # Get vehicle track state if available
                vehicle_id = d.get('id', -1)
                state = 'moving'  # Default state
                
                if vehicle_id in tracking_data:
                    track = tracking_data[vehicle_id]
                    state = track.get('state', ['moving'])[-1]
                
                # Set color based on vehicle state
                color = self.state_colors.get(state, self.colors['vehicle'])
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Only show IDs if setting enabled
                if self.settings['show_ids']:
                    id_text = f"V{vehicle_id}" if vehicle_id != -1 else "Vehicle"
                    cv2.putText(frame, id_text, (x1, y1 - 10), self.font, 
                              self.id_font_size, self.colors['text'], self.font_thickness)
                
                # Show velocity if setting enabled
                if self.settings['show_velocity'] and 'velocity' in d:
                    vel_text = f"{d['velocity']:.1f}px/s"
                    cv2.putText(frame, vel_text, (x1, y1 - 30), self.font, 
                              0.6, self.colors['text'], 1)
                
                # Show confidence if setting enabled  
                if self.settings['show_confidence'] and 'confidence' in d:
                    conf_text = f"Conf: {d['confidence']:.2f}"
                    cv2.putText(frame, conf_text, (x1, y1 - 50), self.font, 
                              0.6, self.colors['text'], 1)
            
            elif d['type'] == 'bin':
                # Draw bins with a distinct color
                cv2.rectangle(frame, (x1, y1), (x2, y2), self.colors['bin'], 2)
                if self.settings['show_ids']:
                    cv2.putText(frame, "Bin", (x1, y1 - 10), self.font, 
                              self.id_font_size, self.colors['text'], self.font_thickness)
    
    def _draw_events(self, frame, events, tracking_data):
        """Draw event regions and information."""
        for event in events:
            tid = event.get('vehicle_id', -1)
            if tid in tracking_data:
                # Get bounding box
                x1, y1, x2, y2 = map(int, tracking_data[tid]['bbox'][-1])
                # Create expanded box around vehicle for event visualization
                expanded_bbox = (x1 - 50, y1 - 50, x2 + 50, y2 + 50)
                
                # Color based on review status
                color = self.colors['alert'] if event.get('review_needed', False) else (153, 50, 204)  # Red or purple
                
                # Draw event box
                cv2.rectangle(frame, 
                             (expanded_bbox[0], expanded_bbox[1]),
                             (expanded_bbox[0] + expanded_bbox[2] - expanded_bbox[0], 
                              expanded_bbox[1] + expanded_bbox[3] - expanded_bbox[1]), 
                             color, 2)
                
                # Get event text
                event_type = event['event_type'].capitalize()
                review_text = " - Review Needed" if event.get('review_needed', False) else ""
                decision_text = f"{event_type}{review_text}"
                
                # Draw event info
                cv2.putText(frame, decision_text, (x1, y2 + 20), self.font, 
                           self.font_size, self.colors['text'], self.font_thickness)
                
                if 'velocity' in event:
                    velocity_text = f"Velocity: {event['velocity']:.1f}px/s"
                    cv2.putText(frame, velocity_text, (x1, y2 + 40), self.font, 
                               self.font_size, self.colors['text'], self.font_thickness)
                
                if 'confidence' in event:
                    conf_text = f"Confidence: {event['confidence']:.2f}"
                    cv2.putText(frame, conf_text, (x1, y2 + 60), self.font, 
                               self.font_size, self.colors['text'], self.font_thickness)
    
    def _draw_stats_overlay(self, frame, fps, total_detections, trash_count, event_count):
        """Draw performance and detection statistics overlay."""
        # Create semi-transparent background for stats
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (280, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Draw stats text
        cv2.putText(frame, f"FPS: {fps:.1f}", (20, 30), self.font, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Mode: {self.current_mode.capitalize()}", (20, 55), self.font, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Detections: {total_detections} ({trash_count} trash)", (20, 80), self.font, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Events: {event_count}", (20, 105), self.font, 0.7, (0, 255, 0), 2)
        
        # Show controls help text at bottom of frame
        controls_text = "Controls: [N]ormal [O]pticalFlow [D]epth [C]ombined [H]eatmap [S]tats [I]Ds [Q]uit"
        cv2.putText(frame, controls_text, (10, frame.shape[0] - 10), 
                   self.font, 0.6, (255, 255, 255), 1)
        
    def capture_labeled_frame(self, frame, filename=None):
        """Save the current visualization frame with label overlay."""
        if filename is None:
            # Create a filename based on timestamp if none provided
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            
        # Add capture indicator
        capture_frame = frame.copy()
        overlay = capture_frame.copy()
        cv2.rectangle(overlay, (0, 0), (capture_frame.shape[1], 40), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, capture_frame, 0.5, 0, capture_frame)
        cv2.putText(capture_frame, f"CAPTURE: {os.path.basename(filename)}", 
                   (20, 30), self.font, 0.7, (0, 255, 255), 2)
            
        # Save the frame
        cv2.imwrite(filename, capture_frame)
        return filename