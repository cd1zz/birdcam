# pc_processor.py - Run this on your powerful computer
import cv2
import torch
import os
import time
import threading
import subprocess
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
import sqlite3
import json
from pathlib import Path
import warnings
import schedule
from werkzeug.utils import secure_filename
import shutil

# Suppress torch warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="torch")
warnings.filterwarnings("ignore", message=".*torch.cuda.amp.autocast.*")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

class BirdProcessingSystem:
    def __init__(self, storage_path="./bird_processing"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        # Directories
        self.incoming_dir = self.storage_path / "incoming"
        self.processed_dir = self.storage_path / "processed"
        self.thumbnails_dir = self.storage_path / "thumbnails"
        self.results_dir = self.storage_path / "results"

        for dir_path in [self.incoming_dir, self.processed_dir, self.thumbnails_dir, self.results_dir]:
            dir_path.mkdir(exist_ok=True)

        # Database
        self.db_path = self.storage_path / "bird_detections.db"
        self.init_database()

        # AI Model - loaded on demand
        self.model = None
        self.model_loaded = False

        # Processing queue
        self.processing_queue = []
        self.processing_lock = threading.Lock()
        self.is_processing = False

        print("🧠 PC Processing System initialized")

    def init_database(self):
        """Initialize detection database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                original_filename TEXT,
                received_time TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                processing_time REAL,
                bird_count INTEGER DEFAULT 0,
                file_size INTEGER,
                duration REAL,
                fps REAL,
                resolution TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bird_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER,
                frame_number INTEGER,
                timestamp REAL,
                confidence REAL,
                bbox_x1 INTEGER,
                bbox_y1 INTEGER,
                bbox_x2 INTEGER,
                bbox_y2 INTEGER,
                species TEXT DEFAULT 'bird',
                thumbnail_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES video_files (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE,
                videos_processed INTEGER DEFAULT 0,
                total_birds INTEGER DEFAULT 0,
                processing_time_total REAL DEFAULT 0,
                avg_processing_time REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def load_model(self):
        """Load YOLO model for processing"""
        if not self.model_loaded:
            print("🤖 Loading YOLO model...")
            self.model = torch.hub.load('ultralytics/yolov5', 'yolov5n', force_reload=False)
            self.model.conf = 0.35  # Lower threshold for better bird detection

            # Use GPU if available
            if torch.cuda.is_available():
                self.model = self.model.cuda()
                print(f"🚀 Using GPU: {torch.cuda.get_device_name()}")
            else:
                print("💻 Using CPU for inference")

            self.model_loaded = True
            print("✅ Model loaded successfully")

    def receive_video(self, file_data, filename):
        """Receive video file from Pi"""
        # Secure filename
        safe_filename = secure_filename(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{safe_filename}"

        file_path = self.incoming_dir / unique_filename

        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_data)

        file_size = file_path.stat().st_size

        # Add to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO video_files (filename, original_filename, received_time, file_size)
            VALUES (?, ?, ?, ?)
        ''', (unique_filename, filename, datetime.now(), file_size))
        conn.commit()
        conn.close()

        # Add to processing queue
        with self.processing_lock:
            self.processing_queue.append(unique_filename)

        print(f"📥 Received: {filename} -> {unique_filename} ({file_size/1024/1024:.1f}MB)")
        return unique_filename

    def convert_to_h264_for_web(self, filename):
        """Convert videos to H.264 for web browser compatibility"""
        input_path = self.processed_dir / filename
        if not input_path.exists():
            return False
        
        try:
            # Check current codec
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-select_streams', 'v:0', 
                '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', 
                str(input_path)
            ], capture_output=True, text=True, timeout=10)
            
            codec = result.stdout.strip()
            if codec == 'h264':
                print(f"✅ {filename} already uses H.264")
                return True
                
            print(f"🔄 Converting {filename} from {codec} to H.264 for web compatibility...")
            
            # Create temporary output file
            temp_path = input_path.with_suffix('.h264.mp4')
            
            # Convert to H.264 with web optimization
            subprocess.run([
                'ffmpeg', '-i', str(input_path), 
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-c:a', 'aac', '-movflags', '+faststart',  # Web-optimized
                '-y',  # Overwrite output file
                str(temp_path)
            ], check=True, timeout=300, capture_output=True)
            
            # Replace original
            input_path.unlink()
            temp_path.rename(input_path)
            
            print(f"✅ Converted {filename} to H.264")
            return True
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"❌ Failed to convert {filename}: {e}")
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            return False

    def process_video_queue(self):
        """Process all videos in queue"""
        if self.is_processing:
            print("⏳ Processing already in progress")
            return

        with self.processing_lock:
            if not self.processing_queue:
                print("📭 No videos to process")
                return

            videos_to_process = self.processing_queue.copy()
            self.processing_queue.clear()

        self.is_processing = True

        # Load model if needed
        if not self.model_loaded:
            self.load_model()

        print(f"🔄 Processing {len(videos_to_process)} videos...")

        for filename in videos_to_process:
            try:
                self.process_single_video(filename)
            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")

        self.is_processing = False
        print("✅ Batch processing complete")

    def process_single_video(self, filename):
        """Process a single video for bird detection"""
        video_path = self.incoming_dir / filename
        if not video_path.exists():
            print(f"❌ Video not found: {filename}")
            return

        print(f"🔍 Processing: {filename}")
        start_time = time.time()

        # Open video
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0

        detections = []
        frame_number = 0
        frames_processed = 0

        # Process every 3rd frame for efficiency
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_number % 3 == 0:  # Process every 3rd frame
                timestamp = frame_number / fps if fps > 0 else frame_number * 0.1

                # Run YOLO detection
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=FutureWarning)
                    results = self.model(frame)

                detections_df = results.pandas().xyxy[0]

                # Extract bird detections
                for _, row in detections_df.iterrows():
                    if row['name'] == 'bird' and row['confidence'] > 0.3:
                        detection = {
                            'frame_number': frame_number,
                            'timestamp': timestamp,
                            'confidence': float(row['confidence']),
                            'bbox': [int(row['xmin']), int(row['ymin']),
                                   int(row['xmax']), int(row['ymax'])],
                            'frame': frame.copy()  # Store frame for thumbnail
                        }
                        detections.append(detection)

                frames_processed += 1

            frame_number += 1

            # Progress indicator
            if frame_number % 300 == 0:
                progress = (frame_number / total_frames) * 100
                print(f"  📊 Progress: {progress:.1f}% ({frames_processed} frames processed)")

        cap.release()

        processing_time = time.time() - start_time

        # Save results
        video_id = self.save_detection_results(
            filename, detections, processing_time, duration, fps, f"{width}x{height}"
        )

        # Generate thumbnails for detections
        if detections:
            self.generate_thumbnails(filename, video_id, detections[:5])  # First 5 detections

        # Move processed video
        processed_path = self.processed_dir / filename
        shutil.move(str(video_path), str(processed_path))

        # Convert to H.264 for web browser compatibility
        self.convert_to_h264_for_web(filename)

        print(f"✅ {filename}: {len(detections)} birds found in {processing_time:.1f}s")

        # Update daily stats
        self.update_daily_stats(len(detections), processing_time)

    def save_detection_results(self, filename, detections, processing_time, duration, fps, resolution):
        """Save detection results to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Update video file record
        cursor.execute('''
            UPDATE video_files
            SET processed = TRUE, processing_time = ?, bird_count = ?,
                duration = ?, fps = ?, resolution = ?
            WHERE filename = ?
        ''', (processing_time, len(detections), duration, fps, resolution, filename))

        # Get video ID
        cursor.execute('SELECT id FROM video_files WHERE filename = ?', (filename,))
        video_id = cursor.fetchone()[0]

        # Insert detections
        for detection in detections:
            cursor.execute('''
                INSERT INTO bird_detections
                (video_id, frame_number, timestamp, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (video_id, detection['frame_number'], detection['timestamp'],
                  detection['confidence'], *detection['bbox']))

        conn.commit()
        conn.close()

        return video_id

    def generate_thumbnails(self, filename, video_id, detections):
        """Generate thumbnails for detected birds"""
        for i, detection in enumerate(detections):
            frame = detection['frame']
            bbox = detection['bbox']

            # Draw bounding box
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            cv2.putText(frame, f"Bird {detection['confidence']:.2f}",
                       (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Add timestamp
            cv2.putText(frame, f"t={detection['timestamp']:.1f}s",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Save thumbnail
            thumb_filename = f"{filename}_{i+1}.jpg"
            thumb_path = self.thumbnails_dir / thumb_filename
            cv2.imwrite(str(thumb_path), frame)

            # Update database with thumbnail path
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE bird_detections
                SET thumbnail_path = ?
                WHERE video_id = ? AND frame_number = ?
            ''', (thumb_filename, video_id, detection['frame_number']))
            conn.commit()
            conn.close()

    def update_daily_stats(self, bird_count, processing_time):
        """Update daily processing statistics"""
        today = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert or update daily stats
        cursor.execute('''
            INSERT OR REPLACE INTO processing_stats
            (date, videos_processed, total_birds, processing_time_total, avg_processing_time)
            VALUES (?,
                    COALESCE((SELECT videos_processed FROM processing_stats WHERE date = ?), 0) + 1,
                    COALESCE((SELECT total_birds FROM processing_stats WHERE date = ?), 0) + ?,
                    COALESCE((SELECT processing_time_total FROM processing_stats WHERE date = ?), 0) + ?,
                    (COALESCE((SELECT processing_time_total FROM processing_stats WHERE date = ?), 0) + ?) /
                    (COALESCE((SELECT videos_processed FROM processing_stats WHERE date = ?), 0) + 1)
            )
        ''', (today, today, today, bird_count, today, processing_time, today, processing_time, today))

        conn.commit()
        conn.close()

    def get_status(self):
        """Get processing system status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Basic stats
        cursor.execute('SELECT COUNT(*) FROM video_files')
        total_videos = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM video_files WHERE processed = TRUE')
        processed_videos = cursor.fetchone()[0]

        cursor.execute('SELECT SUM(bird_count) FROM video_files')
        total_birds = cursor.fetchone()[0] or 0

        cursor.execute('SELECT AVG(processing_time) FROM video_files WHERE processed = TRUE')
        avg_processing_time = cursor.fetchone()[0] or 0

        # Today's stats
        cursor.execute('''
            SELECT videos_processed, total_birds, processing_time_total
            FROM processing_stats WHERE date = ?
        ''', (datetime.now().date(),))
        today_stats = cursor.fetchone()

        conn.close()

        with self.processing_lock:
            queue_size = len(self.processing_queue)

        return {
            'total_videos': total_videos,
            'processed_videos': processed_videos,
            'queue_size': queue_size,
            'total_birds': total_birds,
            'avg_processing_time': round(avg_processing_time, 2),
            'is_processing': self.is_processing,
            'model_loaded': self.model_loaded,
            'gpu_available': torch.cuda.is_available(),
            'today_videos': today_stats[0] if today_stats else 0,
            'today_birds': today_stats[1] if today_stats else 0,
            'today_processing_time': round(today_stats[2], 1) if today_stats else 0
        }

    def get_recent_detections(self, limit=20):
        """Get recent bird detections with thumbnails"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT vf.filename, vf.received_time, bd.timestamp, bd.confidence,
                   bd.thumbnail_path, vf.duration
            FROM bird_detections bd
            JOIN video_files vf ON bd.video_id = vf.id
            WHERE bd.thumbnail_path IS NOT NULL
            ORDER BY vf.received_time DESC, bd.timestamp DESC
            LIMIT ?
        ''', (limit,))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                'filename': row[0],
                'received_time': row[1],
                'timestamp': row[2],
                'confidence': row[3],
                'thumbnail': row[4],
                'duration': row[5]
            }
            for row in results
        ]

# Global processor instance
processor = None

def initialize_processor():
    global processor
    processor = BirdProcessingSystem()

    # Schedule automatic processing every 30 minutes
    schedule.every(30).minutes.do(processor.process_video_queue)

    # Start scheduler
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    print("🚀 Processing system ready")

@app.route('/upload', methods=['POST'])
def upload_video():
    """Receive video from Pi"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No filename'}), 400

    if processor:
        try:
            filename = processor.receive_video(file.read(), file.filename)
            return jsonify({'message': 'Video received', 'filename': filename}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Processor not initialized'}), 500

@app.route('/videos/<filename>')
def serve_video(filename):
    """Serve processed video files"""
    if processor:
        # Check processed directory first
        processed_path = processor.processed_dir / filename
        if processed_path.exists():
            print(f"📹 Serving video from processed: {filename}")
            return send_from_directory(processor.processed_dir, filename)
        
        # Then check incoming directory  
        incoming_path = processor.incoming_dir / filename
        if incoming_path.exists():
            print(f"📹 Serving video from incoming: {filename}")
            return send_from_directory(processor.incoming_dir, filename)
    
    print(f"❌ Video not found: {filename}")
    return "Video not found", 404

@app.route('/thumbnails/<filename>')
def serve_thumbnail(filename):
    """Serve thumbnail images"""
    if processor:
        return send_from_directory(processor.thumbnails_dir, filename)
    return "Not found", 404

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🧠 Bird AI Processor</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 15px; border-radius: 8px; text-align: center; }
            .stat-number { font-size: 2em; font-weight: bold; color: #27ae60; }
            .stat-label { color: #666; font-size: 0.9em; }
            .detections { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            .detection-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }
            .detection-card { border: 1px solid #ddd; border-radius: 8px; padding: 10px; }
            .detection-card img { width: 100%; height: 150px; object-fit: cover; border-radius: 5px; }
            .btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
            .processing { background: #f39c12; }
            .status-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
            .online { background: #27ae60; }
            .processing-active { background: #f39c12; }
            .offline { background: #e74c3c; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧠 Bird AI Processing System</h1>
                <p>Advanced bird detection using YOLO on powerful hardware</p>
                <div id="system-status"></div>
            </div>

            <div class="stats" id="stats">
                <div class="stat-card">
                    <div class="stat-number" id="total-videos">-</div>
                    <div class="stat-label">Total Videos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="processed-videos">-</div>
                    <div class="stat-label">Processed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="queue-size">-</div>
                    <div class="stat-label">In Queue</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-birds">-</div>
                    <div class="stat-label">Birds Found</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="today-videos">-</div>
                    <div class="stat-label">Today's Videos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="avg-time">-</div>
                    <div class="stat-label">Avg Process Time (s)</div>
                </div>
            </div>

            <div class="detections">
                <h2>Recent Bird Detections</h2>
                <button class="btn" onclick="processNow()">Process Queue Now</button>
                <button class="btn" onclick="location.reload()">Refresh</button>
                <div id="detection-grid" class="detection-grid"></div>
            </div>
        </div>

        <script>
            function updateDashboard() {
                fetch('/api/status')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('total-videos').textContent = data.total_videos;
                        document.getElementById('processed-videos').textContent = data.processed_videos;
                        document.getElementById('queue-size').textContent = data.queue_size;
                        document.getElementById('total-birds').textContent = data.total_birds;
                        document.getElementById('today-videos').textContent = data.today_videos;
                        document.getElementById('avg-time').textContent = data.avg_processing_time;

                        const statusDiv = document.getElementById('system-status');
                        let statusClass = 'online';
                        let statusText = '🟢 System Online';

                        if (data.is_processing) {
                            statusClass = 'processing-active';
                            statusText = '🟡 Processing Videos...';
                        }

                        const gpuText = data.gpu_available ? ' | 🚀 GPU Enabled' : ' | 💻 CPU Only';
                        statusDiv.innerHTML = statusText + gpuText;
                    });

                fetch('/api/recent-detections')
                    .then(r => r.json())
                    .then(data => {
                        const grid = document.getElementById('detection-grid');
                        if (data.detections.length === 0) {
                            grid.innerHTML = '<p>No recent detections with thumbnails</p>';
                        } else {
                            grid.innerHTML = data.detections.map(d => `
                                <div class="detection-card">
                                    <img src="/thumbnails/${d.thumbnail}" alt="Bird detection" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk5vIEltYWdlPC90ZXh0Pjwvc3ZnPg=='">
                                    <div><strong>Confidence:</strong> ${(d.confidence * 100).toFixed(1)}%</div>
                                    <div><strong>Time:</strong> ${d.timestamp.toFixed(1)}s</div>
                                    <div><strong>Video:</strong> ${d.filename}</div>
                                    <div><strong>Received:</strong> ${new Date(d.received_time).toLocaleString()}</div>
                                </div>
                            `).join('');
                        }
                    });
            }

            function processNow() {
                fetch('/api/process-now', {method: 'POST'})
                    .then(r => r.json())
                    .then(data => alert(data.message));
            }

            updateDashboard();
            setInterval(updateDashboard, 10000);
        </script>
    </body>
    </html>
    ''')

@app.route('/api/status')
def api_status():
    if processor:
        return jsonify(processor.get_status())
    return jsonify({'error': 'Processor not initialized'})

@app.route('/api/recent-detections')
def api_recent_detections():
    if processor:
        detections = processor.get_recent_detections()
        return jsonify({'detections': detections})
    return jsonify({'error': 'Processor not initialized'})

@app.route('/api/process-now', methods=['POST'])
def api_process_now():
    if processor:
        threading.Thread(target=processor.process_video_queue, daemon=True).start()
        return jsonify({'message': 'Processing queue started'})
    return jsonify({'error': 'Processor not initialized'})

if __name__ == '__main__':
    initialize_processor()
    app.run(host='0.0.0.0', port=8091, threaded=True, debug=False)