#!/usr/bin/env bash
# run_civil_regen.sh — full civil law regen using Fluxion GCP project
# Run from api/ directory: bash run_civil_regen.sh

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/logs/civil_regen_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

export CLOUDSDK_CORE_ACCOUNT="jharboleda1208@gmail.com"
export GOOGLE_CLOUD_PROJECT="project-f3608dc2-59e9-4ff5-95a"
export GEMINI_LINKER_VERTEX_PROJECT="project-f3608dc2-59e9-4ff5-95a"
export GCP_PROJECT="project-f3608dc2-59e9-4ff5-95a"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

TOPICS=(I.C I.D I.E I.F I.G I.H I.I I.J II.A II.B III.A III.B IV.A IV.B V.A V.B V.C VI.A VI.B VI.C VI.D VI.E VI.F VI.G VI.H VI.I VI.J VI.K VII.A VII.B VII.C VII.D VII.E VII.F VIII.A VIII.B IX.A IX.B IX.C IX.D X.A X.B X.C XI.A XI.B XI.C XI.D XI.E XI.F XI.G XII.A XII.B XII.C XII.D)
TOTAL=${#TOPICS[@]}

log "=== Civil law regen: $TOTAL topics from I.C | project: $GOOGLE_CLOUD_PROJECT ==="
log "Log: $LOG"

DONE=0
FAILED=0

for TOPIC in "${TOPICS[@]}"; do
    log "--- [$((DONE+FAILED+1))/$TOTAL] Starting $TOPIC ---"
    python tools/generate_bar_reviewer.py --subject civil --only-sub "$TOPIC" --vertex-project "$GOOGLE_CLOUD_PROJECT" 2>&1 | tee -a "$LOG"
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
