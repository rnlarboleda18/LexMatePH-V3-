"""
get_redigestion_stats.py

Queries the Azure PostgreSQL database to determine the exact progress of the
decadal redigestion campaign, batch by batch, and prints a formatted markdown table.
"""

import os
import json
import psycopg2
import sys
from pathlib import Path
from collections import defaultdict

# Setup paths
_SCRIPTS = Path(__file__).resolve().parent
_WORKSPACE = _SCRIPTS.parent
sys.path.append(str(_WORKSPACE))
sys.path.append(str(_SCRIPTS))
sys.path.append(str(_WORKSPACE / "api"))

import load_local_settings_env
from redigest_flagged_decades import build_batches, load_checkpoint, _CHECKPOINT_PATH

def get_db_connection():
    db_url = os.environ.get("DB_CONNECTION_STRING_AZURE") or os.environ.get("DB_CONNECTION_STRING")
    if not db_url:
        raise ValueError("No database connection string found in environment.")
    return psycopg2.connect(db_url)

def main():
    checkpoint_path = _CHECKPOINT_PATH
    completed_batches = load_checkpoint(checkpoint_path)

    # Find split file
    possible_paths = [
        _WORKSPACE / "scratch" / "decadal_split.json",
        Path("C:/Users/rnlar/.gemini/antigravity/brain/ac8796fd-0d6a-4d86-bb3e-30e75fc2ba03/scratch/decadal_split.json"),
        _SCRIPTS / "decadal_split.json",
    ]
    split_path = None
    for p in possible_paths:
        if p.is_file():
            split_path = p
            break

    if not split_path:
        print(f"Error: decadal_split.json not found.", file=sys.stderr)
        sys.exit(1)

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"Database connection error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading batches from split file: {split_path}")
    print(f"Loading checkpoint from: {checkpoint_path}\n")

    batches = build_batches(split_path, conn)

    # Get a list of all target case IDs and map them to their batches
    id_to_batch = {}
    batch_cases = defaultdict(list)
    for b_name, b_ids in batches:
        for cid in b_ids:
            id_to_batch[cid] = b_name
            batch_cases[b_name].append(cid)

    # Fetch ai_model and updated_at for all target case IDs
    all_target_ids = list(id_to_batch.keys())
    
    # We query in chunks of 5000 to be safe
    chunk_size = 5000
    id_metadata = {}
    
    cur = conn.cursor()
    for i in range(0, len(all_target_ids), chunk_size):
        chunk = all_target_ids[i:i+chunk_size]
        cur.execute("""
            SELECT id, ai_model, updated_at
            FROM sc_decided_cases
            WHERE id = ANY(%s)
        """, (chunk,))
        for cid, model, updated_at in cur.fetchall():
            id_metadata[cid] = (model, updated_at)
    cur.close()
    conn.close()

    # Redigested models are: 'publishers/google/models/gemini-3.5-flash' and 'grok-4-1-fast-reasoning'
    redigested_models = {
        "publishers/google/models/gemini-3.5-flash",
        "grok-4-1-fast-reasoning"
    }

    print("| # | Batch Name | Total Cases | Completed | Pending | Progress | Status |")
    print("|---|------------|-------------|-----------|---------|----------|--------|")

    total_all_cases = 0
    total_all_done = 0
    total_all_pending = 0

    # Let's count and print each batch
    for idx, (b_name, b_ids) in enumerate(batches, 1):
        total_cases = len(b_ids)
        done_cases = 0
        
        for cid in b_ids:
            meta = id_metadata.get(cid)
            if meta:
                model, _ = meta
                if model in redigested_models:
                    done_cases += 1

        pending_cases = total_cases - done_cases
        progress_pct = (done_cases / total_cases * 100) if total_cases > 0 else 0.0
        
        # Status determination
        if b_name in completed_batches:
            status = "Completed"
        elif done_cases == total_cases:
            status = "Completed (Unmarked)"
        elif done_cases > 0:
            status = "In Progress"
        else:
            status = "Pending"

        print(f"| {idx:2d} | `{b_name}` | {total_cases:11,d} | {done_cases:9,d} | {pending_cases:7,d} | {progress_pct:7.1f}% | {status} |")

        total_all_cases += total_cases
        total_all_done += done_cases
        total_all_pending += pending_cases

    overall_pct = (total_all_done / total_all_cases * 100) if total_all_cases > 0 else 0.0
    print("|---|------------|-------------|-----------|---------|----------|--------|")
    print(f"| **TOTAL** | **ALL BATCHES** | **{total_all_cases:,d}** | **{total_all_done:,d}** | **{total_all_pending:,d}** | **{overall_pct:.1f}%** | |")

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
