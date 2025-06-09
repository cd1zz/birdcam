
# web/routes/capture_routes.py
"""
Routes for Pi Capture System
"""
import threading
import cv2
import time
from flask import request, jsonify, Response, render_template, send_from_directory
from core.models import MotionRegion

def create_capture_routes(app, capture_service, sync_service):
    
    @app.route('/')
    def dashboard():
        return render_template('capture_dashboard.html')
    
    @app.route('/api/status')
    def api_status():
        status = capture_service.get_status()
        server_status = sync_service.get_server_status()
        
        return jsonify({
            'pi': {
                'is_capturing': status.is_capturing,
                'queue_size': status.queue_size,
                'last_motion': status.last_motion_time.isoformat() if status.last_motion_time else None
            },
            'server_connected': server_status.get('connected', False),
            'server': server_status if server_status.get('connected') else None
        })
    
    @app.route('/api/sync-now', methods=['POST'])
    def api_sync_now():
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
    
    @app.route('/api/motion-settings', methods=['GET'])
    def api_get_motion_settings():
        region = capture_service.motion_detector.motion_region
        
        # Also try to get settings from server if available
        server_settings = sync_service.get_server_motion_settings()
        
        local_settings = {
            'region': {
                'x1': region.x1, 'y1': region.y1, 
                'x2': region.x2, 'y2': region.y2
            } if region else None,
            'motion_threshold': capture_service.motion_detector.config.threshold,
            'min_contour_area': capture_service.motion_detector.config.min_contour_area,
            'source': 'local'
        }
        
        # Prefer server settings if available and more recent
        if server_settings:
            local_settings.update(server_settings)
            local_settings['source'] = 'server'
        
        return jsonify(local_settings)
    
    @app.route('/api/motion-settings', methods=['POST'])
    def api_set_motion_settings():
        data = request.get_json()
        region_data = data.get('region')
        
        success = True
        messages = []
        
        # Update local settings
        if region_data:
            try:
                region = MotionRegion(
                    region_data['x1'], region_data['y1'],
                    region_data['x2'], region_data['y2']
                )
                capture_service.motion_detector.set_motion_region(region)
                
                # Update config
                capture_service.motion_detector.config.threshold = data.get('motion_threshold', 5000)
                capture_service.motion_detector.config.min_contour_area = data.get('min_contour_area', 500)
                
                messages.append('Local settings updated')
            except Exception as e:
                success = False
                messages.append(f'Failed to update local settings: {str(e)}')
        
        # Try to update server settings too
        try:
            if sync_service.update_server_motion_settings(data):
                messages.append('Server settings updated')
            else:
                messages.append('Server settings update failed (server may be offline)')
        except Exception as e:
            messages.append(f'Server update error: {str(e)}')
        
        if success:
            return jsonify({
                'message': '; '.join(messages),
                'local_updated': True,
                'server_attempted': True
            })
        else:
            return jsonify({'error': '; '.join(messages)}), 400
    
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
        def generate():
            while True:
                ret, frame = capture_service.camera_manager.read_frame()
                if ret:
                    # Resize for web viewing
                    frame = cv2.resize(frame, (640, 480))
                    
                    # Add motion detection overlay
                    try:
                        has_motion = capture_service.motion_detector.detect_motion(frame.copy())
                        color = (0, 255, 0) if has_motion else (0, 0, 255)
                        cv2.putText(frame, f"Motion: {has_motion}", (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                        cv2.putText(frame, f"Recording: {capture_service.is_capturing}", (10, 70),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                        
                        # Draw motion detection region
                        if capture_service.motion_detector.motion_region:
                            region = capture_service.motion_detector.motion_region
                            cv2.rectangle(frame, (region.x1, region.y1), (region.x2, region.y2), (255, 255, 0), 2)
                            cv2.putText(frame, "Detection Zone", (region.x1, region.y1-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    except Exception as e:
                        print(f"Error in live feed overlay: {e}")
                    
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