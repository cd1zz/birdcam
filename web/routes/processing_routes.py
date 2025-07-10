# web/routes/processing_routes.py
"""
Routes for Processing Server with Detections/No-Detections Structure
"""
import threading
from flask import request, jsonify, send_from_directory, send_file
from services.system_metrics import SystemMetricsCollector
from pathlib import Path

def create_processing_routes(app, processing_service, video_repo, detection_repo, config):
    
    # Initialize system metrics collector
    metrics_collector = SystemMetricsCollector(str(config.processing.storage_path))
    
    # Serve the React UI
    ui_build_path = Path(__file__).parent.parent.parent / "web-ui" / "dist"
    
    @app.route('/')
    def serve_ui():
        """Serve the React UI"""
        index_path = ui_build_path / "index.html"
        if index_path.exists():
            return send_file(index_path)
        else:
            return "UI not built. Run 'npm run build' in the web-ui directory.", 404
    
    @app.route('/<path:path>')
    def serve_ui_assets(path):
        """Serve UI assets and handle React routing"""
        # Check if it's a file request
        requested_file = ui_build_path / path
        if requested_file.exists() and requested_file.is_file():
            return send_file(requested_file)
        
        # For React routing (non-API paths), serve index.html
        if not path.startswith('api/'):
            index_path = ui_build_path / "index.html"
            if index_path.exists():
                return send_file(index_path)
        
        return "File not found", 404
    
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

    def _center_distance(boxA, boxB):
        cxA = (boxA[0] + boxA[2]) / 2
        cyA = (boxA[1] + boxA[3]) / 2
        cxB = (boxB[0] + boxB[2]) / 2
        cyB = (boxB[1] + boxB[3]) / 2
        return ((cxA - cxB) ** 2 + (cyA - cyB) ** 2) ** 0.5

    def _cluster_detections(items, time_window=60, iou_thresh=0.1,
                            center_thresh=150, limit=20):
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
                if (_bbox_iou(det.bbox, event['bbox']) < iou_thresh and
                        _center_distance(det.bbox, event['bbox']) > center_thresh):
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
        if limit:
            events = events[:limit]
        return events

    @app.route('/api/recent-detections')
    def api_recent_detections():
        species = request.args.get('species')
        start = request.args.get('start')
        end = request.args.get('end')
        sort = request.args.get('sort', 'desc')
        limit = request.args.get('limit', default=20, type=int)

        raw_items = detection_repo.get_recent_filtered_with_thumbnails(
            species=species, start=start, end=end, limit=100)
        events = _cluster_detections(raw_items, limit=None)
        events.sort(key=lambda e: e['abs_time'], reverse=(sort != 'asc'))
        events = events[:limit]
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
    
    @app.route('/api/reset-queue', methods=['POST'])
    def api_reset_queue():
        """Reset failed/stuck videos back to pending status"""
        try:
            with video_repo.db_manager.get_connection() as conn:
                # Count videos that need to be reset
                cursor = conn.execute("SELECT COUNT(*) FROM videos WHERE status NOT IN ('completed', 'pending')")
                reset_count = cursor.fetchone()[0]
                
                # Reset them to pending
                cursor = conn.execute("UPDATE videos SET status = 'pending' WHERE status NOT IN ('completed', 'pending')")
                conn.commit()
                
                return jsonify({
                    'message': f'Reset {reset_count} videos to pending status',
                    'reset_count': reset_count
                })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/debug/simple')
    def api_debug_simple():
        """Simple debug endpoint with minimal data"""
        try:
            # Direct database check without using ORM objects
            from pathlib import Path
            import sqlite3
            
            db_path = Path(processing_service.config.database.path)
            
            result = {
                'database_exists': db_path.exists(),
                'database_path': str(db_path)
            }
            
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # Count by status
                cursor.execute('SELECT status, COUNT(*) FROM videos GROUP BY status')
                status_counts = dict(cursor.fetchall())
                result['status_counts'] = status_counts
                
                # Count pending specifically
                cursor.execute('SELECT COUNT(*) FROM videos WHERE status = ?', ('pending',))
                pending_count = cursor.fetchone()[0]
                result['pending_count'] = pending_count
                
                # Get recent videos
                cursor.execute('SELECT id, filename, status FROM videos ORDER BY id DESC LIMIT 5')
                recent = cursor.fetchall()
                result['recent_videos'] = [{'id': r[0], 'filename': r[1], 'status': r[2]} for r in recent]
                
                conn.close()
            
            # Check directories
            incoming_dir = Path(processing_service.incoming_dir)
            result['incoming_dir'] = str(incoming_dir)
            result['incoming_exists'] = incoming_dir.exists()
            
            if incoming_dir.exists():
                result['incoming_files'] = len(list(incoming_dir.glob('*.mp4')))
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e), 'type': type(e).__name__}), 500

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
        """Get motion detection settings"""
        import json
        from pathlib import Path
        
        try:
            camera_id = request.args.get('camera_id', '0')
            
            # Safely get storage path
            try:
                storage_path = Path(config.processing.storage_path)
            except Exception as e:
                print(f"Error accessing storage path: {e}")
                storage_path = Path("./bird_processing")
            
            settings_file = storage_path / f"motion_settings_camera_{camera_id}.json"
            
            # Default settings
            default_settings = {
                'region': None,
                'motion_threshold': 5000,
                'min_contour_area': 500,
                'motion_timeout_seconds': 30,
                'motion_box_enabled': True,
                'motion_box_x1': 100,
                'motion_box_y1': 100,
                'motion_box_x2': 500,
                'motion_box_y2': 350,
            }
            
            # Load saved settings if they exist
            if settings_file.exists():
                try:
                    with open(settings_file, 'r') as f:
                        saved_settings = json.load(f)
                        default_settings.update(saved_settings)
                except Exception as e:
                    print(f"Error loading motion settings: {e}")
            
            return jsonify(default_settings)
            
        except Exception as e:
            print(f"Error in motion settings GET: {e}")
            return jsonify({
                'region': None,
                'motion_threshold': 5000,
                'min_contour_area': 500,
                'motion_timeout_seconds': 30,
                'motion_box_enabled': True,
                'motion_box_x1': 100,
                'motion_box_y1': 100,
                'motion_box_x2': 500,
                'motion_box_y2': 350,
            })
    
    @app.route('/api/motion-settings', methods=['POST'])
    def api_set_motion_settings():
        """Set motion detection settings"""
        import json
        from pathlib import Path
        
        try:
            data = request.get_json() or {}
            camera_id = request.args.get('camera_id', '0')
            settings_file = Path(config.processing.storage_path) / f"motion_settings_camera_{camera_id}.json"
            
            # Ensure storage directory exists
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing settings
            current_settings = {}
            if settings_file.exists():
                try:
                    with open(settings_file, 'r') as f:
                        current_settings = json.load(f)
                except Exception as e:
                    print(f"Error loading existing settings: {e}")
            
            # Update with new settings
            current_settings.update(data)
            
            # Save to file
            with open(settings_file, 'w') as f:
                json.dump(current_settings, f, indent=2)
            
            print(f"✅ Saved motion settings for camera {camera_id}: {data}")
            
            return jsonify({
                'message': f'Motion settings saved for camera {camera_id}',
                'saved_settings': current_settings,
                'file_path': str(settings_file)
            })
            
        except Exception as e:
            print(f"❌ Error saving motion settings: {e}")
            return jsonify({
                'error': f'Failed to save motion settings: {str(e)}'
            }), 500
    
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
    
    @app.route('/api/system-metrics')
    def api_system_metrics():
        """Get current system metrics (CPU, memory, disk)"""
        try:
            metrics = metrics_collector.get_metrics_dict()
            return jsonify(metrics)
        except Exception as e:
            return jsonify({'error': str(e)}), 500