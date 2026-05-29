#!/usr/bin/env bash
# run_criminal_regen.sh — regenerate criminal law using Fluxion GCP project
# Run from api/ directory: bash run_criminal_regen.sh

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/logs/criminal_regen_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

export CLOUDSDK_CORE_ACCOUNT="fluxiontechinc@gmail.com"
export GOOGLE_CLOUD_PROJECT="arcane-mason-497813-s6"
export GEMINI_LINKER_VERTEX_PROJECT="arcane-mason-497813-s6"
export GCP_PROJECT="arcane-mason-497813-s6"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

TOPICS=(I.A I.B I.C I.D I.E II.A II.B II.C II.D II.E III.A III.B III.C III.D III.E III.F III.G III.H III.I III.J III.K III.L III.M III.N)
TOTAL=${#TOPICS[@]}

log "=== Criminal law regen: $TOTAL topics | project: $GOOGLE_CLOUD_PROJECT ==="
log "Log: $LOG"

DONE=0
FAILED=0

for TOPIC in "${TOPICS[@]}"; do
    log "--- [$((DONE+FAILED+1))/$TOTAL] Starting $TOPIC ---"
    python tools/generate_bar_reviewer.py --subject criminal --only-sub "$TOPIC" 2>&1 | tee -a "$LOG"
    EXIT=${PIPESTATUS[0]}
    if [[ $EXIT -ne 0 ]]; then
        log "WARN: $TOPIC exited $EXIT"
        ((FAILED++)) || true
    else
        ((DONE++)) || true
    fi
    log "--- Done: $TOPIC (ok=$DONE failed=$FAILED remaining=$((TOTAL-DONE-FAILED))) ---"
    sleep 5
done

log "=== ALL DONE: $DONE published, $FAILED failed ==="
