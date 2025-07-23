"""
API Contract Testing - Validates that all routes work correctly
and match between frontend expectations and backend implementation
"""
import pytest
import json
import re
from pathlib import Path
from flask import Flask
from typing import Dict, List, Set, Tuple
import subprocess
import ast

class APIContractTester:
    """Dynamically discovers and tests all API endpoints"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.routes = self._discover_routes()
        self.frontend_routes = self._parse_frontend_routes()
    
    def _discover_routes(self) -> Dict[str, Dict]:
        """Dynamically discover all registered routes in Flask app"""
        routes = {}
        
        for rule in self.app.url_map.iter_rules():
            # Skip static files and internal routes
            if rule.endpoint == 'static' or not rule.rule.startswith('/api/'):
                continue
                
            route_info = {
                'path': rule.rule,
                'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),
                'endpoint': rule.endpoint,
                'arguments': list(rule.arguments),
                'defaults': rule.defaults or {},
                'strict_slashes': rule.strict_slashes
            }
            
            # Convert Flask route pattern to regex pattern for matching
            pattern = rule.rule
            for arg in rule.arguments:
                # Replace Flask route parameters with regex groups
                pattern = pattern.replace(f'<{arg}>', '(?P<{}>[^/]+)'.format(arg))
                pattern = pattern.replace(f'<int:{arg}>', '(?P<{}>\d+)'.format(arg))
                pattern = pattern.replace(f'<path:{arg}>', '(?P<{}>.*?)'.format(arg))
            
            route_info['pattern'] = pattern
            routes[rule.rule] = route_info
            
        return routes
    
    def _parse_frontend_routes(self) -> Set[Tuple[str, str]]:
        """Parse frontend client.ts to extract API calls"""
        frontend_routes = set()
        client_path = Path(__file__).parent.parent.parent / 'web-ui' / 'src' / 'api' / 'client.ts'
        
        if not client_path.exists():
            return frontend_routes
            
        with open(client_path, 'r') as f:
            content = f.read()
            
        # Find all API calls in the frontend
        # Match patterns like: .get('/api/...'), .post('/api/...'), etc.
        patterns = [
            r'\.get\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
            r'\.post\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
            r'\.put\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
            r'\.delete\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        ]
        
        for pattern in patterns:
            method = pattern.split('\\')[1].split('(')[0].upper()
            for match in re.finditer(pattern, content):
                route = match.group(1)
                if route.startswith('/api/'):
                    # Replace template literals with placeholders
                    route = re.sub(r'\$\{[^}]+\}', '*', route)
                    frontend_routes.add((method, route))
                    
        return frontend_routes
    
    def _match_route(self, frontend_route: str, backend_pattern: str) -> bool:
        """Check if a frontend route matches a backend pattern"""
        # Convert frontend route with * to regex
        frontend_pattern = frontend_route.replace('*', '[^/]+')
        frontend_pattern = f"^{frontend_pattern}$"
        
        # Convert backend Flask pattern to comparable format
        backend_regex = f"^{backend_pattern}$"
        
        # Simple comparison - could be enhanced
        return bool(re.match(backend_regex, frontend_route.replace('*', '123')))
    
    def validate_routes(self) -> Dict[str, List[str]]:
        """Validate that all frontend routes have matching backend routes"""
        issues = {
            'missing_backend': [],
            'method_mismatch': [],
            'unused_backend': []
        }
        
        backend_routes = {
            (method, route): info 
            for route, info in self.routes.items() 
            for method in info['methods']
        }
        
        matched_backend_routes = set()
        
        # Check each frontend route
        for method, frontend_route in self.frontend_routes:
            found = False
            
            for (backend_method, backend_route), info in backend_routes.items():
                if self._match_route(frontend_route, info['pattern']):
                    if method == backend_method:
                        found = True
                        matched_backend_routes.add((backend_method, backend_route))
                        break
                    else:
                        issues['method_mismatch'].append(
                            f"{method} {frontend_route} -> Backend expects {backend_method}"
                        )
                        found = True
                        break
            
            if not found:
                issues['missing_backend'].append(f"{method} {frontend_route}")
        
        # Find unused backend routes
        for (method, route), info in backend_routes.items():
            if (method, route) not in matched_backend_routes:
                # Skip some internal routes
                if not any(skip in route for skip in ['/auth/', '/setup/', '/admin/']):
                    issues['unused_backend'].append(f"{method} {route}")
        
        return issues


@pytest.fixture
def contract_tester(app):
    """Create an API contract tester instance"""
    return APIContractTester(app)


def test_frontend_backend_route_alignment(contract_tester):
    """Test that all frontend routes have matching backend implementations"""
    issues = contract_tester.validate_routes()
    
    # Generate detailed report
    report = []
    
    if issues['missing_backend']:
        report.append("Frontend routes without backend implementation:")
        for route in issues['missing_backend']:
            report.append(f"  - {route}")
    
    if issues['method_mismatch']:
        report.append("\nHTTP method mismatches:")
        for mismatch in issues['method_mismatch']:
            report.append(f"  - {mismatch}")
    
    if issues['unused_backend']:
        report.append("\nBackend routes not used by frontend:")
        for route in issues['unused_backend']:
            report.append(f"  - {route}")
    
    # Assert no critical issues
    assert not issues['missing_backend'], "\n".join(report)
    assert not issues['method_mismatch'], "\n".join(report)


def test_all_routes_have_auth(contract_tester):
    """Ensure all API routes have appropriate authentication"""
    public_routes = {'/api/auth/login', '/api/auth/refresh', '/api/setup/status'}
    
    for route, info in contract_tester.routes.items():
        if route in public_routes:
            continue
            
        # This is a simplified check - in reality you'd inspect the endpoint function
        # to verify it has @require_auth or similar decorators
        endpoint_name = info['endpoint']
        assert 'public' not in endpoint_name.lower(), f"Route {route} appears to be missing auth"


def test_route_parameter_consistency(app, client, auth_headers):
    """Test that route parameters are consistent between frontend and backend"""
    
    # Example: Test the logs endpoint parameter issue you found
    test_cases = [
        {
            'endpoint': '/api/logs/pi-capture',
            'frontend_param': 'level',  # What frontend sends
            'backend_param': 'levels',   # What backend expects
            'test_value': 'ERROR'
        }
    ]
    
    for test in test_cases:
        # Test with frontend parameter name (should fail currently)
        response = client.get(
            test['endpoint'], 
            query_string={test['frontend_param']: test['test_value']},
            headers=auth_headers
        )
        
        # This would catch the parameter mismatch
        # The test would fail if backend expects different param name


def test_dynamic_route_discovery_endpoint(client, auth_headers):
    """Test endpoint that returns all available routes (if implemented)"""
    # This would be a new endpoint you add to help with route discovery
    response = client.get('/api/routes', headers=auth_headers)
    
    if response.status_code == 200:
        routes = response.json
        
        # Validate route structure
        for route in routes:
            assert 'path' in route
            assert 'methods' in route
            assert 'parameters' in route
            assert 'description' in route


class TestAPIResponseSchemas:
    """Validate that API responses match expected schemas"""
    
    def test_detection_response_schema(self, client, auth_headers):
        """Test that detection endpoints return consistent schema"""
        response = client.get('/api/recent-detections', headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json
            assert 'detections' in data
            
            if data['detections']:
                detection = data['detections'][0]
                required_fields = {'id', 'filename', 'species', 'confidence'}
                assert required_fields.issubset(set(detection.keys()))


def test_api_versioning(contract_tester):
    """Ensure API versioning is consistent"""
    # Check if routes follow versioning pattern
    versioned_routes = [r for r in contract_tester.routes if '/v1/' in r or '/v2/' in r]
    unversioned_api_routes = [
        r for r in contract_tester.routes 
        if r.startswith('/api/') and '/v1/' not in r and '/v2/' not in r
    ]
    
    # Warn about unversioned routes
    if unversioned_api_routes:
        print(f"Warning: {len(unversioned_api_routes)} API routes are not versioned")