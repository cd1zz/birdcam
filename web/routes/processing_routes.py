# web/routes/processing_routes.py
"""
Routes for Processing Server with Detections/No-Detections Structure
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
            total_detections = video_repo.get_total_detections()
            today_detections = video_repo.get_today_detections()
            avg_processing_time = video_repo.get_average_processing_time()
        except Exception as e:
            print(f"Error getting enhanced stats: {e}")
            total_detections = 0
            today_detections = 0
            avg_processing_time = 0.0
        
        return jsonify({
            'total_videos': total_videos,
            'processed_videos': processed_videos,
            'queue_size': total_videos - processed_videos,
            'total_detections': total_detections,
            'today_detections': today_detections,
            'avg_processing_time': avg_processing_time,
            'is_processing': processing_service.is_processing,
            'model_loaded': processing_service.model_manager.is_loaded,
            'gpu_available': processing_service.model_manager.gpu_available,
            'detection_classes': processing_service.config.detection.classes
        })
    
    def _bbox_iou(boxA, boxB):
        """Compute Intersection over Union of two bounding boxes"""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
        boxBArea = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
        unionArea = boxAArea + boxBArea - interArea
        return interArea / unionArea if unionArea > 0 else 0.0

    def _cluster_detections(items, time_window=300, iou_thresh=0.3, limit=20):
        """Group detections by temporal and spatial proximity"""
        events = []
        for item in items:
            det = item['detection']
            abs_time = item['received_time'].timestamp() + det.timestamp

            matched = None
            for event in events:
                if det.species != event['species']:
                    continue
                if abs(abs_time - event['abs_time']) > time_window:
                    continue
                if _bbox_iou(det.bbox, event['bbox']) < iou_thresh:
                    continue
                matched = event
                break

            if matched:
                matched['count'] += 1
                matched['abs_time'] = max(matched['abs_time'], abs_time)
                if det.confidence > matched['confidence']:
                    matched.update({
                        'id': det.id,
                        'filename': item['filename'],
                        'timestamp': det.timestamp,
                        'confidence': det.confidence,
                        'thumbnail': det.thumbnail_path,
                        'received_time': item['received_time'],
                        'duration': item['duration'],
                        'bbox': det.bbox,
                    })
            else:
                events.append({
                    'id': det.id,
                    'filename': item['filename'],
                    'received_time': item['received_time'],
                    'timestamp': det.timestamp,
                    'confidence': det.confidence,
                    'thumbnail': det.thumbnail_path,
                    'duration': item['duration'],
                    'species': det.species,
                    'bbox': det.bbox,
                    'count': 1,
                    'abs_time': abs_time,
                })

        events.sort(key=lambda e: e['abs_time'], reverse=True)
        return events[:limit]

    @app.route('/api/recent-detections')
    def api_recent_detections():
        # Fetch a larger number of raw detections for clustering
        raw_items = detection_repo.get_recent_with_thumbnails(limit=100)
        events = _cluster_detections(raw_items)
        for e in events:
            e.pop('bbox', None)
            e.pop('abs_time', None)
        return jsonify({'detections': events})
    
    @app.route('/api/process-now', methods=['POST'])
    def api_process_now():
        try:
            threading.Thread(target=processing_service.process_pending_videos, daemon=True).start()
            return jsonify({'message': 'Processing queue started'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/cleanup-now', methods=['POST'])
    def api_cleanup_now():
        """Manually trigger video cleanup"""
        try:
            threading.Thread(target=processing_service.cleanup_old_videos, daemon=True).start()
            return jsonify({'message': 'Cleanup started'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/delete-detection', methods=['POST'])
    def api_delete_detection():
        data = request.get_json()
        detection_id = data.get('detection_id') if data else None
        if detection_id is None:
            return jsonify({'error': 'detection_id required'}), 400
        try:
            deleted = processing_service.delete_detection(int(detection_id))
            if deleted:
                return jsonify({'message': 'Detection deleted'})
            return jsonify({'error': 'Detection not found'}), 404
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
        """Serve video files from detections or no_detections directories"""
        # Check detections directory first (most likely to be accessed)
        detections_path = config.processing.storage_path / "processed" / "detections" / filename
        if detections_path.exists():
            print(f"📹 Serving detection video: {filename}")
            return send_from_directory(config.processing.storage_path / "processed" / "detections", filename)
        
        # Then check no_detections directory
        no_detections_path = config.processing.storage_path / "processed" / "no_detections" / filename
        if no_detections_path.exists():
            print(f"📹 Serving no-detection video: {filename}")
            return send_from_directory(config.processing.storage_path / "processed" / "no_detections", filename)
        
        # Finally check incoming directory (for videos not yet processed)
        incoming_path = config.processing.storage_path / "incoming" / filename
        if incoming_path.exists():
            print(f"📹 Serving incoming video: {filename}")
            return send_from_directory(config.processing.storage_path / "incoming", filename)
        
        print(f"❌ Video not found: {filename}")
        print(f"   Checked: {detections_path}")
        print(f"   Checked: {no_detections_path}")
        print(f"   Checked: {incoming_path}")
        return "Video not found", 404
    
    @app.route('/thumbnails/<filename>')
    def serve_thumbnail(filename):
        return send_from_directory(config.processing.storage_path / "thumbnails", filename)