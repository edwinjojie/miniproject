import cv2
import numpy as np
import torch
from collections import defaultdict
from ultralytics import YOLO
import torchvision.transforms as T
from collections import deque
class Detector:
    def __init__(self, vehicle_model_path, trash_model_path):
        """Initialize the Detector with vehicle and trash YOLO models and MiDaS."""
        self.vehicle_model = YOLO(vehicle_model_path)
        self.trash_model = YOLO(trash_model_path)
        self.trails = defaultdict(list)
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.id_font_size = 0.5
        self.velocity_font_size = 0.4
        self.state_font_size = 0.4
        self.font_thickness = 1
        self.state_colors = {
            "IDLE": (255, 0, 0),
            "STOPPED_UNLOADING": (0, 0, 255),
            "SLOWING_THROW": (0, 255, 255),
            "TRASH_DISPOSED": (0, 165, 255),
            "POTENTIAL_THROW": (255, 0, 255),
            "DECELERATING_NEAR_TRASH": (255, 255, 0)
        }
        # Initialize MiDaS for depth estimation
        self.midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", pretrained=True)
        self.midas.eval()
        self.midas.to('cpu')
        self.transform = T.Compose([
            T.ToTensor(),
            T.Resize((384, 384)),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        self.prev_frame = None  # For optical flow

    def detect(self, frame):
        """Detect vehicles and trash in the frame with depth estimation."""
        detections = []
        # Prepare frame for MiDaS
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_input = self.transform(img_rgb).unsqueeze(0).to('cpu')
        with torch.no_grad():
            depth = self.midas(img_input)
            depth = torch.nn.functional.interpolate(
                depth.unsqueeze(1), size=frame.shape[:2], mode="bicubic", align_corners=False
            ).squeeze().cpu().numpy()
        # Normalize depth to 0-255
        depth = (depth - depth.min()) / (depth.max() - depth.min()) * 255.0
        
        # Detect vehicles
        vehicle_results = self.vehicle_model(frame, conf=0.5, verbose=False)
        for result in vehicle_results:
            for box in result.boxes:
                bbox = box.xyxy[0].cpu().numpy()
                class_id = int(box.cls[0].cpu().numpy())
                if class_id in [2, 7]:  # 2: car, 7: truck
                    x, y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
                    z = depth[int(y), int(x)]
                    center = (x, y, z)
                    detections.append({
                        'bbox': bbox,
                        'class_id': class_id,
                        'type': 'vehicle',
                        'center': center
                    })
        # Detect trash with lower confidence for small/occluded objects
        trash_results = self.trash_model(frame, conf=0.3, verbose=False)
        for result in trash_results:
            for box in result.boxes:
                bbox = box.xyxy[0].cpu().numpy()
                class_id = int(box.cls[0].cpu().numpy())
                if class_id == 1:  # 1: trash
                    x, y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
                    z = depth[int(y), int(x)]
                    center = (x, y, z)
                    detections.append({
                        'bbox': bbox,
                        'class_id': class_id,
                        'type': 'trash',
                        'center': center,
                        'depth_history': deque(maxlen=10),
                        'trajectory': deque(maxlen=10)  # For throwing motion
                    })
        return detections

    def compute_optical_flow(self, frame):
        """Compute optical flow between consecutive frames."""
        if self.prev_frame is None:
            self.prev_frame = frame.copy()
            return None
        prev_gray = cv2.cvtColor(self.prev_frame, cv2.COLOR_BGR2GRAY)
        current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(prev_gray, current_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        self.prev_frame = frame.copy()
        return flow

    def visualize(self, frame, detections, tracking_data):
        """Visualize detections with bounding boxes, trails, and a state panel."""
        vis_frame = frame.copy()
        state_lines = []
        text_colors = []

        for tid, track in sorted(tracking_data.items(), key=lambda x: x[0]):
            if track['type'] == 'vehicle':
                state = track.get('state', 'IDLE')
                vel = track.get('smoothed_velocity', 0)
                line = f"Vehicle {tid} : {state} | Velocity: {vel:.1f}m/s"
                state_lines.append(line)
                text_colors.append((255, 255, 255))

        if state_lines:
            text_sizes = [cv2.getTextSize(line, self.font, self.state_font_size, self.font_thickness)[0] for line in state_lines]
            max_width = max(size[0] for size in text_sizes)
            panel_height = 30 + len(state_lines) * 20
            overlay = vis_frame.copy()
            cv2.rectangle(overlay, (10, 10), (20 + max_width, panel_height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, vis_frame, 0.4, 0, vis_frame)
            for i, (line, color) in enumerate(zip(state_lines, text_colors)):
                y_pos = 30 + i * 20
                cv2.putText(vis_frame, line, (15, y_pos), self.font, self.state_font_size, color, self.font_thickness)

        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            tid = det.get('id')
            if det['type'] == 'vehicle':
                state = tracking_data.get(tid, {}).get('state', 'IDLE')
                color = self.state_colors.get(state, (255, 0, 0))
                cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
                label = f"V{tid} {tracking_data.get(tid, {}).get('smoothed_velocity', 0):.1f}m/s"
                cv2.putText(vis_frame, label, (x1, y1 - 10), self.font, self.id_font_size, (255, 255, 255), self.font_thickness)
                center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                self.trails[tid].append(center)
                if len(self.trails[tid]) > 30:
                    self.trails[tid].pop(0)
                for i in range(1, len(self.trails[tid])):
                    cv2.line(vis_frame, self.trails[tid][i - 1], self.trails[tid][i], (255, 100, 100), 1)
            elif det['type'] == 'trash':
                cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(vis_frame, f"T{tid}", (x1, y1 - 10), self.font, self.id_font_size, (255, 255, 255), self.font_thickness)
        return vis_frame