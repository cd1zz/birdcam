import cv2
import os
import time
import threading
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, Response, jsonify, render_template_string
import sqlite3
import json
from pathlib import Path
import requests
from requests.exceptions import RequestException, Timeout
import schedule

app = Flask(__name__)

class PiCaptureSystem:
    def __init__(self, stream_url, storage_path="./bird_footage", processing_server=None):
        self.stream_url = stream_url
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.processing_server = processing_server  # IP of your powerful computer
        
        # Directories
        self.raw_dir = self.storage_path / "raw_footage"
        self.sync_dir = self.storage_path / "to_sync"  # Files ready for processing
        for dir_path in [self.raw_dir, self.sync_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Database for local metadata
        self.db_path = self.storage_path / "capture_log.db"
        self.init_database()
        
        # Capture settings
        self.segment_duration = 300  # 5-minute segments
        self.current_writer = None
        self.current_segment_start = None
        self.is_capturing = False
        
        # Enhanced motion detection settings
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=False, varThreshold=16, history=500)
        self.motion_threshold = 5000  # Increased from 2000
        self.min_contour_area = 500   # Minimum size for motion objects
        self.last_motion_time = 0
        self.pre_motion_buffer = []
        self.buffer_size = 150  # 15 seconds at 10fps
        
        # Motion detection region (ignore areas with trees)
        # Format: (x1, y1, x2, y2) - set to None to use full frame
        self.motion_region = None  # Will be set to center region by default
        
        # Sync tracking
        self.files_to_sync = []
        self.sync_lock = threading.Lock()
        
        # Initialize camera capture - ADD THIS LINE
        self._init_capture()
        
        # Load motion detection settings from database
        self.load_motion_settings()
        
    def load_motion_settings(self):
        """Load motion detection settings from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create settings table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS motion_settings (
                id INTEGER PRIMARY KEY,
                region_x1 INTEGER,
                region_y1 INTEGER, 
                region_x2 INTEGER,
                region_y2 INTEGER,
                motion_threshold INTEGER DEFAULT 5000,
                min_contour_area INTEGER DEFAULT 500,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Load existing settings
        cursor.execute('SELECT * FROM motion_settings ORDER BY id DESC LIMIT 1')
        settings = cursor.fetchone()
        
        if settings:
            _, x1, y1, x2, y2, threshold, min_area, _ = settings
            self.motion_region = (x1, y1, x2, y2)
            self.motion_threshold = threshold
            self.min_contour_area = min_area
            print(f"✅ Loaded motion settings: region=({x1},{y1},{x2},{y2}), threshold={threshold}")
        else:
            # Default to center 60% of frame
            self.motion_region = None  # Will be set in detect_motion
            print("📋 Using default motion settings")
            
        conn.commit()
        conn.close()

    def save_motion_settings(self, region, motion_threshold, min_contour_area):
        """Save motion detection settings to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        x1, y1, x2, y2 = region
        cursor.execute('''
            INSERT INTO motion_settings (region_x1, region_y1, region_x2, region_y2, 
                                       motion_threshold, min_contour_area)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (x1, y1, x2, y2, motion_threshold, min_contour_area))
        
        conn.commit()
        conn.close()
        
        # Update current settings
        self.motion_region = region
        self.motion_threshold = motion_threshold
        self.min_contour_area = min_contour_area
        
        print(f"💾 Saved motion settings: region=({x1},{y1},{x2},{y2})")

    def init_database(self):
        """Initialize SQLite database for capture logging"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration INTEGER,
                has_motion BOOLEAN DEFAULT FALSE,
                synced BOOLEAN DEFAULT FALSE,
                processed BOOLEAN DEFAULT FALSE,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def _init_capture(self):
        """Initialize video capture - try direct camera first, then RTSP"""
        # Try direct camera capture first (more reliable)
        self.cap = cv2.VideoCapture(0)  # /dev/video0
        if self.cap.isOpened():
            print("📹 Using direct camera capture")
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 10)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        else:
            # Fallback to RTSP if direct capture fails
            print("📡 Trying RTSP stream...")
            self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
            self.cap.set(cv2.CAP_PROP_FPS, 10)
        
        if not self.cap.isOpened():
            print(f"❌ Failed to open camera/stream")
        else:
            print("✅ Camera/stream opened successfully")

    def detect_motion(self, frame):
        """Enhanced motion detection with region masking and contour filtering"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply region of interest if set
        if self.motion_region is None:
            # Default to center 60% of frame (avoid edges where trees usually are)
            h, w = gray.shape
            self.motion_region = (int(w*0.2), int(h*0.2), int(w*0.8), int(h*0.8))
        
        # Create mask for region of interest
        mask = np.zeros(gray.shape, dtype=np.uint8)
        x1, y1, x2, y2 = self.motion_region
        mask[y1:y2, x1:x2] = 255
        
        # Apply background subtraction only to region of interest
        fg_mask = self.background_subtractor.apply(gray, learningRate=0.01)
        fg_mask = cv2.bitwise_and(fg_mask, mask)
        
        # Find contours to filter out small movements
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check for significant motion (large enough contours)
        significant_motion = False
        for contour in contours:
            if cv2.contourArea(contour) > self.min_contour_area:
                significant_motion = True
                break
        
        return significant_motion

    def start_new_segment(self, motion_triggered=False):
        """Start recording a new video segment"""
        if self.current_writer:
            self.current_writer.release()
        
        timestamp = datetime.now()
        filename = f"segment_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = self.raw_dir / filename
        
        # Use reliable mp4v codec - server will convert to H.264 for web compatibility
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.current_writer = cv2.VideoWriter(str(filepath), fourcc, 10.0, (640, 480))
        
        if not self.current_writer.isOpened():
            print("❌ Failed to initialize video writer")
            return
            
        self.current_segment_start = timestamp
        self.current_filename = filename
        
        # Write pre-motion buffer
        if motion_triggered and self.pre_motion_buffer:
            print(f"Writing {len(self.pre_motion_buffer)} pre-motion frames")
            for buffered_frame in self.pre_motion_buffer:
                self.current_writer.write(buffered_frame)
            self.pre_motion_buffer.clear()
        
        # Log to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO video_segments (filename, start_time, has_motion)
            VALUES (?, ?, ?)
        ''', (filename, timestamp, motion_triggered))
        conn.commit()
        conn.close()
        
        print(f"📹 Started recording: {filename}")

    def continuous_capture(self):
        """Main capture loop - lightweight and efficient"""
        frame_count = 0
        last_heartbeat = time.time()
        
        while True:
            if not self.cap or not self.cap.isOpened():
                print("🔄 Reinitializing capture...")
                self._init_capture()
                time.sleep(1)
                continue
            
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            current_time = time.time()
            
            # Detect motion (very fast)
            has_motion = self.detect_motion(frame)
            
            if has_motion:
                self.last_motion_time = current_time
                if not self.is_capturing:
                    self.start_new_segment(motion_triggered=True)
                    self.is_capturing = True
            else:
                # Maintain pre-motion buffer
                self.pre_motion_buffer.append(frame.copy())
                if len(self.pre_motion_buffer) > self.buffer_size:
                    self.pre_motion_buffer.pop(0)
            
            # Write frame if capturing
            if self.is_capturing and self.current_writer:
                self.current_writer.write(frame)
                frame_count += 1
                
                # Stop after 30 seconds of no motion
                if current_time - self.last_motion_time > 30:
                    self.finish_current_segment()
                    self.is_capturing = False
                    frame_count = 0
                
                # Or after max duration
                elif frame_count > self.segment_duration * 10:  # 10 fps
                    self.finish_current_segment()
                    if current_time - self.last_motion_time < 60:
                        self.start_new_segment(motion_triggered=True)
                    else:
                        self.is_capturing = False
                    frame_count = 0
            
            # Heartbeat every 30 seconds
            if current_time - last_heartbeat > 30:
                print(f"💓 Capture running - Motion: {has_motion}, Recording: {self.is_capturing}")
                last_heartbeat = current_time
            
            time.sleep(0.05)  # Prevent overwhelming CPU

    def finish_current_segment(self):
        """Finish current segment and prepare for sync"""
        if self.current_writer:
            self.current_writer.release()
            self.current_writer = None
            
            end_time = datetime.now()
            duration = (end_time - self.current_segment_start).total_seconds()
            file_path = self.raw_dir / self.current_filename
            file_size = file_path.stat().st_size if file_path.exists() else 0
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE video_segments
                SET end_time = ?, duration = ?, file_size = ?
                WHERE filename = ?
            ''', (end_time, int(duration), file_size, self.current_filename))
            conn.commit()
            conn.close()
            
            # Add to sync queue if it has motion
            if duration > 10:  # Only sync videos longer than 10 seconds
                with self.sync_lock:
                    self.files_to_sync.append(self.current_filename)
                print(f"✅ Finished: {self.current_filename} ({duration:.1f}s, {file_size/1024/1024:.1f}MB)")
            else:
                # Delete very short files
                if file_path.exists():
                    file_path.unlink()
                print(f"🗑️ Deleted short file: {self.current_filename}")

    def sync_files_to_processor(self):
        """Sync files to processing server"""
        if not self.processing_server:
            return
        
        with self.sync_lock:
            files_to_process = self.files_to_sync.copy()
            self.files_to_sync.clear()
        
        for filename in files_to_process:
            try:
                self.sync_single_file(filename)
            except Exception as e:
                print(f"❌ Failed to sync {filename}: {e}")
                # Put it back in queue
                with self.sync_lock:
                    self.files_to_sync.append(filename)

    def sync_single_file(self, filename):
        """Sync a single file to processing server"""
        source_path = self.raw_dir / filename
        if not source_path.exists():
            return
        
        print(f"📤 Syncing {filename} to processing server...")
        
        # Simple HTTP upload (you could also use rsync, scp, etc.)
        with open(source_path, 'rb') as f:
            files = {'video': (filename, f, 'video/mp4')}
            response = requests.post(
                f"http://{self.processing_server}:8091/upload",
                files=files,
                timeout=300  # 5 minutes timeout
            )
        
        if response.status_code == 200:
            # Mark as synced
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE video_segments SET synced = TRUE WHERE filename = ?',
                (filename,)
            )
            conn.commit()
            conn.close()

            # Move to sync directory (keep local copy)
            sync_path = self.sync_dir / filename
            source_path.rename(sync_path)
            print(f"✅ Synced: {filename}")
        else:
            raise Exception(f"Upload failed: {response.status_code}")

    def cleanup_old_files(self, days_to_keep=3):
        """Clean up old synced files"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Clean synced files
        for file_path in self.sync_dir.glob("*.mp4"):
            if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                file_path.unlink()
                print(f"🗑️ Cleaned up old file: {file_path.name}")
        
        # Clean database entries
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM video_segments WHERE start_time < ? AND synced = TRUE',
            (cutoff_date,)
        )
        conn.commit()
        conn.close()

    def get_server_status(self):
        """Get status from processing server"""
        if not self.processing_server:
            return None
        
        try:
            response = requests.get(
                f"http://{self.processing_server}:8091/api/status",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except (RequestException, Timeout) as e:
            print(f"⚠️ Could not reach processing server: {e}")
        
        return None

    def get_server_recent_detections(self, limit=10):
        """Get recent detections from processing server"""
        if not self.processing_server:
            return []
        
        try:
            response = requests.get(
                f"http://{self.processing_server}:8091/api/recent-detections",
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get('detections', [])
        except (RequestException, Timeout) as e:
            print(f"⚠️ Could not reach processing server: {e}")
        
        return []

    def get_status(self):
        """Get combined system status"""
        # Existing Pi status
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM video_segments')
        total_videos = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM video_segments WHERE synced = TRUE')
        synced_videos = cursor.fetchone()[0]
        cursor.execute('SELECT SUM(file_size) FROM video_segments')
        total_size = cursor.fetchone()[0] or 0
        conn.close()

        with self.sync_lock:
            pending_sync = len(self.files_to_sync)

        pi_status = {
            'pi': {
                'total_videos': total_videos,
                'synced_videos': synced_videos,
                'pending_sync': pending_sync,
                'total_size_mb': total_size / 1024 / 1024,
                'is_capturing': self.is_capturing,
                'last_motion': self.last_motion_time
            }
        }

        # Add server status
        server_status = self.get_server_status()
        if server_status:
            pi_status['server'] = server_status
            pi_status['server_connected'] = True
        else:
            pi_status['server_connected'] = False

        return pi_status

# Global system instance
capture_system = None

def initialize_system():
    global capture_system
    # Configuration
    STREAM_URL = "rtsp://192.168.1.136:8554/birdcam"
    PROCESSING_SERVER = "192.168.1.136"  # IP of your powerful computer
    
    capture_system = PiCaptureSystem(STREAM_URL, processing_server=PROCESSING_SERVER)
    
    # Start capture
    capture_thread = threading.Thread(target=capture_system.continuous_capture, daemon=True)
    capture_thread.start()
    
    # Schedule sync every 15 minutes
    schedule.every(15).minutes.do(capture_system.sync_files_to_processor)
    schedule.every().day.at("03:00").do(lambda: capture_system.cleanup_old_files())
    
    # Start scheduler
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("🚀 Pi Capture System initialized")

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🐦 Bird Detection System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f0f8ff; }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
            .main-grid { display: grid; grid-template-columns: 500px 1fr; gap: 20px; margin-bottom: 20px; }
            .live-section { display: flex; flex-direction: column; gap: 20px; }
            .live-feed { background: white; padding: 20px; border-radius: 10px; }
            .live-feed img { width: 100%; border: 2px solid #ddd; border-radius: 8px; }
            .controls { background: white; padding: 20px; border-radius: 10px; }
            .stats-section { display: flex; flex-direction: column; gap: 20px; }
            .system-status { background: white; padding: 20px; border-radius: 10px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
            .stat-card { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
            .stat-number { font-size: 1.5em; font-weight: bold; color: #2c3e50; }
            .stat-label { font-size: 0.85em; color: #666; margin-top: 5px; }
            .detections { background: white; padding: 20px; border-radius: 10px; }
            .detection-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }
            .detection-card { border: 1px solid #ddd; border-radius: 8px; padding: 10px; }
            .detection-card img { width: 100%; height: 120px; object-fit: cover; border-radius: 5px; }
            .detection-card .filename { font-size: 11px; word-break: break-all; margin: 5px 0; }
            .btn { background: #3498db; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; font-size: 14px; }
            .btn:hover { background: #2980b9; }
            .btn.success { background: #27ae60; }
            .btn.warning { background: #f39c12; }
            .status-indicator { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
            .online { background: #27ae60; }
            .recording { background: #e74c3c; }
            .processing { background: #f39c12; }
            .offline { background: #95a5a6; }
            .section-title { display: flex; align-items: center; margin-bottom: 15px; }
            .section-title h3 { margin: 0; margin-right: 10px; }
            @media (max-width: 1200px) {
                .main-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🐦 Bird Detection System</h1>
                <p>Raspberry Pi Capture + AI Processing Dashboard</p>
            </div>

            <div class="main-grid">
                <div class="live-section">
                    <div class="live-feed">
                        <h3>📺 Live Camera Feed</h3>
                        <img src="/live_feed" alt="Live Camera Feed" id="live-image">
                        <p><small>Green = Motion detected | Red = No motion</small></p>
                    </div>
                    
                    <div class="controls">
                        <h3>🎛️ Controls</h3>
                        <button class="btn" onclick="syncNow()">📤 Sync Files</button>
                        <button class="btn warning" onclick="processServerQueue()">🧠 Process Queue</button>
                        <button class="btn" onclick="showSettings()">⚙️ Settings</button>
                        <button class="btn" onclick="location.reload()">🔄 Refresh</button>
                    </div>
                </div>

                <div class="stats-section">
                    <div class="system-status">
                        <div class="section-title">
                            <h3>📊 System Status</h3>
                            <div id="connection-status"></div>
                        </div>
                        
                        <h4>📹 Raspberry Pi (Capture)</h4>
                        <div class="stats-grid" id="pi-stats">
                            <div class="stat-card">
                                <div class="stat-number" id="pi-total-videos">-</div>
                                <div class="stat-label">Videos Captured</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="pi-synced">-</div>
                                <div class="stat-label">Synced</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="pi-pending">-</div>
                                <div class="stat-label">Pending Sync</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="pi-storage">-</div>
                                <div class="stat-label">Storage (MB)</div>
                            </div>
                        </div>
                        <div id="pi-status-text" style="margin-top: 10px;"></div>

                        <h4 style="margin-top: 20px;">🧠 Processing Server</h4>
                        <div class="stats-grid" id="server-stats">
                            <div class="stat-card">
                                <div class="stat-number" id="server-processed">-</div>
                                <div class="stat-label">Videos Processed</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="server-queue">-</div>
                                <div class="stat-label">Queue Size</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="server-birds">-</div>
                                <div class="stat-label">Birds Found</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="server-today">-</div>
                                <div class="stat-label">Today's Birds</div>
                            </div>
                        </div>
                        <div id="server-status-text" style="margin-top: 10px;"></div>
                    </div>
                </div>
            </div>

            <div class="detections">
                <h3>🐦 Recent Bird Detections</h3>
                <div id="detection-grid" class="detection-grid"></div>
            </div>
        </div>

        <script>
            function showSettings() {
                // Create settings modal
                const modal = document.createElement('div');
                modal.style.cssText = `
                    position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                    background: rgba(0,0,0,0.8); z-index: 1000; 
                    display: flex; align-items: center; justify-content: center;
                `;
                
                const settingsContainer = document.createElement('div');
                settingsContainer.style.cssText = `
                    background: white; padding: 20px; border-radius: 10px; 
                    max-width: 90%; max-height: 90%; position: relative;
                    width: 800px;
                `;
                
                settingsContainer.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0;">⚙️ Motion Detection Settings</h3>
                        <button onclick="this.closest('.modal').remove()" style="background: #e74c3c; color: white; border: none; padding: 8px 12px; border-radius: 5px; cursor: pointer;">✕ Close</button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 300px; gap: 20px;">
                        <div>
                            <h4>🎯 Draw Motion Detection Region</h4>
                            <p style="font-size: 14px; color: #666;">Click and drag to draw a rectangle. Only motion inside this area will trigger recording.</p>
                            <div style="position: relative; border: 2px solid #ddd; display: inline-block;">
                                <img id="settings-feed" src="/live_feed" style="width: 400px; height: 300px; cursor: crosshair;">
                                <canvas id="region-canvas" width="400" height="300" style="position: absolute; top: 0; left: 0; pointer-events: auto;"></canvas>
                            </div>
                            <div style="margin-top: 10px;">
                                <button class="btn" onclick="clearRegion()">🗑️ Clear Region</button>
                                <button class="btn" onclick="setDefaultRegion()">📐 Default (Center)</button>
                            </div>
                        </div>
                        
                        <div>
                            <h4>🔧 Detection Parameters</h4>
                            <div style="margin-bottom: 15px;">
                                <label>Sensitivity:</label>
                                <input type="range" id="threshold-slider" min="1000" max="10000" value="5000" style="width: 100%;">
                                <span id="threshold-value">5000</span>
                            </div>
                            
                            <div style="margin-bottom: 15px;">
                                <label>Min Object Size:</label>
                                <input type="range" id="size-slider" min="100" max="2000" value="500" style="width: 100%;">
                                <span id="size-value">500</span>
                            </div>
                            
                            <div style="margin-bottom: 15px;">
                                <h5>Current Region:</h5>
                                <div id="region-info" style="font-family: monospace; font-size: 12px; background: #f5f5f5; padding: 10px;">
                                    No region selected
                                </div>
                            </div>
                            
                            <div>
                                <button class="btn success" onclick="saveSettings()" style="width: 100%; margin-bottom: 10px;">💾 Save Settings</button>
                                <button class="btn" onclick="testMotion()" style="width: 100%;">🧪 Test Motion Detection</button>
                            </div>
                        </div>
                    </div>
                `;
                
                modal.className = 'modal';
                modal.appendChild(settingsContainer);
                document.body.appendChild(modal);
                
                // Initialize canvas drawing
                initializeRegionDrawing();
                
                // Load current settings
                loadCurrentSettings();
                
                // Close on background click
                modal.onclick = (e) => {
                    if (e.target === modal) modal.remove();
                };
            }

            let isDrawing = false;
            let startX, startY, currentRegion = null;

            function initializeRegionDrawing() {
                const canvas = document.getElementById('region-canvas');
                const ctx = canvas.getContext('2d');
                
                canvas.addEventListener('mousedown', startDrawing);
                canvas.addEventListener('mousemove', draw);
                canvas.addEventListener('mouseup', stopDrawing);
                
                // Touch events for mobile
                canvas.addEventListener('touchstart', handleTouch);
                canvas.addEventListener('touchmove', handleTouch);
                canvas.addEventListener('touchend', handleTouch);
            }
            
            function startDrawing(e) {
                isDrawing = true;
                const rect = e.target.getBoundingClientRect();
                startX = e.clientX - rect.left;
                startY = e.clientY - rect.top;
            }
            
            function draw(e) {
                if (!isDrawing) return;
                
                const canvas = document.getElementById('region-canvas');
                const ctx = canvas.getContext('2d');
                const rect = e.target.getBoundingClientRect();
                
                const currentX = e.clientX - rect.left;
                const currentY = e.clientY - rect.top;
                
                // Clear canvas
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // Draw rectangle
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 2;
                ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
                
                // Semi-transparent fill
                ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
                ctx.fillRect(startX, startY, currentX - startX, currentY - startY);
                
                updateRegionInfo(startX, startY, currentX, currentY);
            }
            
            function stopDrawing(e) {
                if (!isDrawing) return;
                isDrawing = false;
                
                const rect = e.target.getBoundingClientRect();
                const endX = e.clientX - rect.left;
                const endY = e.clientY - rect.top;
                
                // Convert canvas coordinates to camera coordinates (640x480)
                const scaleX = 640 / 400;
                const scaleY = 480 / 300;
                
                currentRegion = {
                    x1: Math.round(Math.min(startX, endX) * scaleX),
                    y1: Math.round(Math.min(startY, endY) * scaleY),
                    x2: Math.round(Math.max(startX, endX) * scaleX),
                    y2: Math.round(Math.max(startY, endY) * scaleY)
                };
                
                updateRegionInfo(startX, startY, endX, endY);
            }
            
            function handleTouch(e) {
                e.preventDefault();
                const touch = e.touches[0] || e.changedTouches[0];
                const mouseEvent = new MouseEvent(e.type === 'touchstart' ? 'mousedown' : 
                                                 e.type === 'touchmove' ? 'mousemove' : 'mouseup', {
                    clientX: touch.clientX,
                    clientY: touch.clientY
                });
                e.target.dispatchEvent(mouseEvent);
            }
            
            function updateRegionInfo(x1, y1, x2, y2) {
                const info = document.getElementById('region-info');
                if (currentRegion) {
                    info.innerHTML = `
                        Region: (${currentRegion.x1}, ${currentRegion.y1}) to (${currentRegion.x2}, ${currentRegion.y2})<br>
                        Size: ${currentRegion.x2 - currentRegion.x1} x ${currentRegion.y2 - currentRegion.y1} pixels
                    `;
                } else {
                    info.textContent = 'Draw a region on the image above';
                }
            }
            
            function clearRegion() {
                const canvas = document.getElementById('region-canvas');
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                currentRegion = null;
                updateRegionInfo();
            }
            
            function setDefaultRegion() {
                // Set to center 60% of frame
                currentRegion = {
                    x1: 128,  // 20% of 640
                    y1: 96,   // 20% of 480  
                    x2: 512,  // 80% of 640
                    y2: 384   // 80% of 480
                };
                
                // Draw on canvas
                const canvas = document.getElementById('region-canvas');
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // Convert to canvas coordinates
                const x1 = currentRegion.x1 * 400 / 640;
                const y1 = currentRegion.y1 * 300 / 480;
                const x2 = currentRegion.x2 * 400 / 640;
                const y2 = currentRegion.y2 * 300 / 480;
                
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 2;
                ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
                ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
                ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
                
                updateRegionInfo();
            }
            
            function loadCurrentSettings() {
                fetch('/api/motion-settings')
                    .then(r => r.json())
                    .then(data => {
                        if (data.region) {
                            currentRegion = data.region;
                            // Draw current region on canvas
                            const canvas = document.getElementById('region-canvas');
                            const ctx = canvas.getContext('2d');
                            
                            const x1 = data.region.x1 * 400 / 640;
                            const y1 = data.region.y1 * 300 / 480;
                            const x2 = data.region.x2 * 400 / 640;
                            const y2 = data.region.y2 * 300 / 480;
                            
                            ctx.strokeStyle = '#00ff00';
                            ctx.lineWidth = 2;
                            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
                            ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
                            ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
                            
                            updateRegionInfo();
                        }
                        
                        document.getElementById('threshold-slider').value = data.motion_threshold || 5000;
                        document.getElementById('size-slider').value = data.min_contour_area || 500;
                        document.getElementById('threshold-value').textContent = data.motion_threshold || 5000;
                        document.getElementById('size-value').textContent = data.min_contour_area || 500;
                    });
                
                // Update slider values in real-time
                document.getElementById('threshold-slider').oninput = function() {
                    document.getElementById('threshold-value').textContent = this.value;
                };
                
                document.getElementById('size-slider').oninput = function() {
                    document.getElementById('size-value').textContent = this.value;
                };
            }
            
            function saveSettings() {
                if (!currentRegion) {
                    alert('Please draw a motion detection region first');
                    return;
                }
                
                const settings = {
                    region: currentRegion,
                    motion_threshold: parseInt(document.getElementById('threshold-slider').value),
                    min_contour_area: parseInt(document.getElementById('size-slider').value)
                };
                
                fetch('/api/motion-settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(settings)
                })
                .then(r => r.json())
                .then(data => {
                    alert(data.message || 'Settings saved!');
                    document.querySelector('.modal').remove();
                    updateDashboard();
                })
                .catch(err => alert('Failed to save settings: ' + err));
            }
            
            function testMotion() {
                alert('Wave your hand in the detection region and watch the live feed for motion indicators!');
            }

            function viewVideo(filename) {
                console.log('Attempting to play video:', filename);
                const videoUrl = `http://192.168.1.136:8091/videos/${filename}`;
                console.log('Video URL:', videoUrl);
                
                // Skip CORS-blocked HEAD request, go directly to showing video
                showVideoModal(videoUrl, filename);
            }
            
            function showVideoModal(videoUrl, filename) {
                // Create modal overlay
                const modal = document.createElement('div');
                modal.style.cssText = `
                    position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                    background: rgba(0,0,0,0.8); z-index: 1000; 
                    display: flex; align-items: center; justify-content: center;
                `;
                
                // Create video container
                const videoContainer = document.createElement('div');
                videoContainer.style.cssText = `
                    background: white; padding: 20px; border-radius: 10px; 
                    max-width: 90%; max-height: 90%; position: relative;
                `;
                
                videoContainer.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0;">📹 ${filename}</h3>
                        <button onclick="this.closest('.modal').remove()" style="background: #e74c3c; color: white; border: none; padding: 8px 12px; border-radius: 5px; cursor: pointer;">✕ Close</button>
                    </div>
                    <video controls style="width: 100%; max-width: 800px;" preload="metadata">
                        <source src="${videoUrl}" type='video/mp4; codecs="mp4v.20.8, mp4a.40.2"'>
                        <source src="${videoUrl}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div style="margin-top: 10px;">
                        <a href="${videoUrl}" target="_blank" style="background: #27ae60; color: white; padding: 8px 12px; text-decoration: none; border-radius: 5px; margin-right: 10px;">📥 Download Video</a>
                        <a href="${videoUrl}" target="_blank" style="background: #3498db; color: white; padding: 8px 12px; text-decoration: none; border-radius: 5px;">🔗 Open in New Tab</a>
                    </div>
                    <div id="video-status" style="margin-top: 10px; font-size: 14px; color: #666;"></div>
                `;
                
                modal.className = 'modal';
                modal.appendChild(videoContainer);
                document.body.appendChild(modal);
                
                // Add video event listeners for debugging
                const video = videoContainer.querySelector('video');
                const statusDiv = videoContainer.querySelector('#video-status');
                
                video.addEventListener('loadstart', () => {
                    statusDiv.textContent = 'Loading video...';
                });
                
                video.addEventListener('loadedmetadata', () => {
                    statusDiv.textContent = `Video loaded: ${video.duration.toFixed(1)}s duration`;
                });
                
                video.addEventListener('error', (e) => {
                    console.error('Video error:', e);
                    statusDiv.innerHTML = '<span style="color: red;">❌ Error loading video. Check console for details.</span>';
                });
                
                video.addEventListener('canplay', () => {
                    statusDiv.textContent = 'Video ready to play';
                });
                
                // Close on background click
                modal.onclick = (e) => {
                    if (e.target === modal) modal.remove();
                };
            }

            function updateDashboard() {
                // Update Pi status
                fetch('/api/status')
                    .then(r => r.json())
                    .then(data => {
                        // Pi stats
                        if (data.pi) {
                            document.getElementById('pi-total-videos').textContent = data.pi.total_videos;
                            document.getElementById('pi-synced').textContent = data.pi.synced_videos;
                            document.getElementById('pi-pending').textContent = data.pi.pending_sync;
                            document.getElementById('pi-storage').textContent = Math.round(data.pi.total_size_mb);
                            
                            const piStatus = document.getElementById('pi-status-text');
                            if (data.pi.is_capturing) {
                                piStatus.innerHTML = '<span class="status-indicator recording"></span>RECORDING - Motion detected';
                            } else {
                                piStatus.innerHTML = '<span class="status-indicator online"></span>MONITORING - Waiting for motion';
                            }
                        }

                        // Server stats
                        const connectionStatus = document.getElementById('connection-status');
                        if (data.server_connected && data.server) {
                            connectionStatus.innerHTML = '<span class="status-indicator online"></span>Server Connected';
                            
                            document.getElementById('server-processed').textContent = data.server.processed_videos;
                            document.getElementById('server-queue').textContent = data.server.queue_size;
                            document.getElementById('server-birds').textContent = data.server.total_birds;
                            document.getElementById('server-today').textContent = data.server.today_birds;
                            
                            const serverStatus = document.getElementById('server-status-text');
                            if (data.server.is_processing) {
                                serverStatus.innerHTML = '<span class="status-indicator processing"></span>PROCESSING videos...';
                            } else {
                                const gpu = data.server.gpu_available ? '🚀 GPU' : '💻 CPU';
                                serverStatus.innerHTML = `<span class="status-indicator online"></span>Ready (${gpu})`;
                            }
                        } else {
                            connectionStatus.innerHTML = '<span class="status-indicator offline"></span>Server Offline';
                            ['server-processed', 'server-queue', 'server-birds', 'server-today'].forEach(id => {
                                document.getElementById(id).textContent = '-';
                            });
                            document.getElementById('server-status-text').innerHTML = '<span class="status-indicator offline"></span>Cannot connect to processing server';
                        }
                    })
                    .catch(err => console.log('Status update failed:', err));

                // Update detections
                fetch('/api/server-detections')
                    .then(r => r.json())
                    .then(data => {
                        const grid = document.getElementById('detection-grid');
                        if (data.detections && data.detections.length > 0) {
                            grid.innerHTML = data.detections.map(d => `
                                <div class="detection-card">
                                    <img src="http://192.168.1.136:8091/thumbnails/${d.thumbnail}" alt="Bird detection" 
                                         onerror="this.style.display='none'" style="cursor: pointer;" onclick="viewVideo('${d.filename}')">
                                    <div><strong>Confidence:</strong> ${(d.confidence * 100).toFixed(1)}%</div>
                                    <div><strong>Time:</strong> ${d.timestamp.toFixed(1)}s in video</div>
                                    <div class="filename"><strong>File:</strong> ${d.filename}</div>
                                    <div><strong>Found:</strong> ${new Date(d.received_time).toLocaleString()}</div>
                                    <button class="btn" style="margin-top: 8px; width: 100%; font-size: 12px;" onclick="viewVideo('${d.filename}')">▶️ Play Video</button>
                                </div>
                            `).join('');
                        } else {
                            grid.innerHTML = '<p style="text-align: center; color: #666;">No recent bird detections</p>';
                        }
                    })
                    .catch(err => {
                        document.getElementById('detection-grid').innerHTML = '<p style="text-align: center; color: #999;">Could not load detections (server offline)</p>';
                    });
            }

            function syncNow() {
                fetch('/api/sync-now', {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message || data.error);
                        updateDashboard();
                    })
                    .catch(err => alert('Sync failed: ' + err));
            }

            function processServerQueue() {
                fetch('/api/process-server-queue', {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message || data.error);
                        updateDashboard();
                    })
                    .catch(err => alert('Process failed: ' + err));
            }

            // Error handling for live feed
            document.getElementById('live-image').onerror = function() {
                this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAwIiBoZWlnaHQ9IjM3NSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIyMCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkNhbWVyYSBOb3QgQXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg==';
            };

            updateDashboard();
            setInterval(updateDashboard, 5000);
        </script>
    </body>
    </html>
    ''')

@app.route('/api/status')
def api_status():
    if capture_system:
        return jsonify(capture_system.get_status())
    return jsonify({'error': 'System not initialized'})

@app.route('/api/sync-now', methods=['POST'])
def api_sync_now():
    """Manual sync trigger"""
    if capture_system:
        try:
            # Run sync in background thread to avoid blocking the web request
            threading.Thread(target=capture_system.sync_files_to_processor, daemon=True).start()
            return jsonify({'message': 'Sync started successfully'})
        except Exception as e:
            return jsonify({'error': f'Sync failed: {str(e)}'}), 500
    return jsonify({'error': 'Capture system not initialized'}), 500

@app.route('/api/server-detections')
def api_server_detections():
    """Get recent detections from processing server"""
    if capture_system:
        detections = capture_system.get_server_recent_detections()
        return jsonify({'detections': detections})
    return jsonify({'error': 'System not initialized'})

@app.route('/api/process-server-queue', methods=['POST'])
def api_process_server_queue():
    """Trigger processing on the server"""
    if not capture_system or not capture_system.processing_server:
        return jsonify({'error': 'Processing server not configured'}), 400
    
    try:
        response = requests.post(
            f"http://{capture_system.processing_server}:8091/api/process-now",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            return jsonify({'error': f'Server returned {response.status_code}'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to contact server: {str(e)}'}), 500

@app.route('/api/motion-settings', methods=['GET'])
def api_get_motion_settings():
    """Get current motion detection settings"""
    if capture_system:
        settings = {
            'region': None,
            'motion_threshold': capture_system.motion_threshold,
            'min_contour_area': capture_system.min_contour_area
        }
        
        if capture_system.motion_region:
            x1, y1, x2, y2 = capture_system.motion_region
            settings['region'] = {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
        
        return jsonify(settings)
    return jsonify({'error': 'System not initialized'})

@app.route('/api/motion-settings', methods=['POST'])
def api_set_motion_settings():
    """Save motion detection settings"""
    if not capture_system:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        data = request.get_json()
        region_data = data.get('region')
        motion_threshold = data.get('motion_threshold', 5000)
        min_contour_area = data.get('min_contour_area', 500)
        
        if region_data:
            region = (region_data['x1'], region_data['y1'], region_data['x2'], region_data['y2'])
            capture_system.save_motion_settings(region, motion_threshold, min_contour_area)
            return jsonify({'message': 'Motion settings saved successfully'})
        else:
            return jsonify({'error': 'Invalid region data'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Failed to save settings: {str(e)}'}), 500

@app.route('/live_feed')
def live_feed():
    """Live video feed for troubleshooting"""
    def generate():
        while True:
            if capture_system and capture_system.cap and capture_system.cap.isOpened():
                ret, frame = capture_system.cap.read()
                if ret:
                    # Resize for web viewing
                    frame = cv2.resize(frame, (640, 480))
                    # Add motion detection overlay
                    try:
                        has_motion = capture_system.detect_motion(frame.copy())
                        color = (0, 255, 0) if has_motion else (0, 0, 255)
                        cv2.putText(frame, f"Motion: {has_motion}", (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                        cv2.putText(frame, f"Recording: {capture_system.is_capturing}", (10, 70),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                        
                        # Draw motion detection region
                        if capture_system.motion_region:
                            x1, y1, x2, y2 = capture_system.motion_region
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
                            cv2.putText(frame, "Detection Zone", (x1, y1-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    except:
                        pass
                    # Encode frame
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else:
                # Send blank frame if camera not available
                blank = 255 * cv2.ones((480, 640, 3), dtype=cv2.uint8)
                cv2.putText(blank, "Camera Not Available", (150, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                _, buffer = cv2.imencode('.jpg', blank)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.1)  # 10 FPS for web viewing

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    initialize_system()
    app.run(host='0.0.0.0', port=8090, threaded=True)