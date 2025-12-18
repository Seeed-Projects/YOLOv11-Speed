# YOLOv11 Hailo Tracker

YOLOv11-Hailo-Tracker is a comprehensive real-time object detection, tracking, and speed estimation system optimized for Hailo AI accelerators. This project enables efficient detection of objects (with focus on persons and vehicles) with simultaneous tracking and speed calculation capabilities.

## ✨ Features

- **Real-time Object Detection**: Using optimized YOLOv11 models for fast inference
- **Multi-Object Tracking**: BYTE (ByteTrack) tracking algorithm for consistent object identification across frames
- **Speed Estimation**: Advanced speed calculation for tracked objects using pixel-to-real-world distance conversion
- **Flexible Input Support**: Images, videos, and camera streams
- **Configurable Labels**: Support for detecting specific object classes (default: person, car)

## 🛠️ Requirements

### Hardware
|                                                reComputer AI R2130                                              |
| :----------------------------------------------------------------------------------------------------------------: |
| ![Raspberry Pi AI Kit](https://media-cdn.seeedstudio.com/media/catalog/product/cache/bb49d3ec4ee05b6f018e93f896b8a25d/1/_/1_24_1.jpg) |
| [**Purchase Now**](https://www.seeedstudio.com/reComputer-AI-R2130-12-p-6368.html?utm_source=PiAICourse&utm_medium=github&utm_campaign=Course) |

|                                                reComputer AI Industrial R2135                                             |
| :----------------------------------------------------------------------------------------------------------------: |
| ![Raspberry Pi AI Kit](https://media-cdn.seeedstudio.com/media/catalog/product/cache/bb49d3ec4ee05b6f018e93f896b8a25d/i/m/image-_r235.jpeg) |
| [**Purchase Now**](https://www.seeedstudio.com/reComputer-AI-Industrial-R2135-12-p-6432.html?utm_source=PiAICourse&utm_medium=github&utm_campaign=Course) |

|                                                reComputer Industrial R2045-12                                             |
| :----------------------------------------------------------------------------------------------------------------: |
| ![Raspberry Pi AI Kit](https://media-cdn.seeedstudio.com/media/catalog/product/cache/bb49d3ec4ee05b6f018e93f896b8a25d/1/-/1-recomputer-industrail-r2000_1.jpg) |
| [**Purchase Now**](https://www.seeedstudio.com/reComputer-Industrial-R2045-12-p-6544.html?utm_source=PiAICourse&utm_medium=github&utm_campaign=Course) |


|                                                reComputer Industrial R2045-12                                             |
| :----------------------------------------------------------------------------------------------------------------: |
| ![Raspberry Pi AI Kit](https://media-cdn.seeedstudio.com/media/catalog/product/cache/bb49d3ec4ee05b6f018e93f896b8a25d/i/m/image_6.jpg) |
| [**Purchase Now**](https://www.seeedstudio.com/reComputer-Industrial-R2135-12-p-6547.html?utm_source=PiAICourse&utm_medium=github&utm_campaign=Course) |


- Camera or video input (for streaming applications)

### Software
- **Python**: 3.8 or higher
- **HailoRT**: Version 4.22.0 or compatible
- **Dependencies**: Listed in `requirements.txt`

### System Dependencies
- Linux operating system (tested on Ubuntu)
- OpenCV-compatible camera drivers (for camera input)
- Graphics acceleration (for visualization)

## 📦 Installation

### Prerequisites
1. Install Hailo PCIe driver and PyHailoRT from the [Hailo website](https://hailo.ai/developer-zone/)
2. Ensure your system has a compatible Hailo accelerator installed

### Setup Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/YOLOv11-Speed.git
   cd YOLOv11-Speed
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv --system-site-packages
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the project

  ```bash
  python run_api.py
  ```
5. Access `localhost:5000` to reach the frontend and configure settings.

![alt text](./img/image.png)


## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- YOLOv11 object detection models
- BYTE (ByteTrack) multi-object tracking algorithm
- Hailo Technologies for AI acceleration
- OpenCV for computer vision operations

## 💞 Top contributors:

<a href="https://github.com/Seeed-Projects/YOLOv11-Hailo-Tracker/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Seeed-Projects/YOLOv11-Hailo-Tracker" alt="contrib.rocks image" />
</a>

## 🌟 Star History

![Star History Chart](https://api.star-history.com/svg?repos=Seeed-Projects/YOLOv11-Hailo-Tracker&type=Date)
