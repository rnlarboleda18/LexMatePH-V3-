import os
import re
import shutil
import time
import json
import logging
import ast # Added for robust parsing
from pathlib import Path
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
from google import genai
from google.genai import types

# Config
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash" 
DATA_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")
INPUT_LIST = Path("unique_corrected_cases.txt")
LOG_FILE = "verification_log_rigorous.txt"
MAX_WORKERS = 5

def setup_client():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    return genai.Client(api_key=API_KEY)

class CaseManager:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.file_map = {} 
        self.scan_files()

    def scan_files(self):
        print("Scanning local files...")
        for p in self.root_dir.rglob("*.md"):
            match = re.search(r'^(.*)_([A-Z][a-z]+)_(\d{2})_(\d{4})\.md$', p.name)
            if match:
                case_raw = match.group(1)
                key = self.normalize_key(case_raw)
                if key not in self.file_map:
                    self.file_map[key] = []
                self.file_map[key].append(p)
    
    def normalize_key(self, case_str):
        return re.sub(r'[\W_]+', '', case_str).lower()

    def find_file(self, case_number):
        key = self.normalize_key(case_number)
        return self.file_map.get(key)

def get_header_date(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [f.readline() for _ in range(20)]
        
        date_pattern = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})', re.IGNORECASE)
        
        for line in lines:
            line = line.strip()
            if line.startswith("###") or line.startswith("**"): 
                match = date_pattern.search(line)
                if match:
                    try:
                        month, day, year = match.groups()
                        return datetime.strptime(f"{month} {day}, {year}", "%B %d, %Y")
                    except:
                        continue
        return None
    except:
        return None

def update_file(file_path, new_date_dt):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    header_updated = False
    
    date_str = new_date_dt.strftime("%B %d, %Y")
    date_pattern = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', re.IGNORECASE)
    
    for line in lines:
        if not header_updated and (line.strip().startswith("###") or line.strip().startswith("**") or "G.R." in line):
            match = date_pattern.search(line)
            if match:
                new_line = line.replace(match.group(0), date_str)
                new_lines.append(new_line)
                header_updated = True
                continue
        new_lines.append(line)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    match = re.search(r'^(.*)_([A-Z][a-z]+)_(\d{2})_(\d{4})\.md$', file_path.name)
    if match:
        case_prefix = match.group(1)
    else:
        stem = file_path.stem
        strip_date = re.sub(r'_[A-Z][a-z]+_\d{2}_\d{4}$', '', stem)
        case_prefix = strip_date
    
    new_fname = f"{case_prefix}_{new_date_dt.strftime('%B')}_{new_date_dt.day:02d}_{new_date_dt.year}.md"
    new_dir = DATA_DIR / str(new_date_dt.year)
    new_dir.mkdir(parents=True, exist_ok=True)
    new_path = new_dir / new_fname
    
    if new_path != file_path:
        shutil.move(file_path, new_path)
        return new_path
    return file_path

def verify_case(client, case_number, file_mgr):
    files = file_mgr.find_file(case_number)
    if not files:
        return f"[SKIP-NOFILE] {case_number}"
    
    target_file = files[0]
    local_date = get_header_date(target_file)
    
    prompt = f"""
    Verify the official promulgation date of the Philippine Supreme Court case: "{case_number}".
    
    ACTIONS:
    1. SEARCH the official Supreme Court E-Library (sc.judiciary.gov.ph), Lawphil, ChanRobles, or official reporter websites.
    2. FIND at least 3 distinct sources verifying the date.
    
    OUTPUT FORMAT (JSON ONLY):
    {{
      "promulgation_date": "YYYY-MM-DD" or null,
      "confidence": "High" or "Low",
      "sources": ["url1", "url2", "url3"],
      "reasoning": "Brief explanation of findings"
    }}
    
    If you cannot definitively find the date from reputable sources, return null for date.
    """
    
    try:
        # V2 SDK Syntax
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json" # Ask for JSON mode directly
            )
        )
        
        # Parse JSON
        text = response.text
        if not text:
             reason = "Unknown"
             if response.candidates and response.candidates[0].finish_reason:
                  reason = response.candidates[0].finish_reason
             return f"[ERR] {case_number} - Empty Response. Reason: {reason}"

        text = text.strip()
        # Clean markdown fences
        if text.startswith("```"):
            text = re.sub(r"^```[a-z]*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"```$", "", text)
        text = text.strip()

        # Strategy 0: Sanitize Newlines (Flatten)
        # Gemini 2.0 Flash often includes unescaped newlines in reasoning strings
        sanitized_text = text.replace('\n', ' ').replace('\r', '')

        data = None
        parse_error = ""

        # Strategy 1: Direct JSON on Sanitized Text (with raw_decode)
        try:
            data = json.loads(sanitized_text)
        except Exception as e1:
             # Try raw_decode (ignores extra data at end)
             try:
                 data, _ = json.JSONDecoder().raw_decode(sanitized_text)
             except:
                 try:
                     # Try raw_decode on original text
                     data, _ = json.JSONDecoder().raw_decode(text)
                 except:
                    parse_error = str(e1)
                    
                    # Strategy 2: Regex Extraction on Original
                    match = re.search(r'(\{.*\})', text, re.DOTALL)
                    if match:
                        candidate = match.group(1)
                        # Sanitize candidate
                        candidate_sanitized = candidate.replace('\n', ' ').replace('\r', '')
                        try:
                            data, _ = json.JSONDecoder().raw_decode(candidate_sanitized)
                        except:
                            # Strategy 3: Double Brace Fix
                            cleaned = candidate_sanitized.replace("{{", "{").replace("}}", "}")
                            try:
                               data, _ = json.JSONDecoder().raw_decode(cleaned)
                            except:
                               # Strategy 4: AST Eval
                               try:
                                   data = ast.literal_eval(candidate)
                               except:
                                   pass
                    
                    if data is None:
                        # Strategy 5: Double Brace Fix on Sanitized Full Text
                        cleaned = sanitized_text.replace("{{", "{").replace("}}", "}")
                        try:
                            data, _ = json.JSONDecoder().raw_decode(cleaned)
                        except:
                            # Strategy 6: AST Eval on Full Text
                            try:
                                data = ast.literal_eval(text)
                            except:
                                 pass
        
        if data is None:
             return f"[ERR] {case_number} - JSON/AST Error ({parse_error}). Raw: {text[:200]}..."

        ai_date_str = data.get("promulgation_date")
        if not ai_date_str:
             return f"[AI-UNCERTAIN] {case_number} - {data.get('reasoning')}"

        try:
            ai_date = datetime.strptime(ai_date_str, "%Y-%m-%d")
        except:
            return f"[AI-BADFMT] {case_number} - Bad date: {ai_date_str}"
            
        if data.get("confidence") != "High":
             return f"[AI-LOWCONF] {case_number} - Confidence Low"

        sources = data.get("sources", [])
        if len(sources) < 2: 
             # allow 2
             pass

        if local_date and local_date.date() == ai_date.date():
            return f"[OK] {case_number} - Matches AI ({ai_date.date()})"
            
        update_file(target_file, ai_date)
        old_d = local_date.date() if local_date else "None"
        return f"[FIXED] {case_number} - Local: {old_d} -> AI: {ai_date.date()} | Sources: {len(sources)}"
    except Exception as e:
        return f"[ERR] {case_number} - {str(e)}"
            
        if data.get("confidence") != "High":
             return f"[AI-LOWCONF] {case_number} - Confidence Low"
             
        sources = data.get("sources", [])
        if len(sources) < 2: 
             # allow 2
             pass
             
        if local_date and local_date.date() == ai_date.date():
            return f"[OK] {case_number} - Matches AI ({ai_date.date()})"
            
        update_file(target_file, ai_date)
        old_d = local_date.date() if local_date else "None"
        return f"[FIXED] {case_number} - Local: {old_d} -> AI: {ai_date.date()} | Sources: {len(sources)}"

    except Exception as e:
        return f"[ERR] {case_number} - {str(e)}"

def run_verification():
    if not INPUT_LIST.exists():
        print("Input list not found.")
        return

    with open(INPUT_LIST, 'r') as f:
        cases = [line.strip() for line in f if line.strip()]

    print(f"Loaded {len(cases)} cases.")
    print(f"Model: {MODEL_NAME}") # Confirm model
    mgr = CaseManager(DATA_DIR)
    
    print("Starting verification with Google GenAI SDK (V2)...")
    client = setup_client()
    
    # Initialize log file
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Verification Log - {datetime.now()}\n")

    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(verify_case, client, c, mgr): c for c in cases}
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(cases)):
            res = future.result()
            results.append(res)
            
            # Live Log
            print(res) # Print to console for monitoring
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(res + "\n")

            if "[ERR]" in res and "429" in res:
                 time.sleep(5)
            
    fixed = [r for r in results if "[FIXED]" in r]
    print("\nVerification Complete.")
    print(f"Total: {len(results)}")
    print(f"Fixed: {len(fixed)}")
    print(f"See {LOG_FILE} for details.")

if __name__ == "__main__":
    run_verification()
