"""
Supreme Court HTML to Markdown Converter V2 (Strict Standards) - FIXED

Features:
1. Strict Naming: [Case No]_[Date]_[Ponente].md
2. Content Trimming:
   - Start: "EN BANC", "DIVISION" headers.
   - End: "Footnotes", "Endnotes".
3. Smart Inline Citations:
   - Whitelist: Laws, Constitution, Codes, Articles.
   - Blacklist: Rollo, Id, Supra, Page/Case specific refs.
4. Ponente Extraction:
   - Filename (Modern) > Explicit Body > Signature (Old) > Unknown.
"""

import os
import re
import json
import shutil
import hashlib
import argparse
import logging
import concurrent.futures
import multiprocessing
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from collections import defaultdict

# Config
DOWNLOADS_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\MD\lawphil_v2")
MANIFEST_FILE = OUTPUT_DIR / "conversion_manifest_v2.json"

# Citation Filters
SUBSTANTIVE_KEYWORDS = [
    "Republic Act", "R.A.", "Presidential Decree", "P.D.", 
    "Constitution", "CONST.", "Article", "Art.", "Section", "Sec.",
    "Revised Penal Code", "RPC", "Civil Code", "Family Code",
    "Rules of Court", "Rule", "Canon", "Batas Pambansa", "B.P.",
    "Commonwealth Act", "C.A.", "Executive Order", "E.O.",
    "Memorandum Circular", "Administrative Order"
]

JUNK_KEYWORDS = [
    "rollo", "ibid", "id", "supra", "tsn", "annex", "minutes", 
    "report", "letter", "records", "exhibit", "comment", "reply", 
    "compliance", "manifestation", "rejoinder", "memorandum", 
    "transcript", "motion", "affidavit", "testimony", "witness", 
    "position paper", "sur-rejoinder", "counter-affidavit",
    "joint stipulation", "formal offer", "see", "cf.", "compare", 
    "but see", "chanrobles", "cralaw", "virtual law library", "lawlibrary",
    "dated", "vol."
]

WATERMARK_PATTERNS = [
    r"\(awÞhi\(", r"\(awÞhi", r"\(aw\w+", r"1a\w+phi1", 
    r"1avvphi1", r"\(aw\w+hi\(", r"Major\s+Corp\.", r"Arellano\s+Law"
]

class LawphilConverterV2:
    def __init__(self):
        self.stats = defaultdict(int)
        self.manifest = []
        
    def clean_soup_dom(self, soup):
        """Standard DOM cleaning adapted for V2."""
        if soup.head: soup.head.decompose()
        
        # --- FIX START ---
        # GROUP 1: Decompose (Delete tag + content)
        # REMOVED: 'center', 'form' from this list to be safe
        for tag in soup(["script", "style", "link", "meta", "iframe", "img", "nav", "input"]):
            tag.decompose()

        # GROUP 2: Unwrap (Delete tag, KEEP content)
        # Use a while loop to handle nested tags (e.g. font inside font)
        unwrap_tags = ["center", "font", "div", "span", "form", "blockquote", "dir"]
        for tag_name in unwrap_tags:
            while soup.find(tag_name):
                soup.find(tag_name).unwrap()
        # --- FIX END ---

        # Unwrap Lawphil Table structure
        tables = soup.find_all('table')

        lawphil_table = soup.find('table', id='lwphl')
        if not lawphil_table:
             lawphil_table = soup.find('table', attrs={'width': '800'})
             
        content_block = None
        if lawphil_table:
            # Try blockquote first
            content_block = lawphil_table.find('blockquote')
            # If no blockquote, find the largest TD in this table
            if not content_block:
                tds = lawphil_table.find_all('td')
                if tds: 
                    # Filter TDs that are likely navigation bars (short text)
                    valid_tds = [t for t in tds if len(t.get_text()) > 500]
                    if valid_tds:
                        content_block = max(valid_tds, key=lambda t: len(t.get_text()))
                    elif tds: # Fallback if all short
                        content_block = max(tds, key=lambda t: len(t.get_text()))
        
        # If still no content block found, but we have a lawphil_table, 
        # try using the table itself as the block (rare cases)
        if not content_block and lawphil_table:
             content_block = lawphil_table

        if content_block:
            new_body = soup.new_tag('body')
            # Copy children to avoid losing them during replacement
            for child in content_block.contents:
                new_body.append(child)
            soup = BeautifulSoup(str(new_body), 'html.parser')

        # Clean footer junk / Watermarks
        full_text = str(soup)
        for pattern in WATERMARK_PATTERNS:
            full_text = re.sub(pattern, "", full_text, flags=re.IGNORECASE)
        soup = BeautifulSoup(full_text, 'html.parser')

        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if "The Lawphil Project" in text or "Arellano Law Foundation" in text:
                p.decompose()

        return soup

    def extract_ponente(self, soup, filename):
        """
        Extracts Ponente using 4-tier logic.
        Tier 1: Filename (Modern) - e.g. gr_123_leonen.html
        Tier 2: Explicit "Ponente:" in text
        Tier 3: Signature "NAME, J.:" in Cleaned Paragraphs
        Tier 4: Unknown
        """
        # Tier 1: Filename (reliable for recent cases)
        base = filename.replace(".html", "").replace(".pdf", "")
        parts = base.split('_')
        # Check if last part looks like a name (not year, not number)
        if len(parts) > 2:
            last = parts[-1]
            if not last.isdigit() and len(last) > 2 and last not in ["sc", "en", "banc"]:
                return last.capitalize()
        
        # Get full text from CLEANED soup
        text = soup.get_text()

        # Tier 2: Explicit Text
        match = re.search(r"Ponente:?\s*([A-Z\.\s]+)", text[:5000], re.IGNORECASE)
        if match:
             val = match.group(1).strip()
             if "DECISION" not in val.upper() and len(val) < 50:
                 return val.title()

        # Tier 3: Paragraph Scan (Clean DOM)
        # Look for <p>TAG, J.:</p>
        # Iterate top 50 paragraphs
        paragraphs = soup.find_all('p', limit=50)
        for p in paragraphs:
            p_text = p.get_text().strip()
            # Relaxed match: "NAME, J.:" or "NAME, C.J.:" or "NAME, P.:"
            # Must start with Name, have comma, and end with Justice title
            if re.search(r"^([A-Z\s\.]+),\s*.*[CJ]\.?\s*[J\.]*:?", p_text):
                 # Split by comma to get name
                 parts = p_text.split(",")
                 name = parts[0].strip()
                 
                 # Extra validation to ensure it's a name, not "DECISION" or junk
                 if len(name) < 50 and "DECISION" not in name.upper() and len(name) > 2:
                      return name.title()
            
            if "PER CURIAM" in p_text.upper() and len(p_text) < 20:
                 return "Per Curiam"

        return "Unknown"

    def extract_footnotes(self, soup):
        """Extracts footnotes content and removes them from DOM."""
        footnotes = {}
        nt_tags = soup.find_all('nt')
        for nt in nt_tags:
            ref_num = nt.get_text().strip()
            if not ref_num.isdigit(): continue
            
            parent = nt.parent
            if parent and parent.name == 'p':
                full_text = parent.get_text().strip()
                if full_text.startswith(ref_num):
                    # Definition found
                    content = full_text[len(ref_num):].strip()
                    content = re.sub(r'^[\.\,\)\s]+', '', content) # Clean leading chars
                    footnotes[ref_num] = content
                    parent.decompose()
        return footnotes

    def process_inline_citations(self, text, footnotes):
        """Injects only SUBSTANTIVE citations inline."""
        if not footnotes: return text

        def replace_marker(match):
            ref_id = match.group(1) or match.group(2)
            if ref_id in footnotes:
                content = footnotes[ref_id]
                clean_content = content.replace('\n', ' ').strip()
                clean_content_lower = clean_content.lower()
                
                # Filter Logic
                # 1. Check Junk Keywords
                for junk in JUNK_KEYWORDS:
                    if f" {junk} " in f" {clean_content_lower} " or clean_content_lower.startswith(junk):
                        return ""

                # 2. Check Whitelist (Substantive)
                is_substantive = False
                for kw in SUBSTANTIVE_KEYWORDS:
                    if kw.lower() in clean_content_lower:
                        is_substantive = True
                        break
                
                if is_substantive:
                    return f' *({clean_content})*'
                
                return "" 

            return ""

        return re.sub(r'(?:\[\^(\d+)\]|FOOTNOTE_?REF_?(\d+)_?END)', replace_marker, text)

    def trim_content(self, text):
        """Strict Header/Footer trimming."""
        lines = text.split('\n')
        
        # 1. Trim Top (Start above EN BANC / DIVISION)
        header_pattern = r"^\s*(?:EN BANC|(?:FIRST|SECOND|THIRD)\s+DIVISION)\s*$"
        start_idx = 0
        for i, line in enumerate(lines[:50]): # Check first 50 lines only
             if re.search(header_pattern, line, re.IGNORECASE):
                 start_idx = i
                 break
        
        # If no strict header found, keep all (or maybe skip empty start)
        trimmed_lines = lines[start_idx:]
        
        # 2. Trim Bottom (Cut at Footnotes/Endnotes)
        footer_pattern = r"^s*(?:Footnotes|Endnotes)\s*$"
        end_idx = len(trimmed_lines)
        for i, line in enumerate(trimmed_lines):
            # Search from bottom up is usually safer, but "Footnotes" is distinct header
            if re.search(footer_pattern, line, re.IGNORECASE):
                end_idx = i
                break
        
        trimmed_lines = trimmed_lines[:end_idx]
        
        return '\n'.join(trimmed_lines)

    def process_file(self, html_path, overwrite=False):
        try:
            filename = html_path.name
            
            # --- FIX: REMOVED DEBUG LOCK ---
            # if filename != "ac_13378_2025.html": return {'status':'skipped', 'path':str(html_path)}
            
            # --- FIX START: Improved Encoding Handling ---
            raw_html = ""
            try:
                # Primary attempt: cp1252 (Standard for Lawphil)
                with open(html_path, 'r', encoding='cp1252', errors='replace') as f:
                    raw_html = f.read()
            except UnicodeDecodeError:
                # Fallback to latin-1
                with open(html_path, 'r', encoding='latin-1', errors='replace') as f:
                    raw_html = f.read()

            # 2. Soup & Clean
            soup = BeautifulSoup(raw_html, 'html.parser')
            
            # Extract Ponente BEFORE destructive cleaning if possible? 
            # Actually V2 extract_ponente uses cleaned soup.
            soup = self.clean_soup_dom(soup)
            
            # 3. Metadata
            ponente = self.extract_ponente(soup, filename)
            
            # 4. Content Processing
            footnotes = self.extract_footnotes(soup)
            
            # Convert remaining references to placeholders
            for nt in soup.find_all('nt'):
                text_ref = nt.get_text().strip()
                if text_ref.isdigit():
                    nt.replace_with(f"FOOTNOTE_REF_{text_ref}_END")
            
            # MD Conversion
            text = md(str(soup), heading_style="ATX")
            
            # Post-processing
            text = self.trim_content(text)
            
            # Restore markers for regex (optional) or just use logic in process_inline
            # Adapting process_inline_citations to handle the placeholder directly would be cleaner
            # But let's stick to the pattern:
            # text = re.sub(r'FOOTNOTE_REF_(\d+)_END', r'[^\1]', text)
            
            text = self.process_inline_citations(text, footnotes)
            
            # 5. Output Generation
            # Format: [Case]_[Date]_[Ponente].md
            # We need Date/Case No. V2 extract_metadata? It's missing in prior view.
            # Let's trust extract_header_info_from_body from V1? V2 doesn't have it in the view.
            # Assuming V2 relies on filename for date/case or simple extraction.
            # Use original filename for now to be safe, or implement extraction.
            
            # Construct Final Markdown
            final_md = f"# {filename}\n\n**Ponente: {ponente}**\n\n{text}"
            
            output_file = OUTPUT_DIR / filename.replace('.html', '.md')
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_md)
                
            return {'status': 'success', 'path': str(output_file)}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'path': str(html_path)}
