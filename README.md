Illegal Trash Dumping Detection by Vehicles and Alerting System
Overview
This project implements a system to detect illegal trash dumping by vehicles using video surveillance. It leverages deep learning models (YOLOv8 and MiDaS) for object detection and depth estimation, combined with optical flow and tracking algorithms to identify disposal events. The system generates reports (CSV and Excel) with evidence (video clips and images) and provides real-time visualization with multiple modes (normal, optical flow, depth).
Features

Object Detection: Detects vehicles, trash, and bins using YOLOv8 models.
Event Detection: Identifies throwing, unloading, hidden disposal, and confirmed disposal events based on motion, depth, and vehicle state.
Visualization: Supports multiple visualization modes (normal, optical flow, depth) with overlays for detections, tracks, and events.
Reporting: Generates detailed reports with timestamps, locations, and evidence (before/after images, video clips).
Web Interface: A Flask-based web application for uploading videos and viewing processed results (in app.py).

Requirements

Python: 3.8 or higher
Dependencies:pip install numpy opencv-python torch torchvision ultralytics pandas openpyxl flask flask-cors flask-socketio


Hardware:
CPU with at least 8GB RAM (GPU optional for faster YOLO inference)
Sufficient storage for video outputs and evidence files


Models:
Pre-trained YOLOv8 model for vehicles (e.g., yolov8m.pt)
Custom-trained YOLO model for trash detection (e.g., 100epochv2.pt)



Installation

Clone the Repository:
git clone <repository-url>
cd <repository-directory>


Install Dependencies:
pip install -r requirements.txt

If requirements.txt is not provided, install the packages listed above.

Download Models:

Download yolov8m.pt from the Ultralytics YOLOv8 repository.
Place your custom trash detection model (e.g., 100epochv2.pt) in the models/ directory.


Directory Setup:Ensure the following directories exist:

evidence/: For storing video clips and images
reports/: For storing CSV and Excel reports
videos/: For uploaded videos (used by app.py)Create them manually or run the code, which will create them automatically.



Usage
Command-Line Interface (main.py)
Process a video file to detect disposal events and generate reports:
python main.py <video_path> <vehicle_model_path> <trash_model_path>

Example:
python main.py input_video.mp4 models/yolov8m.pt models/100epochv2.pt


Output:
Video: output.avi with annotated detections and events
Reports: CSV and Excel files in reports/ with event details
Evidence: Images and video clips in evidence/


Controls:
q: Quit
n: Normal visualization mode
o: Optical flow mode
d: Depth visualization mode



Web Interface (app.py)
Run the Flask web application to upload videos and view results:
python app.py


Access the interface at http://localhost:5000.
Upload a .mp4 video and specify a camera ID.
View real-time frame updates and download the generated report.

File Structure
project_directory/
├── main.py                 # Main script for video processing
├── app.py                  # Flask web application
├── detection.py            # Object detection using YOLOv8
├── tracking.py             # Object tracking with SORT algorithm
├── events.py               # Event detection logic
├── visualization_manager.py # Visualization of detections and events
├── depth_visualization.py  # Depth estimation using MiDaS
├── reporting.py            # Report generation (CSV, Excel)
├── config.py               # Configuration variables
├── models/                 # Directory for YOLO models
├── evidence/               # Directory for evidence files
├── reports/                # Directory for report files
├── videos/                 # Directory for uploaded videos
└── README.md               # Project documentation

Key Components

Detector (detection.py): Uses YOLOv8 for vehicle and trash detection, with confirmation logic for reliable detection.
Tracker (tracking.py): Implements SORT for tracking objects across frames, maintaining IDs and states (moving, slowing, stopped).
EventDetector (events.py): Detects disposal events by analyzing motion (optical flow), depth changes, and vehicle behavior.
VisualizationManager (visualization_manager.py): Renders annotations (bounding boxes, IDs, events) with customizable modes.
DepthVisualizer (depth_visualization.py): Generates depth maps using MiDaS for depth-based event detection.
Reporter (reporting.py): Exports events to CSV and Excel, saving evidence (images, video clips).
Web App (app.py): Provides a user-friendly interface for video processing and result visualization.

Notes

Model Paths: Ensure <vehicle_model_path> and <trash_model_path> point to valid YOLO model files.
Video Format: Input videos should be in a compatible format (e.g., .mp4). Output videos use the MJPG codec (output.avi).
Depth Mode: Requires significant memory due to MiDaS model inference.
Error Handling: Check console output for errors related to video loading, model initialization, or file permissions.
Performance: Processing speed depends on hardware and video resolution. Use a GPU for faster YOLO inference.

Troubleshooting

"np not defined": Ensure numpy is installed (pip install numpy).
Video Output Issues: Verify that the output video (output.avi) is not empty. If corrupted, check codec compatibility (MJPG is used).
Excel Report Issues: Ensure openpyxl is installed and that evidence/ and reports/ directories are writable.
Model Errors: Confirm that YOLO model files are in the correct path and format.
Depth Visualization Crash: If depth mode fails, check for sufficient memory and valid torch installation.

References
For the IEEE-formatted references used in the project report, see the project documentation or the REFERENCES section in the report. Key citations include:

YOLOv8 documentation: Ultralytics YOLOv8
MiDaS depth estimation: Ranftl et al., "Towards Robust Monocular Depth Estimation," IEEE Trans. Pattern Anal. Mach. Intell., 2022.

License
This project is licensed under the MIT License. See the LICENSE file for details (if provided).
Contact
For issues or contributions, please open an issue on the repository or contact the project maintainers.
