import os
import cv2
import shutil
import numpy as np
from datetime import datetime
import csv
import pandas as pd
from pathlib import Path
import config  # Import config to access global variables
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font, Alignment, PatternFill

class Reporter:
    def __init__(self, evidence_path, report_path):
        """Initialize with paths for evidence and reports."""
        self.evidence_path = Path(evidence_path)
        self.report_path = Path(report_path)
        self.evidence_path.mkdir(parents=True, exist_ok=True)
        self.report_path.mkdir(parents=True, exist_ok=True)
        # Create temp directory for screenshot images used in Excel
        self.temp_img_path = Path('temp_images')
        self.temp_img_path.mkdir(parents=True, exist_ok=True)

    def save_evidence(self, event, frame, frame_count):
        """Save video clip and screenshot images as evidence based on current frame and count."""
        timestamp_str = event['timestamp'].strftime('%Y%m%d_%H%M%S')
        folder = self.evidence_path / f"event_{timestamp_str}_{event['vehicle_id']}"
        folder.mkdir(parents=True, exist_ok=True)
        
        # Save the current frame as an image
        cv2.imwrite(str(folder / 'detection.jpg'), frame)
        
        # Access video path from config
        video_path = getattr(config, 'video_path', None)
        if not video_path:
            print("Error: video_path not set in config")
            return str(folder / 'detection.jpg'), None  # Return at least the frame image
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path} for evidence")
            return str(folder / 'detection.jpg'), None
        
        # Position to 5 seconds before the event
        fps = cap.get(cv2.CAP_PROP_FPS)
        start_frame = max(0, frame_count - int(5 * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # Set up video writer with proper codec
        fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        clip_path = str(folder / 'clip.mp4')
        out = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
        
        # Capture before image (beginning of clip)
        ret, before_frame = cap.read()
        before_img_path = str(folder / 'before.jpg')
        if ret:
            cv2.imwrite(before_img_path, before_frame)
        
        # Write video frames for 10 seconds (5s before + 5s after)
        frames_to_capture = int(10 * fps)
        middle_frame = int(frames_to_capture / 2)
        after_frame = None
        
        for i in range(frames_to_capture):
            ret, f = cap.read()
            if not ret:
                break
                
            # Capture the middle frame as "after" image
            if i == middle_frame:
                after_frame = f.copy()
                after_img_path = str(folder / 'after.jpg')
                cv2.imwrite(after_img_path, after_frame)
                
            out.write(f)
            
        out.release()
        cap.release()
        
        # Clean up the source copy to save space
        # Instead of copying the whole source video, just note the path
        with open(folder / 'source_video_path.txt', 'w') as f:
            f.write(video_path)
            
        return before_img_path, after_img_path

    def export_events(self, events_data, camera_id, frame, frame_count):
        """Export events to CSV and Excel reports with evidence links."""
        if not events_data:
            return None
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_base = f"report_{timestamp}_{camera_id}"
        
        # CSV report (keep for compatibility)
        csv_file = self.report_path / f"{report_base}.csv"
        csv_data = []
        
        # Excel report
        excel_file = self.report_path / f"{report_base}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Waste Disposal Events"
        
        # Set up Excel headers with formatting
        headers = ['Timestamp', 'Camera ID', 'Vehicle ID', 'Event Type', 'Location', 
                  'Velocity', 'Confidence', 'Before Image', 'After Image', 'Evidence Path']
        
        # Apply header formatting
        header_fill = PatternFill(start_color="66CCFF", end_color="66CCFF", fill_type="solid")
        header_font = Font(bold=True, size=12)
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
        
        # Set column widths
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[chr(64 + col)].width = 18  # ASCII 'A' is 65
        
        # Excel image column width needs to be wider
        ws.column_dimensions['H'].width = 30
        ws.column_dimensions['I'].width = 30
        
        # Process events
        excel_row = 2  # Start after header
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for event in events_data:
                # Save evidence and get image paths
                before_img_path, after_img_path = self.save_evidence(event, frame, frame_count)
                
                # Common data for both CSV and Excel
                event_data = [
                    event['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    camera_id,
                    event['vehicle_id'],
                    event['event_type'],
                    str(event['location']),
                    f"{event['velocity']:.2f}",
                    f"{event.get('confidence', 0.0):.2f}",
                ]
                
                # Add to CSV
                csv_row = event_data.copy()
                csv_row.extend([before_img_path, after_img_path, before_img_path.replace('before.jpg', 'clip.mp4') if before_img_path else 'Evidence generation failed'])
                writer.writerow(csv_row)
                csv_data.append(csv_row)
                
                # Add to Excel
                for col, value in enumerate(event_data, 1):
                    ws.cell(row=excel_row, column=col, value=value)
                
                # Add before image
                if before_img_path and os.path.exists(before_img_path):
                    try:
                        img = XLImage(before_img_path)
                        img.width = 300
                        img.height = 200
                        ws.add_image(img, f'H{excel_row}')
                    except Exception as e:
                        print(f"Failed to add before image: {e}")
                        ws.cell(row=excel_row, column=8, value="Image failed to load")
                
                # Add after image
                if after_img_path and os.path.exists(after_img_path):
                    try:
                        img = XLImage(after_img_path)
                        img.width = 300
                        img.height = 200
                        ws.add_image(img, f'I{excel_row}')
                    except Exception as e:
                        print(f"Failed to add after image: {e}")
                        ws.cell(row=excel_row, column=9, value="Image failed to load")
                
                # Add evidence path
                evidence_path = before_img_path.replace('before.jpg', 'clip.mp4') if before_img_path else 'Evidence generation failed'
                ws.cell(row=excel_row, column=10, value=evidence_path)
                
                excel_row += 1
        
        # Save Excel file
        try:
            wb.save(excel_file)
            print(f"Excel report generated: {excel_file}")
        except Exception as e:
            print(f"Failed to save Excel report: {e}")
        
        # Return both file paths
        return {
            'csv': str(csv_file),
            'excel': str(excel_file),
            'events': csv_data
        }
        
    def cleanup_temp_files(self, older_than_days=7):
        """Clean up temporary files older than specified days."""
        cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 60 * 60)
        
        # Clean up temp image directory
        for file_path in self.temp_img_path.glob('*.jpg'):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    os.remove(file_path)
                    print(f"Removed old temp file: {file_path}")
                except Exception as e:
                    print(f"Failed to remove {file_path}: {e}")