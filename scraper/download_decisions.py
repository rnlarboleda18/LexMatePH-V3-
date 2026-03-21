import requests
from bs4 import BeautifulSoup
import json
import os
import time
from content_parser import parse_decision_content
import argparse


# BASE_URL is not strictly needed if we use full URLs from metadata


def download_decision(url, output_path, decision_metadata=None):
    """
    Downloads the decision HTML content and saves it.
    Also parses content and saves as JSON if generic HTML is retrieved.
    """
    # Check if file already exists
    if os.path.exists(output_path):
        # Check if file is not empty (basic validation)
        if os.path.getsize(output_path) > 100:
             # print(f"Skipping {output_path}, already exists.")
             return False
    
    print(f"Downloading: {url} -> {output_path}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False
        
    # Save Raw HTML
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # Parse and Save Structured JSON
    if decision_metadata:
        try:
            parsed_data = parse_decision_content(html_content)
            
            # User Restricted Schema:
            # 1. case number (from metadata)
            # 2. year (from metadata)
            # 3. main text (from parsed content)
            
            restricted_data = {
                "case_number": decision_metadata.get("case_number", "Unknown"),
                "year": decision_metadata.get("year", "Unknown"),
                "main_text": parsed_data.get("main_text", "")
            }
            
            # Determine JSON path (same name as HTML but .json)
            json_path = output_path.replace(".html", ".json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(restricted_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error parsing content for {url}: {e}")
            
    return True

def main():
    parser = argparse.ArgumentParser(description="Download Decisions Content")
    parser.add_argument("--limit", type=int, help="Limit number of downloads per run", default=0)
    parser.add_argument("--metadata", type=str, help="Path to metadata JSON file", default="sc_decisions_metadata.json")
    args = parser.parse_args()
    
    metadata_file = args.metadata
    if not os.path.exists(metadata_file):
        print(f"Metadata file {metadata_file} not found.")
        return

    with open(metadata_file, "r", encoding="utf-8") as f:
        decisions = json.load(f)
        
    count = 0
    for d in decisions:
        year = str(d.get('year', 'unknown'))
        month = d.get('month', 'unknown')
        case_id = d.get('id')
        
        # Create directory structure: downloads/{Year}/{Month}/
        save_dir = os.path.join("downloads", year, month)
        os.makedirs(save_dir, exist_ok=True)
        
        filename = f"{case_id}.html"
        output_path = os.path.join(save_dir, filename)
        
        if download_decision(d['url'], output_path, decision_metadata=d):
            count += 1
            time.sleep(1) # Be polite
            
        if args.limit > 0 and count >= args.limit:
            print(f"Reached limit of {args.limit} downloads.")
            break
            
    print("Download process completed.")

if __name__ == "__main__":
    main()
