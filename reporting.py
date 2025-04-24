import os
import cv2
import shutil
from datetime import datetime
import csv
from pathlib import Path
import config  # Import config to access global variables

class Reporter:
    def __init__(self, evidence_path, report_path):
        """Initialize with paths for evidence and reports."""
        self.evidence_path = Path(evidence_path)
        self.report_path = Path(report_path)
        self.evidence_path.mkdir(parents=True, exist_ok=True)
        self.report_path.mkdir(parents=True, exist_ok=True)

    def save_evidence(self, event, frame, frame_count):
        """Save video clip as evidence based on current frame and count."""
        timestamp_str = event['timestamp'].strftime('%Y%m%d_%H%M%S')
        folder = self.evidence_path / f"event_{timestamp_str}_{event['vehicle_id']}"
        folder.mkdir(parents=True, exist_ok=True)
        video_path = config.video_path  # Access video_path from config
        if not video_path:
            print("Error: video_path not set in config")
            return None
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path} for evidence")
            return None
        
        # Position to 5 seconds before the event
        start_frame = max(0, frame_count - 100)  # 5s at 20 FPS
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(folder / 'clip.mp4'), fourcc, 20.0, (frame.shape[1], frame.shape[0]))
        for _ in range(200):  # 10 seconds total (5s before + 5s after)
            ret, f = cap.read()
            if ret:
                out.write(f)
        out.release()
        cap.release()
        evidence_path = str(folder / 'clip.mp4')
        shutil.copy(video_path, folder / 'source_video.mp4')  # Backup source
        return evidence_path

    def export_events(self, events_data, camera_id, frame, frame_count):
        """Export events to a CSV report with evidence links."""
        if not events_data:
            return None
        report_file = self.report_path / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{camera_id}.csv"
        with open(report_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Camera ID', 'Vehicle ID', 'Event Type', 'Location', 'Velocity', 'Evidence'])
            for event in events_data:
                evidence_path = self.save_evidence(event, frame, frame_count)
                if evidence_path:
                    writer.writerow([
                        event['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        camera_id,
                        event['vehicle_id'],
                        event['event_type'],
                        str(event['location']),
                        event['velocity'],
                        evidence_path
                    ])
                else:
                    writer.writerow([
                        event['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        camera_id,
                        event['vehicle_id'],
                        event['event_type'],
                        str(event['location']),
                        event['velocity'],
                        'Evidence generation failed'
                    ])
        return str(report_file)