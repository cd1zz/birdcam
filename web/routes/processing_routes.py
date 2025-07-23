# web/routes/processing_routes.py
"""
Routes for Processing Server with Detections/No-Detections Structure
"""
import threading
from flask import request, jsonify, send_from_directory, send_file
from services.system_metrics import SystemMetricsCollector
from pathlib import Path
from web.middleware.auth import require_auth, require_admin, require_auth_or_secret
from web.middleware.ip_restriction import require_internal_network

def create_processing_routes(app, processing_service, video_repo, detection_repo, config):
    
    # Initialize system metrics collector
    metrics_collector = SystemMetricsCollector(str(config.processing.storage_path))
    
    # Combined decorator for admin + internal network
    def require_admin_internal(f):
        return require_internal_network(require_admin(f))
    
    # Combined decorator for auth + internal network  
    def require_auth_internal(f):
        return require_internal_network(require_auth(f))
    
    # Track startup time for uptime calculation
    import time
    startup_time = time.time()
    
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
    @require_auth_or_secret
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
    @require_auth
    def api_status():
        """Enhanced status endpoint with detailed processing metrics"""
        try:
            # Calculate uptime
            uptime = int(time.time() - startup_time)
            
            # Get system metrics
            metrics = metrics_collector.get_metrics_dict()
            
            # Get storage info from metrics
            storage_info = metrics.get('disks', [{}])[0] if metrics.get('disks') else {}
            storage_used = int(storage_info.get('used_gb', 0) * 1024 * 1024 * 1024)  # Convert GB to bytes
            storage_total = int(storage_info.get('total_gb', 100) * 1024 * 1024 * 1024)  # Convert GB to bytes
            
            # Get enhanced processing metrics
            try:
                today_detections = video_repo.get_today_detections()
                videos_today = video_repo.get_processed_count()
                
                # Get queue metrics
                queue_stats = processing_service.get_queue_metrics()
                
                # Get processing performance
                processing_stats = processing_service.get_processing_rate_metrics()
                
                # Get detailed statistics
                detailed_stats = processing_service.get_detailed_processing_stats()
                
            except Exception as e:
                print(f"Error getting enhanced stats: {e}")
                today_detections = 0
                videos_today = 0
                queue_stats = {'queue_length': 0, 'currently_processing': 0, 'failed_videos': 0, 'is_processing': False}
                processing_stats = {'videos_per_hour': 0, 'videos_per_day': 0, 'avg_processing_time': 0, 'session_processed': 0, 'session_failed': 0}
                detailed_stats = {'total_processed': 0, 'videos_with_detections': 0, 'detection_rate': 0, 'total_detections': 0}
            
            return jsonify({
                # Basic metrics (backward compatibility)
                'status': 'running' if processing_service.model_manager.is_loaded else 'stopped',
                'uptime': uptime,
                'cameras_active': 0,  # Processing server doesn't have cameras
                'videos_today': videos_today,
                'detections_today': today_detections,
                'storage_used': storage_used,
                'storage_total': storage_total,
                
                # Enhanced queue metrics
                'queue': {
                    'pending': queue_stats['queue_length'],
                    'processing': queue_stats['currently_processing'],
                    'failed': queue_stats['failed_videos'],
                    'is_processing': queue_stats['is_processing']
                },
                
                # Performance metrics
                'performance': {
                    'processing_rate_hour': processing_stats['videos_per_hour'],
                    'processing_rate_day': processing_stats['videos_per_day'],
                    'avg_processing_time': processing_stats['avg_processing_time'],
                    'detection_rate': detailed_stats['detection_rate'],
                    'session_processed': processing_stats.get('session_processed', 0),
                    'session_failed': processing_stats.get('session_failed', 0)
                },
                
                # System resources
                'system': {
                    'cpu_percent': metrics.get('cpu_percent', 0),
                    'memory_percent': metrics.get('memory_percent', 0),
                    'model_loaded': processing_service.model_manager.is_loaded
                },
                
                # Historical stats
                'totals': {
                    'videos_processed': detailed_stats['total_processed'],
                    'total_detections': detailed_stats['total_detections'],
                    'videos_with_detections': detailed_stats['videos_with_detections']
                }
            })
        except Exception as e:
            print(f"Error in /api/status: {e}")
            # Return a valid response even on error
            return jsonify({
                'status': 'error',
                'uptime': 0,
                'cameras_active': 0,
                'videos_today': 0,
                'detections_today': 0,
                'storage_used': 0,
                'storage_total': 1,
                'queue': {'pending': 0, 'processing': 0, 'failed': 0, 'is_processing': False},
                'performance': {'processing_rate_hour': 0, 'processing_rate_day': 0, 'avg_processing_time': 0, 'detection_rate': 0},
                'system': {'cpu_percent': 0, 'memory_percent': 0, 'model_loaded': False},
                'totals': {'videos_processed': 0, 'total_detections': 0, 'videos_with_detections': 0}
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
    @require_auth
    def api_recent_detections():
        try:
            species = request.args.get('species')
            start = request.args.get('start')
            end = request.args.get('end')
            sort = request.args.get('sort', 'desc')
            limit = request.args.get('limit', default=20, type=int)

            print(f"API request: species={species}, start={start}, end={end}, limit={limit}, sort={sort}")
            
            # Validate parameters
            if limit > 1000:
                return jsonify({'error': 'Limit cannot exceed 1000'}), 400
            
            # Query database with detailed error handling
            try:
                raw_items = detection_repo.get_recent_filtered_with_thumbnails(
                    species=species, start=start, end=end, limit=100)
                print(f"Found {len(raw_items)} raw detection items")
            except Exception as db_error:
                print(f"ERROR: Database query failed: {db_error}")
                print(f"   Database path: {config.database.path}")
                print(f"   Storage path: {config.processing.storage_path}")
                return jsonify({
                    'error': 'Database query failed',
                    'details': str(db_error),
                    'database_path': str(config.database.path)
                }), 500
            
            # Process and cluster detections
            try:
                events = _cluster_detections(raw_items, limit=None)
                events.sort(key=lambda e: e['abs_time'], reverse=(sort != 'asc'))
                events = events[:limit]
                for e in events:
                    e.pop('bbox', None)
                    e.pop('abs_time', None)
                
                print(f"Returning {len(events)} clustered detection events")
                return jsonify({'detections': events})
                
            except Exception as cluster_error:
                print(f"ERROR: Detection clustering failed: {cluster_error}")
                return jsonify({
                    'error': 'Detection processing failed',
                    'details': str(cluster_error)
                }), 500
                
        except Exception as e:
            print(f"ERROR: Unexpected error in /api/recent-detections: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'error': 'Internal server error',
                'details': str(e)
            }), 500
    
    @app.route('/api/process-now', methods=['POST'])
    @require_auth
    def api_process_now():
        try:
            threading.Thread(target=processing_service.process_pending_videos, daemon=True).start()
            return jsonify({'message': 'Processing queue started'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/cleanup-now', methods=['POST'])
    @require_admin
    def api_cleanup_now():
        """Manually trigger video cleanup"""
        try:
            threading.Thread(target=processing_service.cleanup_old_videos, daemon=True).start()
            return jsonify({'message': 'Cleanup started'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/reset-queue', methods=['POST'])
    @require_admin
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
        """Simple debug endpoint for basic connectivity testing"""
        return jsonify({
            'status': 'working',
            'timestamp': time.time(),
            'message': 'Debug endpoint is functional'
        })
    
    @app.route('/api/debug/test')
    def api_debug_test():
        """Test endpoint to verify service is working"""
        return jsonify({'test': 'passed', 'service': 'AI Processing Server'})

    @app.route('/api/delete-detection', methods=['POST'])
    @require_auth
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
    @require_auth_internal
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
    @require_admin_internal
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
            
            # Merge provided settings with current settings
            current_settings.update(data)
            
            # Save to file
            with open(settings_file, 'w') as f:
                json.dump(current_settings, f, indent=2)
            
            print(f"Saved motion settings for camera {camera_id}: {data}")
            
            return jsonify({
                'message': f'Motion settings saved for camera {camera_id}',
                'saved_settings': current_settings,
                'file_path': str(settings_file)
            })
            
        except Exception as e:
            print(f"ERROR: Error saving motion settings: {e}")
            return jsonify({
                'error': f'Failed to save motion settings: {str(e)}'
            }), 500
    
    @app.route('/videos/<filename>')
    def serve_video(filename):
        """Serve video files from detections or no_detections directories"""
        # Check detections directory first (most likely to be accessed)
        detections_path = config.processing.storage_path / "processed" / "detections" / filename
        if detections_path.exists():
            print(f"Serving detection video: {filename}")
            return send_from_directory(config.processing.storage_path / "processed" / "detections", filename)
        
        # Then check no_detections directory
        no_detections_path = config.processing.storage_path / "processed" / "no_detections" / filename
        if no_detections_path.exists():
            print(f"Serving no-detection video: {filename}")
            return send_from_directory(config.processing.storage_path / "processed" / "no_detections", filename)
        
        # Finally check incoming directory (for videos not yet processed)
        incoming_path = config.processing.storage_path / "incoming" / filename
        if incoming_path.exists():
            print(f"Serving incoming video: {filename}")
            return send_from_directory(config.processing.storage_path / "incoming", filename)
        
        print(f"ERROR: Video not found: {filename}")
        print(f"   Checked: {detections_path}")
        print(f"   Checked: {no_detections_path}")
        print(f"   Checked: {incoming_path}")
        return "Video not found", 404
    
    @app.route('/thumbnails/<filename>')
    def serve_thumbnail(filename):
        return send_from_directory(config.processing.storage_path / "thumbnails", filename)
    
    @app.route('/api/system-metrics')
    @require_auth_internal
    def api_system_metrics():
        """Get current system metrics (CPU, memory, disk)"""
        try:
            metrics = metrics_collector.get_metrics_dict()
            return jsonify(metrics)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/system-settings', methods=['GET'])
    @require_auth_internal
    def api_get_system_settings():
        """Get current system settings"""
        import json
        from pathlib import Path
        
        try:
            settings_file = Path(config.processing.storage_path) / "system_settings.json"
            
            # Default settings based on current config
            default_settings = {
                'storage': {
                    'storage_path': str(config.processing.storage_path)
                },
                'detection': {
                    'classes': config.processing.detection.classes,
                    'confidences': config.processing.detection.confidences,
                    'model_name': config.processing.detection.model_name,
                    'process_every_nth_frame': config.processing.detection.process_every_nth_frame,
                    'max_thumbnails_per_video': config.processing.detection.max_thumbnails_per_video
                },
                'retention': {
                    'detection_retention_days': config.processing.detection_retention_days,
                    'no_detection_retention_days': config.processing.no_detection_retention_days
                },
                'sync': {
                    'sync_interval_minutes': 15,  # From env default
                    'upload_timeout_seconds': 300  # From env default
                }
            }
            
            # Load saved settings if they exist
            if settings_file.exists():
                try:
                    with open(settings_file, 'r') as f:
                        saved_settings = json.load(f)
                        # Deep merge saved settings over defaults
                        for category, values in saved_settings.items():
                            if category in default_settings and isinstance(values, dict):
                                default_settings[category].update(values)
                            else:
                                default_settings[category] = values
                except Exception as e:
                    print(f"Error loading system settings: {e}")
            
            return jsonify(default_settings)
            
        except Exception as e:
            print(f"Error in system settings GET: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/system-settings', methods=['POST'])
    @require_admin_internal
    def api_set_system_settings():
        """Update system settings"""
        import json
        from pathlib import Path
        
        try:
            data = request.get_json()
            settings_file = Path(config.processing.storage_path) / "system_settings.json"
            
            # Load existing settings
            existing_settings = {}
            if settings_file.exists():
                try:
                    with open(settings_file, 'r') as f:
                        existing_settings = json.load(f)
                except Exception:
                    pass
            
            # Merge provided settings with current settings
            for category, values in data.items():
                if isinstance(values, dict):
                    if category not in existing_settings:
                        existing_settings[category] = {}
                    existing_settings[category].update(values)
                else:
                    existing_settings[category] = values
            
            # Save settings
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_file, 'w') as f:
                json.dump(existing_settings, f, indent=2)
            
            # Handle storage path change
            if 'storage' in data and 'storage_path' in data['storage']:
                new_path = Path(data['storage']['storage_path'])
                if new_path != config.processing.storage_path:
                    # Create new directories
                    (new_path / "incoming").mkdir(parents=True, exist_ok=True)
                    (new_path / "processed" / "detections").mkdir(parents=True, exist_ok=True)
                    (new_path / "processed" / "no_detections").mkdir(parents=True, exist_ok=True)
                    (new_path / "thumbnails").mkdir(parents=True, exist_ok=True)
                    
                    # Note: Actual path change would require service restart
                    return jsonify({
                        'success': True,
                        'warning': 'Storage path changed. Please restart the service for changes to take effect. Existing files remain in the old location.'
                    })
            
            return jsonify({'success': True})
            
        except Exception as e:
            print(f"Error in system settings POST: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/models/available', methods=['GET'])
    @require_auth
    def api_get_available_models():
        """Get list of available AI models with metadata"""
        from services.model_registry import ModelRegistry
        
        try:
            models = ModelRegistry.get_available_models()
            model_list = [ModelRegistry.to_dict(model) for model in models]
            
            # Get current model from config
            current_model = config.processing.detection.model_name
            
            return jsonify({
                'models': model_list,
                'current': current_model,
                'default': ModelRegistry.get_default_model()
            })
            
        except Exception as e:
            print(f"Error fetching available models: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/models/<model_id>/classes', methods=['GET'])
    @require_auth
    def api_get_model_classes(model_id):
        """Get available classes for a specific model"""
        from services.class_registry import ClassRegistry
        
        try:
            classes = ClassRegistry.get_classes_for_model(model_id)
            class_list = [ClassRegistry.to_dict(cls) for cls in classes]
            categories = ClassRegistry.get_categories(model_id)
            
            # Get current selected classes from config
            current_classes = config.processing.detection.classes
            
            return jsonify({
                'classes': class_list,
                'categories': categories,
                'current': current_classes,
                'presets': {
                    'wildlife': ClassRegistry.get_wildlife_preset(),
                    'people': ClassRegistry.get_people_preset(),
                    'all_animals': ClassRegistry.get_all_animal_classes()
                }
            })
            
        except Exception as e:
            print(f"Error fetching model classes: {e}")
            return jsonify({'error': str(e)}), 500