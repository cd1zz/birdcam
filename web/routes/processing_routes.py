# web/routes/processing_routes.py - FIXED VERSION
"""
Routes for Processing Server
"""
import threading
from flask import request, jsonify, render_template, send_from_directory

def create_processing_routes(app, processing_service, video_repo, detection_repo, config):
    
    @app.route('/')
    def dashboard():
        return render_template('processing_dashboard.html')
    
    @app.route('/upload', methods=['POST'])
    def upload_video():
        if 'video' not in request.files:
            return jsonify({'error': 'No video file'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No filename'}), 400
        
        try:
            filename = processing_service.receive_video(file.read(), file.filename)
            return jsonify({'message': 'Video received', 'filename': filename}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/status')
    def api_status():
        total_videos = video_repo.get_total_count()
        processed_videos = video_repo.get_processed_count()
        
        # Use the new repository methods for better stats
        try:
            total_birds = video_repo.get_total_birds()
            today_birds = video_repo.get_today_birds()
            avg_processing_time = video_repo.get_average_processing_time()
        except Exception as e:
            print(f"Error getting enhanced stats: {e}")
            total_birds = 0
            today_birds = 0
            avg_processing_time = 0.0
        
        return jsonify({
            'total_videos': total_videos,
            'processed_videos': processed_videos,
            'queue_size': total_videos - processed_videos,
            'total_birds': total_birds,
            'today_birds': today_birds,
            'avg_processing_time': avg_processing_time,
            'is_processing': processing_service.is_processing,
            'model_loaded': processing_service.model_manager.is_loaded,
            'gpu_available': processing_service.model_manager.gpu_available
        })
    
    @app.route('/api/recent-detections')
    def api_recent_detections():
        detections_data = detection_repo.get_recent_with_thumbnails()
        detections = []
        
        for item in detections_data:
            detection = item['detection']
            detections.append({
                'filename': item['filename'],
                'received_time': item['received_time'],
                'timestamp': detection.timestamp,
                'confidence': detection.confidence,
                'thumbnail': detection.thumbnail_path,
                'duration': item['duration']
            })
        
        return jsonify({'detections': detections})
    
    @app.route('/api/process-now', methods=['POST'])
    def api_process_now():
        try:
            threading.Thread(target=processing_service.process_pending_videos, daemon=True).start()
            return jsonify({'message': 'Processing queue started'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/motion-settings', methods=['GET'])
    def api_get_motion_settings():
        """Get motion detection settings (placeholder for processing server)"""
        # Processing server doesn't handle motion detection, but we provide endpoint for compatibility
        return jsonify({
            'region': None,
            'motion_threshold': 5000,
            'min_contour_area': 500,
            'note': 'Motion detection is handled by Pi capture system'
        })
    
    @app.route('/api/motion-settings', methods=['POST'])
    def api_set_motion_settings():
        """Set motion detection settings (placeholder for processing server)"""
        # Processing server doesn't handle motion detection
        return jsonify({
            'message': 'Motion settings received but not applied (processing server)',
            'note': 'Motion detection is handled by Pi capture system'
        })
    
    @app.route('/videos/<filename>')
    def serve_video(filename):
        # Check processed directory first
        processed_path = config.processing.storage_path / "processed" / filename
        if processed_path.exists():
            return send_from_directory(config.processing.storage_path / "processed", filename)
        
        # Then check incoming directory
        incoming_path = config.processing.storage_path / "incoming" / filename
        if incoming_path.exists():
            return send_from_directory(config.processing.storage_path / "incoming", filename)
        
        return "Video not found", 404
    
    @app.route('/thumbnails/<filename>')
    def serve_thumbnail(filename):
        return send_from_directory(config.processing.storage_path / "thumbnails", filename)