from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import cv2
import io
import base64
import tempfile
import shutil
from detection import Detector
from tracking import Tracker
from events import EventDetector
from reporting import Reporter
from visualization_manager import VisualizationManager

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = 'videos'
EVIDENCE_FOLDER = 'evidence'
REPORT_FOLDER = 'reports'
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

detector = Detector(os.path.join(BASE_PATH, "models/yolov8m.pt"), os.path.join(BASE_PATH, "models/100epochv2.pt"))
tracker = Tracker()
event_detector = EventDetector()
reporter = Reporter(os.path.join(BASE_PATH, EVIDENCE_FOLDER), os.path.join(BASE_PATH, REPORT_FOLDER))
vis_manager = VisualizationManager(detector)
events_data = {}

@socketio.on('set_visualization_mode')
def handle_set_visualization_mode(data):
    mode = data.get('mode')
    if mode in ['normal', 'depth']:
        vis_manager.set_mode(mode)
        emit('mode_changed', {'mode': mode})

def process_video(video_path, sid, camera_id):
    global events_data
    events_data[sid] = []
    cap = cv2.VideoCapture(video_path)
    tracker.frame_rate = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % 2 == 0:
            detections = detector.detect(frame)
            tracker.assign_ids(detections, frame_count)
            flow, mag = detector.compute_optical_flow(frame)
            depth_map = vis_manager.depth_visualizer.visualize_depth(frame) if vis_manager.current_mode == 'depth' else None
            events = event_detector.process(tracker.tracking_data, {d['id']: (d['bbox'], d.get('velocity', 0)) for d in detections if d['type'] == 'vehicle'}, 
                                          [d for d in detections if d['type'] == 'trash'], frame, flow, depth_map)
            events_data[sid].extend(events)

            vis_frame = vis_manager.visualize(frame, detections, tracker.tracking_data, events, flow)
            _, buffer = cv2.imencode('.jpg', vis_frame)
            frame_data = base64.b64encode(buffer).decode('utf-8')
            emit('frame_update', {'image': frame_data, 'frame_count': frame_count, 'camera_id': camera_id}, room=sid)

        frame_count += 1
    cap.release()
    report_path = reporter.export_events(events_data[sid], camera_id, frame, frame_count)
    emit('processing_complete', {'report_path': report_path, 'events': events_data[sid]}, room=sid)

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith('.mp4'):
        os.makedirs(os.path.join(BASE_PATH, UPLOAD_FOLDER), exist_ok=True)
        filename = f"upload_{os.urandom(8).hex()}.mp4"
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)
        final_path = os.path.join(BASE_PATH, UPLOAD_FOLDER, filename)
        shutil.move(temp_path, final_path)
        sid = request.sid
        camera_id = request.form.get('camera_id', 'Camera1')
        socketio.start_background_task(target=process_video, video_path=final_path, sid=sid, camera_id=camera_id)
        return jsonify({"message": "Processing started", "sid": sid, "camera_id": camera_id}), 200
    return jsonify({"error": "Invalid file format"}), 400

@app.route('/api/download/<path:report_path>', methods=['GET'])
def download_report(report_path):
    return send_file(report_path, as_attachment=True)

if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_PATH, UPLOAD_FOLDER), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, EVIDENCE_FOLDER), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, REPORT_FOLDER), exist_ok=True)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)