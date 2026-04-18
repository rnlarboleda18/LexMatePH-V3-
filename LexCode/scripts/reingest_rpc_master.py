"""
Master **chronological** RPC re-ingestion: reconstruct legal history in order, not only “current law.”

**Textual fidelity (non-AI layers)** — Order is fixed: ``RPC.md`` baseline (1932) first, then each
file in ``AMENDMENTS`` in sequence. Each step writes ``article_versions`` so the database holds a
**chain of custody** from the original Penal Code through every listed Act (compare versions,
identify which Republic Act changed which sentence, support rollback if a bad artifact is detected).

**Route by source** — Baseline uses ``ingest_baseline_deterministic``; RA 8353 uses ``--amendment-json``
(literal blob); RA 6968 uses ``--offline-ra6968``; others use ``process_amendment`` (parser + merge
as configured). See module docstrings on ``deterministic_lexcode`` and ``process_amendment``.
"""
import subprocess
import sys
import os
from pathlib import Path

# Vertex AI usage is now configured in local.settings.json
# os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
# os.environ["GOOGLE_CLOUD_PROJECT"] = "gen-lang-client-0565960161"
# os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

# Repository Root (Assuming script is in LexCode/scripts/)
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "LexCode" / "scripts"
MD_DIR = REPO_ROOT / "LexCode" / "Codals" / "md"
JSON_SPEC_DIR = REPO_ROOT / "LexCode" / "Codals" / "manual_specs"

# Chronological list of files to ingest
AMENDMENTS = [
    # Baseline Ingestion (Full 1930/1932 Content)
    # Note: RPC.md is a large file; we use --force to ensure cleanup.
    {"file": "RPC.md", "args": []},
    # Historical sequence...
    {"file": "Act No. 3999, December 05, 1932.md", "args": []},
    {"file": "act_4117_1933.md", "args": []},
    {"file": "ca_99_1936.md", "args": []},
    {"file": "ca_235_1937.md", "args": []},
    {"file": "ra_12_1946.md", "args": []},
    {"file": "ra_18_1946.md", "args": []},
    {"file": "ra_47_1946.md", "args": []},
    {"file": "ra_1084_1954.md", "args": []},
    {"file": "ra_2632_1960.md", "args": []},
    {"file": "ra_4661_1966.md", "args": []},
    {"file": "ra_6127_1970.md", "args": []},
    {"file": "pd_603_1974.md", "args": []},
    {"file": "pd_942_1976.md", "args": []},
    {"file": "pd_1179_1977.md", "args": []},
    {"file": "pd_1239_1977.md", "args": []},
    {"file": "pd_1613_1979.md", "args": []},
    {"file": "bp_871_1985.md", "args": []},
    {"file": "eo_272_1987.md", "args": []},
    # RA 6968 (1990) - Coup D'État (Deterministic logic)
    {"file": "ra_6968_1990.md", "args": ["--offline-ra6968"]},
    {"file": "ra_7659_1993.md", "args": []},
    # RA 8353 (1997) - Anti-Rape Law (Manual JSON spec for structural reclassification)
    {"file": "ra_8353_1997.md", "args": ["--amendment-json", str(JSON_SPEC_DIR / "ra_8353_manual_spec.json")]},
    {"file": "ra_9344_2006.md", "args": []},
    {"file": "ra_10158_2012.md", "args": []},
    {"file": "ra_10592_2013.md", "args": []},
    # RA 10951 (2017) - Fine Adjustments (AI Merge Mode)
    {"file": "ra_10951_2017.md", "args": []},
    {"file": "ra_11362_2019.md", "args": []},
    {"file": "ra_11594_2021.md", "args": []},
    {"file": "ra_11648_2022.md", "args": []},
    {"file": "ra_11926_2022.md", "args": []},
]

def run_ingestion():
    print(f"\n{'='*70}")
    print(f"MASTER RPC RE-INGESTION PIPELINE")
    print(f"{'='*70}\n")
    
    process_script = SCRIPTS_DIR / "process_amendment.py"
    
    if not process_script.exists():
        print(f"ERROR: Cannot find {process_script}")
        sys.exit(1)

    for i, item in enumerate(AMENDMENTS, 1):
        filename = item["file"]
        extra_args = item["args"]
        
        filepath = MD_DIR / filename
        if not filepath.exists():
            print(f"[{i}/{len(AMENDMENTS)}] SKIP: {filename} (File not found)")
            continue

        print(f"[{i}/{len(AMENDMENTS)}] INGESTING: {filename}...")
        
        # SPECIAL CASE: Baseline RPC.md uses deterministic ingestion
        if filename == "RPC.md":
            baseline_script = SCRIPTS_DIR / "ingest_baseline_deterministic.py"
            cmd = [sys.executable, str(baseline_script)]
        
        # RA 8353 (1997) - Anti-Rape Law (Manual JSON spec)
        elif "--amendment-json" in extra_args:
            json_idx = extra_args.index("--amendment-json")
            json_path = extra_args[json_idx + 1]
            cmd = [sys.executable, str(process_script), "--amendment-json", json_path, "--force"]
            
        elif "--offline-ra6968" in extra_args:
             cmd = [sys.executable, str(process_script), "--file", str(filepath), "--offline-ra6968", "--force"]

        else:
            # Standard AI-powered amendment ingest
            cmd = [sys.executable, str(process_script), "--file", str(filepath), "--force"]

        # Add any other extra args
        if filename != "RPC.md":
            for arg in extra_args:
                if arg not in cmd and arg != extra_args[extra_args.index("--amendment-json") + 1] if "--amendment-json" in extra_args else True:
                    cmd.append(arg)

        try:
            # We capture output to show it cleaner, or just stream it 
            result = subprocess.run(cmd, check=True, text=True)
            print(f"[{i}/{len(AMENDMENTS)}] SUCCESS: {filename}\n")
        except subprocess.CalledProcessError as e:
            print(f"\n{'!'*70}")
            print(f"CRITICAL FAILURE on {filename}!")
            print(f"Command: {' '.join(cmd)}")
            print(f"{'!'*70}\n")
            sys.exit(1)

    print(f"\n{'='*70}")
    print(f"MASTER INGESTION COMPLETED SUCCESSFULLY")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    run_ingestion()
