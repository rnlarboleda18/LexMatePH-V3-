#!/usr/bin/env bash
# run_remedial_resume.sh — continue remedial generation from III.O onwards
# Run from api/ directory: bash run_remedial_resume.sh

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/logs/remedial_regen_resume_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

export CLOUDSDK_CORE_ACCOUNT="rnlarboleda8@gmail.com"
export GOOGLE_CLOUD_PROJECT="gen-lang-client-0813708151"
export GEMINI_LINKER_VERTEX_PROJECT="gen-lang-client-0813708151"
export GCP_PROJECT="gen-lang-client-0813708151"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

TOPICS=(III.O III.P III.Q III.R III.S III.T IV.A IV.B IV.C IV.D IV.E IV.F IV.G V.A V.B V.C V.D V.E V.F V.G V.H V.I V.J VI.A VI.B VI.C VI.D VI.E VI.F VI.G VI.H VI.I VI.J VII.A VII.B VII.C VII.D VII.E VII.F VII.G VII.H VII.I VII.J VII.K VII.L VII.M VII.N VII.O VII.P VII.Q VIII.A VIII.B VIII.C VIII.D VIII.E VIII.F VIII.G VIII.H VIII.I VIII.J VIII.K IX.A IX.B X.A X.B X.C X.D X.E X.F X.G X.H X.I X.J X.K X.L)
TOTAL=${#TOPICS[@]}

log "=== Remedial resume: $TOTAL topics from III.O ==="
log "Log: $LOG"

DONE=0
FAILED=0

for TOPIC in "${TOPICS[@]}"; do
    log "--- [$((DONE+FAILED+1))/$TOTAL] Starting $TOPIC ---"
    python tools/generate_bar_reviewer.py --subject remedial --only-sub "$TOPIC" 2>&1 | tee -a "$LOG"
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
