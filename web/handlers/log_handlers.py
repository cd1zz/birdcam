"""
Log route handlers extracted from web/routes/log_routes.py
These are standalone functions that can be imported by admin_routes.py
"""

from flask import jsonify, request, Response
import subprocess
import json
from datetime import datetime, timedelta
import re
from pathlib import Path
import os
from web.utils.log_utils import convert_time_format, parse_journalctl_output


def get_logs_handler():
    """Get combined logs from both services"""
    try:
        # Get query parameters
        lines = request.args.get("lines", 100, type=int)
        since = request.args.get("since", "1h")
        search = request.args.get("search", None)
        service_filter = request.args.get("service", None)

        # Convert time format for journalctl
        since_arg = convert_time_format(since)

        all_logs = []

        # Get logs from both services
        for service_name, unit_name in [
            ("pi-capture", "pi-capture.service"),
            ("ai-processor", "ai-processor.service"),
        ]:
            if service_filter and service_filter != service_name:
                continue

            cmd = [
                "journalctl",
                "-u",
                unit_name,
                "-n",
                str(lines),
                "--since",
                since_arg,
                "-o",
                "json",
                "--no-pager",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logs = parse_journalctl_output(result.stdout, service_name)
                all_logs.extend(logs)

        # Sort by timestamp
        all_logs.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply level filter if specified

        # Apply search filter if specified
        if search:
            search_lower = search.lower()
            all_logs = [
                log for log in all_logs if search_lower in log["message"].lower()
            ]

        return jsonify({"logs": all_logs[:lines], "total": len(all_logs)})

    except Exception as e:
        return jsonify({"error": "Failed to retrieve logs", "details": str(e)}), 500


def get_log_files_handler():
    """Get list of available log files"""
    try:
        log_files = []

        # Check for systemd journal logs
        services = ["pi-capture.service", "ai-processor.service"]
        for service in services:
            # Check if service logs exist
            cmd = ["journalctl", "-u", service, "-n", "1", "--no-pager"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                log_files.append(
                    {
                        "filename": service,
                        "service": service.replace(".service", ""),
                        "type": "systemd",
                        "size": "N/A",
                        "modified": datetime.now().isoformat(),
                    }
                )

        # Check for remote log files
        remote_log_dir = Path("/var/log/remote")
        if remote_log_dir.exists() and os.access(remote_log_dir, os.R_OK):
            for log_file in remote_log_dir.glob("*/pi-capture.log"):
                stat = log_file.stat()
                log_files.append(
                    {
                        "filename": str(log_file.relative_to(remote_log_dir)),
                        "service": "pi-capture-remote",
                        "hostname": log_file.parent.name,
                        "type": "file",
                        "size": f"{stat.st_size / 1024:.1f} KB",
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

        return jsonify({"files": log_files, "total": len(log_files)})

    except Exception as e:
        return jsonify({"error": "Failed to list log files", "details": str(e)}), 500


def get_capture_logs_handler():
    """Get recent logs from all capture services (including remote)"""
    try:
        # Get query parameters
        lines = request.args.get("lines", 100, type=int)
        since = request.args.get("since", "1h")
        levels = request.args.get("levels", None)
        search = request.args.get("search", None)
        hostname = request.args.get("hostname", None)

        all_logs = []

        # Get local pi-capture logs
        since_arg = convert_time_format(since)
        cmd = [
            "journalctl",
            "-u",
            "pi-capture.service",
            "-n",
            str(lines),
            "--since",
            since_arg,
            "-o",
            "json",
            "--no-pager",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logs = parse_journalctl_output(result.stdout, "pi-capture")
            # Add hostname for local logs
            local_hostname = subprocess.run(
                ["hostname"], capture_output=True, text=True
            ).stdout.strip()
            for log in logs:
                log["hostname"] = local_hostname
                log["source"] = "local"
            all_logs.extend(logs)

        # Get remote pi-capture logs
        remote_log_dir = Path("/var/log/remote")
        if remote_log_dir.exists() and os.access(remote_log_dir, os.R_OK):
            # Parse time filter
            if since:
                since_seconds = {
                    "5m": 300,
                    "15m": 900,
                    "30m": 1800,
                    "1h": 3600,
                    "6h": 21600,
                    "12h": 43200,
                    "24h": 86400,
                    "2d": 172800,
                    "7d": 604800,
                }.get(since, 3600)
                cutoff_time = datetime.now() - timedelta(seconds=since_seconds)
            else:
                cutoff_time = datetime.now() - timedelta(hours=1)

            # Read logs from each remote host
            for log_file in remote_log_dir.glob("*/pi-capture.log"):
                pi_hostname = log_file.parent.name

                # Filter by hostname if specified
                if hostname and hostname != pi_hostname:
                    continue

                try:
                    with open(log_file, "r") as f:
                        file_lines = f.readlines()
                        for line in file_lines[-1000:]:  # Last 1000 lines per file
                            line = line.strip()
                            if not line:
                                continue

                            # Parse syslog format
                            match = re.match(r"^(\S+)\s+(\S+)\s+(\S+):\s+(.*)$", line)
                            if match:
                                timestamp_str, host, service, message = match.groups()

                                # Parse timestamp
                                try:
                                    timestamp = datetime.fromisoformat(
                                        timestamp_str.replace("Z", "+00:00")
                                    )
                                    if timestamp < cutoff_time:
                                        continue
                                    timestamp_str = timestamp.strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    )
                                except Exception:
                                    timestamp_str = datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    )

                                # Detect log level
                                log_level = "INFO"
                                if message.startswith("[ERROR]") or message.startswith(
                                    "[FAIL]"
                                ):
                                    log_level = "ERROR"
                                elif message.startswith("[WARNING]"):
                                    log_level = "WARNING"
                                elif message.startswith("[OK]") or message.startswith(
                                    "[SUCCESS]"
                                ):
                                    log_level = "SUCCESS"
                                elif message.startswith("[DEBUG]"):
                                    log_level = "DEBUG"

                                all_logs.append(
                                    {
                                        "timestamp": timestamp_str,
                                        "hostname": host,
                                        "service": "pi-capture",
                                        "level": log_level,
                                        "message": message,
                                        "source": "remote",
                                    }
                                )
                except Exception as e:
                    print(f"ERROR: Failed to read log file {log_file}: {e}")

        # Sort by timestamp
        all_logs.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply filters
        if levels:
            level_list = [lvl.strip().upper() for lvl in levels.split(",")]
            all_logs = [log for log in all_logs if log["level"] in level_list]

        if search:
            search_lower = search.lower()
            all_logs = [
                log for log in all_logs if search_lower in log["message"].lower()
            ]

        # Get unique hostnames
        hostnames = list(set(log.get("hostname", "unknown") for log in all_logs))

        return jsonify(
            {"logs": all_logs[:lines], "total": len(all_logs), "hostnames": hostnames}
        )

    except Exception as e:
        return (
            jsonify({"error": "Failed to retrieve capture logs", "details": str(e)}),
            500,
        )


def download_logs_handler(filename):
    """Export/download logs as a file"""
    try:
        # Parse filename to determine what logs to export
        # Format: service_YYYYMMDD_HHMMSS.txt or service_YYYYMMDD_HHMMSS.json
        format_type = "json" if filename.endswith(".json") else "text"

        # Get query parameters
        since = request.args.get("since", "24h")
        service_filter = request.args.get("service", None)

        # Convert time format for journalctl
        since_arg = convert_time_format(since)

        all_logs = []

        # Get logs from services
        services = []
        if not service_filter or service_filter == "pi-capture":
            services.append(("pi-capture", "pi-capture.service"))
        if not service_filter or service_filter == "ai-processor":
            services.append(("ai-processor", "ai-processor.service"))

        for service_name, unit_name in services:
            cmd = [
                "journalctl",
                "-u",
                unit_name,
                "--since",
                since_arg,
                "-o",
                "json" if format_type == "json" else "short",
                "--no-pager",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                if format_type == "json":
                    logs = parse_journalctl_output(result.stdout, service_name)
                    all_logs.extend(logs)
                else:
                    all_logs.append(f"=== {service_name.upper()} LOGS ===\n")
                    all_logs.append(result.stdout)
                    all_logs.append("\n\n")

        if format_type == "json":
            return Response(
                json.dumps(all_logs, indent=2),
                mimetype="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        else:
            return Response(
                "".join(all_logs),
                mimetype="text/plain",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

    except Exception as e:
        return jsonify({"error": "Failed to export logs", "details": str(e)}), 500


def clear_logs_handler():
    """Clear log files (admin only)"""
    try:
        data = request.get_json()
        service = data.get("service") if data else None

        cleared = []
        errors = []

        # For systemd services, we can't clear the journal directly
        # But we can rotate it
        if not service or service in ["pi-capture", "ai-processor"]:
            # Vacuum journal to keep only recent entries
            cmd = ["sudo", "journalctl", "--vacuum-time=1h"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                cleared.append("systemd journal (keeping last hour)")
            else:
                errors.append(f"Failed to vacuum journal: {result.stderr}")

        # Clear remote log files if requested
        if not service or service == "pi-capture-remote":
            remote_log_dir = Path("/var/log/remote")
            if remote_log_dir.exists() and os.access(remote_log_dir, os.W_OK):
                for log_file in remote_log_dir.glob("*/pi-capture.log"):
                    try:
                        # Truncate file instead of deleting
                        with open(log_file, "w") as f:
                            f.write("")
                        cleared.append(str(log_file))
                    except Exception as e:
                        errors.append(f"Failed to clear {log_file}: {str(e)}")
            else:
                errors.append("No write access to remote log directory")

        if errors:
            return (
                jsonify(
                    {
                        "message": "Partially cleared logs",
                        "cleared": cleared,
                        "errors": errors,
                    }
                ),
                207,
            )  # Multi-status

        return jsonify({"message": "Logs cleared successfully", "cleared": cleared})

    except Exception as e:
        return jsonify({"error": "Failed to clear logs", "details": str(e)}), 500
