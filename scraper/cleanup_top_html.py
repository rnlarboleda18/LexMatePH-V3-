import os
from pathlib import Path

def cleanup_top_html(root_dir):
    root_path = Path(root_dir)
    if not root_path.exists():
        print(f"Directory not found: {root_path}")
        return

    deleted_count = 0
    errors = 0

    print(f"Scanning {root_path} for *.html#top.html files...")

    for year_dir in root_path.iterdir():
        if year_dir.is_dir():
            # Process files in year directory
            for file_path in year_dir.glob("*.html#top.html"):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    if deleted_count % 100 == 0:
                        print(f"  Deleted {deleted_count} files...")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
                    errors += 1

    print(f"Cleanup Complete.")
    print(f"Total deleted: {deleted_count}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    SOURCE_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html"
    cleanup_top_html(SOURCE_DIR)
