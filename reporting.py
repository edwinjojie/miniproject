import os
import cv2
from PIL import Image
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from datetime import datetime
import io

class Reporter:
    def __init__(self, evidence_path, report_path, location):
        """Initialize the Reporter with paths and location."""
        self.evidence_base = evidence_path
        self.report_base = report_path
        self.location = location
        self.evidence = []

    def save_evidence(self, event):
        """Save event frames as evidence."""
        folder = f"vehicle_{event['vehicle_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        path = os.path.join(self.evidence_base, folder)
        os.makedirs(path, exist_ok=True)
        for i, frame in enumerate(event["frames"]):
            cv2.imwrite(os.path.join(path, f"frame_{i:03d}.jpg"), frame)
        self.evidence.append({
            "path": path,
            "timestamp": event["timestamp"],
            "vehicle_id": event["vehicle_id"],
            "type": event["event_type"]
        })

    def export_events(self, events_data):
        """Export events to an Excel report with embedded images."""
        if not events_data:
            return None
        wb = Workbook()
        ws = wb.active
        headers = ["Timestamp", "Vehicle ID", "Type", "Location", "Frames"]
        ws.append(headers)
        for ev in events_data:
            self.save_evidence(ev)
            evidence_entry = self.evidence[-1]
            img_paths = [os.path.join(evidence_entry["path"], f) for f in os.listdir(evidence_entry["path"]) if f.endswith(".jpg")]
            img_cells = []
            for img_path in img_paths[:2]:
                img = Image.open(img_path)
                img.thumbnail((400, 300))
                bio = io.BytesIO()
                img.save(bio, format="PNG")
                excel_img = ExcelImage(bio)
                img_cells.append(excel_img)
            row = [
                evidence_entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                evidence_entry["vehicle_id"],
                evidence_entry["type"],
                self.location,
                len(img_paths)
            ]
            ws.append(row)
            for i, img in enumerate(img_cells, start=5):
                ws.column_dimensions[chr(64 + i)].width = 40
                ws.add_image(img, f"{chr(64 + i)}{ws.max_row}")
        report_path = os.path.join(self.report_base, f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx")
        wb.save(report_path)
        return report_path