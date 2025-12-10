# YOLOv11 Object Detection - Docker Guide

This project can be containerized using Docker. Here's how to build and run the Docker image.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, but recommended)
- Hailo hardware drivers installed on your host system (for hardware acceleration)

## Building the Docker Image

To build the Docker image, run:

```bash
docker build -t yolov11-detection .
```

The Dockerfile creates a virtual environment with `--system-site-packages` which allows the container to inherit system packages while maintaining a clean Python environment for the application dependencies.

## Running the Container

### Basic Usage

```bash
# Run with default help command
docker run --rm yolov11-detection

# Run detection on sample image
docker run --rm -v $(pwd)/output:/app/output yolov11-detection -i src/data/bus.jpg -n src/models/yolov8n.hef
```

### With Docker Compose

```bash
# Show help
docker-compose run yolov11-detection

# Run detection
docker-compose run yolov11-detection-run
```

## Hardware Access (Important for Hailo)

This project is designed to work with Hailo AI accelerators. To access Hailo hardware from within the container, you may need to run the container with additional privileges or device access:

```bash
# Example with device access (adjust based on your Hailo setup)
docker run --device=/dev/hailo*:/dev/hailo --rm -v $(pwd)/output:/app/output yolov11-detection -i src/data/bus.jpg -n src/models/yolov8n.hef

# Or with privileged access (use with caution)
docker run --privileged --rm -v $(pwd)/output:/app/output yolov11-detection -i src/data/bus.jpg -n src/models/yolov8n.hef
```

## Configuration

The containerized application uses the same configuration as the original project:

- Input files should be mounted to `/app/src/data` inside the container
- Model files should be mounted to `/app/src/models` inside the container
- Output will be saved to `/app/output` inside the container (mapped to local `./output`)

## Docker Compose Services

The `docker-compose.yml` file defines two services:

- `yolov11-detection`: Default service for showing help
- `yolov11-detection-run`: Service pre-configured for running detection on sample data

## Customization

To use your own models or input data:

1. Place your models in the `src/models` directory
2. Place your input data in the `src/data` directory
3. Update your docker run command to point to your files

Example:
```bash
docker run --rm \
  -v $(pwd)/my_data:/app/my_data \
  -v $(pwd)/my_models:/app/my_models \
  -v $(pwd)/output:/app/output \
  yolov11-detection \
  -i my_data/my_image.jpg \
  -n my_models/my_model.hef
```

## Troubleshooting

1. **Hailo hardware not accessible**: Make sure Hailo drivers are installed on the host system and appropriate device mappings are configured.

2. **Permission errors**: Ensure the container has necessary permissions to read input files and write output files.

3. **Missing dependencies**: If you encounter dependency issues, you may need to modify the Dockerfile to install the HailoRT package specific to your hardware.

## Notes

- The Docker image does not include the HailoRT driver itself, as this typically needs to be installed on the host system
- For production use, consider security implications of running containers with device access or privileged mode
- Model files (HEF) and other large assets are not included in the image to keep it lightweight - they should be mounted at runtime