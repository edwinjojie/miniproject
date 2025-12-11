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
try:
    from depth_visualization import DepthVisualizer
    depth_visualizer = DepthVisualizer()
except Exception:
    depth_visualizer = None

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
        h, w = frame.shape[:2]
        target_w = 960
        if w > target_w:
            new_h = int(h * target_w / w)
            frame = cv2.resize(frame, (target_w, new_h))
        if frame_count % 2 == 0:
            if frame_count % 4 == 0:
                flow, mag = detector.compute_optical_flow(frame)
            else:
                flow, mag = (None, None)
            depth_map = None
            if depth_visualizer and vis_manager.current_mode == 'depth':
                try:
                    depth_map = depth_visualizer.visualize_depth(frame)
                except Exception:
                    depth_map = None

            # === DETECTION WITH INITIAL VALIDATION ===
            detections, vehicle_detections = detector.detect(
                frame, 
                detector.prev_frame, 
                flow,
                frame_count
            )
            
            # === TRACKING (assigns IDs) ===
            tracking_data = tracker.assign_ids(detections)
            
            # === FULL VALIDATION WITH TEMPORAL ANALYSIS ===
            validated_detections = []
            rejected_count = 0
            suspicious_count = 0
            confirmed_count = 0
            
            for det in detections:
                # Non-trash detections pass through without validation
                if det['type'] != 'trash':
                    validated_detections.append(det)
                    continue
                
                # Full validation for trash detections
                is_valid, state, reason = detector.validator.validate_detection(
                    det,
                    vehicle_detections,
                    frame_count,
                    flow,
                    depth_map if 'depth_map' in locals() else None
                )
                
                # Add validation state to detection
                det['validation_state'] = state
                
                if is_valid and state == 'CONFIRMED':
                    det['status'] = 'confirmed'
                    validated_detections.append(det)
                    confirmed_count += 1
                    print(f"[CONFIRMED] Frame {frame_count} Track {det['id']}: {reason}")
                elif state == 'SUSPICIOUS':
                    det['status'] = 'suspicious'
                    # Keep tracking but don't confirm yet
                    suspicious_count += 1
                elif state == 'POTENTIAL':
                    det['status'] = 'potential'
                    # Still building evidence
                else:  # REJECTED
                    rejected_count += 1
                    print(f"[REJECTED] Frame {frame_count} Track {det.get('id', 'unknown')}: {reason}")
            
            # Log validation summary
            print(f"[VALIDATION-SUMMARY] Frame {frame_count}: "
                  f"{confirmed_count} confirmed, "
                  f"{suspicious_count} suspicious, "
                  f"{rejected_count} rejected")
            
            # === EVENT DETECTION (only on validated detections) ===
            events = event_detector.process(
                tracking_data,
                validated_detections,  # Use validated instead of raw detections
                frame,
                frame_count,
                flow,
                depth_map if 'depth_map' in locals() else None
            )
            
            # === CLEANUP OLD TRACKS (every 30 frames) ===
            if frame_count % 30 == 0:
                active_ids = [tid for tid, t in tracking_data.items() if t.get('type') == 'trash']
                detector.validator.cleanup_old_tracks(active_ids)
            events_data[sid].extend(events)

            vis_frame = vis_manager.visualize(frame, detections, tracking_data, events, flow, depth_map)
            _, buffer = cv2.imencode('.jpg', vis_frame)
            frame_data = base64.b64encode(buffer).decode('utf-8')
            # Use socketio.emit so background thread can emit to the client's room
            payload = {'image': frame_data, 'frame_count': frame_count, 'camera_id': camera_id}
            if sid:
                socketio.emit('frame_update', payload, to=sid)
            else:
                socketio.emit('frame_update', payload, broadcast=True)

        frame_count += 1
    cap.release()
    report_path = reporter.export_events(events_data[sid], camera_id)
    def _jsonify_event(e):
        pos = e.get('location', [0, 0])
        if isinstance(pos, tuple):
            pos = list(pos)
        x = pos[0] if len(pos) > 0 else 0
        y = pos[1] if len(pos) > 1 else 0
        z = pos[2] if len(pos) > 2 else 0
        ts = e['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(e['timestamp'], 'strftime') else str(e['timestamp'])
        return {
            'timestamp': ts,
            'vehicle_id': e.get('vehicle_id'),
            'event_type': e.get('event_type'),
            'location': [x, y, z],
            'velocity': e.get('velocity'),
            'review_needed': e.get('review_needed', False),
            'frame_count': e.get('frame_count')
        }
    safe_events = [_jsonify_event(e) for e in events_data[sid]]
    complete_payload = {'report_path': report_path, 'events': safe_events}
    if sid:
        socketio.emit('processing_complete', complete_payload, to=sid)
    else:
        socketio.emit('processing_complete', complete_payload, broadcast=True)

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
        # Accept socket id from the HTTP form (frontend should include `sid` from socket.io)
        sid = request.form.get('sid') or request.args.get('sid')
        camera_id = request.form.get('camera_id', 'Camera1')
        if not sid:
            # Log a warning; if no sid provided, processing will still run but frames may be broadcast
            app.logger.warning('No socket sid provided with upload; frames will be broadcast')

        # Start background processing. Use positional args to avoid signature issues.
        socketio.start_background_task(process_video, final_path, sid, camera_id)
        return jsonify({"message": "Processing started", "sid": sid, "camera_id": camera_id}), 200
    return jsonify({"error": "Invalid file format"}), 400

@app.route('/api/download/<path:report_path>', methods=['GET'])
def download_report(report_path):
    return send_file(report_path, as_attachment=True)

@app.route('/api/events', methods=['GET'])
def get_events():
    all_events = []
    for sid_key, evts in events_data.items():
        for idx, e in enumerate(evts):
            pos = e.get('location', [0, 0])
            if isinstance(pos, tuple):
                pos = list(pos)
            x = pos[0] if len(pos) > 0 else 0
            y = pos[1] if len(pos) > 1 else 0
            z = pos[2] if len(pos) > 2 else 0
            all_events.append({
                'id': idx + 1,
                'timestamp': e['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(e['timestamp'], 'strftime') else str(e['timestamp']),
                'source': 'Camera1',
                'type': e.get('event_type'),
                'description': 'Trash disposal event',
                'position': [x, y, z]
            })
    return jsonify(all_events)

@app.route('/api/export/excel', methods=['GET'])
def export_excel():
    ids_param = request.args.get('ids')
    ids = [int(x) for x in ids_param.split(',')] if ids_param else None
    rows = [['Event ID','Timestamp','Source','Type','Description','X','Y','Z']]
    events = []
    for sid_key, evts in events_data.items():
        for idx, e in enumerate(evts):
            events.append((idx + 1, e))
    if ids:
        events = [pair for pair in events if pair[0] in ids]
    for eid, e in events:
        pos = e.get('location', [0, 0])
        if isinstance(pos, tuple):
            pos = list(pos)
        x = pos[0] if len(pos) > 0 else 0
        y = pos[1] if len(pos) > 1 else 0
        z = pos[2] if len(pos) > 2 else 0
        ts = e['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(e['timestamp'], 'strftime') else str(e['timestamp'])
        rows.append([eid, ts, 'Camera1', e.get('event_type'), 'Trash disposal event', x, y, z])
    csv_data = '\n'.join([','.join(map(str, r)) for r in rows]).encode('utf-8')
    return send_file(io.BytesIO(csv_data), mimetype='text/csv', as_attachment=True, download_name='events.csv')

@app.route('/api/export/report/<int:event_id>', methods=['GET'])
def export_report(event_id):
    events = []
    for sid_key, evts in events_data.items():
        for idx, e in enumerate(evts):
            events.append((idx + 1, e))
    match = next((e for eid, e in events if eid == event_id), None)
    if not match:
        return jsonify({'error': 'Event not found'}), 404
    pos = match.get('location', [0,0,0])
    ts = match['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(match['timestamp'], 'strftime') else str(match['timestamp'])
    content = f"Event Report\nID: {event_id}\nTimestamp: {ts}\nSource: Camera1\nType: {match.get('event_type')}\nDescription: Trash disposal event\nPosition: {pos}"
    return send_file(io.BytesIO(content.encode('utf-8')), mimetype='text/plain', as_attachment=True, download_name=f'Event_{event_id}_Report.txt')

if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_PATH, UPLOAD_FOLDER), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, EVIDENCE_FOLDER), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, REPORT_FOLDER), exist_ok=True)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
