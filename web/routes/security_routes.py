# web/routes/security_routes.py
from flask import Blueprint, request, jsonify
from web.middleware.auth import require_auth
from web.middleware.decorators import require_admin_internal
from datetime import datetime, timedelta
import json
import subprocess
import re
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

security_bp = Blueprint('security', __name__)

def parse_security_log_entry(line):
    """Parse a security audit log entry from syslog."""
    try:
        # Extract JSON from syslog line
        # Format: Aug 25 12:07:20 ubuntu-birdcam {"timestamp"[PID]: ...}
        # The [PID] part corrupts the JSON, so we need to fix it
        
        # Find where the JSON starts
        json_start = line.find('{"timestamp"')
        if json_start == -1:
            return None
            
        # Extract from that point and fix the [PID]: issue
        json_str = line[json_start:]
        # Fix the [PID]: that appears after "timestamp"
        json_str = re.sub(r'"\[\d+\]:', '":', json_str)
        
        log_data = json.loads(json_str)
        
        # Only include security audit events
        if log_data.get('logger') != 'birdcam.security.audit':
            return None
            
        return {
            'timestamp': log_data.get('timestamp'),
            'event_type': log_data.get('event_type'),
            'username': log_data.get('username'),
            'ip_address': log_data.get('ip_address'),
            'user_agent': log_data.get('user_agent'),
            'failure_reason': log_data.get('failure_reason'),
            'request_id': log_data.get('request_id'),
            'request_path': log_data.get('request_path'),
            'severity': log_data.get('severity', 'INFO'),
            'target_username': log_data.get('target_username'),
            'new_role': log_data.get('new_role'),
            'changed_by': log_data.get('changed_by'),
            'deactivated_by': log_data.get('deactivated_by')
        }
    except Exception as e:
        logger.debug(f"Failed to parse security log entry: {e}")
        return None

@security_bp.route('/logs', methods=['GET'])
@require_admin_internal
def get_security_logs():
    """Get security audit logs."""
    try:
        # Get query parameters
        hours = int(request.args.get('hours', 24))
        event_type = request.args.get('event_type')
        username = request.args.get('username')
        ip_address = request.args.get('ip_address')
        
        # Calculate time range
        since_time = datetime.now() - timedelta(hours=hours)
        since_str = since_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Build journalctl command
        # Note: We don't use -t flag as syslog doesn't tag properly
        # Instead we'll grep for our logger name
        cmd = [
            'journalctl',
            '--since', since_str,
            '--no-pager',
            '-n', '5000'  # Get more entries since we'll filter
        ]
        
        # Execute command and filter for security audit logs
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to get security logs: {result.stderr}")
            return jsonify({'error': 'Failed to retrieve security logs'}), 500
        
        # Filter for security audit logs
        security_lines = []
        for line in result.stdout.strip().split('\n'):
            if 'birdcam.security.audit' in line:
                security_lines.append(line)
                
        # Parse log entries
        logs = []
        for line in security_lines:
            if not line:
                continue
                
            entry = parse_security_log_entry(line)
            if not entry:
                continue
                
            # Apply filters
            if event_type and entry['event_type'] != event_type:
                continue
            if username and entry.get('username', '').lower() != username.lower():
                continue
            if ip_address and entry.get('ip_address') != ip_address:
                continue
                
            logs.append(entry)
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({'logs': logs})
        
    except Exception as e:
        logger.error(f"Error getting security logs: {e}")
        return jsonify({'error': str(e)}), 500

@security_bp.route('/logs/summary', methods=['GET'])
@require_admin_internal
def get_security_summary():
    """Get security summary statistics."""
    try:
        # Get query parameters
        hours = int(request.args.get('hours', 24))
        
        # Calculate time range
        since_time = datetime.now() - timedelta(hours=hours)
        since_str = since_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get logs
        cmd = [
            'journalctl',
            '--since', since_str,
            '--no-pager',
            '-n', '20000'  # Get more entries since we'll filter
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({'error': 'Failed to retrieve security logs'}), 500
            
        # Filter for security audit logs
        security_lines = []
        for line in result.stdout.strip().split('\n'):
            if 'birdcam.security.audit' in line:
                security_lines.append(line)
                
        # Calculate statistics
        stats = {
            'total_events': 0,
            'failed_logins': 0,
            'successful_logins': 0,
            'password_changes': 0,
            'role_changes': 0,
            'user_deactivations': 0,
            'failed_by_reason': defaultdict(int),
            'failed_by_username': defaultdict(int),
            'failed_by_ip': defaultdict(int),
            'events_by_hour': defaultdict(int)
        }
        
        for line in security_lines:
            if not line:
                continue
                
            entry = parse_security_log_entry(line)
            if not entry:
                continue
                
            stats['total_events'] += 1
            
            # Count by event type
            event_type = entry['event_type']
            if event_type == 'auth_failed':
                stats['failed_logins'] += 1
                stats['failed_by_reason'][entry.get('failure_reason', 'unknown')] += 1
                stats['failed_by_username'][entry.get('username', 'unknown')] += 1
                stats['failed_by_ip'][entry.get('ip_address', 'unknown')] += 1
            elif event_type == 'auth_success':
                stats['successful_logins'] += 1
            elif event_type == 'password_changed':
                stats['password_changes'] += 1
            elif event_type == 'role_changed':
                stats['role_changes'] += 1
            elif event_type == 'user_deactivated':
                stats['user_deactivations'] += 1
            
            # Count by hour
            try:
                timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                stats['events_by_hour'][hour_key] += 1
            except:
                pass
        
        # Convert defaultdicts to regular dicts for JSON serialization
        stats['failed_by_reason'] = dict(stats['failed_by_reason'])
        stats['failed_by_username'] = dict(stats['failed_by_username'])
        stats['failed_by_ip'] = dict(stats['failed_by_ip'])
        stats['events_by_hour'] = dict(stats['events_by_hour'])
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting security summary: {e}")
        return jsonify({'error': str(e)}), 500

@security_bp.route('/users/locked', methods=['GET'])
@require_admin_internal
def get_locked_users():
    """Get users with recent failed login attempts."""
    try:
        # Get failed login attempts from last 24 hours
        hours = 24
        since_time = datetime.now() - timedelta(hours=hours)
        since_str = since_time.strftime('%Y-%m-%d %H:%M:%S')
        
        cmd = [
            'journalctl',
            '--since', since_str,
            '--no-pager',
            '-n', '5000'  # Get more entries since we'll filter
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({'error': 'Failed to retrieve security logs'}), 500
            
        # Filter for security audit logs
        security_lines = []
        for line in result.stdout.strip().split('\n'):
            if 'birdcam.security.audit' in line:
                security_lines.append(line)
                
        # Track failed attempts by username
        failed_attempts = defaultdict(list)
        
        for line in security_lines:
            if not line:
                continue
                
            entry = parse_security_log_entry(line)
            if not entry or entry['event_type'] != 'auth_failed':
                continue
                
            username = entry.get('username', 'unknown')
            failed_attempts[username].append({
                'timestamp': entry['timestamp'],
                'ip_address': entry.get('ip_address'),
                'failure_reason': entry.get('failure_reason')
            })
        
        # Build locked users list
        locked_users = []
        for username, attempts in failed_attempts.items():
            # Sort attempts by timestamp
            attempts.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Check recent attempts (last hour)
            recent_cutoff = datetime.now() - timedelta(hours=1)
            recent_attempts = [
                a for a in attempts 
                if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) > recent_cutoff
            ]
            
            # Consider "locked" if more than 5 attempts in last hour
            is_locked = len(recent_attempts) >= 5
            
            locked_users.append({
                'username': username,
                'total_attempts': len(attempts),
                'recent_attempts': len(recent_attempts),
                'last_attempt': attempts[0] if attempts else None,
                'is_locked': is_locked,
                'attempts': attempts[:10]  # Last 10 attempts
            })
        
        # Sort by most recent attempts
        locked_users.sort(key=lambda x: x['total_attempts'], reverse=True)
        
        return jsonify({'users': locked_users})
        
    except Exception as e:
        logger.error(f"Error getting locked users: {e}")
        return jsonify({'error': str(e)}), 500