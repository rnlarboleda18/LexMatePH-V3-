import requests
from bs4 import BeautifulSoup
import argparse
import json
import os
import time
import re

BASE_URL = "https://chanrobles.com/cralaw/"

# ChanRobles uses full month names in URLs usually, closely tied to the link format
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]

def generate_short_title(title):
    """
    Generates a short title based on PHILJA rules (Petitioner v. Respondent).
    - Removes "G.R. No.", Dates, etc.
    - Handles "People v. Name" and "Republic v. Name".
    - Strips "Spouses", "Heirs of", "et al.".
    """
    # 1. Clean initial junk (GR No, Date) if present at start.
    # Usually title is full text: "G.R. No. 123 - Petitioner v. Respondent"
    # Or just "Petitioner v. Respondent" if pre-cleaned? 
    # In this script, 'text' is the link text which usually includes GR No and Date.
    
    # Remove G.R. No. ... Date - 
    # Example: "G.R. No. 25400 January 14, 1927 - PNB v. PHIL. VEGETABLE OIL CO., ET AL."
    # Regex to find the start of the actual case name (after the dash often)
    
    clean_title = title
    match = re.search(r'G\.R\. No\..+?-\s*(.+)', title, re.IGNORECASE)
    if match:
        clean_title = match.group(1).strip()
        
    # Splitting into Petitioner and Respondent
    # Usually separated by " v. " or " vs. "
    parts = re.split(r'\s+v\.?s?\.?\s+', clean_title, 1, flags=re.IGNORECASE)
    
    if len(parts) < 2:
        return clean_title # Fallback if no " v. " found
        
    petitioner = parts[0].strip()
    respondent = parts[1].strip()
    
    # Helper to clean a name
    def clean_name(name):
        # Remove common prefixes
        name = re.sub(r'^(Spouses|Heirs of|The|In the matter of|Estate of)\s+', '', name, flags=re.IGNORECASE).strip()
        # Remove suffixes like "et al.", "petitioners", "respondents"
        name = re.sub(r',?\s+(et\s+al\.?|petitioners?|respondents?|plaintiffs?|defendants?|appellants?|appellees?).*', '', name, flags=re.IGNORECASE).strip()
        
        # Heuristics for "People of the Philippines" -> "People"
        if "People of the Philippines" in name:
            return "People"
        if "Republic of the Philippines" in name:
            return "Republic"
            
        # Naming convention: Use surname if possible?
        # Difficult to distinguish first/last names reliably without NER. 
        # But PHILJA says "Surname". 
        # Strategy: distinct handling for "People", "Republic". 
        # For others, if it looks like a person's name (multiple words), we might take the *last* word (surname) 
        # BUT many entities are companies "Manila Electric Co.".
        # Taking the *whole* cleaned name is safer for now unless user asks for strict surname extraction for individuals only.
        # User prompt said: "Surname of the first-listed petitioner". 
        # Let's try to extract surname if it looks like a person (no Inc., Corp., etc).
        
        # Simple heuristic: If it has "Inc.", "Corp.", "Co.", it's an entity, keep full name.
        if re.search(r'\b(Inc\.?|Corp\.?|Co\.?|Ltd\.?)\b', name):
            return name
            
        # If "People" or "Republic", return that.
        if name == "People" or name == "Republic":
            return name
            
        # Else assume format "Firstname M. Lastname" -> Lastname
        # Or "Lastname, Firstname" (less common in titles)
        # Take the last token? 
        # "Juan Santos" -> "Santos"
        # "Maria Dela Cruz" -> "Dela Cruz" (Complex!)
        # "Spouses Rodolfo A. Concepcion and Noemi M. Concepcion" -> "Concepcion" (After strips)
        
        # Let's take the *whole* cleaned name for now (minus "Spouses", "et al") as "Short Title" is often cited as "Concepcion v. Matias".
        # If I strictly take the last word, "Dela Cruz" becomes "Cruz".
        # Let's clean the extra fluff and return the remaining name string.
        return name

    short_pet = clean_name(petitioner)
    short_resp = clean_name(respondent)
    
    return f"{short_pet} v. {short_resp}"

def get_decisions_for_month(year, month):
    """
    Fetches the list of decisions for a specific month and year from ChanRobles.
    """
    # URL Pattern: https://chanrobles.com/cralaw/{Year}{Month}decisions.php
    url = f"{BASE_URL}{year}{month}decisions.php"
    print(f"Fetching Index: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 404:
            print(f"Page not found: {url}")
            return []
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    decisions = []
    
    # We are looking for links like: {year}{month}decisions.php?id={id}
    # Example: 1901augustdecisions.php?id=4
    pattern = re.compile(rf"{year}{month}decisions\.php\?id=\d+")
    
    links = soup.find_all('a', href=pattern)
    
    seen_ids = set()
    
    for link in links:
        href = link.get('href')
        full_url = href
        if not href.startswith("http"):
             # ChanRobles links might be relative
             full_url = f"https://chanrobles.com/cralaw/{href}"
             
        # Extract ID
        try:
            case_id = href.split("id=")[1]
        except IndexError:
            continue
            
        if case_id in seen_ids:
            continue
        seen_ids.add(case_id)
        
        text = link.get_text(strip=True)
        
        # Metadata extraction from text
        # Format often: "G.R. No. 12 August 8, 1901 - IN RE: MARCELINO AGUAS001 Phil 1"
        # Extract citation at the end: e.g. "001 Phil 1" or "049 Phil 857"
        # Pattern: 3 digits + Phil + digits
        citation = ""
        citation_match = re.search(r'(\d{3}\s+Phil\.?\s+\d+)$', text)
        if citation_match:
            citation = citation_match.group(1)
            # Remove citation from title
            text = text.replace(citation, "").strip()
        
        decisions.append({
            "source": "chanrobles",
            "title": text,
            "url": full_url,
            "year": year,
            "month": month,
            "id": case_id,
            "citation": citation,
            # Extraction of case_number from title or text
            # Usually "G.R. No. 12345" or "G.R. Nos. 1-2"
            "case_number": (re.search(r"(G\.R\. No\.?s?\.?\s*[\d\-]+)", text, re.IGNORECASE) or 
                           re.search(r"(Administrative Matter No\.\s*[\w\-]+)", text, re.IGNORECASE) or
                           re.search(r"(Bar Matter No\.\s*[\d]+)", text, re.IGNORECASE) or [None, "Unknown"])[1],
            "short_title": generate_short_title(text)
        })
        
    print(f"Found {len(decisions)} decisions for {month} {year}")
    return decisions

def main():
    parser = argparse.ArgumentParser(description="Scrape ChanRobles Decision Metadata")
    parser.add_argument("--year", type=int, help="Year to scrape", required=True)
    parser.add_argument("--month", type=str, help="Specific month (full name, lowercase).")
    parser.add_argument("--output", type=str, help="Output JSON path", default="chanrobles_metadata.json")
    
    args = parser.parse_args()
    
    all_decisions = []
    
    months_to_scrape = [args.month.lower()] if args.month else MONTHS
    
    for month in months_to_scrape:
        if month not in MONTHS:
            print(f"Invalid month: {month}")
            continue
            
        decisions = get_decisions_for_month(args.year, month)
        all_decisions.extend(decisions)
        time.sleep(1) 
        
    output_file = args.output
    
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list): existing_data = []
        except: existing_data = []
    else:
        existing_data = []
        
    # Merge
    # Use URL as unique key usually, or ID+Year+Month
    existing_urls = {d['url'] for d in existing_data}
    new_count = 0
    for d in all_decisions:
        if d['url'] not in existing_urls:
            existing_data.append(d)
            existing_urls.add(d['url'])
            new_count += 1
            
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=4, ensure_ascii=False)
        
    print(f"Saved {len(existing_data)} (New: {new_count}) decisions to {output_file}")

if __name__ == "__main__":
    main()
