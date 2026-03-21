import requests
from bs4 import BeautifulSoup
import argparse
import json
import os
import time
import re

BASE_URL = "https://elibrary.judiciary.gov.ph"

MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

def get_decisions_for_month(year, month):
    """
    Fetches the list of decisions for a specific month and year.
    Returns a list of dictionaries containing metadata.
    """
    url = f"{BASE_URL}/thebookshelf/docmonth/{month}/{year}/1"
    print(f"Fetching: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            print(f"No records found for {month} {year}")
            return []
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    decisions = []
    # The links are usually in a specific format within the content area
    # Looking at the previous verification, links are like: https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/{id}
    
    # We need to be careful about the selector. 
    # Based on the read_url_content output, it seems to be a list of links.
    # Let's find all 'a' tags that contain 'showdocs/1/'
    
    links = soup.find_all('a', href=re.compile(r'/thebookshelf/showdocs/1/\d+'))
    
    for link in links:
        href = link.get('href')
        if not href.startswith("http"):
             href = BASE_URL + href
             
        text = link.get_text(strip=True)
        
        # Simple parsing of text to extract potential G.R. No. and Date if stuck together
        # The text usually looks like:
        # "G.R. No. 12345 ... VS ... January 1, 1901"
        # However, looking at the previous output, the link text might contain newlines.
        
        decisions.append({
            "title": text,
            "url": href,
            "year": year,
            "month": month,
            "id": href.split("/")[-1]
        })
        
    return decisions

def main():
    parser = argparse.ArgumentParser(description="Scrape Supreme Court Decision Metadata")
    parser.add_argument("--year", type=int, help="Year to scrape (e.g., 1901)", required=True)
    parser.add_argument("--month", type=str, help="Specific month to scrape (e.g., Jan). If not set, scrapes entire year.")
    
    args = parser.parse_args()
    
    all_decisions = []
    
    months_to_scrape = [args.month] if args.month else MONTHS
    
    for month in months_to_scrape:
        if month not in MONTHS:
            print(f"Invalid month: {month}")
            continue
            
        decisions = get_decisions_for_month(args.year, month)
        all_decisions.extend(decisions)
        time.sleep(1) # Be polite
        
    # Save to JSON
    output_file = "sc_decisions_metadata.json"
    
    # Load existing if any
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                # verify it's a list
                if not isinstance(existing_data, list):
                    existing_data = []
        except json.JSONDecodeError:
             existing_data = []
    else:
        existing_data = []
        
    # Merge avoiding duplicates
    existing_ids = {d['id'] for d in existing_data}
    new_count = 0
    for d in all_decisions:
        if d['id'] not in existing_ids:
            existing_data.append(d)
            existing_ids.add(d['id'])
            new_count += 1
            
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=4, ensure_ascii=False)
        
    print(f"Saved {len(existing_data)} (New: {new_count}) decisions to {output_file}")

if __name__ == "__main__":
    main()
