"""Visual test harness for motion detection - creates test frames and visualizes detection"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np
from config.settings import MotionConfig
from services.motion_detector import MotionDetector


def create_test_frames():
    """Create a series of test frames with different motion scenarios"""
    frames = []
    
    # Base frame (640x480)
    base = np.zeros((480, 640, 3), dtype=np.uint8)
    base[:] = (50, 50, 50)  # Dark gray background
    
    # Frame 1: No motion (same as base)
    frames.append(("No motion", base.copy()))
    
    # Frame 2: Small motion (small object)
    frame2 = base.copy()
    cv2.circle(frame2, (320, 240), 20, (255, 255, 255), -1)
    frames.append(("Small motion", frame2))
    
    # Frame 3: Large motion (large object)
    frame3 = base.copy()
    cv2.rectangle(frame3, (200, 150), (440, 330), (255, 255, 255), -1)
    frames.append(("Large motion", frame3))
    
    # Frame 4: Motion outside region
    frame4 = base.copy()
    cv2.rectangle(frame4, (50, 50), (150, 150), (255, 255, 255), -1)
    frames.append(("Motion outside region", frame4))
    
    # Frame 5: Multiple small objects
    frame5 = base.copy()
    for i in range(5):
        x = 200 + i * 60
        cv2.circle(frame5, (x, 240), 15, (255, 255, 255), -1)
    frames.append(("Multiple small objects", frame5))
    
    # Frame 6: Gradual change (simulating lighting change)
    frame6 = base.copy()
    frame6[:] = (80, 80, 80)  # Slightly lighter
    frames.append(("Gradual lighting change", frame6))
    
    return frames


def visualize_motion_detection(motion_detector, frame, frame_name, debug_info):
    """Visualize motion detection results"""
    display = frame.copy()
    
    # Draw motion region
    if motion_detector.motion_region:
        region = motion_detector.motion_region
        cv2.rectangle(display, (region.x1, region.y1), (region.x2, region.y2), 
                     (0, 255, 0), 2)
        cv2.putText(display, "Motion Region", (region.x1, region.y1 - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Add debug information
    y_offset = 30
    cv2.putText(display, f"Frame: {frame_name}", (10, y_offset),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    y_offset += 25
    motion_detected = debug_info.get('motion_detected', False)
    color = (0, 255, 0) if motion_detected else (0, 0, 255)
    cv2.putText(display, f"Motion: {'DETECTED' if motion_detected else 'None'}", 
               (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # Add detailed stats
    stats = [
        f"Motion pixels: {debug_info.get('motion_pixels', 0)}",
        f"Contours: {debug_info.get('contour_count', 0)}",
        f"Largest contour: {debug_info.get('largest_contour', 0)}",
        f"Min area threshold: {debug_info.get('min_contour_area', 0)}",
        f"Sensitivity: {debug_info.get('sensitivity_threshold', 0)}"
    ]
    
    y_offset += 30
    for stat in stats:
        cv2.putText(display, stat, (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        y_offset += 20
    
    return display


def test_motion_detector_visual():
    """Run visual tests for motion detector"""
    print("Motion Detector Visual Test")
    print("=" * 50)
    print("This test will create visualizations of motion detection")
    print("Press any key to advance through frames, 'q' to quit\n")
    
    # Create motion detector with specific configuration
    config = MotionConfig(
        threshold=5000,  # Medium sensitivity
        min_contour_area=500,
        learning_rate=0.01,
        motion_timeout_seconds=30,
        max_segment_duration=300,
        motion_box_enabled=True,
        motion_box_x1=160,
        motion_box_y1=120,
        motion_box_x2=480,
        motion_box_y2=360
    )
    
    detector = MotionDetector(config)
    
    # Get test frames
    test_frames = create_test_frames()
    
    # Process each frame
    print("Establishing background model...")
    base_frame = test_frames[0][1]
    
    # Establish background with base frame
    for _ in range(10):
        detector.detect_motion(base_frame)
    
    print("Background established. Starting motion detection tests...\n")
    
    # Test each frame
    for i, (frame_name, frame) in enumerate(test_frames):
        print(f"\nTest {i+1}: {frame_name}")
        
        # Detect motion
        motion_detected = detector.detect_motion(frame)
        
        # Get debug info
        debug_info = detector.get_debug_info(frame)
        
        # Print results
        print(f"  Motion detected: {motion_detected}")
        print(f"  Motion pixels: {debug_info.get('motion_pixels', 0)}")
        print(f"  Largest contour: {debug_info.get('largest_contour', 0)}")
        
        # Visualize
        visualization = visualize_motion_detection(detector, frame, frame_name, debug_info)
        
        # Save visualization
        output_path = f"/tmp/motion_test_{i+1}_{frame_name.replace(' ', '_')}.png"
        cv2.imwrite(output_path, visualization)
        print(f"  Saved visualization to: {output_path}")
        
        # Optional: Display if running with GUI
        try:
            cv2.imshow("Motion Detection Test", visualization)
            key = cv2.waitKey(0)
            if key == ord('q'):
                break
        except Exception as e:
            print(f"  (No display available - images saved to /tmp/): {e}")
    
    cv2.destroyAllWindows()
    
    # Test different sensitivity levels
    print("\n" + "="*50)
    print("Testing different sensitivity levels...")
    
    sensitivities = [
        (1000, "High sensitivity"),
        (5000, "Medium sensitivity"),
        (9000, "Low sensitivity")
    ]
    
    # Create a frame with medium motion
    test_frame = base_frame.copy()
    cv2.rectangle(test_frame, (250, 200), (390, 280), (255, 255, 255), -1)
    
    for threshold, desc in sensitivities:
        config.threshold = threshold
        detector = MotionDetector(config)
        
        # Establish background
        for _ in range(10):
            detector.detect_motion(base_frame)
        
        # Test motion
        motion = detector.detect_motion(test_frame)
        debug = detector.get_debug_info(test_frame)
        
        print(f"\n{desc} (threshold={threshold}):")
        print(f"  Motion detected: {motion}")
        print(f"  Sensitivity value: {debug.get('sensitivity_threshold', 0)}")
        print(f"  Largest contour: {debug.get('largest_contour', 0)}")
    
    print("\n" + "="*50)
    print("Motion detection visual test completed!")
    print("Check /tmp/motion_test_*.png for saved visualizations")


def test_adaptive_background():
    """Test adaptive background learning"""
    print("\n" + "="*50)
    print("Testing Adaptive Background Learning")
    print("=" * 50)
    
    config = MotionConfig(
        threshold=5000,
        min_contour_area=500,
        learning_rate=0.05,  # Higher learning rate for faster adaptation
        motion_timeout_seconds=30,
        max_segment_duration=300,
        motion_box_enabled=True
    )
    
    detector = MotionDetector(config)
    
    # Create gradually changing scene
    frames = []
    for i in range(20):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Gradually increase brightness
        brightness = 50 + i * 5
        frame[:] = (brightness, brightness, brightness)
        
        # Add a static object that should become part of background
        if i >= 5:
            cv2.rectangle(frame, (300, 200), (400, 300), (255, 255, 255), -1)
        
        frames.append(frame)
    
    print("Processing frames with gradual changes...")
    for i, frame in enumerate(frames):
        motion = detector.detect_motion(frame)
        debug = detector.get_debug_info(frame)
        
        if i % 5 == 0:
            print(f"  Frame {i}: Motion={motion}, Pixels={debug.get('motion_pixels', 0)}")
    
    print("\nAdaptive background test completed!")


if __name__ == "__main__":
    test_motion_detector_visual()
    test_adaptive_background()