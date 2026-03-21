import os
import json
import csv
import re
import logging
from tqdm import tqdm

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SCRAPER_DIR = os.path.join(BASE_DIR, 'sc_scraper')
DATA_DIR = os.path.join(BASE_DIR, 'data')
DOWNLOADS_DIR = os.path.join(SCRAPER_DIR, 'downloads')

os.makedirs(DATA_DIR, exist_ok=True)

GENERIC_TERMS = [
    "people of the philippines",
    "republic of the philippines",
    "city of manila",
    "commission on elections",
    "court of appeals",
    "sandiganbayan",
    "civil service commission",
    "nlrc",
    "ombudsman"
]

def clean_text(text):
    if not text:
        return ""
    # Normalize whitespace
    return " ".join(text.split())

def generate_short_title(full_title):
    """
    Generates a short title based on the user's rules:
    - Use significant party name.
    - Avoid generic names (People, Republic, etc.).
    - Handle 'vs.' or 'v.' split.
    """
    if not full_title:
        return ""

    # Remove G.R. No. prefix if present in title for processing
    # Sometimes title starts with "G.R. No. XXXXX - PARTY vs PARTY"
    clean_title = full_title
    if " - " in full_title:
        parts = full_title.split(" - ", 1)
        if parts[0].strip().startswith("G.R.") or parts[0].strip().startswith("A.M."):
            clean_title = parts[1]

    # Split by vs.
    separator = " vs. "
    if " v. " in clean_title:
        separator = " v. "
    elif " VS. " in clean_title:
        separator = " VS. "
    elif " V. " in clean_title:
        separator = " V. "
    
    parties = clean_title.split(separator)
    
    if len(parties) < 2:
        # Fallback if no clear separator
        return clean_title.split(",")[0].strip() # Return first part as fallback

    party_a = parties[0].strip()
    party_b = parties[1].strip()

    # Clean roles like "Petitioner", "Respondent"
    # Regex to remove ", Petitioner", ", Respondent", etc. at the end
    role_pattern = re.compile(r",\s*(Petitioner|Respondent|Appellant|Appellee|Accused|Plaintiff|Defendant)[s]*[\.]*$", re.IGNORECASE)
    
    name_a = role_pattern.sub("", party_a).strip()
    name_b = role_pattern.sub("", party_b).strip()

    # Check against generic list
    lower_a = name_a.lower()
    
    is_generic_a = any(term in lower_a for term in GENERIC_TERMS)
    
    if is_generic_a:
        return name_b # Use the other party
    else:
        return name_a # Default to first party

def compile_data():
    output_csv = os.path.join(DATA_DIR, 'supreme_decisions_dump.csv')
    
    # Check years 1901-2024
    years = list(range(1901, 2025))
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['sc_id', 'title', 'short_title', 'case_number', 'year', 'month', 'source_url', 'content']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        count = 0
        
        for year in tqdm(years, desc="Processing Years"):
            metadata_file = os.path.join(SCRAPER_DIR, f"metadata_{year}.json")
            if not os.path.exists(metadata_file):
                continue
                
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_list = json.load(f)
            except Exception as e:
                logging.error(f"Failed to load metadata for {year}: {e}")
                continue

            for item in metadata_list:
                sc_id = item.get('id')
                month = item.get('month', '').lower()
                year_val = item.get('year')
                
                if not sc_id or not month:
                    continue
                
                # Locate full text file
                # Path: sc_scraper/downloads/{year}/{month}/{id}.json
                content_file = os.path.join(DOWNLOADS_DIR, str(year), month, f"{sc_id}.json")
                
                content = ""
                if os.path.exists(content_file):
                    try:
                        with open(content_file, 'r', encoding='utf-8') as cf:
                            c_data = json.load(cf)
                            content = c_data.get('main_text', '')
                    except Exception as e:
                        # Fallback to HTML if needed or just log? Assuming JSON exists as per downloads check
                        pass
                
                # Generate Short Title
                full_title = item.get('title', '')
                short_title = generate_short_title(full_title)
                
                # If short title is empty, fallback to existing short_title in metadata if available, or full title
                if not short_title:
                    short_title = item.get('short_title') or full_title

                record = {
                    'sc_id': sc_id,
                    'title': clean_text(full_title),
                    'short_title': clean_text(short_title),
                    'case_number': clean_text(item.get('case_number', '')),
                    'year': year_val,
                    'month': month,
                    'source_url': item.get('url', ''),
                    'content': clean_text(content)
                }
                
                writer.writerow(record)
                count += 1
        
        logging.info(f"Compilation complete. {count} records written to {output_csv}")

if __name__ == "__main__":
    compile_data()
