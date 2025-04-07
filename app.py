from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import cv2
import io
import csv
import numpy as np
from detection import Detector
from tracking import Tracker
from events import EventDetector
from reporting import Reporter
from visualization_manager import VisualizationManager  # Import the new manager
import base64
import tempfile
import shutil

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Storage Configuration
UPLOAD_FOLDER = 'videos'
EVIDENCE_FOLDER = 'evidence'
REPORT_FOLDER = 'reports'
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# Initialize components
try:
    detector = Detector(os.path.join(BASE_PATH, "models/yolov8m.pt"), os.path.join(BASE_PATH, "models/100epochv2.pt"))
    tracker = Tracker(distance_threshold=150, max_inactive=30)
    event_detector = EventDetector(temporal_window=10, min_holding=15, min_disposal=20, min_throw=5, depth_threshold=50)
    reporter = Reporter(os.path.join(BASE_PATH, EVIDENCE_FOLDER), os.path.join(BASE_PATH, REPORT_FOLDER), "Location1")
    vis_manager = VisualizationManager(detector)  # Initialize the visualization manager
    events_data = []
except Exception as e:
    print(f"Initialization failed: {e}")
    events_data = []

@socketio.on('set_visualization_mode')
def handle_set_visualization_mode(data):
    mode = data.get('mode')
    if mode in ['normal', 'depth', 'optical_flow']:
        vis_manager.set_mode(mode)
        emit('mode_changed', {'mode': mode})
    else:
        emit('error', {'message': 'Invalid mode'})

def process_video(video_path, sid):
    global events_data
    events_data = []
    cap = cv2.VideoCapture(video_path)
    tracker.frame_rate = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        detections = detector.detect(frame)
        tracker.assign_ids(detections, frame_count)
        flow = detector.compute_optical_flow(frame)
        event_detector.process(tracker.tracking_data, detections, frame, flow)
        events_data.extend(event_detector.events_data[-1:])

        # Use the visualization manager for rendering
        vis_frame = vis_manager.visualize(frame, detections, tracker.tracking_data, flow)
        _, buffer = cv2.imencode('.jpg', vis_frame)
        frame_data = base64.b64encode(buffer).decode('utf-8')
        emit('frame_update', {'image': frame_data, 'frame_count': frame_count}, room=sid)

        frame_count += 1
    cap.release()
    reporter.export_events(events_data)
    emit('processing_complete', {'eventsDetected': len(events_data), 'events': events_data}, room=sid)

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith('.mp4'):
        try:
            os.makedirs(os.path.join(BASE_PATH, UPLOAD_FOLDER), exist_ok=True)
            filename = f"upload_{os.urandom(8).hex()}.mp4"
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            file.save(temp_path)
            final_path = os.path.join(BASE_PATH, UPLOAD_FOLDER, filename)
            shutil.move(temp_path, final_path)
            sid = request.sid if hasattr(request, 'sid') else None
            if sid:
                socketio.start_background_task(target=process_video, video_path=final_path, sid=sid)
            return jsonify({"message": "Processing started", "sid": sid}), 200
        except Exception as e:
            return jsonify({"error": f"Upload processing failed: {e}"}), 500
    return jsonify({"error": "Invalid file format"}), 400

if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_PATH, UPLOAD_FOLDER), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, EVIDENCE_FOLDER), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, REPORT_FOLDER), exist_ok=True)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)