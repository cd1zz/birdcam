#!/usr/bin/env python3
"""
Script to validate that frontend API calls match backend routes
Run this to detect mismatches between frontend client and backend implementation
"""
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json

def parse_frontend_routes(client_file: Path) -> List[Dict]:
    """Parse the frontend client.ts file to extract API calls"""
    routes = []
    
    with open(client_file, 'r') as f:
        content = f.read()
    
    # Find all API method calls
    patterns = {
        'GET': r'\.get(?:<[^>]*>)?\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        'POST': r'\.post(?:<[^>]*>)?\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        'PUT': r'\.put(?:<[^>]*>)?\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        'DELETE': r'\.delete(?:<[^>]*>)?\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
    }
    
    for method, pattern in patterns.items():
        for match in re.finditer(pattern, content):
            path = match.group(1)
            if path.startswith('/api/'):
                # Handle template literals
                if '${' in path:
                    # Extract the template literal pattern
                    path = re.sub(r'\$\{[^}]+\}', '*', path)
                
                routes.append({
                    'method': method,
                    'path': path,
                    'line': content[:match.start()].count('\n') + 1
                })
    
    # Also look for endpoint definitions in the api object
    api_pattern = r'(\w+):\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?\s*=>\s*[^{]*{[^}]*[\'"`](/api/[^\'"`]+)'
    for match in re.finditer(api_pattern, content, re.MULTILINE | re.DOTALL):
        func_name = match.group(1)
        path = match.group(2)
        
        # Try to determine method from function name or content
        method = 'GET'  # default
        if 'post' in func_name.lower() or 'create' in func_name.lower() or 'update' in func_name.lower():
            method = 'POST'
        elif 'put' in func_name.lower():
            method = 'PUT'
        elif 'delete' in func_name.lower():
            method = 'DELETE'
        
        routes.append({
            'method': method,
            'path': path,
            'function': func_name,
            'line': content[:match.start()].count('\n') + 1
        })
    
    return routes


def parse_backend_routes(project_root: Path) -> List[Dict]:
    """Parse backend Python files to find route definitions"""
    routes = []
    
    # Find all Python files in web directory
    web_dir = project_root / 'web'
    
    route_patterns = [
        # Flask route decorators
        r'@\w+\.route\s*\(\s*[\'"`]([^\'"`]+)[\'"`]\s*(?:,\s*methods\s*=\s*\[([^\]]+)\])?',
        # Blueprint route decorators
        r'@\w+_bp\.route\s*\(\s*[\'"`]([^\'"`]+)[\'"`]\s*(?:,\s*methods\s*=\s*\[([^\]]+)\])?',
        # Direct route registration
        r'\.add_url_rule\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
    ]
    
    for py_file in web_dir.rglob('*.py'):
        with open(py_file, 'r') as f:
            content = f.read()
        
        for pattern in route_patterns:
            for match in re.finditer(pattern, content):
                path = match.group(1)
                methods_str = match.group(2) if len(match.groups()) > 1 else None
                
                if methods_str:
                    # Parse methods from the list
                    methods = [m.strip().strip('"\'') for m in methods_str.split(',')]
                else:
                    methods = ['GET']  # Default Flask method
                
                for method in methods:
                    routes.append({
                        'method': method.upper(),
                        'path': path,
                        'file': str(py_file.relative_to(project_root)),
                        'line': content[:match.start()].count('\n') + 1
                    })
    
    return routes


def normalize_path(path: str) -> str:
    """Normalize a path for comparison"""
    # Replace parameter placeholders
    path = re.sub(r'<[^>]+>', '*', path)  # Flask style
    path = re.sub(r'\{[^}]+\}', '*', path)  # OpenAPI style
    path = re.sub(r'/\*', '/*', path)  # Normalize wildcards
    return path


def find_matching_backend_route(frontend_route: Dict, backend_routes: List[Dict]) -> List[Dict]:
    """Find backend routes that match a frontend route"""
    matches = []
    frontend_normalized = normalize_path(frontend_route['path'])
    
    for backend_route in backend_routes:
        backend_normalized = normalize_path(backend_route['path'])
        
        if (frontend_route['method'] == backend_route['method'] and 
            frontend_normalized == backend_normalized):
            matches.append(backend_route)
    
    return matches


def generate_report(project_root: Path):
    """Generate a comprehensive API route validation report"""
    # Parse routes
    client_file = project_root / 'web-ui' / 'src' / 'api' / 'client.ts'
    
    if not client_file.exists():
        print(f"Error: Could not find {client_file}")
        return
    
    print("Parsing frontend routes...")
    frontend_routes = parse_frontend_routes(client_file)
    
    print("Parsing backend routes...")
    backend_routes = parse_backend_routes(project_root)
    
    # Analyze matches
    missing_backend = []
    matched = []
    
    for frontend_route in frontend_routes:
        matches = find_matching_backend_route(frontend_route, backend_routes)
        
        if not matches:
            missing_backend.append(frontend_route)
        else:
            matched.append((frontend_route, matches))
    
    # Find unused backend routes
    used_backend_routes = set()
    for _, backend_matches in matched:
        for backend_route in backend_matches:
            used_backend_routes.add((backend_route['method'], normalize_path(backend_route['path'])))
    
    unused_backend = []
    for backend_route in backend_routes:
        route_key = (backend_route['method'], normalize_path(backend_route['path']))
        if route_key not in used_backend_routes and backend_route['path'].startswith('/api/'):
            # Skip some internal/admin routes
            if not any(skip in backend_route['path'] for skip in ['/auth/logout', '/auth/refresh']):
                unused_backend.append(backend_route)
    
    # Generate report
    print("\n" + "="*80)
    print("API ROUTE VALIDATION REPORT")
    print("="*80)
    
    print(f"\nSummary:")
    print(f"  Frontend routes found: {len(frontend_routes)}")
    print(f"  Backend routes found: {len(backend_routes)}")
    print(f"  Matched routes: {len(matched)}")
    print(f"  Missing in backend: {len(missing_backend)}")
    print(f"  Unused backend routes: {len(unused_backend)}")
    
    if missing_backend:
        print(f"\n❌ Frontend routes without backend implementation ({len(missing_backend)}):")
        for route in missing_backend:
            print(f"  - {route['method']} {route['path']} (client.ts:{route['line']})")
    
    if unused_backend:
        print(f"\n⚠️  Backend routes not used by frontend ({len(unused_backend)}):")
        for route in unused_backend:
            print(f"  - {route['method']} {route['path']} ({route['file']}:{route['line']})")
    
    # Check for parameter mismatches
    print("\n🔍 Checking for potential parameter mismatches...")
    
    # Known parameter issues
    param_checks = [
        ('level', 'levels', '/api/logs/'),
    ]
    
    issues_found = False
    for frontend_param, backend_param, path_pattern in param_checks:
        # Search in client.ts for usage
        with open(client_file, 'r') as f:
            content = f.read()
        
        pattern = rf'{frontend_param}[\'"`]?\s*:'
        for match in re.finditer(pattern, content):
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            line = content[line_start:line_end]
            
            if path_pattern in line:
                print(f"  - Parameter mismatch: Frontend uses '{frontend_param}' but backend expects '{backend_param}'")
                print(f"    Location: client.ts:{content[:match.start()].count('\n') + 1}")
                issues_found = True
    
    if not issues_found:
        print("  ✓ No known parameter mismatches found")
    
    print("\n" + "="*80)
    
    # Save detailed report
    report_data = {
        'summary': {
            'frontend_routes': len(frontend_routes),
            'backend_routes': len(backend_routes),
            'matched': len(matched),
            'missing_backend': len(missing_backend),
            'unused_backend': len(unused_backend)
        },
        'missing_backend': missing_backend,
        'unused_backend': unused_backend,
        'matched': [
            {
                'frontend': fr,
                'backend': br
            }
            for fr, br in matched
        ]
    }
    
    report_file = project_root / 'api_routes_report.json'
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")


if __name__ == '__main__':
    # Find project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    
    generate_report(project_root)