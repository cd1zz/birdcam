# web/routes/capture_routes.py
"""
Routes for Pi Capture System - provides API endpoints for camera streaming,
motion detection status, and system configuration.
"""
import os
import threading
import cv2
import time
import requests
from flask import request, jsonify, Response, stream_with_context
from core.models import MotionRegion
from services.system_metrics import SystemMetricsCollector
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.capture_service import CaptureService

def create_capture_routes(app, capture_services, sync_service, settings_repos):

    default_service = next(iter(capture_services.values()))
    default_repo = settings_repos.get(default_service.capture_config.camera_id)
    
    # Initialize system metrics collector
    metrics_collector = SystemMetricsCollector(str(default_service.video_writer.output_dir))
    
    # Track startup time for uptime calculation
    startup_time = time.time()

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
        """Return status in the format expected by the Analytics page"""
        try:
            capture_service = get_service()
            status = capture_service.get_status()
            
            # Calculate uptime
            uptime = int(time.time() - startup_time)
            
            # Get system metrics
            metrics = metrics_collector.get_metrics_dict()
            
            # Get storage info from metrics
            storage_info = metrics.get('disks', [{}])[0] if metrics.get('disks') else {}
            storage_used = int(storage_info.get('used_gb', 0) * 1024 * 1024 * 1024)  # Convert GB to bytes
            storage_total = int(storage_info.get('total_gb', 100) * 1024 * 1024 * 1024)  # Convert GB to bytes
            
            # Count videos and cameras
            videos_today = capture_service.video_writer.get_videos_count_today() if hasattr(capture_service.video_writer, 'get_videos_count_today') else status.queue_size
            cameras_active = len([s for s in capture_services.values() if s.is_running])
            
            return jsonify({
                'status': 'running' if status.is_capturing else 'stopped',
                'uptime': uptime,
                'cameras_active': cameras_active,
                'videos_today': videos_today,
                'detections_today': 0,  # Pi doesn't do detections
                'storage_used': storage_used,
                'storage_total': storage_total
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
                'storage_total': 1
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
            # Get the specific camera service (not just default)
            camera_id = request.args.get('camera_id')
            if camera_id:
                try:
                    camera_id = int(camera_id)
                    capture_service = capture_services.get(camera_id, get_service())
                except ValueError:
                    capture_service = get_service()
            else:
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
            print(f"[MOTION SETTINGS] Received POST data: {data}")
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
            
            # Validate region data if provided
            if region_data:
                if not all(k in region_data for k in ['x1', 'y1', 'x2', 'y2']):
                    return jsonify({'error': 'Invalid region data - missing coordinates'}), 400
                
                # Validate coordinate values
                try:
                    x1, y1, x2, y2 = region_data['x1'], region_data['y1'], region_data['x2'], region_data['y2']
                    if not all(isinstance(coord, (int, float)) for coord in [x1, y1, x2, y2]):
                        return jsonify({'error': f'Coordinates must be numeric. Got: x1={type(x1)}, y1={type(y1)}, x2={type(x2)}, y2={type(y2)}'}), 400
                    if x1 >= x2 or y1 >= y2:
                        return jsonify({'error': f'Invalid region dimensions: x1={x1}, y1={y1}, x2={x2}, y2={y2}'}), 400
                    if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
                        return jsonify({'error': f'Coordinates must be non-negative: x1={x1}, y1={y1}, x2={x2}, y2={y2}'}), 400
                except (KeyError, TypeError) as e:
                    print(f"ERROR parsing region data: {e}")
                    print(f"region_data = {region_data}")
                    return jsonify({'error': f'Invalid coordinate format: {str(e)}'}), 400
            
            # Validate other parameters
            if not isinstance(motion_threshold, (int, float)) or motion_threshold <= 0:
                return jsonify({'error': 'Motion threshold must be positive'}), 400
            if not isinstance(min_contour_area, (int, float)) or min_contour_area <= 0:
                return jsonify({'error': 'Min contour area must be positive'}), 400
            if not isinstance(motion_timeout_seconds, (int, float)) or motion_timeout_seconds <= 0:
                return jsonify({'error': 'Motion timeout must be positive'}), 400
            
            # Get the specific camera service (not just default)
            camera_id = request.args.get('camera_id')
            if camera_id:
                try:
                    camera_id = int(camera_id)
                    capture_service = capture_services.get(camera_id, get_service())
                except ValueError:
                    capture_service = get_service()
            else:
                capture_service = get_service()

            # Configure motion detector parameters
            capture_service.motion_detector.config.threshold = motion_threshold
            capture_service.motion_detector.config.min_contour_area = min_contour_area
            capture_service.motion_detector.config.motion_timeout_seconds = motion_timeout_seconds
            capture_service.motion_detector.config.motion_box_enabled = motion_box_enabled
            capture_service.motion_detector.config.motion_box_x1 = motion_box_x1
            capture_service.motion_detector.config.motion_box_y1 = motion_box_y1
            capture_service.motion_detector.config.motion_box_x2 = motion_box_x2
            capture_service.motion_detector.config.motion_box_y2 = motion_box_y2

            # Configure motion detection region
            if motion_box_enabled:
                region = MotionRegion(motion_box_x1, motion_box_y1, motion_box_x2, motion_box_y2)
                capture_service.motion_detector.set_motion_region(region)
            elif region_data:
                region = MotionRegion(
                    region_data['x1'], region_data['y1'],
                    region_data['x2'], region_data['y2']
                )
                capture_service.motion_detector.set_motion_region(region)
            
            # Apply timeout to capture service
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
            
            # Attempt to sync settings with processing server
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
    
    # API endpoints only - UI served from processing server
    
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
            # Get camera name from environment or use default
            camera_name = os.getenv(f'CAMERA_NAME_{cam_id}', f'Camera {cam_id}')
            camera_list.append({
                'id': cam_id,
                'name': camera_name,
                'is_active': service.camera_manager.is_opened(),
                'sensor_type': 'IMX500' if cam_id == 1 else 'OV5647'  
            })
        return jsonify({'cameras': camera_list})
    
    @app.route('/api/active-passive/stats')
    def api_active_passive_stats():
        """Get active-passive camera statistics"""
        service = get_service()
        if not service.is_active:
            return jsonify({'error': 'This endpoint only works on the active camera'}), 400
        
        stats = {
            'active_camera_id': service.camera_id,
            'passive_camera_connected': service.passive_camera_service is not None,
            'passive_camera_id': service.passive_camera_service.camera_id if service.passive_camera_service else None,
            'is_recording': service.is_capturing,
            'passive_is_recording': service.passive_camera_service.is_capturing if service.passive_camera_service else False,
            'last_motion_time': service.last_motion_time,
            'latest_motion': service.latest_motion
        }
        return jsonify(stats)
    
    @app.route('/api/active-passive/config', methods=['GET'])
    def api_active_passive_config():
        """Get active-passive camera configuration"""
        service = get_service()
        return jsonify({
            'active_camera_enabled': True,  # Always enabled in active-passive mode
            'camera_count': len(capture_services),
            'active_camera_id': 0,
            'passive_camera_ids': [cid for cid in capture_services.keys() if cid != 0],
            'mode': 'active-passive'
        })
    
    @app.route('/api/active-passive/test-trigger')
    def api_test_active_passive_trigger():
        """Test active-passive trigger (simulate motion on active camera)"""
        service = get_service()
        if not service.is_active:
            return jsonify({'error': 'Test trigger only works on active camera (camera 0)'}), 400
        
        try:
            # Simulate motion detection on active camera
            if not service.is_capturing:
                service._start_recording()
                if service.passive_camera_service and not service.passive_camera_service.is_capturing:
                    service.passive_camera_service._start_recording_from_active()
                return jsonify({'success': True, 'message': 'Test recording started on active and passive cameras'})
            else:
                return jsonify({'success': True, 'message': 'Cameras are already recording'})
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
            
            # Get active-passive stats
            active_passive_stats = {
                'mode': 'active-passive',
                'active_camera_id': 0,
                'passive_camera_ids': [cid for cid in capture_services.keys() if cid != 0],
                'camera_count': len(capture_services)
            }
            
            # Get system metrics
            system_metrics = metrics_collector.get_metrics_dict()
            
            return jsonify({
                'cameras': camera_stats,
                'server': server_status,
                'active_passive': active_passive_stats,
                'system': system_metrics,
                'timestamp': time.time()
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500