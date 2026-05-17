#!/usr/bin/env bash
# Bar 2026 — sequential generation in specified order
# Subjects run one at a time; each writes its own log file.
set -e
cd "$(dirname "$0")"
PYTHON=".venv/Scripts/python.exe"
SCRIPT="tools/generate_bar_reviewer.py"
LOGDIR="logs"

run_subject() {
    local subj="$1"
    local logfile="$LOGDIR/bar_gen_${subj}.log"
    echo ""
    echo "========================================================"
    echo "Starting: $subj  ($(date '+%Y-%m-%d %H:%M:%S'))"
    echo "Log: $logfile"
    echo "========================================================"
    "$PYTHON" "$SCRIPT" --subject "$subj" 2>&1 | tee "$logfile"
    echo "Done: $subj  ($(date '+%Y-%m-%d %H:%M:%S'))"
}

# Run in specified order
run_subject remedial
run_subject criminal
run_subject civil
run_subject labor
run_subject commercial
run_subject political

echo ""
echo "All subjects complete. Review admin panel to publish drafts."
