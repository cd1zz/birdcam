# Pi Capture to AI Processor Logging Integration Guide

## Current State Analysis

### Pi Capture Logging (UPDATED)
- Now uses bracketed format matching AI Processor style ([OK], [ERROR], etc.)
- Uses new `CaptureLogger` class in `utils/capture_logger.py`
- Logs captured by systemd journal when running as service
- Ready for remote log forwarding via rsyslog

### AI Processor Logging
- Uses print statements with bracketed prefixes ([OK], [ERROR], etc.)
- Has syslog integration for HTTP access logs
- Provides `/api/logs/*` endpoints for log retrieval
- Can display logs in unified web UI

## Integration Strategies

### Option 1: Remote Syslog Forwarding (Recommended)
Forward Pi Capture logs to AI Processor server using syslog protocol.

**Advantages:**
- Real-time log streaming
- Minimal code changes required
- Industry standard approach
- Works with existing systemd setup

**Implementation:**
1. Configure rsyslog on Pi to forward logs
2. Set up rsyslog receiver on AI Processor server
3. Update log routes to include Pi logs

### Option 2: HTTP Log Shipping
Periodically send batched logs via HTTP API.

**Advantages:**
- Works through firewalls
- Can handle intermittent connectivity
- Easy to implement retry logic

**Disadvantages:**
- Not real-time
- Requires new API endpoints
- More complex error handling

### Option 3: Shared Network Storage
Write logs to shared network location accessible by both systems.

**Advantages:**
- Simple implementation
- No network protocols needed

**Disadvantages:**
- Requires shared filesystem
- Not suitable for distributed deployments
- Potential permission issues

## Recommended Implementation (Option 1: Syslog)

### Step 1: Pi Capture Logging Format (COMPLETED)
Pi Capture logging has been updated to use bracketed format:

```python
# utils/capture_logger.py (ALREADY IMPLEMENTED)
from utils.capture_logger import logger

# Example usage:
logger.camera("Camera initialized", camera_id=0, resolution='1920x1080')
logger.ok("Capture started")
logger.error("Failed to sync", filename="video.mp4")
logger.motion("Motion detected", confidence=0.95)
```

All Pi Capture services now use consistent bracketed logging:
- `[SETUP]` - Setup operations
- `[OK]` - Successful operations  
- `[ERROR]` - Errors
- `[WARNING]` - Warnings
- `[CAMERA]` - Camera operations
- `[MOTION]` - Motion detection
- `[VIDEO]` - Video operations
- `[SYNC]` - File synchronization
- `[CAPTURE]` - Capture operations
- `[TRIGGER]` - Cross-camera triggers
- `[LINK]` - Camera linking
- And more...

### Step 2: Configure Syslog on Raspberry Pi

Create `/etc/rsyslog.d/50-pi-capture.conf`:

```bash
# Template for Pi Capture logs
template(name="PiCaptureFormat" type="string"
  string="%timestamp:::date-rfc3339% %hostname% pi-capture: %msg%\n"
)

# Forward Pi Capture logs to AI Processor
if $programname == 'pi-capture' then {
    # Local file (optional)
    action(type="omfile" file="/var/log/pi-capture.log" template="PiCaptureFormat")
    
    # Forward to AI Processor server
    action(type="omfwd" 
           target="AI_PROCESSOR_IP" 
           port="514" 
           protocol="udp"
           template="PiCaptureFormat"
           queue.type="LinkedList"
           queue.filename="pi-capture-fwd"
           action.resumeRetryCount="-1"
           queue.saveOnShutdown="on"
    )
}
```

### Step 3: Configure Syslog Receiver on AI Processor

Create `/etc/rsyslog.d/50-receive-pi-logs.conf`:

```bash
# Enable UDP syslog reception
module(load="imudp")
input(type="imudp" port="514")

# Template for received Pi logs
template(name="PiLogFormat" type="string"
  string="/var/log/remote/pi-capture/%hostname%-%$year%%$month%%$day%.log"
)

# Save Pi Capture logs
if $programname == 'pi-capture' then {
    action(type="omfile" dynaFile="PiLogFormat" createDirs="on")
}
```

### Step 4: Update systemd Service for Syslog

Modify the Pi Capture service to use syslog identifier:

```ini
# /etc/systemd/system/pi-capture.service
[Service]
...
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-capture
```

### Step 5: Update Log API Routes

Add endpoint to retrieve Pi logs on AI Processor:

```python
# web/routes/log_routes.py

@log_bp.route('/api/logs/remote/pi-capture')
@auth_required
def get_remote_pi_logs():
    """Get logs from remote Pi Capture devices"""
    try:
        # Read from remote log directory
        log_dir = Path('/var/log/remote/pi-capture')
        logs = []
        
        if log_dir.exists():
            # Get latest log file
            log_files = sorted(log_dir.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if log_files:
                latest_log = log_files[0]
                with open(latest_log, 'r') as f:
                    for line in f.readlines()[-1000:]:  # Last 1000 lines
                        # Parse syslog format
                        parts = line.strip().split(' ', 4)
                        if len(parts) >= 5:
                            logs.append({
                                'timestamp': parts[0],
                                'hostname': parts[1],
                                'service': parts[2].rstrip(':'),
                                'message': parts[4],
                                'level': _detect_log_level(parts[4])
                            })
        
        return jsonify({'logs': logs, 'source': 'remote'})
        
    except Exception as e:
        print(f"[ERROR] Failed to retrieve remote Pi logs: {e}")
        return jsonify({'error': str(e)}), 500

def _detect_log_level(message):
    """Detect log level from message prefix"""
    if message.startswith('[ERROR]') or message.startswith('[FAIL]'):
        return 'error'
    elif message.startswith('[WARNING]'):
        return 'warning'
    elif message.startswith('[OK]') or message.startswith('[SUCCESS]'):
        return 'success'
    elif message.startswith('[DEBUG]'):
        return 'debug'
    else:
        return 'info'
```

### Step 6: Update Web UI LogViewer

Modify LogViewer to show remote Pi logs:

```typescript
// Add new log source option
const [logSource, setLogSource] = useState<'local' | 'remote'>('local');

// Update API call based on source
const endpoint = logSource === 'remote' 
  ? '/api/logs/remote/pi-capture'
  : `/api/logs/${service}`;
```

## Alternative: HTTP Log Shipping Implementation

If syslog is not feasible, implement HTTP-based log shipping:

```python
# pi_capture/log_shipper.py
import requests
import queue
import threading
import time
from datetime import datetime

class LogShipper:
    def __init__(self, ai_processor_url: str, api_key: str):
        self.url = f"{ai_processor_url}/api/logs/ship"
        self.api_key = api_key
        self.log_queue = queue.Queue(maxsize=1000)
        self.running = False
        
    def start(self):
        """Start background thread for log shipping"""
        self.running = True
        shipper_thread = threading.Thread(target=self._ship_logs, daemon=True)
        shipper_thread.start()
        
    def log(self, level: str, message: str, **kwargs):
        """Add log to shipping queue"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            'service': 'pi-capture',
            'host': socket.gethostname(),
            **kwargs
        }
        
        try:
            self.log_queue.put_nowait(log_entry)
        except queue.Full:
            # Drop oldest log if queue is full
            self.log_queue.get()
            self.log_queue.put_nowait(log_entry)
            
    def _ship_logs(self):
        """Background thread to ship logs"""
        batch = []
        
        while self.running:
            try:
                # Collect logs for batching
                timeout = 5.0 if batch else None
                log = self.log_queue.get(timeout=timeout)
                batch.append(log)
                
                # Ship when batch is full or timeout
                if len(batch) >= 100:
                    self._send_batch(batch)
                    batch = []
                    
            except queue.Empty:
                # Timeout - ship whatever we have
                if batch:
                    self._send_batch(batch)
                    batch = []
                    
    def _send_batch(self, batch):
        """Send log batch to AI Processor"""
        try:
            response = requests.post(
                self.url,
                json={'logs': batch},
                headers={'X-API-Key': self.api_key},
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[ERROR] Failed to ship logs: {e}")
```

## Testing the Integration

1. **Test Syslog Forwarding:**
   ```bash
   # On Pi
   logger -t pi-capture "[TEST] Syslog forwarding test"
   
   # On AI Processor
   tail -f /var/log/remote/pi-capture/*.log
   ```

2. **Verify Web UI Display:**
   - Access AI Processor web UI
   - Navigate to System Logs
   - Select "Remote Pi Logs" source
   - Verify logs appear correctly

3. **Monitor Network Traffic:**
   ```bash
   tcpdump -i any -n port 514
   ```

## Security Considerations

1. **Syslog Security:**
   - Use TLS for syslog if sensitive data
   - Configure firewall rules for port 514
   - Consider using RELP for reliable delivery

2. **HTTP Security:**
   - Always use HTTPS for log shipping
   - Implement API key rotation
   - Rate limit log endpoints

3. **Access Control:**
   - Limit who can view remote logs
   - Implement log retention policies
   - Consider log anonymization

## Maintenance

1. **Log Rotation:**
   ```bash
   # /etc/logrotate.d/pi-capture-remote
   /var/log/remote/pi-capture/*.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
   }
   ```

2. **Monitoring:**
   - Set up alerts for log forwarding failures
   - Monitor disk usage on AI Processor
   - Track log shipping metrics

3. **Troubleshooting:**
   - Check rsyslog status: `systemctl status rsyslog`
   - Verify network connectivity
   - Review rsyslog error logs