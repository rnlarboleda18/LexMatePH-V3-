
import os
import csv

CSV_PATH = r"analysis/sc_elib_verification.csv"
MD_DIR = r"data/sc_elib_md"

def main():
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return

    print(f"Reading {CSV_PATH} to identify files to delete...")
    
    files_to_delete = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == 'NO_HEADER':
                files_to_delete.append(row['filename'])

    print(f"Found {len(files_to_delete)} files marked as NO_HEADER.")
    
    deleted_count = 0
    errors = 0
    
    for filename in files_to_delete:
        file_path = os.path.join(MD_DIR, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_count += 1
            else:
                print(f"File not found: {filename}")
        except Exception as e:
            print(f"Error deleting {filename}: {e}")
            errors += 1
            
    print(f"Deleted {deleted_count} files.")
    if errors > 0:
        print(f"Encountered {errors} errors.")

if __name__ == "__main__":
    main()
