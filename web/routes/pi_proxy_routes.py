# web/routes/pi_proxy_routes.py
"""
Secure proxy routes for Pi camera endpoints
These routes add authentication to Pi camera streams
"""
import requests
from flask import Response, jsonify, request, stream_with_context
from web.middleware import require_auth
from web.middleware.auth import require_auth_with_query
from web.middleware.decorators import require_auth_internal
import os

def create_pi_proxy_routes(app, config):
    """Create authenticated proxy routes for Pi camera endpoints"""
    
    # Get Pi server URL from environment
    # The Pi server is what the processing server uses to receive uploads
    pi_host = os.getenv('CAPTURE_SERVER', os.getenv('PI_SERVER', 'localhost'))
    pi_port = os.getenv('CAPTURE_PORT', '8090')
    PI_SERVER = f"http://{pi_host}:{pi_port}"
    
    @app.route('/api/pi/camera/<camera_id>/stream')
    @require_auth_with_query
    def proxy_camera_stream(camera_id):
        """Proxy camera stream from Pi with authentication"""
        try:
            # Forward query parameters (excluding token)
            params = request.args.copy()
            params.pop('token', None)  # Remove token from forwarded params
            
            pi_url = f"{PI_SERVER}/api/camera/{camera_id}/stream"
            if params:
                from urllib.parse import urlencode
                pi_url += f"?{urlencode(params)}"
            
            # Stream the response from Pi
            pi_response = requests.get(pi_url, stream=True, timeout=5)
            
            def generate():
                for chunk in pi_response.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            
            return Response(
                stream_with_context(generate()),
                content_type=pi_response.headers.get('Content-Type', 'multipart/x-mixed-replace; boundary=frame'),
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi camera: {str(e)}'}), 502
        except Exception as e:
            return jsonify({'error': f'Stream error: {str(e)}'}), 500
    
    @app.route('/api/pi/camera/<camera_id>/snapshot')
    @require_auth_with_query
    def proxy_camera_snapshot(camera_id):
        """Proxy camera snapshot from Pi with authentication"""
        try:
            # Forward query parameters (excluding token)
            params = request.args.copy()
            params.pop('token', None)  # Remove token from forwarded params
            
            pi_url = f"{PI_SERVER}/api/camera/{camera_id}/snapshot"
            if params:
                from urllib.parse import urlencode
                pi_url += f"?{urlencode(params)}"
            
            pi_response = requests.get(pi_url, timeout=10)
            
            return Response(
                pi_response.content,
                content_type=pi_response.headers.get('Content-Type', 'image/jpeg'),
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate'
                }
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi camera: {str(e)}'}), 502
        except Exception as e:
            return jsonify({'error': f'Snapshot error: {str(e)}'}), 500
    
    @app.route('/api/pi/status')
    @require_auth
    def proxy_pi_status():
        """Proxy Pi status endpoint with authentication"""
        try:
            pi_response = requests.get(f"{PI_SERVER}/api/status", timeout=5)
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502
    
    @app.route('/api/pi/cameras')
    @require_auth
    def proxy_pi_cameras():
        """Proxy camera list from Pi with authentication"""
        try:
            pi_response = requests.get(f"{PI_SERVER}/api/cameras", timeout=5)
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502
    
    @app.route('/api/pi/motion-settings', methods=['GET', 'POST'])
    @require_auth
    def proxy_pi_motion_settings():
        """Proxy motion settings to/from Pi with authentication"""
        try:
            camera_id = request.args.get('camera_id', '0')
            pi_url = f"{PI_SERVER}/api/motion-settings?camera_id={camera_id}"
            
            if request.method == 'GET':
                pi_response = requests.get(pi_url, timeout=5)
            else:
                # POST - forward the JSON data
                pi_response = requests.post(
                    pi_url,
                    json=request.get_json(),
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
            
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502
    
    @app.route('/api/pi/motion-debug')
    @require_auth
    def proxy_pi_motion_debug():
        """Proxy motion debug info from Pi with authentication"""
        try:
            camera_id = request.args.get('camera_id', '0')
            pi_url = f"{PI_SERVER}/api/motion-debug?camera_id={camera_id}"
            pi_response = requests.get(pi_url, timeout=5)
            
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502
    
    @app.route('/api/pi/sync-now', methods=['POST'])
    @require_auth
    def proxy_pi_sync_now():
        """Proxy sync-now command to Pi with authentication"""
        try:
            pi_response = requests.post(f"{PI_SERVER}/api/sync-now", timeout=10)
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502
    
    @app.route('/api/pi/process-server-queue', methods=['POST'])
    @require_auth
    def proxy_pi_process_queue():
        """Proxy process-server-queue command to Pi with authentication"""
        try:
            pi_response = requests.post(f"{PI_SERVER}/api/process-server-queue", timeout=10)
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502
    
    @app.route('/api/pi/system-metrics')
    @require_auth
    def proxy_pi_system_metrics():
        """Proxy system metrics from Pi with authentication"""
        try:
            pi_response = requests.get(f"{PI_SERVER}/api/system-metrics", timeout=5)
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502
    
    @app.route('/api/pi/active-passive/config')
    @require_auth_internal
    def proxy_pi_active_passive_config():
        """Proxy active-passive config from Pi with authentication"""
        try:
            pi_response = requests.get(f"{PI_SERVER}/api/active-passive/config", timeout=5)
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502
    
    @app.route('/api/pi/active-passive/stats')
    @require_auth
    def proxy_pi_active_passive_stats():
        """Proxy active-passive stats from Pi with authentication"""
        try:
            pi_response = requests.get(f"{PI_SERVER}/api/active-passive/stats", timeout=5)
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502
    
    @app.route('/api/pi/active-passive/test-trigger')
    @require_auth
    def proxy_pi_active_passive_test():
        """Proxy active-passive test trigger from Pi with authentication"""
        try:
            pi_response = requests.get(f"{PI_SERVER}/api/active-passive/test-trigger", timeout=5)
            return Response(
                pi_response.content,
                content_type='application/json',
                status=pi_response.status_code
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to connect to Pi: {str(e)}'}), 502