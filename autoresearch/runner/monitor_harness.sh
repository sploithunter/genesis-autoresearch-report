#!/bin/bash
# Monitor harness-bench tmux sessions — live log capture + interaction handler
# Called by the autoresearch loop to babysit running benchmark tasks
#
# Usage: ./monitor_harness.sh [--full] [--struggles]
#   --full      Capture full pane history (last 500 lines) to live log file
#   --struggles Extract and report agent struggles from the live log

MODE="${1:---status}"
LIVE_LOG_DIR="/Users/jason/Documents/Genesis_rc1/Genesis_LIB/autoresearch/results/live_logs"
mkdir -p "$LIVE_LOG_DIR"

# Find all harness-bench tmux sessions
sessions=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep '^harness-bench-' || true)

if [ -z "$sessions" ]; then
    echo '{"active_sessions": 0, "status": "no_sessions"}'
    exit 0
fi

for session in $sessions; do
    # Always check for interactive prompts first
    pane=$(tmux capture-pane -t "$session" -p -S -30 2>/dev/null || echo "")

    # Auto-accept trust dialog
    if echo "$pane" | grep -q "Yes, I trust this folder"; then
        echo "TRUST_DIALOG detected in $session - sending Enter to accept"
        tmux send-keys -t "$session" Enter 2>/dev/null
    fi

    # Auto-accept confirmation prompts
    if echo "$pane" | grep -q "Enter to confirm"; then
        echo "CONFIRM_PROMPT detected in $session - sending Enter"
        tmux send-keys -t "$session" Enter 2>/dev/null
    fi

    if [ "$MODE" = "--full" ] || [ "$MODE" = "--struggles" ]; then
        # Capture full pane history (last 500 lines) to timestamped log
        timestamp=$(date +%Y%m%d_%H%M%S)
        log_file="$LIVE_LOG_DIR/${session}_${timestamp}.log"
        tmux capture-pane -t "$session" -p -S -500 2>/dev/null > "$log_file"
        echo "Live log saved: $log_file ($(wc -l < "$log_file") lines)"

        if [ "$MODE" = "--struggles" ]; then
            # Extract struggles: errors, retries, time spent debugging
            echo "=== STRUGGLES in $session ==="
            grep -n "Error\|ModuleNotFoundError\|ImportError\|Traceback\|not found\|failed\|FAIL\|timeout\|retry\|trying again\|Let me\|instead" "$log_file" 2>/dev/null | head -20
            echo "=== END STRUGGLES ==="
        fi
    fi

    # Report status
    if echo "$pane" | grep -q "Error:"; then
        error_line=$(echo "$pane" | grep "Error:" | tail -1)
        echo "ERROR in $session: $error_line"
    fi

    if echo "$pane" | grep -q "Processing\|thought for\|Reading\|Writing\|Running\|Composing\|Vibing\|Drizzling\|Fluttering"; then
        echo "SESSION $session: Claude is actively working"
    elif echo "$pane" | grep -q "❯"; then
        echo "SESSION $session: Claude is at prompt (idle or waiting)"
    else
        echo "SESSION $session: status unknown"
    fi
done
