from flask import Blueprint, jsonify, request, g
from web.middleware.auth import require_auth, require_admin
import subprocess
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
from pathlib import Path
import glob
import os

# Create blueprint
log_routes = Blueprint('logs', __name__, url_prefix='/api/logs')

def convert_time_format(since: str) -> str:
    """Convert frontend time format to journalctl format"""
    time_map = {
        '5m': '5 minutes ago',
        '15m': '15 minutes ago',
        '30m': '30 minutes ago',
        '1h': '1 hour ago',
        '6h': '6 hours ago',
        '12h': '12 hours ago',
        '24h': '24 hours ago',
        '2d': '2 days ago',
        '7d': '7 days ago'
    }
    return time_map.get(since, since)

def parse_journalctl_output(output: str, service_name: str) -> List[Dict]:
    """Parse journalctl JSON output into structured log entries"""
    logs = []
    for line in output.strip().split('\n'):
        if not line:
            continue
        try:
            entry = json.loads(line)
            
            # Extract relevant fields
            timestamp = entry.get('__REALTIME_TIMESTAMP')
            if timestamp:
                # Convert microseconds to datetime
                dt = datetime.fromtimestamp(int(timestamp) / 1000000)
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp_str = 'Unknown'
            
            # Get the message
            message = entry.get('MESSAGE', '')
            
            # Get priority/level
            priority = entry.get('PRIORITY', 6)
            # Convert to int if it's a string
            try:
                priority = int(priority)
            except (ValueError, TypeError):
                priority = 6
            
            level = 'INFO'
            if priority <= 3:
                level = 'ERROR'
            elif priority == 4:
                level = 'WARNING'
            elif priority == 7:
                level = 'DEBUG'
            
            # Get unit name
            unit = entry.get('_SYSTEMD_UNIT', '')
            
            # For syslog messages, parse the facility
            syslog_facility = entry.get('SYSLOG_FACILITY')
            syslog_identifier = entry.get('SYSLOG_IDENTIFIER', '')
            
            # Check if this is a birdcam access log
            if syslog_identifier == 'birdcam.access' or (syslog_facility == '128' and 'birdcam.access' in message):
                # Parse the access log format
                match = re.search(r'birdcam\.access: (.+)', message)
                if match:
                    message = match.group(1)
                level = 'ACCESS'
            
            # Detect processing-related messages by content or syslog identifier
            if syslog_identifier == 'python' or any(emoji in message for emoji in ['🔄', '✅', '❌', '🎯', '🦅', '📊', '⚙️', '🤖', '📥', '📤']):
                # This is likely a processing log from print statements
                if '❌' in message or 'error' in message.lower() or 'failed' in message.lower():
                    level = 'ERROR'
                elif '⚠️' in message or 'warning' in message.lower():
                    level = 'WARNING'
                else:
                    level = 'INFO'
            
            logs.append({
                'timestamp': timestamp_str,
                'level': level,
                'service': service_name,
                'unit': unit,
                'message': message,
                'syslog_identifier': syslog_identifier
            })
            
        except json.JSONDecodeError:
            # Fall back to plain text parsing if JSON fails
            logs.append({
                'timestamp': 'Unknown',
                'level': 'INFO',
                'service': service_name,
                'unit': '',
                'message': line,
                'syslog_identifier': ''
            })
    
    return logs

@log_routes.route('/pi-capture', methods=['GET'])
@require_admin
def get_pi_capture_logs():
    """Get logs from the Pi capture service"""
    try:
        # Get query parameters
        lines = request.args.get('lines', 100, type=int)
        since = request.args.get('since', '1h')  # Default to last hour
        level = request.args.get('level', None)  # Filter by log level
        search = request.args.get('search', None)  # Search term
        
        # Convert time format for journalctl
        since_arg = convert_time_format(since)
        
        # Build journalctl command
        cmd = [
            'journalctl',
            '-u', 'pi-capture.service',
            '-n', str(lines),
            '--since', since_arg,
            '-o', 'json',
            '--no-pager'
        ]
        
        # Execute command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Failed to retrieve logs',
                'details': result.stderr
            }), 500
        
        # Parse logs - this already includes all logs from the service (both stdout and syslog)
        logs = parse_journalctl_output(result.stdout, 'pi-capture')
        
        # Sort by timestamp
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply level filter if specified
        if levels:
            level_list = [l.strip().upper() for l in levels.split(',')]
            logs = [log for log in logs if log['level'] in level_list]
        
        # Apply search filter if specified
        if search:
            search_lower = search.lower()
            logs = [log for log in logs if search_lower in log['message'].lower()]
        
        return jsonify({
            'logs': logs[:lines],  # Limit to requested number after filtering
            'total': len(logs),
            'service': 'pi-capture',
            'hostname': subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve logs',
            'details': str(e)
        }), 500

@log_routes.route('/ai-processor', methods=['GET'])
@require_admin
def get_ai_processor_logs():
    """Get logs from the AI processor service"""
    try:
        # Get query parameters
        lines = request.args.get('lines', 100, type=int)
        since = request.args.get('since', '1h')
        levels = request.args.get('levels', None)
        search = request.args.get('search', None)
        
        # Convert time format for journalctl
        since_arg = convert_time_format(since)
        
        # Build journalctl command
        cmd = [
            'journalctl',
            '-u', 'ai-processor.service',
            '-n', str(lines),
            '--since', since_arg,
            '-o', 'json',
            '--no-pager'
        ]
        
        # Execute command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Check if it's a permission error
            if 'permission denied' in result.stderr.lower() or result.returncode == 1 and not result.stdout:
                return jsonify({
                    'error': 'Failed to retrieve logs',
                    'details': 'Permission denied. The service may need to be configured to allow log access, or you may need to add the web server user to the systemd-journal group.'
                }), 500
            return jsonify({
                'error': 'Failed to retrieve logs',
                'details': result.stderr
            }), 500
        
        # Parse logs - this already includes all logs from the service (both stdout and syslog)
        logs = parse_journalctl_output(result.stdout, 'ai-processor')
        
        # Sort by timestamp
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply level filter if specified
        if levels:
            level_list = [l.strip().upper() for l in levels.split(',')]
            logs = [log for log in logs if log['level'] in level_list]
        
        # Apply search filter if specified
        if search:
            search_lower = search.lower()
            logs = [log for log in logs if search_lower in log['message'].lower()]
        
        return jsonify({
            'logs': logs[:lines],
            'total': len(logs),
            'service': 'ai-processor',
            'hostname': subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve logs',
            'details': str(e)
        }), 500

@log_routes.route('/combined', methods=['GET'])
@require_admin
def get_combined_logs():
    """Get combined logs from both services"""
    try:
        # Get query parameters
        lines = request.args.get('lines', 100, type=int)
        since = request.args.get('since', '1h')
        levels = request.args.get('levels', None)
        search = request.args.get('search', None)
        service_filter = request.args.get('service', None)
        
        # Convert time format for journalctl
        since_arg = convert_time_format(since)
        
        all_logs = []
        
        # Get logs from both services
        for service_name, unit_name in [
            ('pi-capture', 'pi-capture.service'),
            ('ai-processor', 'ai-processor.service')
        ]:
            if service_filter and service_filter != service_name:
                continue
                
            cmd = [
                'journalctl',
                '-u', unit_name,
                '-n', str(lines),
                '--since', since_arg,
                '-o', 'json',
                '--no-pager'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logs = parse_journalctl_output(result.stdout, service_name)
                all_logs.extend(logs)
        
        # No need for separate syslog query - the service logs already include all logs
        
        # Sort by timestamp
        all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply level filter if specified
        if levels:
            level_list = [l.strip().upper() for l in levels.split(',')]
            all_logs = [log for log in all_logs if log['level'] in level_list]
        
        # Apply search filter if specified
        if search:
            search_lower = search.lower()
            all_logs = [log for log in all_logs if search_lower in log['message'].lower()]
        
        return jsonify({
            'logs': all_logs[:lines],
            'total': len(all_logs)
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve logs',
            'details': str(e)
        }), 500

@log_routes.route('/levels', methods=['GET'])
@require_auth
def get_log_levels():
    """Get available log levels"""
    return jsonify({
        'levels': ['ERROR', 'WARNING', 'INFO', 'DEBUG', 'ACCESS']
    })

@log_routes.route('/remote/pi-capture', methods=['GET'])
@require_admin
def get_remote_pi_capture_logs():
    """Get logs from remote Pi Capture devices via rsyslog"""
    try:
        # Get query parameters
        lines = request.args.get('lines', 100, type=int)
        since = request.args.get('since', '1h')
        levels = request.args.get('levels', None)
        search = request.args.get('search', None)
        hostname = request.args.get('hostname', None)  # Filter by specific Pi hostname
        
        # Remote log directory
        remote_log_dir = Path('/var/log/remote')
        logs = []
        
        # Check if directory exists and is readable
        if not remote_log_dir.exists():
            return jsonify({
                'logs': [],
                'total': 0,
                'service': 'pi-capture-remote',
                'hostnames': [],
                'source': 'remote',
                'warning': 'Remote log directory does not exist. Rsyslog may not be configured.'
            })
        
        if not os.access(remote_log_dir, os.R_OK):
            return jsonify({
                'error': 'Permission denied accessing remote log directory',
                'details': f'The web server user cannot read {remote_log_dir}. You may need to add the web server user to the syslog or adm group.',
                'fix': 'sudo usermod -a -G adm $USER (replace $USER with your web server user)'
            }), 500
        
        if remote_log_dir.exists():
            # Get all Pi capture log files from hostname subdirectories
            log_files = list(remote_log_dir.glob('*/pi-capture.log'))
            
            # Filter by hostname if specified
            if hostname:
                log_files = [f for f in log_files if hostname in f.parent.name]
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Parse time filter
            if since:
                since_seconds = {
                    '5m': 300, '15m': 900, '30m': 1800,
                    '1h': 3600, '6h': 21600, '12h': 43200,
                    '24h': 86400, '2d': 172800, '7d': 604800
                }.get(since, 3600)
                
                cutoff_time = datetime.now() - timedelta(seconds=since_seconds)
            else:
                cutoff_time = datetime.now() - timedelta(hours=1)
            
            # Read logs from each file
            for log_file in log_files:
                # Extract hostname from parent directory name
                pi_hostname = log_file.parent.name
                
                try:
                    with open(log_file, 'r') as f:
                        # Read last N lines efficiently
                        file_lines = f.readlines()
                        for line in file_lines[-1000:]:  # Last 1000 lines per file
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Parse syslog format
                            # Example: 2024-01-20T10:30:45.123456+00:00 raspberrypi pi-capture: [OK] Camera initialized
                            match = re.match(r'^(\S+)\s+(\S+)\s+(\S+):\s+(.*)$', line)
                            if match:
                                timestamp_str, host, service, message = match.groups()
                                
                                # Parse timestamp
                                try:
                                    # Handle RFC3339 format
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    
                                    # Skip if outside time range
                                    if timestamp < cutoff_time:
                                        continue
                                        
                                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                                except:
                                    # Fallback to current time if parsing fails
                                    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # Detect log level from message prefix
                                log_level = 'INFO'
                                if message.startswith('[ERROR]') or message.startswith('[FAIL]'):
                                    log_level = 'ERROR'
                                elif message.startswith('[WARNING]'):
                                    log_level = 'WARNING'
                                elif message.startswith('[OK]') or message.startswith('[SUCCESS]'):
                                    log_level = 'SUCCESS'
                                elif message.startswith('[DEBUG]'):
                                    log_level = 'DEBUG'
                                
                                logs.append({
                                    'timestamp': timestamp_str,
                                    'hostname': host,
                                    'service': 'pi-capture',
                                    'level': log_level,
                                    'message': message,
                                    'source': 'remote'
                                })
                            else:
                                # Fallback for non-standard format
                                logs.append({
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'hostname': pi_hostname,
                                    'service': 'pi-capture',
                                    'level': 'INFO',
                                    'message': line,
                                    'source': 'remote'
                                })
                
                except Exception as e:
                    print(f"ERROR: Failed to read log file {log_file}: {e}")
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply level filter if specified
        if levels:
            level_list = [l.strip().upper() for l in levels.split(',')]
            logs = [log for log in logs if log['level'] in level_list]
        
        # Apply search filter if specified
        if search:
            search_lower = search.lower()
            logs = [log for log in logs if search_lower in log['message'].lower()]
        
        # Get unique hostnames
        hostnames = list(set(log['hostname'] for log in logs))
        
        return jsonify({
            'logs': logs[:lines],
            'total': len(logs),
            'service': 'pi-capture-remote',
            'hostnames': hostnames,
            'source': 'remote'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve remote Pi logs',
            'details': str(e)
        }), 500


@log_routes.route('/export', methods=['GET'])
@require_admin
def export_logs():
    """Export logs as a downloadable file"""
    try:
        # Get query parameters
        since = request.args.get('since', '24h')
        service_filter = request.args.get('service', None)
        format_type = request.args.get('format', 'text')  # text or json
        levels = request.args.get('levels', None)
        
        # Convert time format for journalctl
        since_arg = convert_time_format(since)
        
        all_logs = []
        
        # Get logs from services
        services = []
        if not service_filter or service_filter == 'pi-capture':
            services.append(('pi-capture', 'pi-capture.service'))
        if not service_filter or service_filter == 'ai-processor':
            services.append(('ai-processor', 'ai-processor.service'))
        
        for service_name, unit_name in services:
            cmd = [
                'journalctl',
                '-u', unit_name,
                '--since', since_arg,
                '-o', 'json' if format_type == 'json' else 'short',
                '--no-pager'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                if format_type == 'json':
                    logs = parse_journalctl_output(result.stdout, service_name)
                    all_logs.extend(logs)
                else:
                    all_logs.append(f"=== {service_name.upper()} LOGS ===\\n")
                    all_logs.append(result.stdout)
                    all_logs.append("\\n\\n")
        
        if format_type == 'json':
            from flask import Response
            return Response(
                json.dumps(all_logs, indent=2),
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename=birdcam_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                }
            )
        else:
            from flask import Response
            return Response(
                ''.join(all_logs),
                mimetype='text/plain',
                headers={
                    'Content-Disposition': f'attachment; filename=birdcam_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
                }
            )
            
    except Exception as e:
        return jsonify({
            'error': 'Failed to export logs',
            'details': str(e)
        }), 500