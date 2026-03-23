"""
Supreme Court HTML to Markdown Converter (Smart Citation Edition)

Converts HTML case files to markdown with:
1. Smart Inline Citations (Resolves "Id.", links G.R. Nos, filters junk).
2. Unique constraint enforcement.
3. Fixes ghost artifacts and formatting.
4. Removes "Consent/Welcome" popups and watermark artifacts.
"""

import os
import json
import shutil
import re
import random
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import argparse
import hashlib
from collections import defaultdict
import concurrent.futures
import multiprocessing
import google.generativeai as genai
from dotenv import load_dotenv

# Directories
SC_SCRAPER_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper")
DOWNLOADS_DIR = SC_SCRAPER_DIR / "downloads_enhanced"
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\MD\1975-2024")
MANIFEST_FILE = OUTPUT_DIR / "conversion_manifest.json"

# Division keywords to search for
DIVISION_KEYWORDS = [
    "EN BANC",
    "FIRST DIVISION",
    "SECOND DIVISION",
    "THIRD DIVISION",
    "SPECIAL FIRST DIVISION",
    "SPECIAL SECOND DIVISION",
    "SPECIAL THIRD DIVISION"
]

# Load environment variables
load_dotenv(Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\.env"))

class CaseConverter:
    def __init__(self):
        self.stats = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        # Initialize Gemini
        api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            print("Warning: GOOGLE_API_KEY not found. LLM features disabled.")
            self.model = None

        self.manifest = []
        self.processed_cases = set()  # Track unique case_number + date
        self.processed_hashes = defaultdict(set) # Track content hashes per case key
        self.processed_paths = set() # Track processed source HTML paths
        self.duplicates_dir = None # Will be set by args if needed

    def clean_with_llm(self, html_content):
        """
        Uses Gemini 2.0 Flash to clean and convert HTML to Markdown.
        Instructions: Inline footnotes, remove junk, remove headers/footers.
        """
        if not self.model:
            return self.clean_and_convert(html_content)

        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove scripts/styles first to save tokens
        for tag in soup(["script", "style", "nav", "footer", "iframe"]):
            tag.decompose()
        
        cleaned_html = str(soup)
        
        prompt = f"""
        You are a legal data processing expert. Convert the following Philippine Supreme Court Decision from HTML to Markdown.
        
        CRITICAL FILTERING RULE (THE "STUDENT VALUE" TEST):
        1. **REMOVE "Junk" Citations**: Delete any footnote or citation that refers solely to internal case records that a student cannot access.
           - Keywords to remove: "Rollo", "Id.", "TSN", "Annex", "Minutes", "Report", "Letter dated".
           - Example: If a footnote says `^[Rollo, p. 288.]` or `^[Id. at 50.]`, delete the entire footnote.

        2. **KEEP "Value" Citations**: Retain inline footnotes that refer to legal authority or provide explanations.
           - Keep: Citations to other Supreme Court cases (e.g., People v. Soliman), Laws (e.g., R.A. 3019), the Constitution, books, or dictionaries.
           - Keep: Explanatory notes (e.g., "The court distinguished this from the 2012 ruling...").

        FORMATTING GUIDELINES:
        - **Header**: Remove all navigation/branding. Keep only the Case Title and G.R. Number as a Heading 1 (#).
        - **Structure**: Use ## for main headings and ### for sub-headings.
        - **Typography**: Convert HTML bold/italics to Markdown (**bold**, *italics*).
        - **Inline Footnoting**: Convert valid "Value" citations into inline footnotes using `^[Content]`. Place them immediately after the relevant punctuation.
        - **Clean Output**: Do not generate a reference list at the bottom. Return ONLY the clean Markdown text.

        HTML CONTENT:
        {cleaned_html}
        """
        
        import time

        try:
            # Retry logic for 429 Resource Exhausted
            retries = 3
            backoff_factor = 2
            
            for attempt in range(retries):
                try:
                    response = self.model.generate_content(prompt)
                    return response.text
                except Exception as e:
                    if "429" in str(e) or "resource exhausted" in str(e).lower():
                        if attempt < retries - 1:
                            wait_time = (backoff_factor ** attempt) * 5  # 5, 10, 20 seconds
                            print(f"LLM 429 Rate Limit. Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise e # Re-raise to trigger fallback after retries
                    else:
                        raise e # Re-raise other errors immediately
                        
        except Exception as e:
            print(f"LLM Error: {e}. Falling back to Regex.")
            return self.clean_and_convert(html_content)

    def is_garbage_file(self, soup):
        """
        Determine if file is garbage (has case number but no real content).
        Returns True if garbage, False otherwise.
        """
        # Get text content
        text_content = soup.get_text()
        clean_text = re.sub(r'\s+', ' ', text_content).strip()
        
        # Minimum content length (500 chars)
        if len(clean_text) < 500:
            return True
        
        # Check if it's mostly just navigation/ads
        if clean_text.count('ChanRobles') > 10:  
            content_without_ads = re.sub(r'ChanRobles.*?(?=\n|$)', '', clean_text, flags=re.IGNORECASE)
            if len(content_without_ads) < 500:
                print("    [GARBAGE] Content is mostly navigation links.")
                return True
        
        # --- NEW: VALID ENDING CHECK ---
        # User Rule: Must have "concluding words" or Justice signatures
        
        # 1. IMMEDIATE PASS: "SO ORDERED"
        if re.search(r"SO\s+ORDERED", clean_text, re.IGNORECASE):
            return False

        # 2. Look for Concluding Keywords (English + Spanish)
        # Search window: Max(30k chars, 50% of content) to handle large files with big footers
        search_window = max(30000, len(clean_text) // 2)
        last_chunk = clean_text[-search_window:] 
        
        # Look for Justice Signature Pattern 
        has_signature = re.search(r'[A-Za-z\s\.,-]+,\s*(C\.?J\.?|J\.?|JJ\.?|M\.?|MM\.?|P\.?|Pres\.?)\.?:?', last_chunk)
        
        keywords = [
            r"WHEREFORE", r"ACCORDINGLY", r"RESOLVED",
            r"AFFIRMED", r"DENIED", r"DISMISSED", r"REVERSED",
            r"MODIFIED", r"SET\s+ASIDE", r"PETITION\s+IS\s+GRANTED",
            r"JUDGMENT\s+IS\s+RENDERED",
            # Spanish Keywords
            r"SE\s+DICTA\s+SENTENCIA", r"ASI\s+SE\s+ORDENA",
            r"EST[AÁ]N\s+CONFORMES", r"SE\s+DENIEGA",
            r"SE\s+CONFIRMA", r"CONFORME"
        ]
        has_conclusion = False
        for kw in keywords:
            if re.search(kw, last_chunk, re.IGNORECASE):
                has_conclusion = True
                break
        
        # 3. Look for "Separate Opinions" header
        has_opinions = re.search(r"Separate\s+Opinions", clean_text, re.IGNORECASE)
            
        if not has_signature and not has_conclusion and not has_opinions:
             print("    [GARBAGE] Missing valid ending (Signature, Conclusion, or Opinion Header).")
             return True
             
        return False

    def find_division_keyword(self, soup):
        """Find the division keyword in the HTML content."""
        for keyword in DIVISION_KEYWORDS:
             for tag in soup.find_all(string=re.compile(keyword, re.IGNORECASE)):
                parent = tag.parent
                return parent, keyword
        return None, None

    def clean_soup_dom(self, soup):
        """
        Robust DOM cleaning:
        1. Remove HEAD
        2. Remove Consent/Welcome Popups (Nuclear Method)
        3. Remove Header (Prioritize Case No. -> Division Keywords)
        4. Remove Footer (Back to Home, Jurisprudence lists)
        5. Remove Garbage tags
        """
        # Pre-clean: Remove HEAD
        if soup.head: soup.head.decompose()

        # --- 0. POPUP CLEANING (NUCLEAR OPTION) ---
        # Level 1: Destroy known Google Funding Choices classes
        popup_classes = [
            'fc-consent-root', 'fc-ab-root', 'fc-dialog-overlay', 
            'fc-dialog-container', 'fc-dialog', 'fc-choice-dialog', 
            'fc-footer-buttons-container'
        ]
        for tag in soup.find_all(class_=popup_classes):
            tag.decompose()

        # Level 2: Search for specific Consent text and destroy container
        consent_text = soup.find(string=re.compile(r"This site asks for consent to use your data", re.IGNORECASE))
        if consent_text:
            current = consent_text.parent
            for _ in range(10): # Traverse up to 10 parents
                if current and current.name == 'div':
                    if current.get('class') and any('fc-' in c for c in current.get('class', [])):
                         current.decompose()
                         break
                if current: current = current.parent
                else: break

        # --- 1. Header Cleaning ---
        start_marker = None
        
        def is_case_header(text):
            # Broader check for case prefixes
            return re.search(r'(G\.?R\.?|A\.?C\.?|A\.?M\.?|B\.?M\.?|U\.?D\.?K\.?|O\.?C\.?A\.?|I\.?P\.?I\.?|R\.?T\.?J\.?)\s*No\.?', text, re.IGNORECASE)

        # Priority 1: Case Number Header (G.R., A.C., etc)
        for tag in soup.find_all(['h1', 'h2', 'h3', 'strong', 'p', 'div', 'span']):
            text = tag.get_text().strip()
            if is_case_header(text):
                if len(text) < 300: 
                    start_marker = tag
                    break
        
        # Priority 2: Division Keywords
        if not start_marker:
            div_tag, _ = self.find_division_keyword(soup)
            if div_tag: start_marker = div_tag
            
        # Priority 3: "D E C I S I O N"
        if not start_marker:
             for tag in soup.find_all(['h1', 'strong', 'p', 'div']):
                text = tag.get_text().strip()
                if "D E C I S I O N" in text and len(text) < 200:
                    start_marker = tag
                    break

        # Execute Header Clean
        if start_marker:
             current = start_marker
             block_container = None
             while current and current.parent:
                 if current.name in ['div', 'p', 'center', 'h1', 'h2', 'table']:
                     block_container = current
                 if current.parent.name == 'body' or current.parent.get('class') == ['mainContent']:
                     if block_container is None: block_container = current
                     break
                 current = current.parent
             
             if block_container:
                current = block_container
                while current and current.name != 'body' and current.parent:
                    for sibling in list(current.find_previous_siblings()):
                        sibling.decompose()
                    current = current.parent

        # --- 2. Footer Cleaning (SAFE MODE) ---
        footer_patterns = [r"Back\s+to\s+Main", r"Back\s+to\s+Home"]
        footer_regex = re.compile("|".join(footer_patterns), re.IGNORECASE)
        
        footer_tags = soup.find_all(string=footer_regex)
        for tag in footer_tags:
            if len(tag) > 50: continue 
            container = tag.find_parent(['p', 'div', 'center', 'h3', 'h4'])
            if container:
                # SAFE DELETE: Only delete siblings of the specific container, then the container itself.
                for sibling in list(container.find_next_siblings()):
                    sibling.decompose()
                container.decompose()
                break

        # --- 3. Garbage Tags ---
        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'iframe', 'ins']):
            tag.decompose()
        
        garbage_classes = [
            'adsbygoogle', 'gcse-search', 'top-sidebar', 'style37', 'style19',
            'fc-consent-root', 'fc-ab-root'
        ]
        for garbage in soup.find_all(class_=garbage_classes):
             garbage.decompose()
             
        # --- 4. Watermark Cleaning (DOM Level) ---
        for span in soup.find_all('span', style=True):
            style = span['style'].lower().replace(';', ' ') 
            if 'color: #ffffff' in style and 'font-size: 1pt' in style:
                span.decompose()

        return soup

    def clean_and_convert(self, html_content):
        """
        Consolidated cleaning function.
        """
        
        # --- STEP 1: PARSE & REMOVE DOM JUNK ---
        soup = BeautifulSoup(html_content, "html.parser")

        # Use Robust DOM Cleaner
        soup = self.clean_soup_dom(soup)
        
        # Remove images
        for img in soup.find_all("img"):
            img.decompose()
        
        # Remove standard non-content tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        # --- STEP 1.4: EXTRACT FOOTNOTE DEFINITIONS ---
        # Extracts content and deletes the footer section from the DOM
        extracted_footnotes = self.extract_and_destroy_footnotes(soup)

        # --- STEP 1.5: STANDARDIZE FOOTNOTES ---
        sup_tags = soup.find_all('sup')
        for tag in sup_tags:
            text = tag.get_text().strip()
            if text.isdigit():
                tag.replace_with(f"FOOTNOTE_REF_{text}_END")

        # --- STEP 1.6: CATCH "FLOATING" PLAIN TEXT FOOTNOTES ---
        html_str = str(soup)
        floating_fn_pattern = r'(?:(?<=[a-z",])|(?<=(?<!\d)\.))(\d{1,3})(?=\s|<|$)'
        
        def float_replacer(match):
            num = match.group(1)
            return f"FOOTNOTE_REF_{num}_END"
            
        html_str = re.sub(floating_fn_pattern, float_replacer, html_str)
        
        soup = BeautifulSoup(html_str, "html.parser")

        # --- STEP 2: CONVERT TO MARKDOWN ---
        text = md(str(soup), heading_style="ATX")

        # Restore Footnote Tokens
        text = re.sub(r'FOOTNOTE[_\\]*REF[_\\]*(\d+)[_\\]*END', r'[^\1]', text)

        # --- STEP 4: AGGRESSIVE REGEX CLEANING ---
        watermarks = [
            # Catch "ChanRoblesVirtuaLawlibrary" (no spaces, typo in Virtual)
            r"chanrobles\w*law\w*library", 
            # Catch "ChanRoblesVirtualLawLibrary" (no spaces)
            r"chanrobles\w+", 
            # Catch standard spaced versions
            r"chanrobles\s+virtual\s+law\s+library",
            r"chanrobles\s+virtual\s+aw\s+library", 
            # Catch URL-like artifacts
            r"jgc:chanrobles\.com\.ph",
            r":\s*1998\s*red", 
            r"cralawredlibrary-red",
            r"cralawredlibrary",
            # Existing patterns
            r"Philippine Supreme Court Decisions\/Resolutions",
            r"Philippine Supreme Court Jurisprudence",
            r"\[Philippine Supreme Court Jurisprudence\]\(.*?\)",
            r"\[Year \d{4}\]",
            r"\[\w+ \d{4} Decisions\]",
            r"virtual law library",
            r">\s*>\s*>", 
            r"1awp\+\+i1", 
            r"1wphi1"
        ]
        
        for pattern in watermarks:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        text = re.sub(r":\s*\.", ":", text)
        text = text.replace("ï¿½", "")
        text = text.replace("\uFFFD", "")

        # --- STEP 5: SMART START & DEDUPLICATION ---
        lines = text.split('\n')
        cleaned_lines = []
        found_case_number = False
        
        strong_triggers = [
            r'^\W*EN\s+BANC\W*$',
            r'^\W*(?:FIRST|SECOND|THIRD)\s+DIVISION\W*$',
            r'^\W*DISSENTING\s+OPINION\W*$',
            r'^\W*CONCURRING\s+OPINION\W*$',
            r'^\W*SEPARATE\s+OPINION\W*$',
            r'^\W*CONCURRING\s+AND\s+DISSENTING\s+OPINION\W*$'
        ]
        
        weak_triggers = [
            r'G\.R\. No\.', r'A\.M\. No\.', r'A\.C\. No\.',
            r'B\.M\. No\.', r'OCA IPI No\.', r'U\.D\.K\.'
        ]
        
        for line in lines:
            stripped = line.strip()
            if not stripped or re.match(r'^[A-Za-z]+\s+\d{4}\s*-\s*$', stripped): continue
            if "decisions.php" in stripped: continue

            is_strong = any(re.search(p, stripped, re.IGNORECASE) for p in strong_triggers)
            is_weak = any(re.search(p, stripped, re.IGNORECASE) for p in weak_triggers)

            if is_strong:
                found_case_number = True
                cleaned_lines = [stripped]
                continue
            
            if is_weak:
                if not found_case_number:
                    found_case_number = True
                    cleaned_lines = [stripped]
                    continue
                if cleaned_lines and stripped in cleaned_lines[-1]:
                    continue

            if cleaned_lines and stripped == cleaned_lines[-1]:
                continue

            cleaned_lines.append(stripped)

        # --- STEP 6: FINAL POLISH ---
        final_text = '\n\n'.join(cleaned_lines)
        final_text = re.sub(r'\n{3,}', '\n\n', final_text)
        text = '\n'.join(cleaned_lines)
        
        # --- STEP 6: SMART INLINE CITATION INJECTION ---
        text = self.process_inline_footnotes(text, extracted_footnotes)
        
        # --- STEP 7: CLEANUP PHANTOM MARKERS ---
        text = re.sub(r'  +', ' ', text)
        
        # --- STEP 8: EXTRACT METADATA AND ADD FRONTMATTER ---
        # Note: We need original HTML for header parsing, but this method (clean_and_convert)
        # receives 'html_content' (string) as argument? Not usually passed to clean_and_convert in older versions.
        # But wait, clean_and_convert definition signature needs checking. 
        # Assuming clean_and_convert(self, html_content) is the signature.
        # Wait, line 214: def clean_and_convert(self, html_content, soup=None):
        
        meta = self.extract_metadata(soup, text, html_content)
        
        frontmatter = "---\n"
        frontmatter += f"case_number: \"{meta.get('Case Number') or ''}\"\n"
        frontmatter += f"date: \"{meta.get('Date') or ''}\"\n"
        frontmatter += f"short_title: \"{meta.get('Title') or ''}\"\n"
        frontmatter += f"decided_by: \"{meta.get('Decided by') or ''}\"\n"
        frontmatter += f"ponente: \"{meta.get('Ponente') or ''}\"\n"
        if meta.get('Decided by') == "En Banc":
             frontmatter += f"separate_opinion: \"{meta.get('Opinions') or ''}\"\n"
        frontmatter += "---\n\n"

        return frontmatter + text.strip()

    def extract_metadata(self, soup, clean_text_content, raw_html=None):
        """
        Extracts metadata using a combination of Soup DOM and Cleaned Text.
        """
        meta = {
            'Case Number': None,
            'Date': None,
            'Title': None,
            'Ponente': None,
            'Decided by': None, # Division or En Banc
            'Opinions': None
        }

        # Clean lines for easier scanning
        cleaned_lines = [line.strip() for line in clean_text_content.split('\n') if line.strip()]

        # 1. Decided By (Division vs En Banc)
        if re.search(r'EN\s+BANC', clean_text_content, re.IGNORECASE):
            meta['Decided by'] = "En Banc"
        else:
            div_match = re.search(r'(FIRST|SECOND|THIRD)\s+DIVISION', clean_text_content, re.IGNORECASE)
            if div_match:
                meta['Decided by'] = f"{div_match.group(1).title()} Division"

        # 2. Case Number and Date (Fallback to Filename logic if missing in text, 
        # but here we try to find it in the text header)
        
        # 3. Title (Petitioner vs Respondent)
        # Scan for "Petitioner" and "Respondent" lines
        petitioner_raw = "Petitioner"
        respondent_raw = "Respondent"
        
        p_index = -1
        r_index = -1
        
        for i, line in enumerate(cleaned_lines[:50]): # Scan top 50 lines
            if "Petitioner" in line or "Plaintiff" in line or "Appellant" in line:
                # Capture line BEFORE this one? Or this line itself?
                # Usually: NAME, Petitioner, vs. NAME, Respondent.
                pass 
                
        # Simple Title extraction (Heuristic: Find "vs" or "versus")
        vs_match = re.search(r'(.+)\s+(?:vs\.?|versus)\s+(.+)', clean_text_content, re.IGNORECASE)
        # This is unreliable using regex on full text. 
        # Better to rely on the "Short Title" logic usually available in valid Lawphil parsers.
        # But for this universal script, we might leave Title as None if difficult.
        
        # 4. Ponente
        start_index = -1
        for i, line in enumerate(cleaned_lines):
            # Allow for **D E C I S I O N** or similar
            if re.match(r'^[\*#]*\s*D\s*E\s*C\s*I\s*S\s*I\s*O\s*N\s*[\*#]*$', line, re.IGNORECASE) or \
               re.match(r'^[\*#]*\s*R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N\s*[\*#]*$', line, re.IGNORECASE):
                start_index = i
                break
        
        if start_index != -1:
            # Look at next 5 lines
            for i in range(start_index + 1, min(start_index + 6, len(cleaned_lines))):
                candidate = cleaned_lines[i]
                # Regex for: **TIJAM, J.:**  or **TIJAM, *J.*
                # Capture "NAME" and "TITLE" allowing for markdown junk in between
                ponente_match = re.search(r'(?:\*\*|\*|^)([A-Z\.]+)(?:,|\s+)(?:[\*_]*\s*)+(C\.?J\.?|J\.?)', candidate)
                if ponente_match:
                    name_part = ponente_match.group(1).strip()
                    suffix_part = ponente_match.group(2).strip()
                    
                    clean_name = name_part.replace('*', '').replace('_', '')
                    clean_name = clean_name.title()
                    
                    meta['Ponente'] = f"{clean_name}, {suffix_part}"
                    break
        
        # Fallback Ponente
        if not meta['Ponente']:
             penned_match = re.search(r'Penned by (?:Associate Justice)?\s*([A-Z\.\s,]+)', clean_text_content, re.IGNORECASE)
             if penned_match:
                 meta['Ponente'] = penned_match.group(1).strip()
        
        if not meta['Ponente']:
            for i in range(len(cleaned_lines) - 1, max(0, len(cleaned_lines) - 50), -1):
                line = cleaned_lines[i].strip()
                match = re.search(r'^([A-Z\.\s]+),\s*(?:J\.|C\.J\.|Chief Justice|Associate Justice)\.?\s*$', line)
                if match:
                    name = match.group(1).strip()
                    if len(name) > 3 and "CONCUR" not in name and "CERTIFICATION" not in name:
                        meta['Ponente'] = name.title() + ", J."
                        break

        # 5. Opinions
        parsed_opinions = []
        if raw_html:
            # Look for lines starting with unicode diamond or HTML entity
            # Capture everything until the next <br> or end of string
            header_matches = re.finditer(r'<br\s*/?>\s*(?:&#9830;|♦)\s*(.*?)(?=<br|[\r\n])', raw_html, re.IGNORECASE)
            
            for m in header_matches:
                line_html = m.group(1).strip()
                line_text = re.sub(r'<[^>]+>', '', line_html).strip() # clean tags
                line_text = re.sub(r'\s+', ' ', line_text)
                
                # Check if it is "Decision"
                if re.match(r'^Decision\b', line_text, re.IGNORECASE):
                    pass 
                else:
                    parsed_opinions.append(line_text)

        if parsed_opinions:
            meta['Opinions'] = "\n".join(parsed_opinions)
        else:
            opinions = []
            if re.search(r'SEPARATE\s+OPINION', clean_text_content, re.IGNORECASE):
                opinions.append("Separate")
            if re.search(r'CONCURRING\s+OPINION', clean_text_content, re.IGNORECASE):
                opinions.append("Concurring")
            if re.search(r'DISSENTING\s+OPINION', clean_text_content, re.IGNORECASE):
                opinions.append("Dissenting")
            
            if meta.get('Decided by') == "En Banc" and opinions:
                meta['Opinions'] = ", ".join(sorted(list(set(opinions))))
            else:
                 meta['Opinions'] = "None"
        
        return meta

    def sanitize_filename(self, text, max_length=150):
        """Sanitize text for use in Windows filenames and truncate to safe length"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, '_')
        text = re.sub(r'[_\s]+', '_', text)
        text = text.strip('_')
        if len(text) > max_length:
            text = text[:max_length]
        return text
    
    def extract_and_destroy_footnotes(self, soup):
        """
        Extracts footnote content and aggressively DELETES the footnote 
        section from the DOM.
        """
        footnotes = {}

        # 0. Lawphil Specific: Capture <nt> and <a class="nt"> tags BEFORE general cleanup
        # This handles the specific format used by Lawphil (both old and new)
        candidates = soup.find_all('nt') + soup.find_all('a', class_='nt')
        for tag in candidates:
            ref_num = tag.get_text().strip()
            if not ref_num.isdigit(): continue
            
            parent = tag.parent
            if parent and parent.name == 'p':
                full_text = parent.get_text().strip()
                # Heuristic: Tag is at start of paragraph
                if full_text.startswith(ref_num):
                    content = full_text[len(ref_num):].strip()
                    content = re.sub(r'^[\.\,\)\s]+', '', content)
                    footnotes[ref_num] = content
                    # Destroy parent to prevent duplicate text
                    parent.decompose()

        # 1. Capture content via SUP tags before deletion
        footer_markers = ["Endnotes", "Footnotes"]
        start_node = None
        
        for marker in footer_markers:
            found = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','b','strong','div', 'em', 'span'] 
                             and marker.lower() in tag.get_text().lower()
                             and len(tag.get_text()) < 50) 
            if found:
                if found.name in ['b', 'strong', 'em', 'span', 'font']:
                    block_parent = found.find_parent(['p', 'div', 'h1', 'h2', 'h3', 'h4'])
                    if block_parent: found = block_parent
                start_node = found
                break
        
        if start_node:
            siblings = list(start_node.find_all_next())
            pending_id = None
            
            for tag in siblings:
                text = tag.get_text().strip()
                if not text: continue
                
                # Case 1: Full match "1. Content" or "[1] Content"
                match_full = re.match(r'^\s*\[?(\d+)\]?[\.\):]?\s+(.+)', text, re.DOTALL)
                
                if match_full:
                    fid = match_full.group(1)
                    content = match_full.group(2)
                    if fid not in footnotes: footnotes[fid] = content
                    pending_id = None
                    continue

                # Case 2: Number only "1." or "[1]" (Split Tag Scenario)
                match_num = re.match(r'^\s*\[?(\d+)\]?[\.\):]?\s*$', text)
                if match_num:
                    pending_id = match_num.group(1)
                    continue
                
                # Case 3: Content only (Matches pending_id if exists)
                if pending_id:
                    if pending_id not in footnotes: footnotes[pending_id] = text
                    pending_id = None

            for sibling in list(start_node.find_next_siblings()):
                sibling.decompose()
            start_node.decompose()

        # 2. Fallback: Search for remaining <sup> tags
        if not footnotes:
            html_content = str(soup)
            pattern = re.compile(
                r'(?:<br\s*/?>\s*|<blockquote[^>]*>\s*|<p[^>]*>\s*)'
                r'<sup[^>]*>(\d+)</sup>\s*'
                r'(.*?)(?=(?:<br\s*/?>\s*)+<sup|</p>|</blockquote>|$)', 
                re.IGNORECASE | re.DOTALL
            )
            matches = pattern.findall(html_content)
            for fn_id, content in matches:
                clean_content = re.sub(r'<[^>]+>', '', content).strip()
                clean_content = re.sub(r'\s+', ' ', clean_content)
                footnotes[fn_id] = clean_content

        return footnotes

    def resolve_footnotes(self, footnotes):
        """
        RESOLVES "Id." and "Supra" citations to their full text.
        """
        resolved_footnotes = {}
        sorted_ids = sorted([int(k) for k in footnotes.keys()])
        
        for i in sorted_ids:
            fn_id = str(i)
            original_text = footnotes[fn_id]
            soup = BeautifulSoup(original_text, "html.parser")
            text_content = soup.get_text().strip()
            
            if re.match(r"^(Id\.|Ibid\.|Ibid|Id)\b", text_content, re.IGNORECASE):
                previous_id = str(i - 1)
                if previous_id in resolved_footnotes:
                    prev_text = resolved_footnotes[previous_id]
                    suffix_match = re.search(r"(at\s+.*|p\.\s+.*|, pp\.\s+.*)", text_content, re.IGNORECASE)
                    suffix = suffix_match.group(1) if suffix_match else ""
                    base_citation = prev_text
                    if suffix:
                         if base_citation.endswith("."): base_citation = base_citation[:-1]
                         resolved_footnotes[fn_id] = f"{base_citation}, {suffix}"
                    else:
                        resolved_footnotes[fn_id] = prev_text
                else:
                    resolved_footnotes[fn_id] = text_content
            elif "supra" in text_content.lower():
                match = re.search(r"(?:note|footnote)\s+(\d+)", text_content, re.IGNORECASE)
                if match:
                    target_id = match.group(1)
                    if target_id in resolved_footnotes:
                        target_text = resolved_footnotes[target_id]
                        suffix_match = re.search(r"(at\s+.*|p\.\s+.*|, pp\.\s+.*)", text_content, re.IGNORECASE)
                        suffix = suffix_match.group(1) if suffix_match else ""
                        base_citation = target_text
                        if suffix:
                             if base_citation.endswith("."): base_citation = base_citation[:-1]
                             resolved_footnotes[fn_id] = f"{base_citation}, {suffix}"
                        else:
                            resolved_footnotes[fn_id] = base_citation
                    else:
                        resolved_footnotes[fn_id] = text_content
                else:
                    resolved_footnotes[fn_id] = text_content
            else:
                resolved_footnotes[fn_id] = text_content

        return resolved_footnotes

    def process_inline_footnotes(self, markdown_text, html_footnotes=None):
        """
        Replaces [^N] markers with SMART inline citations.
        """
        footnotes = {}
        # 1. Parse existing MD footnotes
        md_footnote_pattern = re.compile(r'^\[\^(\d+)\]:\s*(.*?)(?=\n\[\^|$)', re.MULTILINE | re.DOTALL)
        for match in md_footnote_pattern.finditer(markdown_text):
            fn_id = match.group(1)
            content = match.group(2).strip()
            footnotes[fn_id] = content
            
        # 2. Merge HTML footnotes
        if html_footnotes:
            for fn_id, content in html_footnotes.items():
                footnotes[fn_id] = content

        if not footnotes:
            return markdown_text

        resolved_footnotes = self.resolve_footnotes(footnotes)

        # "Junk" keywords - Case-Specific Evidence to remove entirely
        junk_regex = [
            r'^[il]d[\.,\s]',      # "Id." or "ld." (Start only)
            r'^ibid', 
            r'^supra', 
            r'rollo',             # MATCH ANYWHERE
            r'tsn',               # MATCH ANYWHERE
            r'^see', 
            r'^note', 
            r'^annex',
            r'^exhibit',
            r'^report',
            r'p\.\s*\d+',         # Page numbers
            r'pp\.\s*\d+',
            r'^\d+\s*$',          # Just numbers
            r'decision\s+dated',  # Descriptions of lower court rulings
            r'resolution\s+dated',
            r'minutes\s+(?:of|on|dated)', # "Minutes of...", "Minutes on..."
            r'jbc\s+minutes',
            r'jbc\s+files',       # "JBC files of..."
            r'(?:orsn\s+)?report\s+dated', # "ORSN Report dated", "Report dated"
            r'letter\s+dated',    # "Letter dated..."
            r'hearing\s+on',      # "Hearing on..."
            r'reply',             # "Respondent's Reply..."
            r'memorandum',        # "Memorandum Ad Cautelam"
            r'comment\s+dated',
            r'sworn\s+statement',
            r'affidavit',
            r'attestation',
            r'jbc\s+announcement',
             # Watermarks
            r'chanrobles', r'cralaw', r'virtual\s+law\s+library', r'lawlibrary'
        ]

        def replace_match(match):
            footnote_id = match.group(1)
            if footnote_id in resolved_footnotes:
                content = resolved_footnotes[footnote_id]
                
                # Check using regex list
                for pattern in junk_regex:
                    if re.search(pattern, content, re.IGNORECASE):
                        return ""

                clean_content = content.replace('\n', ' ').strip()
                
                # --- SMART LINKING LOGIC ---
                gr_match = re.search(r"(G\.R\.\s*No[s]?\.?)\s*([L\d\-\s,&]+)", clean_content, re.IGNORECASE)
                final_output = clean_content
                
                if gr_match:
                    raw_nums = gr_match.group(2)
                    clean_num = re.split(r'[&,\s]', raw_nums)[0].strip()
                    final_output = f"[**{clean_content}**](app://case/GR{clean_num})"
                else:
                    final_output = f"**{clean_content}**"
                
                return f'<span class="smart-citation">({final_output})</span>'
            return ""

        new_text = re.sub(r'\[\^(\d+)\](?!:)', replace_match, markdown_text)
        new_text = re.sub(r'^\[\^(\d+)\]:.*', '', new_text, flags=re.MULTILINE)
        
        # --- NEW: Safe Mode Footer Cleaning (Stricter + Fallbacks) ---
        footer_markers = [
            r'^\s*\*\*NOTICE OF JUDGMENT\*\*',
            r'^\s*Notice of Judgment',
            r'^\s*Copy sent to:',
            r'^\s*footnotestext',
            # LEVEL 3: MARKDOWN LEVEL CLUTTER KILLER
            r'^\s*Welcome\s*\n\s*This\s+site\s+asks\s+for\s+consent', 
            r'^\s*This\s+site\s+asks\s+for\s+consent',
        ]
        for marker in footer_markers:
            match = re.search(marker, new_text, re.IGNORECASE | re.MULTILINE)
            if match:
                new_text = new_text[:match.start()]
                break 
        
        new_text = re.sub(r'(\n>\s*)+$', '', new_text)
        return new_text.strip()

    def clean_case_number(self, case_number):
        if not case_number: return None
        case_number = re.split(r'\s+-\s+', case_number)[0]
        case_number = re.split(r'\s+vs\.?\s+', case_number, flags=re.IGNORECASE)[0]
        case_number = re.split(r'\s+v\.?\s+', case_number, flags=re.IGNORECASE)[0]
        case_number = re.sub(r'[\.\s,:-]*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+.*$', '', case_number, flags=re.IGNORECASE)
        case_number = re.sub(r'[,\s]+$', '', case_number)
        case_number = re.sub(r'\.+$', '.', case_number)
        return case_number.strip()
    
    def extract_case_number(self, html_content, soup):
        try:
            prefixes = [r'G\.?\s*R\.?', r'A\.?\s*C\.?', r'A\.?\s*M\.?', r'B\.?\s*M\.?', r'Adj\.?\s*Res\.?', r'Adm\.?\s*Case', r'Adm\.?\s*Matter', r'UNAV', r'UDK', r'OCA', r'I\.?P\.?I\.?', r'R\.?T\.?J\.?', r'Misc\.?\s*Bar', r'Nos?\.?']
            prefix_group = "|".join(prefixes)
            prefix_pattern = f"(?:\\b(?:{prefix_group}))(?=\\W|$)"

            # Lookahead stoppers:
            # 1. Separators: - vs v
            # 2. Date with comma: Month DD, YYYY
            # 3. Date with colon: Month DD : YYYY (Common in ChanRobles)
            # 4. Closing bracket: ]
            # 5. End of line
            stopper_lookahead = r"(?=\s+-\s+|\s+vs\.?\s+|\s+v\.?\s+|" \
                                r"\s+[A-Z][a-z]+ \d{1,2}\s*[:\,]\s*\d{4}|" \
                                r"\]|" \
                                r"\s*$)"

            case_pattern = re.compile(f"({prefix_pattern}" + r".*?)" + stopper_lookahead, re.IGNORECASE | re.DOTALL)
            
            title_text = ""
            title_tag = soup.find('title')
            if title_tag: title_text = title_tag.get_text().strip()
            else: 
                 h3 = soup.find('h3')
                 if h3: title_text = h3.get_text().strip()
            
            if title_text:
                match = case_pattern.search(title_text)
                if match:
                    raw_case = match.group(1).strip("] ")
                    if len(raw_case) < 100: return self.clean_case_number(raw_case)
                    else:
                        truncated = raw_case.split('\n')[0]
                        if len(truncated) < 100: return self.clean_case_number(truncated)

            for header in soup.find_all(['h1', 'h2']):
                text = header.get_text().strip()
                match = re.search(fr"({prefix_pattern}.*?){stopper_lookahead}", text, re.IGNORECASE)
                if match:
                     raw_case = match.group(1).strip("] ")
                     if len(raw_case) < 100: return self.clean_case_number(raw_case)
                     else:
                        truncated = raw_case.split('\n')[0]
                        if len(truncated) < 100: return self.clean_case_number(truncated)
            return None
        except Exception as e:
            print(f"Error extracting case number: {e}")
            return None
    
    def extract_date(self, soup, year=None, month=None):
        try:
            def try_parse_date(date_str):
                formats = [
                    "%B %d, %Y",       # January 1, 2024
                    "%B %d : %Y",      # January 1 : 2024
                    "%b %d, %Y",       # Jan 1, 2024
                    "%B %d,%Y"         # January 1,2024
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                    except: continue
                return None

            strong_tags = soup.find_all('strong')
            for strong in strong_tags:
                text = strong.get_text()
                # Expanded regex
                match = re.search(r',?\s*([A-Z][a-z]+\s+\d{1,2}\s*[:\,]\s*\d{4})', text)
                if match:
                    parsed = try_parse_date(match.group(1))
                    if parsed: return parsed
            
            h2_tags = soup.find_all('h2')
            for h2 in h2_tags:
                text = h2.get_text()
                match = re.search(r',?\s*([A-Z][a-z]+\s+\d{1,2}\s*[:\,]\s*\d{4})', text)
                if match:
                    parsed = try_parse_date(match.group(1))
                    if parsed: return parsed

            title_tag = soup.find('title')
            if title_tag:
                 text = title_tag.get_text()
                 match = re.search(r'([A-Z][a-z]+\s+\d{1,2}\s*[:\,]\s*\d{4})', text)
                 if match:
                     parsed = try_parse_date(match.group(1))
                     if parsed: return parsed
            
            if year and month:
                try:
                    month_map = {'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3, 'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9, 'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12}
                    month_num = month_map.get(str(month).lower())
                    if month_num: return f"{year}-{month_num:02d}-01"
                except: pass
        except Exception as e:
            print(f"Error extracting date: {e}")
        return None

    def replace_with_retry(self, src, dst, retries=3, delay=1):
        for i in range(retries):
            try:
                if dst.exists(): dst.unlink()
                os.replace(src, dst)
                return True
            except OSError:
                if i < retries - 1: time.sleep(delay)
                else: raise
        return False

    def process_file(self, html_path, metadata=None, use_llm=False, overwrite=False):
        try:
            path_parts = Path(html_path).parts
            year = None
            month = None
            if len(path_parts) >= 3:
                for part in path_parts:
                    if part.isdigit() and len(part) == 4:
                        year = part
                        break
                month_candidate = path_parts[-2]
                if not month_candidate.isdigit(): month = month_candidate
            
            with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            case_number = self.extract_case_number(html_content, soup)
            date = self.extract_date(soup, year, month)
            
            if not case_number or case_number == 'Unknown':
                 if metadata: case_number = metadata.get('case_number', 'Unknown')
                 if not case_number or case_number == 'Unknown':
                    return {'status': 'failed', 'error': f"Missing case number: {html_path}", 'path': str(html_path)}
            
            if not date:
                 if metadata: date = metadata.get('date')
                 if not date:
                    return {'status': 'failed', 'error': f"Missing date: {html_path}", 'path': str(html_path)}
            
            safe_case_number = self.sanitize_filename(case_number)
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                formatted_date = f"{dt.strftime('%B')}_{dt.day}_{dt.year}"
            except Exception as e:
                formatted_date = date

            filename = f"{safe_case_number}_{formatted_date}.md"
            year_str = "Unknown"
            if year: year_str = str(year)
            elif date:
                 try: year_str = str(datetime.strptime(date, "%Y-%m-%d").year)
                 except: pass
                 
            year_dir = OUTPUT_DIR / year_str
            output_path = year_dir / filename
            
            if output_path.exists() and not overwrite:
                return {'status': 'skipped', 'error': 'File exists', 'path': str(html_path)}

            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.clean_soup_dom(soup)
            
            if self.is_garbage_file(soup):
                 return {'status': 'failed', 'error': f"Garbage File (Content too short or ads only): {html_path}", 'path': str(html_path)}
            
            markdown_body = self.clean_and_convert(html_content)
                
            if not markdown_body:
                return {'status': 'failed', 'error': f"Empty markdown output: {html_path}", 'path': str(html_path)}

            # --- OPTIMIZATION: HASH BODY ONLY ---
            # Calculate hash on the body content *before* adding the header.
            # This ensures that if the date parsing changes slightly (e.g. 01 vs 1),
            # but the case body is identical, we catch it as a duplicate.
            content_hash = hashlib.md5(markdown_body.encode('utf-8')).hexdigest()
            case_key = f"{case_number}|{date}"
            
            # Extract Title
            title = ""
            try:
                 t_tag = soup.find('title')
                 if t_tag: title = t_tag.get_text().strip()
                 else:
                        h3 = soup.find('h3')
                        if h3: title = h3.get_text().strip()
            except: pass

            # Build Header
            header = f"# {case_number} - {date}\n\n"
            if title:
                if len(title) > 300: title = title[:300] + "..."
                header += f"## {title}\n\n"
            
            final_markdown = header + markdown_body
            
            temp_path = output_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(final_markdown)
            
            self.replace_with_retry(temp_path, output_path)
            
            entry = {
                "source_html": str(html_path),
                "case_number": case_number,
                "date": date,
                "title": title,
                "output_md": str(output_path),
                "filename": filename
            }
            if metadata: entry["metadata"] = metadata
            
            return {
                'status': 'success',
                'entry': entry,
                'case_key': case_key,
                'content_hash': content_hash,
                'path': str(html_path)
            }
            
        except Exception as e:
            return {'status': 'failed', 'error': f"Error processing {html_path}: {e}", 'path': str(html_path)}
    
    def get_latest_cases(self, n=5):
        latest_dir = DOWNLOADS_DIR / "2024"
        if not latest_dir.exists(): return []
        html_files = []
        for root, dirs, files in os.walk(latest_dir):
            for file in files:
                if file.endswith('.html'):
                    html_files.append(Path(root) / file)
        html_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return html_files[:n]
    
    def get_random_cases(self, n=5):
        all_files = []
        sample_years = ['2020', '2010', '2000', '1990', '1980', '1970', '1960', '1950']
        for year in sample_years:
            year_dir = DOWNLOADS_DIR / year
            if year_dir.exists():
                for root, dirs, files in os.walk(year_dir):
                    for file in files:
                        if file.endswith('.html'):
                            all_files.append(Path(root) / file)
        if len(all_files) > n: return random.sample(all_files, n)
        return all_files
    
    def load_metadata(self, year):
        metadata_file = SC_SCRAPER_DIR / f"metadata_{year}.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load metadata for {year}: {e}")
        return []
    
    def run_test(self):
        print("=" * 80)
        print("TEST MODE: Converting 5 latest + 5 random cases")
        print("=" * 80)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        latest = self.get_latest_cases(5)
        random_cases = self.get_random_cases(5)
        test_cases = latest + random_cases
        print(f"\nFound {len(test_cases)} test cases to process\n")
        
        for html_path in test_cases:
            year = html_path.parts[-2] if len(html_path.parts) > 1 else None
            metadata = None
            if year and year.isdigit():
                metadata_list = self.load_metadata(year)
                file_id = html_path.stem
                if metadata_list:
                    for meta in metadata_list:
                        if str(meta.get('id', '')) == file_id:
                            metadata = meta
                            break
            
            result = self.process_file(html_path, metadata)
            self.stats["processed"] += 1
            if result['status'] == 'success':
                self.manifest.append(result['entry'])
                self.processed_cases.add(result['case_key'])
                self.processed_hashes[result['case_key']].add(result['content_hash'])
                self.stats['success'] += 1
                print(f"✅ Success: {result['path']}")
            else:
                self.stats['failed'] += 1
                self.stats['errors'].append(result['error'])
                print(f"❌ {result['error']}")

        with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)
        
        print(f"\nManifest saved to: {MANIFEST_FILE}")
        print(f"Markdown files saved to: {OUTPUT_DIR}")
    
    def collect_html_files(self, start_year=None, end_year=None):
        print(f"Scanning {DOWNLOADS_DIR} for HTML files...")
        found_files = []
        
        for root, dirs, files in os.walk(DOWNLOADS_DIR):
            if "Separate Opinions" in dirs:
                dirs.remove("Separate Opinions")
            if "Separate Opinions" in Path(root).parts:
                 continue

            for file in files:
                if file.endswith(".html"):
                    path = Path(root) / file
                    if start_year and end_year:
                        parts = path.parts
                        file_year = None
                        for part in reversed(parts):
                            if part.isdigit() and len(part) == 4:
                                file_year = int(part)
                                break
                        if file_year:
                            if start_year <= file_year <= end_year:
                                found_files.append(path)
                    else:
                        found_files.append(path)
                        
        found_files.sort(key=lambda x: str(x), reverse=True)
        return found_files

    def run_with_specific_tasks(self, tasks, workers=1, overwrite=False):
        from concurrent.futures import ProcessPoolExecutor, as_completed
        start_time = datetime.now()
        final_tasks_to_run = []
        if not overwrite:
            for t in tasks:
                if str(t[0]) not in self.processed_paths:
                    final_tasks_to_run.append(t)
                else:
                    self.stats["skipped"] += 1
            print(f"Skipping {len(tasks) - len(final_tasks_to_run)} already processed files.")
        else:
            final_tasks_to_run = tasks

        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(process_file_wrapper, t[0], t[1], False, overwrite): t[0] 
                for t in final_tasks_to_run
            }
            
            for i, future in enumerate(as_completed(future_to_file)):
                result = future.result()
                if i % 100 == 0:
                    percent = (i / len(final_tasks_to_run)) * 100 if len(final_tasks_to_run) > 0 else 0
                    print(f"Progress: {i}/{len(final_tasks_to_run)} ({percent:.1f}%) - {self.stats['processed']} processed")
                
                self.stats["processed"] += 1
                
                if result['status'] == 'success':
                    case_key = result['case_key']
                    content_hash = result['content_hash']
                    entry = result['entry']
                    is_duplicate = content_hash in self.processed_hashes[case_key]
                    
                    if hasattr(self, 'duplicates_dir') and self.duplicates_dir:
                        if is_duplicate: self.stats["skipped"] += 1
                        else:
                             self.manifest.append(entry)
                             self.processed_cases.add(case_key)
                             self.processed_hashes[case_key].add(content_hash)
                             self.stats["success"] += 1
                    else:
                        if is_duplicate and not overwrite: 
                            self.stats["skipped"] += 1
                            try: Path(entry['output_md']).unlink() 
                            except: pass
                        else:
                            self.manifest.append(entry)
                            self.processed_cases.add(case_key)
                            self.processed_hashes[case_key].add(content_hash)
                            self.stats["success"] += 1
                
                elif result['status'] == 'skipped':
                     self.stats["skipped"] += 1
                else:
                    self.stats["failed"] += 1
                    self.stats["errors"].append(result['error'])
                
                if i % 500 == 0:
                     with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
                         json.dump(self.manifest, f, indent=2, ensure_ascii=False)
        
        with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)
            
        print("\n" + "=" * 80)
        print("CONVERSION COMPLETE")
        print("=" * 80)
        print(f"Processed: {self.stats['processed']}")
        print(f"Success:   {self.stats['success']}")
        print(f"Failed:    {self.stats['failed']}")
        print(f"Skipped:   {self.stats['skipped']}")
        
        if self.stats['errors']:
            error_log = OUTPUT_DIR / "conversion_errors.txt"
            with open(error_log, "w", encoding="utf-8") as f:
                for err in self.stats['errors']:
                    f.write(err + "\n")
            print(f"Errors written to: {error_log}")

    def run_full_conversion(self, workers=1, clean=False, start_year=None, end_year=None, overwrite=False, file_list=None):
        if clean and OUTPUT_DIR.exists():
            print(f"Cleaning output directory: {OUTPUT_DIR}")
            shutil.rmtree(OUTPUT_DIR)
            OUTPUT_DIR.mkdir()
        
        if not clean and MANIFEST_FILE.exists():
            try:
                with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
                    self.manifest = json.load(f)
                    for entry in self.manifest:
                        case_key = f"{entry['case_number']}|{entry['date']}"
                        self.processed_cases.add(case_key)
                        self.processed_paths.add(entry['source_html'])
            except Exception as e:
                print(f"Error loading manifest: {e}")
        
        html_files = []
        if file_list:
            if isinstance(file_list, list):
                html_files = [Path(p) for p in file_list]
            elif isinstance(file_list, (str, Path)):
                with open(file_list, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line: html_files.append(Path(line))
        else:
             html_files = self.collect_html_files(start_year, end_year)
        
        print(f"Found {len(html_files)} HTML files to process")
        
        tasks = []
        for html_path in html_files:
            tasks.append((html_path, None))
            
        print(f"Queueing {len(tasks)} files for conversion (Workers: {workers})...")
        self.run_with_specific_tasks(tasks, workers=workers, overwrite=overwrite)

# Wrapper for multiprocessing
def process_file_wrapper(html_path, metadata=None, use_llm=False, overwrite=False):
    converter = CaseConverter()
    return converter.process_file(html_path, metadata, use_llm, overwrite)

def main():
    parser = argparse.ArgumentParser(description='Convert SC HTML cases to markdown')
    parser.add_argument('--test', action='store_true', help='Run test mode (5 latest + 5 random)')
    # Defaulting to 8 workers based on T16 Ryzen 7 profile
    parser.add_argument('--workers', type=int, default=8, help='Number of parallel workers (default: 8)')
    parser.add_argument('--retry-errors', type=str, help='Path to error log file to retry specific failures')
    parser.add_argument('--save-duplicates-to', type=str, help='Directory to save duplicate files instead of deleting them')
    parser.add_argument('--clean', action='store_true', help='Delete output directory before starting')
    parser.add_argument('--start-year', type=int, help='Start year filter (inclusive)')
    parser.add_argument('--end-year', type=int, help='End year filter (inclusive)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing output files')
    parser.add_argument('--file-list', type=str, help='Path to text file containing list of HTML files to process')
    parser.add_argument('--continuous', action='store_true', help='Run in continuous mode watching for new files')
    
    args = parser.parse_args()
    
    converter = CaseConverter()
    
    if args.save_duplicates_to:
        dup_dir = Path(args.save_duplicates_to)
        dup_dir.mkdir(parents=True, exist_ok=True)
        converter.duplicates_dir = dup_dir
    
    if args.test:
        converter.run_test()
    else:
        if args.continuous:
            print(f"Starting CONTINUOUS conversion mode (Workers: {args.workers})...")
            print("Press Ctrl+C to stop.")
            
            while True:
                try:
                    converter.run_full_conversion(
                        workers=args.workers, 
                        clean=False,
                        start_year=args.start_year, 
                        end_year=args.end_year,
                        overwrite=args.overwrite,
                        file_list=args.file_list
                    )
                    
                    print("Waiting 30 seconds for new files...")
                    time.sleep(30)
                except KeyboardInterrupt:
                    print("Stopping continuous conversion.")
                    break
                except Exception as e:
                    print(f"Error in continuous loop: {e}")
                    time.sleep(30)
        else:
            converter.run_full_conversion(
                workers=args.workers, 
                clean=args.clean, 
                start_year=args.start_year, 
                end_year=args.end_year,
                overwrite=args.overwrite,
                file_list=args.file_list
            )

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
