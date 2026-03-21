
import subprocess
import os
import sys

# Files to process (excluding Act 4117 as it's superseded by CA 99)
files = [
    "data/CodexPhil/Codals/md/ca_99_1936.md",
    "data/CodexPhil/Codals/md/ca_235_1937.md",
    "data/CodexPhil/Codals/md/ra_12_1946.md",
    "data/CodexPhil/Codals/md/ra_18_1946.md"
]

print("Batch Processing Amendments...")
print("=" * 60)

for file_path in files:
    full_path = os.path.join(os.getcwd(), file_path)
    print(f"\nProcessing: {file_path}")
    
    cmd = [sys.executable, "data/CodexPhil/scripts/process_amendment.py", "--file", full_path]
    
    try:
        # Run synchronously to ensure order and avoid DB lock contention
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Success")
        # Print the summary part of the output
        output_lines = result.stdout.split('\n')
        summary_idx = -1
        for i, line in enumerate(output_lines):
            if "SUMMARY REPORT" in line:
                summary_idx = i - 1
                break
        if summary_idx >= 0:
            print('\n'.join(output_lines[summary_idx:]))
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed: {e}")
        print("Output:", e.stdout)
        print("Error:", e.stderr)

print("\nBatch processing complete.")
