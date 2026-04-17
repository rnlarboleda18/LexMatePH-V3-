import sys
import os
import re
import argparse
from pathlib import Path

# Fix paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "api"))

from process_amendment_full_ai import process_amendment_full_ai

def ingest_by_section(md_file, code_short_name="RPC", chunk_size=5):
    print(f"Reading large file: {md_file}")
    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the header (everything before the first Section 1.)
    header_match = re.search(r"^(.*?)(?=\*\*Section 1\.\*\*)", content, re.DOTALL | re.MULTILINE)
    header = header_match.group(1) if header_match else "---"
    
    # Split by Section markers
    sections = re.split(r"(?=\*\*Section \d+\.\*\*)", content[len(header):])
    sections = [s.strip() for s in sections if s.strip()]
    
    print(f"Detected {len(sections)} sections.")
    
    # Process in chunks
    for i in range(0, len(sections), chunk_size):
        chunk = sections[i:i + chunk_size]
        chunk_text = header + "\n\n" + "\n\n".join(chunk)
        
        # Save temporary chunk file
        temp_file = Path(md_file).parent / f"temp_chunk_{i}.md"
        with open(temp_file, "w", encoding="utf-8") as tf:
            tf.write(chunk_text)
            
        print(f"\n--- Processing Chunk {i//chunk_size + 1} (Sections {i+1} to {min(i+chunk_size, len(sections))}) ---")
        try:
            process_amendment_full_ai(str(temp_file), code_short_name=code_short_name)
        except Exception as e:
            print(f"Error in chunk {i}: {e}")
        finally:
            if temp_file.exists():
                os.remove(temp_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--code", default="RPC")
    parser.add_argument("--chunk-size", type=int, default=5)
    args = parser.parse_args()
    
    ingest_by_section(args.file, args.code, args.chunk_size)
