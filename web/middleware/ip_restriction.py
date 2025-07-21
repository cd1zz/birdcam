# web/middleware/ip_restriction.py
"""
IP-based access restriction middleware
"""
from functools import wraps
from flask import request, jsonify
import ipaddress
import logging

logger = logging.getLogger(__name__)

def is_internal_ip(ip_str: str) -> bool:
    """
    Check if an IP address is from a private/internal network.
    
    Covers:
    - 10.0.0.0/8 (10.0.0.0 - 10.255.255.255)
    - 172.16.0.0/12 (172.16.0.0 - 172.31.255.255)
    - 192.168.0.0/16 (192.168.0.0 - 192.168.255.255)
    - 127.0.0.0/8 (localhost)
    - ::1 (IPv6 localhost)
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        
        # Check for IPv6 localhost
        if ip_str == '::1':
            return True
            
        # Check for IPv4 private networks and localhost
        if isinstance(ip, ipaddress.IPv4Address):
            return (
                ip.is_private or 
                ip.is_loopback or
                ip in ipaddress.ip_network('10.0.0.0/8') or
                ip in ipaddress.ip_network('172.16.0.0/12') or
                ip in ipaddress.ip_network('192.168.0.0/16')
            )
            
        # For IPv6, check if it's a private address
        return ip.is_private or ip.is_loopback
        
    except ValueError:
        logger.warning(f"Invalid IP address: {ip_str}")
        return False

def require_internal_network(f):
    """
    Decorator to restrict access to internal network IPs only.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP address
        # Check for X-Forwarded-For header (when behind proxy)
        if request.headers.get('X-Forwarded-For'):
            # Get the first IP in the chain (original client)
            client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            client_ip = request.remote_addr
            
        logger.info(f"Setup access attempt from IP: {client_ip}")
        
        # Check if IP is internal
        if not is_internal_ip(client_ip):
            logger.warning(f"Setup access denied for external IP: {client_ip}")
            return jsonify({
                'error': 'Access denied',
                'message': 'Initial setup can only be performed from the local network'
            }), 403
            
        return f(*args, **kwargs)
        
    return decorated_function