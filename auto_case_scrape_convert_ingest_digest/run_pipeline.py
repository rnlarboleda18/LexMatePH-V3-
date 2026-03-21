import os
import subprocess
import logging
import time

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data"
HTML_DIR = os.path.join(DATA_DIR, "lawphil_html") 
MD_DIR = os.path.join(DATA_DIR, "lawphil_md")

TARGET_CASES = [
    "Jaka Food v. Pacot (G.R. No. 151358, Mar 28, 2005)",
    "People v. Orit (G.R. No. 120967, July 5, 1997)",
    "Geminis v. People (G.R. No. 118431, Oct 23, 1996)",
    "Intod v. CA (G.R. No. 103119, Oct 21, 1992)",
    "Leria v. People (G.R. No. 256828, Oct 11, 2023)",
    "Togado v. People (G.R. No. 260973, Aug 6, 2024)",
    "CPRA (A.M. No. 22-09-01-SC, Apr 11, 2023)",
    "People v. Webb (G.R. No. 176864, Dec 14, 2010)",
    "Burbe v. Magulta (A.C. No. 99-634, June 10, 2002)",
    "Biaquillo v. CA (G.R. No. 129277, Sep 30, 1999)"
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def run_step(script_name, description, env=None):
    logging.info(f"\n{'='*50}\nSTARTING STEP: {description}\n{'='*50}")
    script_path = os.path.join(BASE_DIR, script_name)
    
    # Merge current env with passed env
    active_env = os.environ.copy()
    if env:
        active_env.update(env)
        
    try:
        subprocess.run(["python", script_path], check=True, env=active_env)
        logging.info(f"✅ STEP COMPLETED: {description}")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ STEP FAILED: {description} (Error code: {e.returncode})")
        exit(1)

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto", help="Pipeline mode: 'auto' runs full pipeline, 'manual' stops after conversion.")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping step")
    parser.add_argument("--skip-convert", action="store_true", help="Skip conversion step")
    args = parser.parse_args()

    # 0. Prepare Target List
    target_file = os.path.join(BASE_DIR, "target_list.txt")
    with open(target_file, "w") as f:
        for case in TARGET_CASES:
            f.write(case + "\n")
    logging.info(f"Generated target list with {len(TARGET_CASES)} cases.")

    # 1. SCRAPE
    if not args.skip_scrape:
        run_step("crawler.py", "Scraping HTML Files")
    else:
        logging.info("⏭️ SKIPPING SCRAPE")

    # 2. CONVERT
    if not args.skip_convert:
        # Pass explicit paths to the converter
        run_step("converter.py", "Converting HTML to Markdown", env={
            "DOWNLOADS_DIR": HTML_DIR,
            "OUTPUT_DIR": MD_DIR
        })
    else:
        logging.info("⏭️ SKIPPING CONVERT")

    if args.mode == "manual":
        logging.info("\n🛑 MANUAL MODE: Stopping pipeline for review. Visit the Web Dashboard to examine files.")
        logging.info("Run ingestion manually via the dashboard when ready.")
        return

    # 3. INGEST
    run_step("ingester.py", "Ingesting Metadata to Postgres")

    # 4. DIGEST
    run_step("digester.py", "Generating AI Digests")

    logging.info("\n🎉 PIPELINE COMPLETE! All cases processed.")

if __name__ == "__main__":
    main()
