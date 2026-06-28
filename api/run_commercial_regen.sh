#!/usr/bin/env bash
# run_commercial_regen.sh — full commercial law regen using Fluxion GCP project
# Run from api/ directory: bash run_commercial_regen.sh

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/logs/commercial_regen_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

export CLOUDSDK_CORE_ACCOUNT="lumindalori@gmail.com"
export GOOGLE_CLOUD_PROJECT="project-0c3350f3-e867-449e-8f7"
export GEMINI_LINKER_VERTEX_PROJECT="project-0c3350f3-e867-449e-8f7"
export GCP_PROJECT="project-0c3350f3-e867-449e-8f7"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

TOPICS=(I.A I.B II.A II.B II.C II.D II.E II.F II.G II.H II.I II.J II.K II.L III.A III.B III.C IV.A IV.B IV.C IV.D IV.E V.A V.B V.C VI.A VI.B VI.C VI.D VIII.A VIII.B VIII.C VIII.D)
TOTAL=${#TOPICS[@]}

log "=== Commercial law regen: $TOTAL topics | project: $GOOGLE_CLOUD_PROJECT ==="
log "Log: $LOG"

DONE=0
FAILED=0

for TOPIC in "${TOPICS[@]}"; do
    log "--- [$((DONE+FAILED+1))/$TOTAL] Starting $TOPIC ---"
    python tools/generate_bar_reviewer.py --subject commercial --only-sub "$TOPIC" --vertex-project "$GOOGLE_CLOUD_PROJECT" 2>&1 | tee -a "$LOG"
    EXIT=${PIPESTATUS[0]}
    if [[ $EXIT -ne 0 ]]; then
        log "WARN: $TOPIC exited $EXIT — continuing"
        ((FAILED++)) || true
    else
        ((DONE++)) || true
    fi
    log "--- Done: $TOPIC (ok=$DONE failed=$FAILED remaining=$((TOTAL-DONE-FAILED))) ---"
    sleep 5
done

log "=== ALL DONE: $DONE published, $FAILED failed ==="
