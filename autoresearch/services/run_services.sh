#!/bin/bash
# Launch all Genesis DDS tool services on domain 55
# Services run in background; PIDs written to .service_pids for cleanup

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GENESIS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PID_FILE="$SCRIPT_DIR/.service_pids"

# Activate environment
cd "$GENESIS_DIR"
source .venv/bin/activate 2>/dev/null
source .env 2>/dev/null

export PYTHONPATH="$GENESIS_DIR:$PYTHONPATH"

echo "Starting Genesis DDS tool services on domain 55..."
echo "" > "$PID_FILE"

python "$SCRIPT_DIR/dds_reference_service.py" &
echo $! >> "$PID_FILE"
echo "  DDSReferenceService started (PID $!)"

python "$SCRIPT_DIR/dds_pattern_service.py" &
echo $! >> "$PID_FILE"
echo "  DDSPatternService started (PID $!)"

python "$SCRIPT_DIR/dds_diagnostic_service.py" &
echo $! >> "$PID_FILE"
echo "  DDSDiagnosticService started (PID $!)"

echo "All services started. PIDs in $PID_FILE"
echo "Waiting for services to initialize..."
sleep 5
echo "Services ready."
