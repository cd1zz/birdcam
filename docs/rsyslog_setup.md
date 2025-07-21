# Rsyslog Setup for Remote Log Forwarding

This guide shows how to properly forward logs from Pi Capture systems to the AI Processor using rsyslog.

## Why Use Rsyslog?

- **Built into Linux** - No custom code needed
- **Reliable** - Handles network failures, buffering, and retries automatically
- **Efficient** - Uses standard syslog protocol
- **Secure** - Can use TLS encryption if needed
- **Standard** - Works with any log aggregation system

## Setup Instructions

### On the Raspberry Pi (Log Sender)

1. Copy the rsyslog configuration:
   ```bash
   sudo cp /home/pi/birdcam/config/rsyslog/pi-capture.conf /etc/rsyslog.d/50-pi-capture.conf
   ```

2. Edit the configuration to set your AI Processor IP:
   ```bash
   sudo nano /etc/rsyslog.d/50-pi-capture.conf
   # Replace AI_PROCESSOR_IP with your actual IP address
   ```

3. Restart rsyslog:
   ```bash
   sudo systemctl restart rsyslog
   ```

### On the AI Processor (Log Receiver)

1. Copy the rsyslog configuration:
   ```bash
   sudo cp /home/craig/birdcam/config/rsyslog/ai-processor.conf /etc/rsyslog.d/50-ai-processor.conf
   ```

2. Create log directory:
   ```bash
   sudo mkdir -p /var/log/remote
   sudo chown syslog:adm /var/log/remote
   ```

3. Open firewall port (if using UFW):
   ```bash
   sudo ufw allow 514/udp
   sudo ufw allow 514/tcp  # Optional for TCP
   ```

4. Restart rsyslog:
   ```bash
   sudo systemctl restart rsyslog
   ```

## Viewing Remote Logs

### On the AI Processor

Remote logs are stored in `/var/log/remote/[hostname]/pi-capture.log`:

```bash
# View remote Pi logs
sudo tail -f /var/log/remote/*/pi-capture.log

# View all logs including remote ones in journal
sudo journalctl -f

# Filter for specific Pi hostname
sudo journalctl -f _HOSTNAME=raspberrypi
```

### Using the Web UI

The existing log viewer at `/logs` will automatically show remote Pi logs if they're being forwarded to the journal.

## Testing the Setup

### On the Pi:
```bash
# Test sending a log message
logger -t pi-capture "Test message from Pi"

# Check if rsyslog is forwarding
sudo tail -f /var/log/syslog | grep pi-capture
```

### On the AI Processor:
```bash
# Check if receiving logs
sudo tail -f /var/log/remote/*/pi-capture.log
```

## Advanced Configuration

### Use TCP Instead of UDP (More Reliable)

On Pi, change the forwarding action:
```
action(type="omfwd" 
       target="AI_PROCESSOR_IP" 
       port="514" 
       protocol="tcp"  # Changed from udp
       ...)
```

### Forward All Logs

To forward all logs from the Pi (not just pi-capture):
```
# In pi-capture.conf, add:
*.* @@AI_PROCESSOR_IP:514  # @@ for TCP, @ for UDP
```

### Add Encryption (TLS)

For secure log transmission over untrusted networks:

1. Generate certificates on both systems
2. Configure rsyslog to use TLS:
   ```
   # Load TLS driver
   module(load="imtcp" StreamDriver.Name="gtls" StreamDriver.Mode="1")
   
   # Configure certificates
   global(
     DefaultNetstreamDriverCAFile="/etc/rsyslog.d/ca.pem"
     DefaultNetstreamDriverCertFile="/etc/rsyslog.d/cert.pem"
     DefaultNetstreamDriverKeyFile="/etc/rsyslog.d/key.pem"
   )
   ```

## Troubleshooting

### Logs Not Appearing

1. Check rsyslog status:
   ```bash
   sudo systemctl status rsyslog
   ```

2. Check for errors:
   ```bash
   sudo journalctl -u rsyslog -e
   ```

3. Test connectivity:
   ```bash
   # From Pi
   nc -vz AI_PROCESSOR_IP 514
   ```

4. Check firewall:
   ```bash
   # On AI Processor
   sudo ufw status
   sudo iptables -L -n | grep 514
   ```

### Performance Tuning

The configuration includes:
- **Queue buffering** - Stores up to 10,000 messages if network is down
- **Disk spooling** - Saves unsent logs to disk (up to 100MB)
- **Automatic retry** - Retries every 30 seconds indefinitely

### Log Rotation

Configure logrotate for remote logs:

```bash
# Create /etc/logrotate.d/remote-logs
/var/log/remote/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 syslog adm
    sharedscripts
    postrotate
        /usr/bin/killall -HUP rsyslogd
    endscript
}
```

## Benefits Over Custom Solution

1. **No code maintenance** - Uses standard Linux tools
2. **Battle-tested** - Rsyslog handles edge cases automatically
3. **Better performance** - Native C implementation
4. **Flexibility** - Easy to add filters, transformations, or additional destinations
5. **Integration** - Works with Elasticsearch, Splunk, Graylog, etc.