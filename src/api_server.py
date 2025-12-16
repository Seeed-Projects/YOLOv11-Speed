#!/usr/bin/env python3
"""
REST API server for YOLOv11 object detection with tracking and speed estimation.
Provides endpoints for controlling detection parameters and streaming video.
"""
import json
import threading
import time
import queue
import os
import sys
from flask import Flask, jsonify, request, Response, send_from_directory
from flask_cors import CORS
import cv2
import numpy as np

# Add src to path for importing modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Global variables to manage the detection process
is_running = False
stop_event = threading.Event()  # Event to signal stop
current_config = {
    "video_source": "camera",           # "camera" or video file path
    "confidence_threshold": 0.25,       # 0.0 to 1.0 (can be updated while running)
    "pixel_distance_mm": 10.0,          # millimeters per pixel (can be updated in real-time)
    "enable_tracking": True,             # requires restart
    "enable_speed_estimation": True,     # requires restart
    "target_labels": ["person", "car"], # requires restart
    "enable_loitering_detection": False, # can be updated in real-time
    "loitering_threshold": 10.0         # seconds, can be updated in real-time
}

# Video frame queue for streaming (increased size to reduce flickering)
frame_queue = queue.Queue(maxsize=30)
last_config_update = time.time()

# Configuration locks for thread safety
config_lock = threading.Lock()

app = Flask(__name__, static_folder='../frontend')
CORS(app)  # Enable CORS for cross-origin requests

def create_detection_pipeline(config):
    """Create a detection pipeline that can handle real-time configuration updates."""
    global is_running, stop_event
    from object_detection import run_inference_pipeline
    from utils.toolbox import get_labels, load_json_file
    from functools import partial
    from types import SimpleNamespace
    import queue as q
    import threading
    from tracker.byte_tracker import BYTETracker
    from utils.hailo_inference import HailoInfer
    from utils.toolbox import init_input_source, preprocess, visualize, FrameRateTracker
    from object_detection_post_process import inference_result_handler
    from speed_estimation import SpeedEstimationManager

    # Convert pixel distance from mm to m for the detection pipeline
    pixel_distance_m = config["pixel_distance_mm"] / 1000.0

    # Initialize cap variable to avoid UnboundLocalError in finally block
    cap = None

    try:
        # Get labels
        labels_path = "src/config/coco.txt"
        labels = get_labels(labels_path)

        # Load base config
        config_path = "src/config/config.json"
        base_config_data = load_json_file(config_path)

        # Initialize input source
        from utils.toolbox import init_input_source
        video_source = config["video_source"] if config["video_source"] != "camera" else "camera"
        cap, images = init_input_source(
            video_source,
            1,
            "hd"
        )

        # Initialize components based on config
        tracker = None
        if config["enable_tracking"]:
            tracker_config = base_config_data.get("visualization_params", {}).get("tracker", {})
            tracker = BYTETracker(SimpleNamespace(**tracker_config))

        fps_tracker = FrameRateTracker()
        input_queue = q.Queue()
        output_queue = q.Queue()

        # Initialize speed estimation if needed
        speed_manager = None
        if config["enable_speed_estimation"] and config["enable_tracking"]:
            fps = 30.0  # Default FPS for camera
            # If it's a video file, try to get actual FPS
            if cap is not None and video_source != "camera":
                video_fps = cap.get(cv2.CAP_PROP_FPS)
                if video_fps > 0:
                    fps = video_fps
            speed_manager = SpeedEstimationManager(pixel_distance=pixel_distance_m, fps=fps)

        # Initialize loitering detection manager to persist across frames
        from object_detection_post_process import LoiteringDetectionManager
        fps_for_loitering = speed_manager.fps if speed_manager else 30.0
        loitering_manager = LoiteringDetectionManager(loitering_threshold=config.get("loitering_threshold", 10.0),
                                                       fps=fps_for_loitering)

        # Create a callback that can access the global config for real-time updates
        def post_process_callback_with_realtime_config(original_frame, infer_results):
            # Check if stop was requested
            if stop_event.is_set():
                return original_frame  # Return original frame if stopping

            # Get current config values for this processing
            with config_lock:
                current_confidence = current_config["confidence_threshold"]
                current_pixel_distance = current_config["pixel_distance_mm"] / 1000.0  # Convert to meters
                current_loitering_threshold = current_config.get("loitering_threshold", 10.0)
                current_loitering_enabled = current_config.get("enable_loitering_detection", False)

            # Update loitering manager threshold if changed
            loitering_manager.loitering_threshold = current_loitering_threshold
            fps_for_update = speed_manager.fps if speed_manager else 30.0
            loitering_manager.frame_threshold = current_loitering_threshold * fps_for_update

            # Update config data with current confidence
            config_data = base_config_data.copy()
            if "visualization_params" not in config_data:
                config_data["visualization_params"] = {}
            config_data["visualization_params"]["score_thres"] = current_confidence

            # Process the frame with the actual detection pipeline
            processed_frame = inference_result_handler(
                original_frame, infer_results, labels, config_data,
                tracker=tracker, camera_width=640, camera_height=480,
                pixel_distance=current_pixel_distance,  # Use current pixel distance
                speed_estimation=config["enable_speed_estimation"],
                speed_manager=speed_manager,
                target_labels=config["target_labels"],
                loitering_detection=current_loitering_enabled,
                loitering_manager=loitering_manager,
                loitering_threshold=current_loitering_threshold,
                enable_person_only="person" in config["target_labels"]
            )

            # Put the processed frame in our queue for streaming
            try:
                if not frame_queue.full():
                    frame_queue.put_nowait(processed_frame.copy())
                else:
                    # Drop oldest frame if queue is full
                    try:
                        frame_queue.get_nowait()
                        frame_queue.put_nowait(processed_frame.copy())
                    except:
                        pass
            except:
                pass  # Queue is full, skip frame

            return processed_frame

        # For real-time config updates, we'll need to modify the core object detection pipeline
        # which is complex. Instead, we'll restart the pipeline when config changes are received
        # but for the confidence and pixel distance, we'll implement a dynamic callback

        # Initialize Hailo inference
        hailo_inference = HailoInfer("src/models/yolov11n.hef", 1)
        height, width, _ = hailo_inference.get_input_shape()

        # Create processing threads (modified to support real-time updates)
        preprocess_thread = threading.Thread(
            target=preprocess,
            args=(images, cap, 1, input_queue, width, height)
        )

        def run_visualize_with_updates(output_queue, cap, save_stream_output, output_dir, fps_tracker):
            """Run visualization loop with ability to update config"""
            while is_running and not stop_event.is_set():
                try:
                    item = output_queue.get(timeout=0.5)  # shorter timeout
                    if item is None:  # End signal
                        break

                    original_frame, infer_results = item
                    processed_frame = post_process_callback_with_realtime_config(original_frame, infer_results)

                    # Check if stop was requested
                    if stop_event.is_set():
                        break

                    # Ensure frame gets to the stream even if there are processing delays
                    try:
                        if not frame_queue.full():
                            frame_queue.put_nowait(processed_frame.copy())
                        else:
                            # Drop oldest frame if queue is full
                            try:
                                frame_queue.get_nowait()
                                frame_queue.put_nowait(processed_frame.copy())
                            except:
                                pass
                    except:
                        pass  # Queue is full, skip frame

                except q.Empty:
                    continue  # Check is_running again
                except Exception as e:
                    print(f"Visualization error: {e}")
                    import traceback
                    traceback.print_exc()
                    break

        postprocess_thread = threading.Thread(
            target=run_visualize_with_updates,
            args=(output_queue, cap, False, "./output", fps_tracker)
        )

        def infer_with_updates(hailo_inference, input_queue, output_queue):
            """Inference function with config updates support."""
            from functools import partial

            def inference_callback(
                completion_info,
                bindings_list: list,
                input_batch: list,
                output_queue: q.Queue
            ) -> None:
                """Process inference results and put them in output queue."""
                if completion_info.exception:
                    print(f'Inference error: {completion_info.exception}')
                else:
                    for i, bindings in enumerate(bindings_list):
                        if len(bindings._output_names) == 1:
                            result = bindings.output().get_buffer()
                        else:
                            result = {
                                name: np.expand_dims(
                                    bindings.output(name).get_buffer(), axis=0
                                )
                                for name in bindings._output_names
                            }
                        output_queue.put((input_batch[i], result))

            while is_running and not stop_event.is_set():
                try:
                    next_batch = input_queue.get(timeout=1)  # Use timeout to allow checking is_running
                    if not next_batch:
                        break  # Stop signal received

                    input_batch, preprocessed_batch = next_batch

                    # Prepare the callback for handling the inference result
                    inference_callback_fn = partial(
                        inference_callback,
                        input_batch=input_batch,
                        output_queue=output_queue
                    )

                    # Check if stop was requested before running inference
                    if stop_event.is_set():
                        break

                    # Run async inference
                    hailo_inference.run(preprocessed_batch, inference_callback_fn)

                except q.Empty:
                    continue  # Check is_running again
                except Exception as e:
                    print(f"Inference error: {e}")
                    import traceback
                    traceback.print_exc()
                    break

            # Release resources and context
            try:
                hailo_inference.close()
            except:
                pass

        infer_thread = threading.Thread(
            target=infer_with_updates,
            args=(hailo_inference, input_queue, output_queue)
        )

        # Create a separate thread for the preprocess function that can be interrupted
        def preprocess_with_stop(images, cap, batch_size, input_queue, width, height):
            """Preprocess with stop signal support."""
            from utils.toolbox import preprocess_images, preprocess_from_cap, default_preprocess
            from utils.toolbox import validate_images, divide_list_to_batches
            import cv2
            import queue

            preprocess_fn = default_preprocess

            if images is not None:
                # Handle images case
                try:
                    validate_images(images, batch_size)
                except ValueError as e:
                    print(f"Image validation error: {e}")
                    return
                preprocess_images(images, batch_size, input_queue, width, height, preprocess_fn)
            else:
                # Handle camera/video case - implement stop signal support
                frames = []
                processed_frames = []

                while is_running and not stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        # Try to reinitialize the camera if read fails
                        # This can happen if the camera is disconnected or has an error
                        time.sleep(0.1)
                        continue

                    frames.append(frame)
                    processed_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    processed_frame = preprocess_fn(processed_frame, width, height)
                    processed_frames.append(processed_frame)

                    if len(frames) == batch_size:
                        try:
                            # Check stop event before putting to queue
                            if stop_event.is_set():
                                break
                            input_queue.put((frames, processed_frames), timeout=0.5)
                            processed_frames, frames = [], []
                        except queue.Full:
                            # If queue is full, skip this batch
                            processed_frames, frames = [], []
                            continue
                        except:
                            # Other exception, continue the loop
                            processed_frames, frames = [], []
                            continue

        preprocess_thread = threading.Thread(
            target=preprocess_with_stop,
            args=(images, cap, 1, input_queue, width, height)
        )

        # Start threads
        preprocess_thread.start()
        postprocess_thread.start()
        infer_thread.start()

        fps_tracker.start()

        # Wait for completion with stop support
        preprocess_thread.join(timeout=1)  # Use timeout to allow interruption
        if stop_event.is_set():
            # Force stop all threads when stop event is set
            try:
                # Signal postprocess thread to exit by pushing None to output queue
                output_queue.put(None, timeout=1)  # Signal process thread to exit
                preprocess_thread.join(timeout=1)  # Wait for preprocess thread to finish
                infer_thread.join(timeout=1)      # Wait for inference thread to finish
                postprocess_thread.join(timeout=1)  # Wait for postprocess thread to finish
            except:
                pass  # If any thread doesn't stop gracefully, continue
        else:
            infer_thread.join()
            output_queue.put(None)  # Signal process thread to exit
            postprocess_thread.join()

        if fps_tracker:
            print(fps_tracker.frame_rate_summary())

    except Exception as e:
        print(f"Error in detection pipeline: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Release camera capture if it exists
        if cap is not None:
            try:
                cap.release()
            except:
                pass
        is_running = False
        stop_event.clear()  # Reset the stop event


def enforce_tracking_speed_estimation_rule(config):
    """
    Enforce the rule: if speed estimation is enabled, tracking must also be enabled.

    Args:
        config (dict): Configuration dictionary to validate and adjust

    Returns:
        dict: Adjusted configuration following the rule
    """
    updated_config = config.copy()

    # Determine the final speed estimation state based on the new config and current config
    final_speed_estimation = config.get('enable_speed_estimation',
                                       current_config.get('enable_speed_estimation', False))

    # If speed estimation will be enabled (either being set or already is), tracking must also be enabled
    if final_speed_estimation:
        updated_config['enable_tracking'] = True

    return updated_config


def update_config_realtime(config_updates):
    """Update configuration parameters that can be changed in real-time."""
    global current_config, last_config_update

    # These parameters can be updated in real-time
    real_time_params = ['confidence_threshold', 'pixel_distance_mm']

    with config_lock:
        for param, value in config_updates.items():
            if param in real_time_params:
                current_config[param] = value

    last_config_update = time.time()

# Video stream generator
def generate_video_stream():
    """Generator function to create an MJPEG video stream."""
    # Keep track of the last frame to send if new frames are not available
    last_frame = None
    while True:
        try:
            if not frame_queue.empty():
                frame = frame_queue.get_nowait()  # Use nowait to avoid blocking
                last_frame = frame  # Keep the last frame for consistency

                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    frame_bytes = buffer.tobytes()

                    # Yield the frame in multipart format for MJPEG stream
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # If no new frame is available but we have a previous frame, reuse it
                if last_frame is not None:
                    ret, buffer = cv2.imencode('.jpg', last_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                # Small delay to control frame rate if no new frames
                time.sleep(0.033)  # ~30 FPS when no new frames

        except Exception as e:
            print(f"Stream generation error: {e}")
            time.sleep(0.1)  # Brief pause before continuing

@app.route('/')
def index():
    """Serve the main web page."""
    try:
        return send_from_directory('../frontend', 'index.html')
    except FileNotFoundError:
        # Return a simple error page if frontend files don't exist
        return '<h1>Frontend files not found. Please ensure the frontend directory exists with index.html</h1>'

@app.route('/api/status')
def get_status():
    """Get the current detection status and configuration."""
    global is_running, current_config
    
    # Calculate approximate FPS (in a real implementation, this would come from the detection process)
    fps_value = 30.0 if is_running else 0.0
    
    return jsonify({
        "running": is_running,
        "config": current_config,
        "fps": fps_value
    })

@app.route('/api/start', methods=['POST'])
def start_detection():
    """Start the detection pipeline."""
    global is_running, current_config, stop_event

    if is_running:
        return jsonify({"error": "Detection is already running"}), 400

    # Reset the stop event when starting
    stop_event.clear()

    # Update config from request
    new_config = request.json or {}

    # Enforce the rule: if speed estimation is enabled, tracking must also be enabled
    new_config = enforce_tracking_speed_estimation_rule(new_config)

    current_config.update(new_config)

    # Start the actual detection pipeline in a separate thread
    is_running = True
    detection_thread = threading.Thread(target=create_detection_pipeline, args=(current_config,))
    detection_thread.daemon = True
    detection_thread.start()

    return jsonify({
        "message": "Detection started successfully",
        "status": "running"
    })

@app.route('/api/stop', methods=['POST'])
def stop_detection():
    """Stop the detection pipeline."""
    global is_running, stop_event

    if not is_running:
        return jsonify({"error": "Detection is not running"}), 400

    # Set the stop event to signal all threads to stop
    stop_event.set()
    is_running = False

    # Clear the frame queue to clear old frames
    try:
        while not frame_queue.empty():
            frame_queue.get_nowait()
    except:
        pass

    return jsonify({
        "message": "Detection stopped successfully",
        "status": "stopped"
    })

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Get or update the current configuration."""
    global current_config
    
    if request.method == 'GET':
        return jsonify(current_config)
    
    elif request.method == 'POST':
        # Update configuration with real-time parameters
        new_config = request.json or {}

        # Enforce the rule: if speed estimation is enabled, tracking must also be enabled
        new_config = enforce_tracking_speed_estimation_rule(new_config)

        update_config_realtime(new_config)

        return jsonify({
            "message": "Configuration updated",
            "config": current_config
        })

@app.route('/api/video_stream')
def video_stream():
    """MJPEG video stream endpoint."""
    return Response(
        generate_video_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    """Upload video file to the server."""
    try:
        if 'video_file' not in request.files:
            return jsonify({"success": False, "error": "No video file provided"}), 400

        file = request.files['video_file']

        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        # Check if file has a valid video extension
        allowed_extensions = {'mp4', 'avi', 'mov', 'mkv', 'm4v', 'wmv', 'flv', 'webm'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({"success": False, "error": "Invalid file type"}), 400

        # Create videos directory if it doesn't exist
        videos_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'videos')
        os.makedirs(videos_dir, exist_ok=True)

        # Save the file
        filename = f"uploaded_{int(time.time())}_{file.filename}"
        file_path = os.path.join(videos_dir, filename)
        file.save(file_path)

        # Return success with the file path relative to the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Two levels up from src/api_server.py = project root
        relative_path = os.path.relpath(file_path, project_root)

        return jsonify({
            "success": True,
            "file_path": relative_path,
            "message": "Video uploaded successfully"
        })

    except Exception as e:
        print(f"Error uploading video: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)