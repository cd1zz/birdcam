# web/routes/capture_routes.py - UPDATED FOR UNIFIED DASHBOARD
"""
Routes for Pi Capture System with Unified Dashboard
"""
import threading
import cv2
import numpy as np
import time
import requests
from flask import request, jsonify, Response, render_template, send_from_directory, stream_with_context
from core.models import MotionRegion

def create_capture_routes(app, capture_services, sync_service, settings_repos):

    default_service = next(iter(capture_services.values()))
    default_repo = settings_repos.get(default_service.capture_config.camera_id)

    def get_service() -> 'CaptureService':
        cam_id = request.args.get('camera_id', default_service.capture_config.camera_id)
        try:
            cam_id = int(cam_id)
        except ValueError:
            cam_id = default_service.capture_config.camera_id
        return capture_services.get(cam_id, default_service)

    def get_repo(cam_id: int):
        return settings_repos.get(cam_id, default_repo)
    
    @app.route('/')
    def dashboard():
        """Unified dashboard with server addresses injected"""
        processing_server_url = f"http://{sync_service.server_host}:{sync_service.server_port}"

        # Derive capture host/port from the current request
        host_parts = request.host.split(":")
        capture_host = host_parts[0]
        capture_port = host_parts[1] if len(host_parts) > 1 else ("443" if request.scheme == "https" else "80")

        return render_template(
            'unified_dashboard.html',
            processing_server_url=processing_server_url,
            processing_host=sync_service.server_host,
            processing_port=sync_service.server_port,
            capture_host=capture_host,
            capture_port=capture_port
        )
    
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
            
            settings = {
                'region': {
                    'x1': region.x1, 'y1': region.y1, 
                    'x2': region.x2, 'y2': region.y2
                } if region else None,
                'motion_threshold': capture_service.motion_detector.config.threshold,
                'min_contour_area': capture_service.motion_detector.config.min_contour_area,
                'motion_timeout_seconds': capture_service.motion_config.motion_timeout_seconds,
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
            
            if not region_data or not all(k in region_data for k in ['x1', 'y1', 'x2', 'y2']):
                return jsonify({'error': 'Invalid region data'}), 400
            
            capture_service = get_service()

            region = MotionRegion(
                region_data['x1'], region_data['y1'],
                region_data['x2'], region_data['y2']
            )
            
            # Update motion detector
            capture_service.motion_detector.set_motion_region(region)
            capture_service.motion_detector.config.threshold = motion_threshold
            capture_service.motion_detector.config.min_contour_area = min_contour_area
            capture_service.motion_detector.config.motion_timeout_seconds = motion_timeout_seconds
            
            # IMPORTANT: Update the capture service timeout too
            capture_service.motion_config.motion_timeout_seconds = motion_timeout_seconds
            
            # Save to database for persistence
            repo = get_repo(capture_service.capture_config.camera_id)
            if repo:
                repo.save_motion_settings(region, motion_threshold, min_contour_area, motion_timeout_seconds)
            
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
    
    @app.route('/live_feed')
    def live_feed():
        """Live video feed for troubleshooting"""
        # Get the service WITHIN the request context, before starting the generator
        capture_service = get_service()
        
        def generate():
            while True:
                # Use the capture_service from the closure - don't call get_service() here
                ret, frame = capture_service.camera_manager.read_frame()
                if ret:
                    frame = cv2.resize(frame, (640, 480))
                    
                    try:
                        has_motion = capture_service.motion_detector.detect_motion(frame.copy())
                        capture_service.latest_motion = has_motion
                        
                        if capture_service.motion_detector.motion_region:
                            region = capture_service.motion_detector.motion_region
                            cv2.rectangle(frame, (region.x1, region.y1), (region.x2, region.y2), (255, 255, 0), 2)
                    except Exception as e:
                        print(f"Error in live feed overlay: {e}")
                    
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                else:
                    blank = 255 * np.ones((480, 640, 3), dtype=np.uint8)
                    cv2.putText(blank, "Camera Not Available", (150, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                    _, buffer = cv2.imencode('.jpg', blank)
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                
                time.sleep(0.1)
        
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @app.route('/videos/<filename>')
    def serve_video(filename):
        """Proxy video requests to the processing server."""
        try:
            url = f"{sync_service.base_url}/videos/{filename}"
            resp = requests.get(url, stream=True)  # No timeout to avoid truncated streams

            if resp.status_code == 200:
                return Response(
                    stream_with_context(resp.iter_content(chunk_size=8192)),
                    content_type=resp.headers.get("Content-Type", "video/mp4"),
                )
            return resp.content, resp.status_code

        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route('/thumbnails/<filename>')
    def serve_thumbnail(filename):
        """Proxy thumbnail requests to the processing server."""
        try:
            url = f"{sync_service.base_url}/thumbnails/{filename}"
            resp = requests.get(url, stream=True)  # No timeout to avoid truncated streams

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