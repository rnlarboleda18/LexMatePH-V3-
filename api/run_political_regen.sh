#!/usr/bin/env bash
# run_political_regen.sh — full political law regen using Fluxion GCP project
# Run from api/ directory: bash run_political_regen.sh

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/logs/political_regen_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

export CLOUDSDK_CORE_ACCOUNT="jharboleda1208@gmail.com"
export GOOGLE_CLOUD_PROJECT="project-f3608dc2-59e9-4ff5-95a"
export GEMINI_LINKER_VERTEX_PROJECT="project-f3608dc2-59e9-4ff5-95a"
export GCP_PROJECT="project-f3608dc2-59e9-4ff5-95a"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

TOPICS=(I.A I.B I.C I.D I.E I.F I.G I.H I.I II.A II.B II.C III.A III.B III.C III.D III.E IV.A IV.B IV.C IV.D IV.E IV.F IV.G IV.H V.A V.B V.C V.D VI.A VI.B VI.C VI.D VI.E VII.A VII.B VII.C VII.D VII.E VIII.A VIII.B VIII.C VIII.D VIII.E VIII.F VIII.G VIII.H VIII.I VIII.J VIII.K VIII.L VIII.M VIII.N VIII.O VIII.P VIII.Q VIII.R VIII.S VIII.T VIII.U VIII.V VIII.W VIII.X IX.A IX.B IX.C IX.D IX.E IX.F X.A X.B X.C X.D XI.A XI.B XI.C XI.D XI.E XI.F XI.G XI.H XI.I XI.J XI.K XI.L XII.A XII.B XII.C XII.D XII.E XII.F XIII.A XIII.B XIII.C XIII.D XIII.E XIV.A XIV.B XIV.C XIV.D XIV.E XIV.F XIV.G XIV.H XIV.I XIV.J XIV.K XIV.L XIV.M)
TOTAL=${#TOPICS[@]}

log "=== Political law regen: $TOTAL topics | project: $GOOGLE_CLOUD_PROJECT ==="
log "Log: $LOG"

DONE=0
FAILED=0

for TOPIC in "${TOPICS[@]}"; do
    log "--- [$((DONE+FAILED+1))/$TOTAL] Starting $TOPIC ---"
    python tools/generate_bar_reviewer.py --subject political --only-sub "$TOPIC" --vertex-project "$GOOGLE_CLOUD_PROJECT" 2>&1 | tee -a "$LOG"
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
