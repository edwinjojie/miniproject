import cv2
import sys
from detection import Detector
from tracking import Tracker
from events import EventDetector
from visualization_manager import VisualizationManager
from depth_visualization import DepthVisualizer
from reporting import Reporter
import config

def process_video(video_path, vehicle_model_path, trash_model_path, output_path):
    """Process video to detect waste disposal events with larger resolution."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        sys.exit(1)

    # Define the desired resolution for visualization (1080x720 as requested)
    # Change these values to adjust the output resolution if needed
    output_width, output_height = 1080, 720

    detector = Detector(vehicle_model_path, trash_model_path)
    tracker = Tracker()
    event_detector = EventDetector()
    vis_manager = VisualizationManager()
    depth_visualizer = DepthVisualizer()
    reporter = Reporter("evidence", "reports")
    config.frame_count = 0

    # Use XVID codec with .avi extension for compatibility
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, 30.0, (output_width, output_height))
    if not out.isOpened():
        print("Error: Could not open video writer")
        sys.exit(1)

    events_data = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Resize the input frame to the desired resolution
        frame = cv2.resize(frame, (output_width, output_height))
        config.frame_count += 1
        detections = detector.detect(frame)
        tracking_data = tracker.assign_ids(detections)
        flow, _ = detector.compute_optical_flow(frame)
        mode = vis_manager.current_mode
        depth_map = depth_visualizer.visualize_depth(frame) if mode == 'depth' else None

        events = event_detector.process(tracking_data, detections, frame, flow, depth_map)
        events_data.extend(events)
        vis_frame = vis_manager.visualize(frame, detections, tracking_data, events, flow, depth_map)

        out.write(vis_frame)
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

    report_path = reporter.export_events(events_data, "Camera1", frame, config.frame_count)
    if report_path:
        print(f"Report generated at: {report_path}")
    else:
        print("Report generation failed.")
    cap.release()
    out.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python main.py <video_path> <vehicle_model_path> <trash_model_path>")
        sys.exit(1)
    process_video(sys.argv[1], sys.argv[2], sys.argv[3], 'output.avi')  # Changed to match .avi extension