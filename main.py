import cv2
import os
from detection import Detector
from tracking import Tracker
from events import EventDetector
from reporting import Reporter
from depth_visualization import DepthVisualizer

def main():
    config = {
        "vehicle_model_path": "models/yolov8m.pt",
        "trash_model_path": "./models/100epochv2.pt",
        "video_path": "videos/video2.mp4",
        "evidence_path": "evidence",
        "report_path": "reports",
        "distance_threshold": 150,
        "max_inactive_frames": 30,
        "temporal_window": 10,
        "min_holding": 15,
        "min_disposal": 20,
        "min_throw": 5,
        "depth_threshold": 50,
        "camera_location": "Location1"
    }
    os.makedirs(config["evidence_path"], exist_ok=True)
    os.makedirs(config["report_path"], exist_ok=True)
    
    detector = Detector(config["vehicle_model_path"], config["trash_model_path"])
    tracker = Tracker(config["distance_threshold"], config["max_inactive_frames"])
    event_detector = EventDetector(
        temporal_window=config["temporal_window"],
        min_holding=config["min_holding"],
        min_disposal=config["min_disposal"],
        min_throw=config["min_throw"],
        depth_threshold=config["depth_threshold"]
    )
    reporter = Reporter(config["evidence_path"], config["report_path"], config["camera_location"])
    depth_visualizer = DepthVisualizer()
    
    cap = cv2.VideoCapture(config["video_path"])
    frame_count = 0
    events_data = []  # Local events storage for main.py
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        detections = detector.detect(frame)
        tracker.assign_ids(detections, frame_count)
        event_detector.process(tracker.tracking_data, detections, frame)
        events_data.extend(event_detector.events_data[-1:])  # Append new events
        vis_frame = detector.visualize(frame, detections, tracker.tracking_data)
        depth_frame = depth_visualizer.visualize_depth(frame)
        
        cv2.imshow("Waste Disposal Monitoring", vis_frame)
        cv2.imshow("Depth Visualization", depth_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        frame_count += 1
    
    cap.release()
    cv2.destroyAllWindows()
    report_path = reporter.export_events(events_data)
    print(f"Report generated at: {report_path}")

if __name__ == "__main__":
    main()