# web/routes/capture_routes.py - UPDATED FOR UNIFIED DASHBOARD
"""
Routes for Pi Capture System with Unified Dashboard
"""
import threading
import cv2
import numpy as np
import time
import requests
from flask import request, jsonify, Response, send_from_directory, stream_with_context
from core.models import MotionRegion
from services.system_metrics import SystemMetricsCollector

def create_capture_routes(app, capture_services, sync_service, settings_repos):

    default_service = next(iter(capture_services.values()))
    default_repo = settings_repos.get(default_service.capture_config.camera_id)
    
    # Initialize system metrics collector
    metrics_collector = SystemMetricsCollector(str(default_service.video_writer.output_dir))

    def get_service() -> 'CaptureService':
        cam_id = request.args.get('camera_id', default_service.capture_config.camera_id)
        try:
            cam_id = int(cam_id)
        except ValueError:
            cam_id = default_service.capture_config.camera_id
        return capture_services.get(cam_id, default_service)

    def get_repo(cam_id: int):
        return settings_repos.get(cam_id, default_repo)
    
    # Simple status page
    @app.route('/')
    def index():
        return '''
        <html>
        <head><title>BirdCam Pi Capture System</title></head>
        <body>
        <h1>🐦 BirdCam Pi Capture System</h1>
        <p>This is the Pi capture system. The web UI is served from the processing server.</p>
        <h2>Available APIs:</h2>
        <ul>
        <li><a href="/api/status">System Status</a></li>
        <li><a href="/api/cameras">Camera List</a></li>
        <li><a href="/api/camera/0/stream">Camera Stream</a></li>
        </ul>
        <p><strong>Main UI:</strong> Access the full web interface at your processing server (port 8091)</p>
        </body>
        </html>
        '''
    
    @app.route('/api/status')
    def api_status():
        capture_service = get_service()
        status = capture_service.get_status()
        server_status = sync_service.get_server_status()
        
        return jsonify({
            'pi': {
                'is_capturing': status.is_capturing,
                'has_motion': getattr(capture_service, 'latest_motion', False),
                'queue_size': status.queue_size,
                'last_motion': status.last_motion_time.isoformat() if status.last_motion_time else None,
                'total_videos': 0,  # TODO: Add to capture service
                'total_size_mb': 0,  # TODO: Add to capture service
                'pending_sync': status.queue_size
            },
            'server_connected': server_status.get('connected', False),
            'server': server_status if server_status.get('connected') else None
        })
    
    @app.route('/api/server-status')
    def api_server_status():
        """Proxy to get server status"""
        server_status = sync_service.get_server_status()
        return jsonify({
            'server_connected': server_status.get('connected', False),
            'server': server_status if server_status.get('connected') else None
        })
    
    @app.route('/api/sync-now', methods=['POST'])
    def api_sync_now():
        capture_service = get_service()
        try:
            threading.Thread(target=capture_service.sync_files, daemon=True).start()
            return jsonify({'message': 'Sync started successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/server-detections')
    def api_server_detections():
        """Get recent detections from processing server"""
        try:
            detections = sync_service.get_server_detections()
            return jsonify({'detections': detections or []})
        except Exception as e:
            print(f"Error getting server detections: {e}")
            return jsonify({'detections': [], 'error': str(e)})
    
    @app.route('/api/server-metrics')
    def api_server_metrics():
        """Proxy to get server system metrics"""
        try:
            url = f"{sync_service.base_url}/api/system-metrics"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return jsonify(resp.json())
            else:
                return jsonify({'error': f'Server returned status {resp.status_code}'}), resp.status_code
        except requests.exceptions.Timeout:
            return jsonify({'error': 'Server request timed out'}), 504
        except requests.exceptions.ConnectionError:
            return jsonify({'error': 'Could not connect to processing server'}), 503
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/delete-detection', methods=['POST'])
    def api_delete_detection():
        data = request.get_json()
        detection_id = data.get('detection_id') if data else None
        if detection_id is None:
            return jsonify({'error': 'detection_id required'}), 400
        try:
            if sync_service.delete_server_detection(int(detection_id)):
                return jsonify({'message': 'Detection deleted'})
            return jsonify({'error': 'Failed to delete detection'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/motion-settings', methods=['GET'])
    def api_get_motion_settings():
        """Get motion detection settings"""
        try:
            capture_service = get_service()
            region = capture_service.motion_detector.motion_region
            config = capture_service.motion_detector.config
            
            settings = {
                'region': {
                    'x1': region.x1, 'y1': region.y1, 
                    'x2': region.x2, 'y2': region.y2
                } if region else None,
                'motion_threshold': config.threshold,
                'min_contour_area': config.min_contour_area,
                'motion_timeout_seconds': capture_service.motion_config.motion_timeout_seconds,
                'motion_box_enabled': config.motion_box_enabled,
                'motion_box_x1': config.motion_box_x1,
                'motion_box_y1': config.motion_box_y1,
                'motion_box_x2': config.motion_box_x2,
                'motion_box_y2': config.motion_box_y2,
                'source': 'current'
            }
            
            return jsonify(settings)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/motion-debug')
    def api_motion_debug():
        """Get real-time motion detection debug info"""
        try:
            # Get the latest frame
            capture_service = get_service()
            ret, frame = capture_service.camera_manager.read_frame()
            if not ret:
                return jsonify({'error': 'Camera not available'})
            
            # Get debug info from motion detector
            debug_info = capture_service.motion_detector.get_debug_info(frame)
            return jsonify(debug_info)
            
        except Exception as e:
            return jsonify({'error': f'Debug failed: {str(e)}'})

    @app.route('/api/motion-settings', methods=['POST'])
    def api_set_motion_settings():
        """Save motion detection settings persistently"""
        try:
            data = request.get_json()
            region_data = data.get('region')
            motion_threshold = data.get('motion_threshold', 5000)
            min_contour_area = data.get('min_contour_area', 500)
            motion_timeout_seconds = data.get('motion_timeout_seconds', 30)
            motion_box_enabled = data.get('motion_box_enabled', True)
            motion_box_x1 = data.get('motion_box_x1', 0)
            motion_box_y1 = data.get('motion_box_y1', 0)
            motion_box_x2 = data.get('motion_box_x2', 640)
            motion_box_y2 = data.get('motion_box_y2', 480)
            
            # Validate motion box coordinates if enabled
            if motion_box_enabled:
                if not all(isinstance(coord, (int, float)) for coord in [motion_box_x1, motion_box_y1, motion_box_x2, motion_box_y2]):
                    return jsonify({'error': 'Motion box coordinates must be numeric'}), 400
                if motion_box_x1 >= motion_box_x2 or motion_box_y1 >= motion_box_y2:
                    return jsonify({'error': 'Invalid motion box dimensions'}), 400
                if motion_box_x1 < 0 or motion_box_y1 < 0 or motion_box_x2 < 0 or motion_box_y2 < 0:
                    return jsonify({'error': 'Motion box coordinates must be non-negative'}), 400
            
            if region_data and not all(k in region_data for k in ['x1', 'y1', 'x2', 'y2']):
                return jsonify({'error': 'Invalid region data'}), 400
            
            # Validate coordinate values
            try:
                x1, y1, x2, y2 = region_data['x1'], region_data['y1'], region_data['x2'], region_data['y2']
                if not all(isinstance(coord, (int, float)) for coord in [x1, y1, x2, y2]):
                    return jsonify({'error': 'Coordinates must be numeric'}), 400
                if x1 >= x2 or y1 >= y2:
                    return jsonify({'error': 'Invalid region dimensions'}), 400
                if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
                    return jsonify({'error': 'Coordinates must be non-negative'}), 400
            except (KeyError, TypeError):
                return jsonify({'error': 'Invalid coordinate format'}), 400
            
            # Validate other parameters
            if not isinstance(motion_threshold, (int, float)) or motion_threshold <= 0:
                return jsonify({'error': 'Motion threshold must be positive'}), 400
            if not isinstance(min_contour_area, (int, float)) or min_contour_area <= 0:
                return jsonify({'error': 'Min contour area must be positive'}), 400
            if not isinstance(motion_timeout_seconds, (int, float)) or motion_timeout_seconds <= 0:
                return jsonify({'error': 'Motion timeout must be positive'}), 400
            
            capture_service = get_service()

            # Update motion detector configuration
            capture_service.motion_detector.config.threshold = motion_threshold
            capture_service.motion_detector.config.min_contour_area = min_contour_area
            capture_service.motion_detector.config.motion_timeout_seconds = motion_timeout_seconds
            capture_service.motion_detector.config.motion_box_enabled = motion_box_enabled
            capture_service.motion_detector.config.motion_box_x1 = motion_box_x1
            capture_service.motion_detector.config.motion_box_y1 = motion_box_y1
            capture_service.motion_detector.config.motion_box_x2 = motion_box_x2
            capture_service.motion_detector.config.motion_box_y2 = motion_box_y2

            # Update motion region based on motion box settings
            if motion_box_enabled:
                region = MotionRegion(motion_box_x1, motion_box_y1, motion_box_x2, motion_box_y2)
                capture_service.motion_detector.set_motion_region(region)
            elif region_data:
                region = MotionRegion(
                    region_data['x1'], region_data['y1'],
                    region_data['x2'], region_data['y2']
                )
                capture_service.motion_detector.set_motion_region(region)
            
            # IMPORTANT: Update the capture service timeout too
            capture_service.motion_config.motion_timeout_seconds = motion_timeout_seconds
            
            # Save to database for persistence
            repo = get_repo(capture_service.capture_config.camera_id)
            if repo:
                # Use motion box coordinates if enabled, otherwise use region data
                if motion_box_enabled:
                    region_for_db = MotionRegion(motion_box_x1, motion_box_y1, motion_box_x2, motion_box_y2)
                else:
                    region_for_db = region if region_data else MotionRegion(motion_box_x1, motion_box_y1, motion_box_x2, motion_box_y2)
                
                repo.save_motion_settings(region_for_db, motion_threshold, min_contour_area, motion_timeout_seconds, 
                                        motion_box_enabled, motion_box_x1, motion_box_y1, motion_box_x2, motion_box_y2)
            
            # Try to update server settings too
            server_updated = False
            try:
                if sync_service.update_server_motion_settings(data):
                    server_updated = True
            except Exception as e:
                print(f"Failed to update server settings: {e}")
            
            message = f'Settings saved: sensitivity={motion_threshold}, size={min_contour_area}, timeout={motion_timeout_seconds}s'
            if server_updated:
                message += ' (synced to server)'
            else:
                message += ' (local only - server offline)'
            
            return jsonify({
                'message': message,
                'local_updated': True,
                'server_updated': server_updated
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to save settings: {str(e)}'}), 500
    
    @app.route('/api/process-server-queue', methods=['POST'])
    def api_process_server_queue():
        """Trigger processing on the server"""
        try:
            if sync_service.trigger_processing():
                return jsonify({'message': 'Processing triggered on server'})
            else:
                return jsonify({'error': 'Failed to trigger processing (server may be offline)'}), 500
        except Exception as e:
            return jsonify({'error': f'Failed to contact server: {str(e)}'}), 500
    
    # Live feed UI route removed - API only
    
    @app.route('/api/health')
    def api_health():
        """Simple health check endpoint"""
        return jsonify({
            'status': 'ok',
            'timestamp': time.time(),
            'cameras_count': len(capture_services),
            'service_info': 'Pi Capture System'
        })
    
    @app.route('/videos/<filename>')
    def serve_video(filename):
        """Proxy video requests to the processing server."""
        try:
            url = f"{sync_service.base_url}/videos/{filename}"
            resp = requests.get(url, stream=True, timeout=30)  # 30 second timeout for videos

            if resp.status_code == 200:
                return Response(
                    stream_with_context(resp.iter_content(chunk_size=8192)),
                    content_type=resp.headers.get("Content-Type", "video/mp4"),
                    headers={
                        'Accept-Ranges': 'bytes',
                        'Content-Length': resp.headers.get('Content-Length', '0')
                    }
                )
            return resp.content, resp.status_code

        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route('/thumbnails/<filename>')
    def serve_thumbnail(filename):
        """Proxy thumbnail requests to the processing server."""
        try:
            url = f"{sync_service.base_url}/thumbnails/{filename}"
            resp = requests.get(url, stream=True, timeout=10)  # 10 second timeout for thumbnails

            if resp.status_code == 200:
                return Response(
                    stream_with_context(resp.iter_content(chunk_size=8192)),
                    content_type=resp.headers.get("Content-Type", "image/jpeg"),
                )
            return resp.content, resp.status_code

        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route('/api/cameras')
    def api_list_cameras():
        """List available cameras"""
        camera_list = []
        for cam_id, service in capture_services.items():
            camera_list.append({
                'id': cam_id,
                'name': f'Camera {cam_id}',
                'is_active': service.camera_manager.is_opened(),
                'sensor_type': 'IMX500' if cam_id == 1 else 'OV5647'  
            })
        return jsonify({'cameras': camera_list})
    
    @app.route('/api/motion-broadcaster/stats')
    def api_motion_broadcaster_stats():
        """Get motion broadcaster statistics"""
        service = get_service()
        stats = service.get_motion_broadcaster_stats()
        return jsonify(stats)
    
    @app.route('/api/motion-broadcaster/config', methods=['GET', 'POST'])
    def api_motion_broadcaster_config():
        """Get or update motion broadcaster configuration"""
        service = get_service()
        broadcaster = service.motion_broadcaster
        
        if request.method == 'GET':
            return jsonify({
                'cross_trigger_enabled': broadcaster.cross_trigger_enabled,
                'trigger_timeout': broadcaster.trigger_timeout
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            
            if 'cross_trigger_enabled' in data:
                broadcaster.set_cross_trigger_enabled(data['cross_trigger_enabled'])
            
            if 'trigger_timeout' in data:
                timeout = float(data['trigger_timeout'])
                if timeout > 0:
                    broadcaster.set_trigger_timeout(timeout)
                else:
                    return jsonify({'error': 'Trigger timeout must be positive'}), 400
            
            return jsonify({'success': True})
    
    @app.route('/api/motion-broadcaster/active-cameras')
    def api_motion_broadcaster_active_cameras():
        """Get list of cameras with recent motion"""
        service = get_service()
        active_cameras = service.motion_broadcaster.get_active_cameras()
        return jsonify({'active_cameras': list(active_cameras)})
    
    @app.route('/api/motion-broadcaster/test-trigger/<int:camera_id>')
    def api_test_motion_trigger(camera_id):
        """Test motion trigger for a specific camera"""
        service = get_service()
        try:
            service.motion_broadcaster.report_motion(camera_id, confidence=0.9)
            return jsonify({'success': True, 'message': f'Test motion triggered for camera {camera_id}'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/system-metrics')
    def api_system_metrics():
        """Get current system metrics (CPU, memory, disk)"""
        try:
            metrics = metrics_collector.get_metrics_dict()
            return jsonify(metrics)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/camera/<int:camera_id>/stream')
    def api_camera_stream(camera_id):
        """Live MJPEG stream for a specific camera"""
        try:
            capture_service = capture_services.get(camera_id)
            if not capture_service:
                return jsonify({'error': f'Camera {camera_id} not found'}), 404
            
            # Check if motion box overlay is requested
            show_motion_box = request.args.get('show_motion_box', 'false').lower() == 'true'
            
            def generate_frames():
                while True:
                    try:
                        ret, frame = capture_service.camera_manager.read_frame()
                        if not ret:
                            break
                        
                        # Draw motion box overlay if requested
                        if show_motion_box:
                            config = capture_service.motion_detector.config
                            if config.motion_box_enabled:
                                # Draw motion box rectangle
                                cv2.rectangle(frame, 
                                            (config.motion_box_x1, config.motion_box_y1),
                                            (config.motion_box_x2, config.motion_box_y2),
                                            (0, 255, 0), 2)  # Green rectangle
                                
                                # Add text label
                                cv2.putText(frame, "Motion Detection Area", 
                                          (config.motion_box_x1, config.motion_box_y1 - 10),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                            else:
                                # Show "Motion Detection Disabled" message
                                cv2.putText(frame, "Motion Detection Disabled", 
                                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        
                        # Encode frame as JPEG
                        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if not ret:
                            continue
                        
                        # Yield frame in MJPEG format
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                        
                        time.sleep(0.1)  # ~10 FPS
                    except Exception as e:
                        print(f"Stream error: {e}")
                        break
            
            return Response(generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/camera/<int:camera_id>/snapshot')
    def api_camera_snapshot(camera_id):
        """Get single frame snapshot from camera"""
        try:
            capture_service = capture_services.get(camera_id)
            if not capture_service:
                return jsonify({'error': f'Camera {camera_id} not found'}), 404
            
            # Check if motion box overlay is requested
            show_motion_box = request.args.get('show_motion_box', 'false').lower() == 'true'
            
            ret, frame = capture_service.camera_manager.read_frame()
            if not ret:
                return jsonify({'error': 'Failed to capture frame'}), 500
            
            # Draw motion box overlay if requested
            if show_motion_box:
                config = capture_service.motion_detector.config
                if config.motion_box_enabled:
                    # Draw motion box rectangle
                    cv2.rectangle(frame, 
                                (config.motion_box_x1, config.motion_box_y1),
                                (config.motion_box_x2, config.motion_box_y2),
                                (0, 255, 0), 2)  # Green rectangle
                    
                    # Add text label
                    cv2.putText(frame, "Motion Detection Area", 
                              (config.motion_box_x1, config.motion_box_y1 - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                else:
                    # Show "Motion Detection Disabled" message
                    cv2.putText(frame, "Motion Detection Disabled", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not ret:
                return jsonify({'error': 'Failed to encode frame'}), 500
            
            return Response(buffer.tobytes(), mimetype='image/jpeg')
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/statistics/summary')
    def api_statistics_summary():
        """Get comprehensive system statistics"""
        try:
            # Get metrics from all cameras
            camera_stats = []
            for cam_id, service in capture_services.items():
                status = service.get_status()
                camera_stats.append({
                    'camera_id': cam_id,
                    'is_capturing': status.is_capturing,
                    'queue_size': status.queue_size,
                    'last_motion': status.last_motion_time.isoformat() if status.last_motion_time else None,
                    'is_active': service.camera_manager.is_opened()
                })
            
            # Get server status
            server_status = sync_service.get_server_status()
            
            # Get motion broadcaster stats
            broadcaster_stats = default_service.get_motion_broadcaster_stats()
            
            # Get system metrics
            system_metrics = metrics_collector.get_metrics_dict()
            
            return jsonify({
                'cameras': camera_stats,
                'server': server_status,
                'motion_broadcaster': broadcaster_stats,
                'system': system_metrics,
                'timestamp': time.time()
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500