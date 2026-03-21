
import csv
import os
import re

INPUT_CSV = r"analysis/sc_elib_verification.csv"
OUTPUT_CSV = r"analysis/sc_elib_clean_metadata.csv"

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        return

    print(f"Reading {INPUT_CSV}...")
    
    # Regex for Date at end of string: Month DD, YYYY or similar
    # e.g. "..., January 27, 2006"
    date_regex = re.compile(r',\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4})$')

    clean_rows = []
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == 'OK':
                raw = row['header_raw']
                # Better parsing
                # Find the date pattern at the end
                match = date_regex.search(raw)
                if match:
                    date_str = match.group(1).strip()
                    # Everything before that match and the comma is the case number
                    case_str = raw[:match.start()].strip()
                    # Remove trailing comma if captured or left
                    if case_str.endswith(','):
                        case_str = case_str[:-1].strip()
                else:
                    # Fallback to the naive split or just use what we have?
                    # The naive split was: case_numbers = text before last comma
                    # If regex fails (no date format), maybe use the original columns or skip date?
                    # Let's try to clean up.
                    case_str = row['case_numbers']
                    date_str = row['date']

                clean_rows.append({
                    'filename': row['filename'],
                    'case_numbers': case_str,
                    'date': date_str
                })

    print(f"Found {len(clean_rows)} clean records.")
    
    print(f"Writing to {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ['filename', 'case_numbers', 'date']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_rows)

    print("Done.")

if __name__ == "__main__":
    main()
