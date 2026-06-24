#!/usr/bin/env bash
# run_fails_regen.sh — regen only FAIL topics from all subjects
# Run from api/ directory: bash run_fails_regen.sh

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/logs/fails_regen_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

export CLOUDSDK_CORE_ACCOUNT="jharboleda1208@gmail.com"
export GOOGLE_CLOUD_PROJECT="project-f3608dc2-59e9-4ff5-95a"
export GEMINI_LINKER_VERTEX_PROJECT="project-f3608dc2-59e9-4ff5-95a"
export GCP_PROJECT="project-f3608dc2-59e9-4ff5-95a"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# subject:topic pairs — FAILs only
TOPICS=(
    "criminal:III.J"
    "civil:II.B"
    "civil:V.B"
    "civil:IX.D"
    "commercial:VIII.B"
    "commercial:VIII.D"
    "political:VIII.E"
    "political:VIII.G"
    "political:XI.L"
    "labor:IV.C"
    "labor:IV.F"
    "labor:VII.D"
)
TOTAL=${#TOPICS[@]}

log "=== FAIL topics regen: $TOTAL topics | project: $GOOGLE_CLOUD_PROJECT ==="
log "Log: $LOG"

DONE=0
FAILED=0

for ENTRY in "${TOPICS[@]}"; do
    SUBJECT="${ENTRY%%:*}"
    TOPIC="${ENTRY##*:}"
    log "--- [$((DONE+FAILED+1))/$TOTAL] $SUBJECT / $TOPIC ---"
    python tools/generate_bar_reviewer.py --subject "$SUBJECT" --only-sub "$TOPIC" --vertex-project "$GOOGLE_CLOUD_PROJECT" 2>&1 | tee -a "$LOG"
    EXIT=${PIPESTATUS[0]}
    if [[ $EXIT -ne 0 ]]; then
        log "WARN: $SUBJECT/$TOPIC exited $EXIT — continuing"
        ((FAILED++)) || true
    else
        ((DONE++)) || true
    fi
    log "--- Done: $SUBJECT/$TOPIC (ok=$DONE failed=$FAILED remaining=$((TOTAL-DONE-FAILED))) ---"
    sleep 5
done

log "=== ALL DONE: $DONE published, $FAILED failed ==="
