import cv2
import os
from detection import Detector
from tracking import Tracker
from events import EventDetector
from reporting import Reporter
from visualization_manager import VisualizationManager
import numpy as np

def compute_potential_areas(flow, tracking_data):
    """Identify potential disposal areas based on optical flow near vehicles."""
    # Check if flow is None
    if flow is None:
        return []  # Return an empty list if no flow data is available
    
    potential_areas = []
    for tid, track in tracking_data.items():
        if track['type'] == 'vehicle':
            x1, y1, x2, y2 = map(int, track['bbox'])
            # Expand ROI by 50%
            w, h = x2 - x1, y2 - y1
            roi_x1 = max(0, x1 - w // 4)
            roi_y1 = max(0, y1 - h // 4)
            roi_x2 = min(flow.shape[1], x2 + w // 4)
            roi_y2 = min(flow.shape[0], y2 + h // 4)
            # Extract flow in ROI
            roi_flow = flow[roi_y1:roi_y2, roi_x1:roi_x2]
            # Compute magnitude
            mag, _ = cv2.cartToPolar(roi_flow[..., 0], roi_flow[..., 1])
            avg_mag = np.mean(mag)
            if avg_mag > 5:  # Threshold for potential disposal
                potential_areas.append({
                    'top_left': (roi_x1, roi_y1),
                    'bottom_right': (roi_x2, roi_y2)
                })
    return potential_areas

def process_video(video_path):
    """Process video with visualization mode toggling, including optical flow."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return None
    
    tracker.frame_rate = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    events_data = []

    # Initialize the visualization manager with the existing detector
    vis_manager = VisualizationManager(detector)
    vis_manager.set_mode('normal')  # Start with normal visualization

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        detections = detector.detect(frame)
        tracker.assign_ids(detections, frame_count)
        flow = detector.compute_optical_flow(frame)  # Compute optical flow for every frame
        event_detector.process(tracker.tracking_data, detections, frame, flow)
        events_data.extend(event_detector.events_data[-1:])

        # Added computation for potential areas and low-confidence detections
        potential_areas = compute_potential_areas(flow, tracker.tracking_data)
        low_conf_detections = [det for det in detections if det['type'] == 'trash' and det['confidence'] < 0.5]

        # Updated visualize call to pass new parameters
        vis_frame = vis_manager.visualize(frame, detections, tracker.tracking_data, flow, potential_areas, low_conf_detections)

        # Display the visualized frame
        cv2.imshow("Visualization", vis_frame)

        # Keyboard controls to toggle visualization modes
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('n'):
            vis_manager.set_mode('normal')
            print("Switched to Normal Visualization")
        elif key == ord('d'):
            vis_manager.set_mode('depth')
            print("Switched to Depth Visualization")
        elif key == ord('o'):
            vis_manager.set_mode('optical_flow')
            print("Switched to Optical Flow Visualization")

        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()
    report_path = reporter.export_events(events_data)
    return report_path

def main():
    config = {
        "vehicle_model_path": "models/yolov8m.pt",
        "trash_model_path": "models/100epochv2.pt",
        "video_path": "videos/ODOT camera films litterbug dumping trash on highway in Cleveland.mp4",
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
    
    global detector, tracker, event_detector, reporter
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
    
    video_path = config["video_path"]
    report_path = process_video(video_path)
    if report_path:
        print(f"Report generated at: {report_path}")
    else:
        print("Video processing failed.")

if __name__ == "__main__":
    main()