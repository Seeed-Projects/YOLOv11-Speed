# YOLOv11 Object Detection and Tracking

This project provides real-time object detection and tracking using Hailo AI accelerators with YOLO models.

## Project Structure

```
yolov11_speed/
├── run_detection.py          # Main entry point to run the detection
├── requirements.txt          # Python dependencies
├── download_resources.sh     # Script to download models and sample data
├── README.md                 # This file
├── src/                      # Source code directory
│   ├── __init__.py
│   ├── object_detection.py              # Main detection script
│   ├── object_detection_post_process.py # Post-processing functions
│   ├── config/               # Configuration files
│   │   ├── __init__.py
│   │   ├── config.json       # Detection and tracking parameters
│   │   └── coco.txt          # COCO dataset labels
│   ├── data/                 # Sample data
│   │   ├── __init__.py
│   │   ├── bus.jpg           # Sample input image
│   │   └── full_mov_slow.mp4 # Sample input video
│   ├── models/               # HEF model files
│   │   ├── __init__.py
│   │   └── yolov11n.hef      # YOLOv11 model
│   ├── tracker/              # Object tracking modules
│   │   ├── __init__.py
│   │   ├── byte_tracker.py   # BYTE tracker implementation
│   │   ├── kalman_filter.py  # Kalman filter for tracking
│   │   ├── matching.py       # Track matching algorithms
│   │   └── basetrack.py      # Base tracking class
│   ├── utils/                # Utility functions
│   │   ├── __init__.py
│   │   ├── hailo_inference.py # Hailo inference wrapper
│   │   └── toolbox.py        # Common utilities
│   └── tests/                # Test files
│       └── __init__.py
```

## Requirements

- HailoRT 4.22.0
- Python 3.8+
- Dependencies listed in requirements.txt

## Installation

1. Install Hailo PCIe driver and PyHailoRT:
    - Download from the Hailo website

2. Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Download models and sample data:
    ```bash
    ./download_resources.sh --arch 8    # For Hailo-8
    # or
    ./download_resources.sh --arch 10   # For Hailo-10
    ```

## Usage

### Run detection on a single image:
```bash
python run_detection.py -i src/data/bus.jpg -n src/models/yolov11n.hef
```

### Run detection with tracking:
```bash
python run_detection.py -i src/data/bus.jpg -n src/models/yolov11n.hef --track
```

### Run detection on a video:
```bash
python run_detection.py -i src/data/full_mov_slow.mp4 -n src/models/yolov11n.hef
```

### Run detection on camera stream:
```bash
python run_detection.py -i camera -n src/models/yolov11n.hef --track
```

### Run detection with custom labels (e.g., bird, car, person):
```bash
python run_detection.py -i camera -n src/models/yolov11n.hef --track --speed-estimation --label bird car person
```

### Run detection with default labels (person and car):
```bash
python run_detection.py -i camera -n src/models/yolov11n.hef --track --speed-estimation
```

## Configuration

Parameters for detection and tracking can be adjusted in `src/config/config.json`:

- `score_thres`: Minimum confidence score to display detections
- `max_boxes_to_draw`: Maximum number of boxes to draw per frame
- `tracker`: Parameters for the BYTE tracker

## Output

The processed results are saved in the `output` directory by default.

## Notes

- The project supports YOLOv5, YOLOv6, YOLOv7, YOLOv8, YOLOv9, YOLOv10, and YOLOx models
- Only HEF files containing HailoRT Postprocess are supported
- Images formats supported: JPG, JPEG, PNG, BMP