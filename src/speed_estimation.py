"""
Speed estimation module for calculating vehicle/pedestrian speed using tracked object positions
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import time
from collections import deque


class SpeedEstimator:
    """
    Class to estimate speed of tracked objects based on pixel positions and real-world calibration
    """
    def __init__(self, pixel_distance: float = 0.01, fps: float = 30.0, max_history: int = 10):
        """
        Initialize speed estimator
        
        Args:
            pixel_distance (float): Real-world distance per pixel in meters
            fps (float): Frames per second of the video stream
            max_history (int): Maximum number of historical positions to store for speed calculation
        """
        self.pixel_distance = pixel_distance  # meters per pixel
        self.fps = fps
        self.max_history = max_history
        
        # Store historical positions for each track ID
        self.position_history: Dict[int, deque] = {}
        self.speed_history: Dict[int, deque] = {}
        
    def update_position(self, track_id: int, center_x: float, center_y: float, 
                       timestamp: Optional[float] = None) -> Optional[float]:
        """
        Update position for a tracked object and calculate speed if enough history exists
        
        Args:
            track_id: Unique identifier for the tracked object
            center_x: Center X coordinate in pixels
            center_y: Center Y coordinate in pixels
            timestamp: Timestamp for the position, if None uses current time
            
        Returns:
            Speed in km/h or None if not enough history exists
        """
        if timestamp is None:
            timestamp = time.time()
            
        # Create history deque if it doesn't exist
        if track_id not in self.position_history:
            self.position_history[track_id] = deque(maxlen=self.max_history)
            self.speed_history[track_id] = deque(maxlen=self.max_history)
            
        # Add current position and timestamp
        current_pos = (center_x, center_y, timestamp)
        self.position_history[track_id].append(current_pos)
        
        # Calculate speed if we have at least 2 positions
        if len(self.position_history[track_id]) >= 2:
            # Get the two most recent positions
            prev_pos = self.position_history[track_id][-2]
            curr_pos = self.position_history[track_id][-1]

            # Calculate distance in pixels
            pixel_distance = np.sqrt((curr_pos[0] - prev_pos[0])**2 +
                                   (curr_pos[1] - prev_pos[1])**2)

            # Convert to real-world distance in meters
            real_distance = pixel_distance * self.pixel_distance

            # Calculate time difference in seconds
            time_diff = curr_pos[2] - prev_pos[2]

            if time_diff > 0 and real_distance > 0.001:  # Only calculate speed if there's meaningful movement
                # Calculate speed in m/s, then convert to km/h
                speed_mps = real_distance / time_diff
                speed_kmh = speed_mps * 3.6  # Convert m/s to km/h

                # Store the calculated speed
                self.speed_history[track_id].append(speed_kmh)

                return speed_kmh
            elif time_diff > 0:
                # If no movement, set speed to 0
                self.speed_history[track_id].append(0.0)
                return 0.0

        return None
        
    def get_average_speed(self, track_id: int, window_size: int = 3) -> Optional[float]:
        """
        Get average speed over the last few calculations for a track ID
        
        Args:
            track_id: Unique identifier for the tracked object
            window_size: Number of recent speed values to average
            
        Returns:
            Average speed in km/h or None if not enough data
        """
        if track_id in self.speed_history and len(self.speed_history[track_id]) > 0:
            recent_speeds = list(self.speed_history[track_id])[-window_size:]
            if len(recent_speeds) > 0:
                return sum(recent_speeds) / len(recent_speeds)
        return None
        
    def clear_track_history(self, track_id: int):
        """
        Clear history for a specific track ID
        """
        if track_id in self.position_history:
            del self.position_history[track_id]
        if track_id in self.speed_history:
            del self.speed_history[track_id]
    
    def clear_all_history(self):
        """
        Clear all stored history
        """
        self.position_history.clear()
        self.speed_history.clear()


class SpeedEstimationManager:
    """
    Manager for handling speed estimation across multiple tracks
    """
    def __init__(self, pixel_distance: float = 0.01, fps: float = 30.0):
        """
        Initialize the speed estimation manager
        
        Args:
            pixel_distance (float): Real-world distance per pixel in meters
            fps (float): Frames per second of the video stream
        """
        self.speed_estimator = SpeedEstimator(pixel_distance=pixel_distance, fps=fps)
        self.track_timestamps = {}  # Keep track of timestamps for each track
        
    def estimate_speed(self, track_id: int, bbox: List[float], 
                      frame_timestamp: Optional[float] = None) -> Optional[float]:
        """
        Estimate speed for a tracked object based on its bounding box
        
        Args:
            track_id: Unique identifier for the tracked object
            bbox: Bounding box in format [xmin, ymin, xmax, ymax]
            frame_timestamp: Timestamp for the frame, if None uses current time
            
        Returns:
            Speed in km/h or None if not enough history exists
        """
        if frame_timestamp is None:
            frame_timestamp = time.time()
            
        # Calculate center of bounding box
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        
        # Update position and calculate speed
        speed = self.speed_estimator.update_position(track_id, center_x, center_y, frame_timestamp)
        
        return speed
        
    def get_smoothed_speed(self, track_id: int, window_size: int = 3) -> Optional[float]:
        """
        Get smoothed/average speed for a track ID
        
        Args:
            track_id: Unique identifier for the tracked object
            window_size: Number of recent speed values to average
            
        Returns:
            Average speed in km/h or None if not enough data
        """
        return self.speed_estimator.get_average_speed(track_id, window_size)
    
    def draw_speed_on_frame(self, frame: np.ndarray, track_id: int, 
                           bbox: List[int], speed: Optional[float]) -> np.ndarray:
        """
        Draw speed information on the frame
        
        Args:
            frame: Image frame to draw on
            track_id: Unique identifier for the tracked object
            bbox: Bounding box in format [xmin, ymin, xmax, ymax]
            speed: Speed in km/h to display
            
        Returns:
            Frame with speed information drawn
        """
        if speed is not None:
            # Format speed to 1 decimal place
            speed_text = f"{speed:.1f} km/h"
            
            # Position text above the bounding box
            text_x = int(bbox[0])
            text_y = int(bbox[1]) - 10
            
            # Ensure text is within frame bounds
            text_y = max(text_y, 30)  # At least 30 pixels from top
            
            # Draw text background
            (text_width, text_height), baseline = cv2.getTextSize(speed_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (text_x, text_y - text_height - baseline), 
                         (text_x + text_width, text_y + baseline), (0, 0, 0), -1)
            
            # Draw text
            cv2.putText(frame, speed_text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return frame