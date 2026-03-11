#!/bin/bash
# Stop all Genesis DDS tool services

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/.service_pids"

if [ -f "$PID_FILE" ]; then
    echo "Stopping Genesis DDS tool services..."
    while read -r pid; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  Stopped PID $pid"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
    echo "All services stopped."
else
    echo "No service PID file found."
fi
