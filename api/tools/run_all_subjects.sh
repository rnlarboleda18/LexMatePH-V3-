#!/usr/bin/env bash
# run_all_subjects.sh — generate and publish all 6 BAR 2026 subjects sequentially.
# Usage: bash tools/run_all_subjects.sh [--start-from <subject>]
# Subjects: criminal remedial political civil labor commercial

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$(dirname "$SCRIPT_DIR")"
LOG="$SCRIPT_DIR/logs/run_all_subjects_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

cd "$API_DIR"

SUBJECTS=(criminal remedial political civil labor commercial)
START_FROM="${1:-criminal}"

# Fast-forward to requested start subject
skip=1
for s in "${SUBJECTS[@]}"; do
  [[ "$s" == "$START_FROM" ]] && skip=0
  [[ "$skip" -eq 0 ]] && REMAINING+=("$s")
done
REMAINING=("${REMAINING[@]:-${SUBJECTS[@]}}")

log "=== BAR 2026 Generation Pipeline ==="
log "Subjects to run: ${REMAINING[*]}"

for SUBJECT in "${REMAINING[@]}"; do
  log "--- Starting subject: $SUBJECT ---"
  python tools/generate_bar_reviewer.py --subject "$SUBJECT" 2>&1 | tee -a "$LOG"
  EXIT=${PIPESTATUS[0]}
  if [[ $EXIT -ne 0 ]]; then
    log "WARN: $SUBJECT exited with code $EXIT — continuing"
  fi

  log "Publishing $SUBJECT topics..."
  python tools/publish_all_subjects.py 2>&1 | tee -a "$LOG"
  log "--- Done: $SUBJECT ---"
  sleep 10
done

log "=== All subjects complete ==="
