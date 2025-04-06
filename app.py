from flask import Flask, request, jsonify, send_file
from detection import Detector
from tracking import Tracker
from events import EventDetector
from reporting import Reporter
import os
import cv2
from datetime import datetime
import io
import csv
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'videos'
app.config['EVIDENCE_FOLDER'] = 'evidence'
app.config['REPORT_FOLDER'] = 'reports'

# Initialize components
detector = Detector("models/yolov8m.pt", "./models/100epochv2.pt")
tracker = Tracker(distance_threshold=150, max_inactive=30)
event_detector = EventDetector(temporal_window=10, min_holding=15, min_disposal=20, min_throw=5, depth_threshold=50)
reporter = Reporter(app.config['EVIDENCE_FOLDER'], app.config['REPORT_FOLDER'], "Location1")
events_data = []  # Store events globally for now

def process_video(video_path):
    global events_data
    events_data = []
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        detections = detector.detect(frame)
        tracker.assign_ids(detections, frame_count)
        event_detector.process(tracker.tracking_data, detections, frame)
        events_data.extend(event_detector.events_data[-1:])  # Append new events
        frame_count += 1
    cap.release()
    reporter.export_events(events_data)  # Save evidence and generate report
    return events_data

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith('.mp4'):
        filename = secure_filename(file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(video_path)
        events = process_video(video_path)
        return jsonify({"eventsDetected": len(events), "events": events}), 200
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
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['EVIDENCE_FOLDER'], exist_ok=True)
    os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)