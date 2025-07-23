#!/usr/bin/env python3
"""
Raspberry Pi Environment Configuration Generator for BirdCam

This script helps users configure their Raspberry Pi camera setup by:
- Auto-detecting available cameras (CSI and USB)
- Providing an interactive configuration wizard
- Generating a proper .env.pi file
- Creating a SECRET_KEY for secure communication
"""

import os
import sys
import secrets
import subprocess
import re
from pathlib import Path


def detect_csi_cameras():
    """Detect available CSI cameras using libcamera-list"""
    cameras = []
    try:
        result = subprocess.run(['libcamera-list'], capture_output=True, text=True)
        if result.returncode == 0:
            # Parse output looking for camera entries
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                if 'Available cameras' in line:
                    continue
                match = re.match(r'^(\d+)\s*:\s*(.+)$', line)
                if match:
                    cam_id = match.group(1)
                    cam_name = match.group(2).strip()
                    cameras.append({
                        'id': int(cam_id),
                        'name': cam_name,
                        'type': 'CSI'
                    })
    except FileNotFoundError:
        print("Warning: libcamera-list not found. CSI camera detection unavailable.")
    except Exception as e:
        print(f"Warning: Error detecting CSI cameras: {e}")
    
    return cameras


def detect_usb_cameras():
    """Detect available USB cameras"""
    cameras = []
    
    # Check /dev/video* devices
    video_devices = sorted(Path('/dev').glob('video*'))
    
    for device in video_devices:
        device_num = int(device.name.replace('video', ''))
        try:
            # Try to get device info using v4l2-ctl
            result = subprocess.run(
                ['v4l2-ctl', '-d', str(device), '--info'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Extract device name from output
                name_match = re.search(r'Card type\s*:\s*(.+)', result.stdout)
                name = name_match.group(1) if name_match else f"USB Camera {device_num}"
                
                cameras.append({
                    'id': device_num,
                    'name': name.strip(),
                    'type': 'USB',
                    'device': str(device)
                })
        except FileNotFoundError:
            # v4l2-ctl not available, just list the device
            cameras.append({
                'id': device_num,
                'name': f"USB Camera {device_num}",
                'type': 'USB',
                'device': str(device)
            })
        except Exception:
            pass
    
    return cameras


def generate_secret_key():
    """Generate a secure secret key"""
    return secrets.token_urlsafe(32)


def get_yes_no(prompt, default=None):
    """Get yes/no answer from user"""
    if default is True:
        prompt += " [Y/n]: "
    elif default is False:
        prompt += " [y/N]: "
    else:
        prompt += " [y/n]: "
    
    while True:
        answer = input(prompt).strip().lower()
        if not answer and default is not None:
            return default
        if answer in ['y', 'yes']:
            return True
        if answer in ['n', 'no']:
            return False
        print("Please answer 'yes' or 'no'")


def get_number(prompt, default=None, min_val=None, max_val=None):
    """Get numeric input from user"""
    if default is not None:
        prompt += f" [{default}]: "
    else:
        prompt += ": "
    
    while True:
        answer = input(prompt).strip()
        if not answer and default is not None:
            return default
        try:
            value = float(answer)
            if min_val is not None and value < min_val:
                print(f"Value must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("Please enter a valid number")


def main():
    """Main configuration generator"""
    print("=" * 60)
    print("BirdCam Raspberry Pi Configuration Generator")
    print("=" * 60)
    print()
    
    # Check if .env.pi already exists
    env_path = Path('.env.pi')
    if env_path.exists():
        overwrite = get_yes_no(
            ".env.pi already exists. Overwrite?",
            default=False
        )
        if not overwrite:
            print("Configuration cancelled.")
            return
    
    config = {}
    
    # Detect cameras
    print("Detecting cameras...")
    csi_cameras = detect_csi_cameras()
    usb_cameras = detect_usb_cameras()
    
    print(f"\nFound {len(csi_cameras)} CSI camera(s):")
    for cam in csi_cameras:
        print(f"  - Camera {cam['id']}: {cam['name']}")
    
    print(f"\nFound {len(usb_cameras)} USB camera(s):")
    for cam in usb_cameras:
        print(f"  - {cam['device']}: {cam['name']}")
    
    # Camera configuration
    print("\n" + "-" * 40)
    print("CAMERA CONFIGURATION")
    print("-" * 40)
    
    # Motion detection camera
    print("\nMotion Detection Camera (Camera 0):")
    print("This camera will actively detect motion and trigger recordings.")
    
    if csi_cameras:
        use_csi = get_yes_no(
            "Use CSI camera for motion detection?",
            default=True
        )
        if use_csi:
            config['CAMERA_TYPE_0'] = 'picamera2'
            if len(csi_cameras) > 1:
                cam_id = int(get_number(
                    "Which CSI camera ID?",
                    default=0,
                    min_val=0,
                    max_val=len(csi_cameras)-1
                ))
                config['CAMERA_DEVICE_0'] = str(cam_id)
            else:
                config['CAMERA_DEVICE_0'] = '0'
        else:
            config['CAMERA_TYPE_0'] = 'opencv'
            if usb_cameras:
                print("\nAvailable USB cameras:")
                for i, cam in enumerate(usb_cameras):
                    print(f"  {i}: {cam['device']} - {cam['name']}")
                idx = int(get_number(
                    "Select USB camera index",
                    default=0,
                    min_val=0,
                    max_val=len(usb_cameras)-1
                ))
                config['CAMERA_DEVICE_0'] = usb_cameras[idx]['device']
            else:
                config['CAMERA_DEVICE_0'] = '/dev/video0'
    else:
        config['CAMERA_TYPE_0'] = 'opencv'
        if usb_cameras:
            print("\nAvailable USB cameras:")
            for i, cam in enumerate(usb_cameras):
                print(f"  {i}: {cam['device']} - {cam['name']}")
            idx = int(get_number(
                "Select USB camera index",
                default=0,
                min_val=0,
                max_val=len(usb_cameras)-1
            ))
            config['CAMERA_DEVICE_0'] = usb_cameras[idx]['device']
        else:
            config['CAMERA_DEVICE_0'] = input("Enter camera device path [/dev/video0]: ").strip() or '/dev/video0'
    
    config['CAMERA_NAME_0'] = input("Camera name [Front Yard]: ").strip() or "Front Yard"
    
    # Resolution
    print("\nCamera resolution options:")
    print("  1. 640x480 (Low)")
    print("  2. 1280x720 (HD)")
    print("  3. 1920x1080 (Full HD)")
    print("  4. Custom")
    
    res_choice = get_number("Select resolution", default=2, min_val=1, max_val=4)
    if res_choice == 1:
        config['CAMERA_WIDTH_0'] = '640'
        config['CAMERA_HEIGHT_0'] = '480'
    elif res_choice == 2:
        config['CAMERA_WIDTH_0'] = '1280'
        config['CAMERA_HEIGHT_0'] = '720'
    elif res_choice == 3:
        config['CAMERA_WIDTH_0'] = '1920'
        config['CAMERA_HEIGHT_0'] = '1080'
    else:
        config['CAMERA_WIDTH_0'] = str(int(get_number("Width", default=1280, min_val=320, max_val=3840)))
        config['CAMERA_HEIGHT_0'] = str(int(get_number("Height", default=720, min_val=240, max_val=2160)))
    
    config['CAMERA_FPS_0'] = str(int(get_number("Frames per second", default=15, min_val=1, max_val=60)))
    
    # Additional passive cameras
    print("\n" + "-" * 40)
    print("PASSIVE CAMERAS")
    print("-" * 40)
    print("\nPassive cameras record continuously when motion is detected")
    print("on the main camera, but don't perform motion detection themselves.")
    
    camera_count = 1
    add_more = get_yes_no("\nAdd passive cameras?", default=False)
    
    while add_more and camera_count < 5:
        print(f"\nConfiguring Camera {camera_count}:")
        
        all_cameras = csi_cameras + usb_cameras
        if all_cameras:
            print("Available cameras:")
            for i, cam in enumerate(all_cameras):
                if cam['type'] == 'CSI':
                    print(f"  {i}: CSI Camera {cam['id']} - {cam['name']}")
                else:
                    print(f"  {i}: {cam['device']} - {cam['name']}")
            
            idx = int(get_number(
                "Select camera index",
                default=0,
                min_val=0,
                max_val=len(all_cameras)-1
            ))
            
            selected = all_cameras[idx]
            if selected['type'] == 'CSI':
                config[f'CAMERA_TYPE_{camera_count}'] = 'picamera2'
                config[f'CAMERA_DEVICE_{camera_count}'] = str(selected['id'])
            else:
                config[f'CAMERA_TYPE_{camera_count}'] = 'opencv'
                config[f'CAMERA_DEVICE_{camera_count}'] = selected['device']
        else:
            cam_type = input("Camera type (picamera2/opencv) [opencv]: ").strip() or 'opencv'
            config[f'CAMERA_TYPE_{camera_count}'] = cam_type
            if cam_type == 'picamera2':
                config[f'CAMERA_DEVICE_{camera_count}'] = input("CSI Camera ID [0]: ").strip() or '0'
            else:
                config[f'CAMERA_DEVICE_{camera_count}'] = input(f"Device path [/dev/video{camera_count}]: ").strip() or f'/dev/video{camera_count}'
        
        config[f'CAMERA_NAME_{camera_count}'] = input(f"Camera name [Camera {camera_count}]: ").strip() or f"Camera {camera_count}"
        
        # Use same resolution as camera 0 by default
        use_same_res = get_yes_no(
            f"Use same resolution as Camera 0 ({config['CAMERA_WIDTH_0']}x{config['CAMERA_HEIGHT_0']})?",
            default=True
        )
        if use_same_res:
            config[f'CAMERA_WIDTH_{camera_count}'] = config['CAMERA_WIDTH_0']
            config[f'CAMERA_HEIGHT_{camera_count}'] = config['CAMERA_HEIGHT_0']
            config[f'CAMERA_FPS_{camera_count}'] = config['CAMERA_FPS_0']
        else:
            config[f'CAMERA_WIDTH_{camera_count}'] = str(int(get_number("Width", default=1280, min_val=320, max_val=3840)))
            config[f'CAMERA_HEIGHT_{camera_count}'] = str(int(get_number("Height", default=720, min_val=240, max_val=2160)))
            config[f'CAMERA_FPS_{camera_count}'] = str(int(get_number("FPS", default=15, min_val=1, max_val=60)))
        
        camera_count += 1
        if camera_count < 5:
            add_more = get_yes_no("\nAdd another passive camera?", default=False)
        else:
            print("\nMaximum camera limit reached (5 cameras)")
            add_more = False
    
    config['CAMERA_COUNT'] = str(camera_count)
    
    # Motion detection settings
    print("\n" + "-" * 40)
    print("MOTION DETECTION SETTINGS")
    print("-" * 40)
    
    config['MOTION_AREA_THRESHOLD'] = str(get_number(
        "\nMinimum motion area (% of frame)",
        default=0.5,
        min_val=0.1,
        max_val=10.0
    ))
    
    config['MOTION_CONTOUR_THRESHOLD'] = str(int(get_number(
        "Minimum contour area (pixels)",
        default=500,
        min_val=50,
        max_val=5000
    )))
    
    config['PRE_MOTION_SECONDS'] = str(int(get_number(
        "Pre-motion buffer (seconds)",
        default=3,
        min_val=0,
        max_val=10
    )))
    
    config['POST_MOTION_SECONDS'] = str(int(get_number(
        "Post-motion recording (seconds)",
        default=5,
        min_val=1,
        max_val=30
    )))
    
    # Storage settings
    print("\n" + "-" * 40)
    print("STORAGE SETTINGS")
    print("-" * 40)
    
    config['STORAGE_PATH'] = input("\nVideo storage path [/var/birdcam/videos]: ").strip() or "/var/birdcam/videos"
    config['LOG_FILE'] = input("Log file path [/var/log/birdcam/pi_capture.log]: ").strip() or "/var/log/birdcam/pi_capture.log"
    
    # Processing server settings
    print("\n" + "-" * 40)
    print("AI PROCESSING SERVER")
    print("-" * 40)
    
    print("\nThe AI processing server will analyze captured videos.")
    config['PROCESSING_SERVER'] = input("Processing server URL [http://localhost:5001]: ").strip() or "http://localhost:5001"
    
    # Security
    print("\n" + "-" * 40)
    print("SECURITY SETTINGS")
    print("-" * 40)
    
    print("\nGenerating secure secret key...")
    config['SECRET_KEY'] = generate_secret_key()
    print("Secret key generated successfully.")
    print("\nIMPORTANT: This key must match on the AI processing server!")
    
    # Advanced settings
    advanced = get_yes_no("\nConfigure advanced settings?", default=False)
    if advanced:
        print("\n" + "-" * 40)
        print("ADVANCED SETTINGS")
        print("-" * 40)
        
        config['FRAME_BUFFER_SIZE'] = str(int(get_number(
            "\nFrame buffer size",
            default=90,
            min_val=30,
            max_val=300
        )))
        
        config['VIDEO_CODEC'] = input("Video codec [h264]: ").strip() or "h264"
        config['VIDEO_QUALITY'] = str(int(get_number(
            "Video quality (10-51, lower=better)",
            default=23,
            min_val=10,
            max_val=51
        )))
        
        config['MOTION_GAUSSIAN_SIZE'] = str(int(get_number(
            "Motion blur kernel size (odd number)",
            default=21,
            min_val=3,
            max_val=99
        )))
        
        config['MOTION_THRESHOLD'] = str(int(get_number(
            "Motion threshold (0-255)",
            default=25,
            min_val=5,
            max_val=100
        )))
        
        config['DEBUG'] = 'true' if get_yes_no("Enable debug mode?", default=False) else 'false'
    else:
        # Use defaults for advanced settings
        config['FRAME_BUFFER_SIZE'] = '90'
        config['VIDEO_CODEC'] = 'h264'
        config['VIDEO_QUALITY'] = '23'
        config['MOTION_GAUSSIAN_SIZE'] = '21'
        config['MOTION_THRESHOLD'] = '25'
        config['DEBUG'] = 'false'
    
    # Write configuration
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    
    print(f"\nCameras configured: {config['CAMERA_COUNT']}")
    for i in range(int(config['CAMERA_COUNT'])):
        print(f"  Camera {i}: {config[f'CAMERA_NAME_{i}']} ({config[f'CAMERA_TYPE_{i}']})")
    
    print(f"\nMotion detection:")
    print(f"  Area threshold: {config['MOTION_AREA_THRESHOLD']}%")
    print(f"  Pre/Post buffer: {config['PRE_MOTION_SECONDS']}s / {config['POST_MOTION_SECONDS']}s")
    
    print(f"\nStorage: {config['STORAGE_PATH']}")
    print(f"Processing server: {config['PROCESSING_SERVER']}")
    
    print("\n" + "-" * 60)
    
    if get_yes_no("\nSave this configuration?", default=True):
        # Write .env.pi file
        with open('.env.pi', 'w') as f:
            f.write("# BirdCam Raspberry Pi Configuration\n")
            f.write("# Generated by pi_env_generator.py\n\n")
            
            # Group settings logically
            f.write("# Camera Configuration\n")
            f.write(f"CAMERA_COUNT={config['CAMERA_COUNT']}\n")
            for i in range(int(config['CAMERA_COUNT'])):
                f.write(f"\n# Camera {i}")
                if i == 0:
                    f.write(" (Motion Detection)")
                f.write("\n")
                f.write(f"CAMERA_NAME_{i}={config[f'CAMERA_NAME_{i}']}\n")
                f.write(f"CAMERA_TYPE_{i}={config[f'CAMERA_TYPE_{i}']}\n")
                f.write(f"CAMERA_DEVICE_{i}={config[f'CAMERA_DEVICE_{i}']}\n")
                f.write(f"CAMERA_WIDTH_{i}={config[f'CAMERA_WIDTH_{i}']}\n")
                f.write(f"CAMERA_HEIGHT_{i}={config[f'CAMERA_HEIGHT_{i}']}\n")
                f.write(f"CAMERA_FPS_{i}={config[f'CAMERA_FPS_{i}']}\n")
            
            f.write("\n# Motion Detection Settings\n")
            f.write(f"MOTION_AREA_THRESHOLD={config['MOTION_AREA_THRESHOLD']}\n")
            f.write(f"MOTION_CONTOUR_THRESHOLD={config['MOTION_CONTOUR_THRESHOLD']}\n")
            f.write(f"MOTION_GAUSSIAN_SIZE={config['MOTION_GAUSSIAN_SIZE']}\n")
            f.write(f"MOTION_THRESHOLD={config['MOTION_THRESHOLD']}\n")
            f.write(f"PRE_MOTION_SECONDS={config['PRE_MOTION_SECONDS']}\n")
            f.write(f"POST_MOTION_SECONDS={config['POST_MOTION_SECONDS']}\n")
            
            f.write("\n# Video Settings\n")
            f.write(f"FRAME_BUFFER_SIZE={config['FRAME_BUFFER_SIZE']}\n")
            f.write(f"VIDEO_CODEC={config['VIDEO_CODEC']}\n")
            f.write(f"VIDEO_QUALITY={config['VIDEO_QUALITY']}\n")
            
            f.write("\n# Storage and Processing\n")
            f.write(f"STORAGE_PATH={config['STORAGE_PATH']}\n")
            f.write(f"LOG_FILE={config['LOG_FILE']}\n")
            f.write(f"PROCESSING_SERVER={config['PROCESSING_SERVER']}\n")
            
            f.write("\n# Security\n")
            f.write(f"SECRET_KEY={config['SECRET_KEY']}\n")
            
            f.write("\n# Debug\n")
            f.write(f"DEBUG={config['DEBUG']}\n")
        
        print("\nConfiguration saved to .env.pi")
        print("\n" + "!" * 60)
        print("IMPORTANT: Save this SECRET_KEY for the AI processing server:")
        print(config['SECRET_KEY'])
        print("!" * 60)
        
        # Create directories if they don't exist
        print("\nCreating required directories...")
        os.makedirs(config['STORAGE_PATH'], exist_ok=True)
        os.makedirs(os.path.dirname(config['LOG_FILE']), exist_ok=True)
        print("Directories created.")
        
        print("\n" + "=" * 60)
        print("Configuration complete!")
        print("\nNext steps:")
        print("1. Run: source .venv/bin/activate")
        print("2. Run: pip install -r requirements.capture.txt")
        print("3. Test: python pi_capture/main.py")
        print("4. Install service: sudo ./scripts/setup/install_pi_capture_service.sh")
        print("=" * 60)
    else:
        print("\nConfiguration cancelled.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)