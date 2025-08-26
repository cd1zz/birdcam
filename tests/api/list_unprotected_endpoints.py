#!/usr/bin/env python3
"""
Quick script to list all endpoints and identify which ones lack authentication.
Run from project root: python tests/api/list_unprotected_endpoints.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.discovery.discover_endpoints import discover_endpoints
from config.settings import load_processing_config
from web.app import create_processing_app
from tests.conftest import DummyProcessingService, DummyRepo


def check_endpoint_auth(client, endpoint, method='GET'):
    """Check if an endpoint requires authentication."""
    try:
        if method == 'GET':
            response = client.get(endpoint)
        elif method == 'POST':
            response = client.post(endpoint, json={})
        else:
            return 'UNKNOWN'
        
        if response.status_code in [401, 403]:
            return 'PROTECTED'
        elif response.status_code == 404:
            return 'NOT_FOUND'
        elif response.status_code == 405:
            return 'METHOD_NOT_ALLOWED'
        elif response.status_code in [200, 400]:
            return 'ACCESSIBLE'
        else:
            return f'STATUS_{response.status_code}'
    except Exception as e:
        return f'ERROR: {str(e)}'


def main():
    # Create Flask app
    config = load_processing_config()
    app = create_processing_app(
        DummyProcessingService(),
        DummyRepo(),
        DummyRepo(),
        config,
    )
    app.config["TESTING"] = True
    
    # Discover all endpoints
    endpoints = discover_endpoints(app)
    
    # Group endpoints by protection status
    results = {
        'ACCESSIBLE': [],
        'PROTECTED': [],
        'NOT_FOUND': [],
        'OTHER': []
    }
    
    print("Analyzing API endpoints...")
    print("=" * 60)
    
    with app.test_client() as client:
        for endpoint in endpoints:
            path = endpoint['path']
            
            # Skip parameterized endpoints for now
            if '<' in path:
                continue
            
            # Test the first available method
            method = endpoint['methods'][0] if endpoint['methods'] else 'GET'
            status = check_endpoint_auth(client, path, method)
            
            if status == 'ACCESSIBLE':
                results['ACCESSIBLE'].append((path, method))
            elif status == 'PROTECTED':
                results['PROTECTED'].append((path, method))
            elif status == 'NOT_FOUND':
                results['NOT_FOUND'].append((path, method))
            else:
                results['OTHER'].append((path, method, status))
    
    # Print results
    print(f"\n🔓 ACCESSIBLE WITHOUT AUTH ({len(results['ACCESSIBLE'])} endpoints):")
    print("-" * 60)
    for path, method in sorted(results['ACCESSIBLE']):
        print(f"  {method:6} {path}")
    
    print(f"\n🔒 PROTECTED ({len(results['PROTECTED'])} endpoints):")
    print("-" * 60)
    for path, method in sorted(results['PROTECTED']):
        print(f"  {method:6} {path}")
    
    if results['NOT_FOUND']:
        print(f"\n❓ NOT FOUND ({len(results['NOT_FOUND'])} endpoints):")
        print("-" * 60)
        for path, method in sorted(results['NOT_FOUND']):
            print(f"  {method:6} {path}")
    
    if results['OTHER']:
        print(f"\n⚠️  OTHER STATUS ({len(results['OTHER'])} endpoints):")
        print("-" * 60)
        for path, method, status in sorted(results['OTHER']):
            print(f"  {method:6} {path} -> {status}")
    
    # Summary
    total = sum(len(results[k]) for k in results)
    protected_count = len(results['PROTECTED'])
    accessible_count = len(results['ACCESSIBLE'])
    
    print("\n📊 SUMMARY:")
    print("-" * 60)
    print(f"Total endpoints analyzed: {total}")
    print(f"Protected endpoints: {protected_count} ({protected_count/total*100:.1f}%)")
    print(f"Accessible without auth: {accessible_count} ({accessible_count/total*100:.1f}%)")
    
    # Highlight sensitive accessible endpoints
    sensitive_keywords = ['upload', 'delete', 'settings', 'system', 'camera', 'stream', 'motion']
    sensitive_accessible = []
    
    for path, method in results['ACCESSIBLE']:
        if any(keyword in path.lower() for keyword in sensitive_keywords):
            sensitive_accessible.append((path, method))
    
    if sensitive_accessible:
        print("\n🚨 POTENTIALLY SENSITIVE ENDPOINTS WITHOUT AUTH:")
        print("-" * 60)
        for path, method in sorted(sensitive_accessible):
            print(f"  {method:6} {path}")


if __name__ == '__main__':
    main()