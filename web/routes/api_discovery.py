"""
API Discovery Route - Provides introspection of available API endpoints
This helps with testing and documentation
"""
from flask import Blueprint, jsonify, current_app
from web.middleware.auth import require_auth
from werkzeug.routing import Rule
import inspect
from typing import Dict, Any

api_discovery = Blueprint('api_discovery', __name__)


def extract_route_info(rule: Rule) -> Dict[str, Any]:
    """Extract detailed information about a route"""
    # Get the view function
    endpoint = current_app.view_functions.get(rule.endpoint)
    
    info = {
        'path': rule.rule,
        'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),
        'arguments': list(rule.arguments),
        'description': '',
        'parameters': {},
        'requires_auth': False,
        'requires_admin': False,
        'requires_internal': False
    }
    
    if endpoint:
        # Extract docstring
        info['description'] = inspect.getdoc(endpoint) or ''
        
        # Check for decorators by inspecting the function
        source = inspect.getsource(endpoint) if hasattr(endpoint, '__code__') else ''
        info['requires_auth'] = '@require_auth' in source or 'require_auth(' in source
        info['requires_admin'] = '@require_admin' in source or 'require_admin(' in source
        info['requires_internal'] = '@require_internal_network' in source
        
        # Try to extract parameter information from the function signature
        try:
            sig = inspect.signature(endpoint)
            for param_name, param in sig.parameters.items():
                if param_name not in ['self', 'request']:
                    info['parameters'][param_name] = {
                        'type': str(param.annotation) if param.annotation != param.empty else 'any',
                        'required': param.default == param.empty,
                        'default': str(param.default) if param.default != param.empty else None
                    }
        except (ValueError, TypeError) as e:
            # Some functions may not have introspectable signatures
            current_app.logger.debug(f"Could not inspect signature for {endpoint.__name__}: {e}")
    
    return info


@api_discovery.route('/api/discovery/routes', methods=['GET'])
@require_auth
def discover_routes():
    """
    Returns a comprehensive list of all available API routes
    This endpoint is used for testing and documentation purposes
    """
    routes = []
    
    # Group routes by blueprint
    blueprints = {}
    
    for rule in current_app.url_map.iter_rules():
        # Skip non-API routes
        if not rule.rule.startswith('/api/') or rule.endpoint == 'static':
            continue
        
        route_info = extract_route_info(rule)
        
        # Determine blueprint
        blueprint_name = rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'main'
        
        if blueprint_name not in blueprints:
            blueprints[blueprint_name] = []
        
        blueprints[blueprint_name].append(route_info)
    
    # Sort routes within each blueprint
    for blueprint in blueprints.values():
        blueprint.sort(key=lambda x: x['path'])
    
    return jsonify({
        'total_routes': sum(len(routes) for routes in blueprints.values()),
        'blueprints': blueprints,
        'api_version': current_app.config.get('API_VERSION', '1.0.0')
    })


@api_discovery.route('/api/discovery/validate', methods=['POST'])
@require_auth
def validate_frontend_routes():
    """
    Validates that frontend routes match backend implementation
    Accepts a list of routes used by frontend and returns validation results
    """
    from flask import request
    
    frontend_routes = request.json.get('routes', [])
    backend_routes = {}
    
    # Build a map of backend routes
    for rule in current_app.url_map.iter_rules():
        if rule.rule.startswith('/api/'):
            for method in rule.methods - {'HEAD', 'OPTIONS'}:
                key = f"{method} {rule.rule}"
                backend_routes[key] = extract_route_info(rule)
    
    results = {
        'valid': [],
        'missing': [],
        'mismatched': []
    }
    
    for frontend_route in frontend_routes:
        method = frontend_route.get('method', 'GET')
        path = frontend_route.get('path', '')
        
        # Try to find matching backend route
        found = False
        for backend_key, backend_info in backend_routes.items():
            backend_method, backend_path = backend_key.split(' ', 1)
            
            # Simple matching - could be enhanced to handle parameters
            if method == backend_method and paths_match(path, backend_path):
                results['valid'].append({
                    'frontend': frontend_route,
                    'backend': backend_info
                })
                found = True
                break
        
        if not found:
            results['missing'].append(frontend_route)
    
    return jsonify({
        'summary': {
            'total_frontend_routes': len(frontend_routes),
            'valid': len(results['valid']),
            'missing': len(results['missing']),
            'mismatched': len(results['mismatched'])
        },
        'results': results
    })


def paths_match(frontend_path: str, backend_path: str) -> bool:
    """Check if frontend path matches backend path pattern"""
    # Convert Flask parameter syntax to regex
    import re
    
    # Replace Flask parameters with wildcards
    pattern = backend_path
    pattern = re.sub(r'<[^>]+>', '[^/]+', pattern)
    pattern = f"^{pattern}$"
    
    return bool(re.match(pattern, frontend_path))


@api_discovery.route('/api/discovery/openapi', methods=['GET'])
@require_auth
def generate_openapi_spec():
    """
    Generates an OpenAPI 3.0 specification for the API
    This can be used for documentation and contract testing
    """
    spec = {
        'openapi': '3.0.0',
        'info': {
            'title': 'BirdCam API',
            'version': current_app.config.get('API_VERSION', '1.0.0'),
            'description': 'API for BirdCam wildlife detection system'
        },
        'servers': [
            {'url': '/api', 'description': 'Main API'}
        ],
        'paths': {},
        'components': {
            'securitySchemes': {
                'bearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT'
                }
            }
        }
    }
    
    for rule in current_app.url_map.iter_rules():
        if not rule.rule.startswith('/api/') or rule.endpoint == 'static':
            continue
        
        route_info = extract_route_info(rule)
        path = rule.rule.replace('<', '{').replace('>', '}')
        
        if path not in spec['paths']:
            spec['paths'][path] = {}
        
        for method in route_info['methods']:
            operation = {
                'summary': route_info['description'].split('\n')[0] if route_info['description'] else '',
                'description': route_info['description'],
                'parameters': [],
                'responses': {
                    '200': {'description': 'Success'},
                    '401': {'description': 'Unauthorized'},
                    '500': {'description': 'Server Error'}
                }
            }
            
            # Add security requirements
            if route_info['requires_auth']:
                operation['security'] = [{'bearerAuth': []}]
            
            # Add path parameters
            for arg in route_info['arguments']:
                operation['parameters'].append({
                    'name': arg,
                    'in': 'path',
                    'required': True,
                    'schema': {'type': 'string'}
                })
            
            spec['paths'][path][method.lower()] = operation
    
    return jsonify(spec)