# Ensure these are installed globally: pip install flask flask-cors flask-socketio eventlet opencv-python numpy torch ultralytics scipy pillow

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
import base64
import tempfile
import shutil

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")

# Storage Configuration
UPLOAD_FOLDER = 'videos'
EVIDENCE_FOLDER = 'evidence'
REPORT_FOLDER = 'reports'
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# Initialize components
try:
    detector = Detector(os.path.join(BASE_PATH, "models/yolov8m.pt"), os.path.join(BASE_PATH, "./models/100epochv2.pt"))
    tracker = Tracker(distance_threshold=150, max_inactive=30)
    event_detector = EventDetector(temporal_window=10, min_holding=15, min_disposal=20, min_throw=5, depth_threshold=50)
    reporter = Reporter(os.path.join(BASE_PATH, EVIDENCE_FOLDER), os.path.join(BASE_PATH, REPORT_FOLDER), "Location1")
    events_data = []
except Exception as e:
    print(f"Initialization failed: {e}")
    events_data = []

def process_video(video_path, sid):
    global events_data
    events_data = []
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        # Detect and track
        detections = detector.detect(frame)
        tracker.assign_ids(detections, frame_count)
        event_detector.process(tracker.tracking_data, detections, frame)
        events_data.extend(event_detector.events_data[-1:])
        
        # Visualize frame
        vis_frame = detector.visualize(frame, detections, tracker.tracking_data)
        _, buffer = cv2.imencode('.jpg', vis_frame)
        frame_data = base64.b64encode(buffer).decode('utf-8')
        socketio.emit('frame_update', {'image': frame_data, 'frame_count': frame_count}, room=sid)
        
        # Emit events if any
        if events_data[-1:]:
            socketio.emit('event_update', {'events': events_data[-1:]}, room=sid)
        
        frame_count += 1
    cap.release()
    reporter.export_events(events_data)
    socketio.emit('processing_complete', {'eventsDetected': len(events_data), 'events': events_data}, room=sid)

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
            sid = request.sid  # WebSocket session ID
            socketio.start_background_task(target=process_video, video_path=final_path, sid=sid)
            return jsonify({"message": "Processing started", "sid": sid}), 200
        except Exception as e:
            return jsonify({"error": f"Upload processing failed: {e}"}), 500
    return jsonify({"error": "Invalid file format"}), 400

@app.route('/api/events', methods=['GET'])
def get_events():
    return jsonify(events_data)

@app.route('/api/export/excel', methods=['GET'])
def export_excel():
    ids = request.args.get('ids', '').split(',')
    filtered_events = [e for e in events_data if not ids or str(e['vehicle_id']) in ids]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Source", "Type", "Description"])
    for event in filtered_events:
        writer.writerow([event['vehicle_id'], event['timestamp'], "Camera", event['event_type'], event['state']])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        attachment_filename='events.csv'
    )

@app.route('/api/export/report/<int:event_id>', methods=['GET'])
def export_report(event_id):
    event = next((e for e in events_data if e['vehicle_id'] == event_id), None)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    report_content = f"Event Report\n\nID: {event['vehicle_id']}\nTimestamp: {event['timestamp']}\nType: {event['event_type']}\nLocation: {event['location']}\nVelocity: {event['velocity']:.1f}u"
    return send_file(
        io.BytesIO(report_content.encode()),
        mimetype='text/plain',
        as_attachment=True,
        attachment_filename=f'Event_{event_id}_Report.txt'
    )

if __name__ == '__main__':
    os.makedirs(os.path.join(BASE_PATH, UPLOAD_FOLDER), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, EVIDENCE_FOLDER), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, REPORT_FOLDER), exist_ok=True)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)