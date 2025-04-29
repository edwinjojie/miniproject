import cv2
import sys
import numpy as np
from detection import Detector
from tracking import Tracker
from events import EventDetector
from visualization_manager import VisualizationManager
from depth_visualization import DepthVisualizer
from reporting import Reporter
import config
import os

def process_video(video_path, vehicle_model_path, trash_model_path, output_path):
    """Process video to detect waste disposal events with larger resolution."""
    # Set video_path in config
    config.video_path = video_path
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        sys.exit(1)

    # Define output resolution
    output_width, output_height = 1080, 720

    # Initialize components
    detector = Detector(vehicle_model_path, trash_model_path)
    tracker = Tracker()
    event_detector = EventDetector()
    vis_manager = VisualizationManager()
    depth_visualizer = DepthVisualizer()
    reporter = Reporter("evidence", "reports")
    config.frame_count = 0

    # Use MJPG codec for better compatibility
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(output_path, fourcc, 30.0, (output_width, output_height))
    if not out.isOpened():
        print("Error: Could not open video writer")
        sys.exit(1)

    events_data = []
    frames_written = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Resize frame
        frame = cv2.resize(frame, (output_width, output_height))
        config.frame_count += 1
        
        # Process frame
        detections = detector.detect(frame)
        tracking_data = tracker.assign_ids(detections)
        flow, _ = detector.compute_optical_flow(frame)
        mode = vis_manager.current_mode
        depth_map = depth_visualizer.visualize_depth(frame) if mode == 'depth' else None

        # Pass frame_count to event detector
        events = event_detector.process(tracking_data, detections, frame, config.frame_count, flow, depth_map)
        events_data.extend(events)
        
        vis_frame = vis_manager.visualize(frame, detections, tracking_data, events, flow, depth_map[1] if depth_map else None)  # Use color-mapped depth for visualization
        
        # Verify vis_frame format before writing
        if vis_frame.shape == (output_height, output_width, 3) and vis_frame.dtype == np.uint8:
            out.write(vis_frame)
            frames_written += 1
            print(f"Writing frame {config.frame_count}")
        
        cv2.imshow('Waste Detection', vis_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('n'):
            vis_manager.set_mode('normal')
        elif key == ord('o'):
            vis_manager.set_mode('optical_flow')
        elif key == ord('d'):
            vis_manager.set_mode('depth')

    # Generate report with all events
    print(f"Total events detected: {len(events_data)}")
    report_path = reporter.export_events(events_data, "Camera1")
    
    if report_path:
        print(f"Report generated at: {report_path['excel']}")
    else:
        print("Report generation failed.")
    
    # Cleanup
    cap.release()
    out.release()
    print(f"Total frames written: {frames_written}")
    if os.path.getsize(output_path) > 0:
        print(f"Video saved successfully at {output_path}")
    else:
        print("Warning: Video file is empty")
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python main.py <video_path> <vehicle_model_path> <trash_model_path>")
        sys.exit(1)
    process_video(sys.argv[1], sys.argv[2], sys.argv[3], 'output.avi')