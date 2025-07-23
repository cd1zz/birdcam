"""Utility functions for log parsing and time conversion."""

import json
import re
from datetime import datetime
from typing import Dict, List


def convert_time_format(since: str) -> str:
    """Convert frontend time format to journalctl format."""
    time_map = {
        "5m": "5 minutes ago",
        "15m": "15 minutes ago",
        "30m": "30 minutes ago",
        "1h": "1 hour ago",
        "6h": "6 hours ago",
        "12h": "12 hours ago",
        "24h": "24 hours ago",
        "2d": "2 days ago",
        "7d": "7 days ago",
    }
    return time_map.get(since, since)


def parse_journalctl_output(output: str, service_name: str) -> List[Dict]:
    """Parse journalctl JSON output into structured log entries."""
    logs: List[Dict] = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        try:
            entry = json.loads(line)

            timestamp = entry.get("__REALTIME_TIMESTAMP")
            if timestamp:
                dt = datetime.fromtimestamp(int(timestamp) / 1_000_000)
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = "Unknown"

            message = entry.get("MESSAGE", "")

            priority = entry.get("PRIORITY", 6)
            try:
                priority = int(priority)
            except (ValueError, TypeError):
                priority = 6

            level = "INFO"
            if priority <= 3:
                level = "ERROR"
            elif priority == 4:
                level = "WARNING"
            elif priority == 7:
                level = "DEBUG"

            unit = entry.get("_SYSTEMD_UNIT", "")
            syslog_facility = entry.get("SYSLOG_FACILITY")
            syslog_identifier = entry.get("SYSLOG_IDENTIFIER", "")

            if syslog_identifier == "birdcam.access" or (
                syslog_facility == "128" and "birdcam.access" in message
            ):
                match = re.search(r"birdcam\.access: (.+)", message)
                if match:
                    message = match.group(1)
                level = "ACCESS"

            keywords = ["processing", "YOLO", "detection", "segment"]
            emojis = ["🔄", "✅", "❌", "🎯", "🦅", "📊", "⚙️", "🤖", "📥", "📤"]
            if (
                syslog_identifier == "python"
                or any(e in message for e in emojis)
                or any(k.lower() in message.lower() for k in keywords)
            ):
                lower = message.lower()
                if "❌" in message or "error" in lower or "failed" in lower:
                    level = "ERROR"
                elif "⚠️" in message or "warning" in lower:
                    level = "WARNING"
                else:
                    level = "INFO"

            logs.append(
                {
                    "timestamp": timestamp_str,
                    "level": level,
                    "service": service_name,
                    "unit": unit,
                    "message": message,
                    "syslog_identifier": syslog_identifier,
                }
            )
        except json.JSONDecodeError:
            logs.append(
                {
                    "timestamp": "Unknown",
                    "level": "INFO",
                    "service": service_name,
                    "unit": "",
                    "message": line,
                    "syslog_identifier": "",
                }
            )

    return logs
