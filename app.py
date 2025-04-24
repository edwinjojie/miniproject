from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import cv2
import tempfile
import shutil

from detection import Detector
from tracking import Tracker
from events import EventDetector
from reporting import Reporter
from visualization_manager import VisualizationManager
import numpy as np

app = Flask(__name__)
CORS(app)

# --- Configuration ---
BASE_PATH       = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER   = os.path.join(BASE_PATH, 'videos')
EVIDENCE_FOLDER = os.path.join(BASE_PATH, 'evidence')
REPORT_FOLDER   = os.path.join(BASE_PATH, 'reports')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EVIDENCE_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

# --- Initialize your pipeline components ---
detector      = Detector(os.path.join(BASE_PATH, "model/yolov8m.pt"),
                         os.path.join(BASE_PATH, "model/100epochv2.pt"))
tracker       = Tracker(distance_threshold=150, max_inactive=30)
event_detector= EventDetector(temporal_window=10,
                              min_holding=15,
                              min_disposal=20,
                              min_throw=5,
                              depth_threshold=50)
reporter      = Reporter(EVIDENCE_FOLDER, REPORT_FOLDER, "Location1")
vis_manager   = VisualizationManager(detector)
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
    """Runs detection → tracking → event detection → reporting on the given file,
       returns the list of all detected events."""
    print("1")
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
        try:
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

            

            frame_count += 1
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
            if event_detector.events_data:
                events.extend(event_detector.events_data[-1:])
        except Exception as e:
            app.logger.exception(f"Error processing frame {frame_count}")
            # either break, or continue to skip bad frames
            break

        frame_count += 1
 
    cap.release()
    cv2.destroyAllWindows()
   
    return report_path

    

    # write out reports & evidence
  

@app.route('/api/upload', methods=['POST'])
def upload_video():
    # 1. validate
    if 'file' not in request.files:
        return jsonify(error="No file part"), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(error="No selected file"), 400
    if not file.filename.lower().endswith('.mp4'):
        return jsonify(error="Invalid file format; only .mp4 allowed"), 400

    try:
        # 2. save to a safe temp, then move into your upload folder
        temp_name  = f"upload_.mp4"
        temp_path  = os.path.join(tempfile.gettempdir(), temp_name)
        file.save(temp_path)

        final_path = os.path.join(UPLOAD_FOLDER, temp_name)
        shutil.move(temp_path, final_path)
        print("the filepath",final_path)
        # 3. process synchronously
        events = process_video(final_path)
        app.logger.info(f"Finished processing, found {len(events)} events")
        # 4. return JSON
        return jsonify(
            eventsDetected=len(events),
            events=events
        ), 200

    except Exception as e:
        return jsonify(error=f"Processing failed: {str(e)}"), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
