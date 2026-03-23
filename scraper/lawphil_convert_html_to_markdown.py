"""
Supreme Court HTML to Markdown Converter (Lawphil Specific Optimized) - Table Fix + No LLM

Converts Lawphil scraped HTML case files to markdown with:
1. Smart Inline Citations (Resolves "Id.", links G.R. Nos, filters junk).
2. Targeted Lawphil DOM cleaning (Handling table#lwphl, class="cb", class="jn").
3. Specific support for <nt> tags used in both text and footnotes.
4. Preserves Tables (Q&A sections) by not stripping table tags.
"""

import os
import json
import shutil
import re
import random
import time
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import argparse
import hashlib
from collections import defaultdict
import concurrent.futures
import multiprocessing
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Directories - Using getenv with relative defaults for portability
SC_SCRAPER_DIR = Path(os.getenv("SC_SCRAPER_DIR", "./sc_scraper"))
DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./data/MD/lawphil"))
MANIFEST_FILE = OUTPUT_DIR / "conversion_manifest.json"

def flow_is_descendant(node, ancestor):
    """Checks if node is a descendant of ancestor."""
    for parent in node.parents:
        if parent == ancestor:
            return True
    return False

def process_inline_footnotes_simple(markdown_text):
    """
    detects [1], [2] etc and converts to [^1], [^2].
    Limits to 1-3 digits to avoid catching [1994] years.
    """
    # 1. Inline markers: "text [1] text" -> "text [^1] text"
    def repl(m):
        return f"[^{m.group(1)}]"
    
    # Replace [1]...[999] with [^1]...[^999]
    text = re.sub(r'\[(\d{1,3})\]', repl, markdown_text)
    
    # 2. Definitions: Markdownify usually leaves them as "[^1] Text" or "[^1]Text" at start of line
    # We want standard markdown "[^1]: Text"
    
    def def_repl(m):
        return f"[^{m.group(1)}]:"
        
    # Regex looks for [^1] at start of line, followed by space or immediately text?
    # SC ELib converter used: r'^\[\^(\d+)\]\s+'
    # Let's be robust and include optional colon just in case
    text = re.sub(r'^\[\^(\d+)\]:?\s*', def_repl, text, flags=re.MULTILINE)
    
    return text


class CaseConverter:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.stats = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        self.manifest = []
        self.processed_cases = set()
        self.processed_hashes = defaultdict(set)
        self.processed_paths = set()
        self.duplicates_dir = None

    def clean_soup_dom(self, soup):
        """
        Specific DOM cleaning for Lawphil structure.
        Target: <table id="lwphl"> -> <blockquote>
        """
        if soup.head: 
            soup.head.decompose()

        # Remove scripts and styles immediately
        for tag in soup(["script", "style", "link", "meta", "iframe", "img"]):
            tag.decompose()

        # --- LAWPHIL SPECIFIC UNWRAPPING ---
        lawphil_table = soup.find('table', id='lwphl')
        
        if not lawphil_table:
            lawphil_table = soup.find('table', attrs={'width': '800'})

        content_block = None
        if lawphil_table:
            # Try to use the table itself as the block
            content_block = lawphil_table
        
        if content_block:
            # CONSOLIDATE FOOTNOTES: Move any orphan footnotes into the content block
            # This handles 2021+ layouts where footnotes are siblings to the content table
            all_notes = soup.find_all('nt') + soup.find_all('a', class_='nt')
            for tag in all_notes:
                # Find the container (usually a P tag)
                container = tag.find_parent('p') or tag.parent
                if container:
                    # Check if container is already inside content_block
                    if not flow_is_descendant(container, content_block):
                        # Move it to the end of content_block
                        # We append it to a new row or just the end?
                        # Appending to the last TD is safest if it's a table
                        if content_block.name == 'table':
                            last_td = content_block.find_all('td')[-1] if content_block.find_all('td') else content_block
                            last_td.append(container)
                        else:
                            content_block.append(container)

            # Create a new clean body with just the content
        # CRITICAL FIX: Use .contents directly instead of regex to avoid content loss
        if content_block.name == 'table':
            # Don't use regex - it can corrupt nested structures
            # Instead, extract all children and convert to string
            inner_html = "".join([str(child) for child in content_block.children])
            
            # CRITICAL FIX: Also capture sibling content after the table
            # Many Lawphil cases have separate opinions OUTSIDE the main table
            post_table_content = []
            for sibling in content_block.find_next_siblings():
                # Skip footer/junk elements
                sibling_text = sibling.get_text().strip()
                if len(sibling_text) < 50 and ("Lawphil" in sibling_text or "Arellano" in sibling_text):
                    continue  # Skip footers
                post_table_content.append(str(sibling))
            
            # Append post-table content to inner_html
            if post_table_content:
                inner_html += "\n" + "\n".join(post_table_content)
        else:
            # If it's a td, div, or blockquote, just get inner HTML directly
            inner_html = "".join([str(x) for x in content_block.contents])
            
        # Re-parse as new body
        soup = BeautifulSoup(inner_html, 'html.parser')

        # Unwrap structural tags to flatten the layout
        # 1. unwrapping html/body metadata wrappers if any
        if soup.html: soup.html.unwrap()
        if soup.body: soup.body.unwrap()

        # Pre-pass: Protect Signature Tables/Data Tables
        # We look for tables that are likely CONTENT, not LAYOUT
        # Heuristic: Borders, or contains "Associate Justice", or specific width/align combinations?
        # Lawphil Signature table: width="90%", align="center", contains "Associate Justice"
        
        protected_tables = []
        for t in soup.find_all('table'):
            t_text = t.get_text()
            if "Associate Justice" in t_text or "Chief Justice" in t_text:
                # Rename to prevent unwrapping
                t.name = "protected_table"
                protected_tables.append(t)

        # 2. unwrap main layout table container  
        while True:
            t = soup.find(['table', 'tbody', 'thead', 'tfoot'], recursive=False)
            if t:
                parent = t.parent
                if parent:
                    for child in list(t.children):
                        parent.insert(parent.contents.index(t), child)
                    t.decompose()
                else:
                    break
            else:
                break

        # 3. unwrap all layout rows (TR)
        for tr in list(soup.find_all('tr', recursive=False)):
            parent = tr.parent
            if parent:
                # Add spacing before row
                parent.insert(parent.contents.index(tr), soup.new_string('\n'))
                for child in list(tr.children):
                    parent.insert(parent.contents.index(tr), child)
                tr.decompose()

        # 4. unwrap all layout cells (TD/TH)
        for td in list(soup.find_all(['td', 'th'], recursive=False)):
            parent = td.parent
            if parent:
                # Add spacing before cell content
                parent.insert(parent.contents.index(td), soup.new_string('\n'))
                for child in list(td.children):
                    parent.insert(parent.contents.index(td), child)
                td.decompose()
        
        # Restore protected tables (signature tables)
        for t in protected_tables:
            t.name = "table"
            # Force spacing for cells to prevent run-on text
            for td in t.find_all('td'):
                td.insert_after(soup.new_string(" <br><br> "))
            
            # Ensure internal BRs are spaced
            for br in t.find_all('br'):
                br.replace_with(" <br> ") 

        # Clean specific Lawphil artifacts
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            # Safety check: Footers are short. If p contains the whole doc due to bad HTML, skip deletion.
            if len(text) < 300:
                if "The Lawphil Project" in text or "Arellano Law Foundation" in text:
                    p.decompose()

        return soup

    def extract_metadata_from_head(self, html_content):
        """Extracts metadata specifically from Lawphil meta tags before soup cleaning."""
        soup = BeautifulSoup(html_content, 'html.parser')
        meta_data = {}
        
        # <meta name="subject" content="..."> (Usually Case Title)
        subject = soup.find('meta', attrs={'name': 'subject'})
        if subject: meta_data['title'] = subject.get('content')
        
        # <title> (Usually G.R. No.)
        title_tag = soup.find('title')
        if title_tag: meta_data['case_number'] = title_tag.get_text().strip()
        
        return meta_data

    def extract_header_info_from_body(self, soup):
        """
        Extracts G.R. No and Date from Lawphil's specific header format:
        <p class="cb">[ G.R. No. 273136, August 20, 2024 ]</p>
        """
        info = {'case_number': None, 'date': None}
        
        # Define search strategies in order of reliability
        search_groups = [
            soup.find_all('p', class_='cb'), # Standard Lawphil
            soup.find_all('b'),              # Bold headers
            soup.find_all('p')[:20]          # First 20 paragraphs fallback
        ]

        for group in search_groups:
            # If we already have both, stop
            if info['case_number'] and info['date']: break
            
            if not group: continue

            for tag in group:
                text = tag.get_text().strip()
                
                # Check 1: Full Header Pattern [GR, Date]
                # Pattern: [ G.R. No. XXXXX, Month DD, YYYY ] (optional brackets)
                # match = re.search(r'\[?\s*(G\.?R\.?.*?),\s*([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})\s*\]?', text, re.IGNORECASE)
                
                # More robust pattern that doesn't require brackets
                match = re.search(r'(G\.?R\.?.*?),\s*([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})', text, re.IGNORECASE)
                
                if match:
                    if not info['case_number']: info['case_number'] = match.group(1).strip()
                    if not info['date']: info['date'] = match.group(2).strip()
                
                # Check 2: Isolated Date (if not yet found)
                if not info['date']:
                    # Strict date pattern: Month DD, YYYY
                    date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})', text)
                    if date_match:
                         # Extra validation to avoid catching random dates in text logic
                         # Only accept if the text is short (likely a header) or contains GR/No
                         if len(text) < 100 or "G.R." in text:
                            try:
                                dt_str = date_match.group(1).replace(",", "")
                                datetime.strptime(dt_str, "%B %d %Y")
                                info['date'] = date_match.group(1)
                            except: pass
                
                # Check 3: Isolated Case Number (if not yet found)
                if not info['case_number']:
                    if "G.R." in text or "No." in text:
                        clean_no = text.replace("[", "").replace("]", "").strip()
                        # heuristic to avoid grabbing long sentences
                        # Must contain G.R. to be safe
                        if len(clean_no) < 50 and "G.R." in clean_no:
                            # Fix: Check if it contains a date and strip it (more aggressive than $)
                                date_match_coupled = re.search(r'([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})', clean_no)
                                if date_match_coupled:
                                    extracted_date = date_match_coupled.group(1)
                                    clean_no = clean_no.replace(extracted_date, "").strip()
                                
                                info['case_number'] = clean_no

            # If we found at least the date, we can probably stop being aggressive
            # But let's keep going if case_number is missing
            if info['date'] and info['case_number']:
                break

        return info
        
    def normalize_html_footnotes(self, soup):
        """
        Converts Lawphil <nt> tags to standard [N] markers.
        Instead of destroying them, we normalize them so markdownify can see them.
        Also handles <sup>N</sup> if they seem to be footnotes.
        """
        # Find both <nt> tags and <a class="nt"> tags, and also <sup>
        candidates = soup.find_all('nt') + soup.find_all('a', class_='nt') + soup.find_all('sup')
        
        for tag in candidates:
            ref_num = tag.get_text().strip()
            # Allow digits OR special chars like *, but for SUP, be stricter?
            if not ref_num: continue
            
            # For <sup>, ensure it looks like a footnote (digits or single char)
            if tag.name == 'sup':
                # Avoid converting "1st", "2nd" to [1st]
                if not re.match(r'^(\d+|[*â€ ])$', ref_num):
                    continue

            
            parent = tag.parent
            if parent and parent.name == 'p':
                full_text = parent.get_text().strip()
                
                # Check if this is a DEFINITION (starts with the number)
                # e.g. "1 Text..."
                if full_text.startswith(ref_num):
                    # It's a definition.
                    # We want to ensure it looks like "[1] Text..."
                    # Check if it already has brackets? Unlikely in HTML.
                    
                    # We replace the TAG with "[ref_num]".
                    # The parent P text will then become "[1] Text..." which is what we want.
                    tag.replace_with(f"[{ref_num}]")
                    
                    # Ensure space after?
                    # If html was <a>1</a>Text, now it is [1]Text. 
                    # We might want [1] Text.
                    # But let's leave it to markdownify, regex can handle [^1]:?
                else:
                    # It's a REFERENCE in text.
                    # "...text <nt>1</nt> text..."
                    tag.replace_with(f"[{ref_num}]")
            else:
                # Fallback for non-P parents
                tag.replace_with(f"[{ref_num}]")


    def clean_and_convert(self, html_content, soup=None):
        """Consolidated cleaning function."""
        if not soup:
            soup = BeautifulSoup(html_content, "html.parser")
            soup = self.clean_soup_dom(soup)
        
        # Step 1: Normalize Footnotes (Don't destroy)
        # Convert <nt> to [N]
        self.normalize_html_footnotes(soup)

        # Step 2: Handle Text-Inline Tags (REMOVED - normalize_html_footnotes does it)
        # remaining_tags = soup.find_all('nt') + soup.find_all('a', class_='nt')
        # for tag in remaining_tags: ...

        # Step 3: Convert to Markdown
        # CRITICAL: Do NOT strip blockquote - separate opinions are often wrapped in blockquote tags
        text = md(str(soup), heading_style="ATX", 
                  strip=['img', 'a', 'table', 'thead', 'tbody', 'th', 'tr', 'td', 'center', 'font', 'span', 'div', 'style', 'script', 'dir']) 
        
        # Reformat markers: FOOTNOTE_REF_1_END -> [^1] (REMOVED - we use [1] now)
        # text = re.sub(r'FOOTNOTE[_\\]*REF[_\\]*(.+?)[_\\]*END', r'[^\1]', text)

        # Step 4: Cleaning Artifacts
        text = self.remove_lawphil_watermarks(text)

        # Step 5: Clean Lines & Headers
        lines = text.split('\n')
        cleaned_lines = []
        
        start_collecting = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped: continue
            
            # --- TOP TRIMMING LOGIC ---
            if not start_collecting:
                header_text = stripped.upper().replace('*', '').strip()
                if "DIVISION" in header_text or "EN BANC" in header_text:
                    start_collecting = True
                else:
                    continue

            # --- BOTTOM TRIMMING LOGIC ---
            # SC ELib logic handles bottom trimming via "Credit" check in HTML phase.
            # Here we just rely on markdown.
            # With reorganize_footnotes, we don't want to cut footnotes randomly.
            
            # Fix Headers
            if re.match(r'^\*\*[^*]+\*\*$', stripped) and len(stripped) < 100:
                header_text = stripped.replace('*', '').strip()
                if any(x in header_text.upper() for x in ["DECISION", "RESOLUTION", "EN BANC", "DIVISION", "SEPARATE OPINION"]):
                    stripped = f"## {header_text}"
                else:
                    stripped = f"### {header_text}"

            cleaned_lines.append(stripped)

        if not cleaned_lines:
            # Fallback if no division header found
             for line in lines:
                stripped = line.strip()
                if not stripped: continue
                cleaned_lines.append(stripped)

        final_text = '\n\n'.join(cleaned_lines)
        
        # Collapse multiple empty blockquote lines
        # Pattern: (> [space]* newline) repeated 2 or more times -> single > newline
        final_text = re.sub(r'(?:^>\s*\n){2,}', '>\n', final_text, flags=re.MULTILINE)
        
        final_text = re.sub(r'\n{3,}', '\n\n', final_text)
        
        # Step 6: Smart Inline Citation Injection (REMOVED - User Request)
        # final_text = self.process_inline_footnotes(final_text, extracted_footnotes)
        
        # Step 7: Linear Footnote Processing (NEW - User Request)
        final_text = self.process_linear_footnotes(final_text)

        # Step 8: Extract Metadata (SKIPPED)
        
        return final_text.strip()

        
        # Step 7: Extract Metadata (SKIPPED - User Requested Removal of Frontmatter)
        # meta = self.extract_metadata(soup, final_text, html_content)
        
        # Return only the body text without YAML header
        return final_text.strip()

    def remove_lawphil_watermarks(self, text):
        watermarks = [
            r"The Lawphil Project - Arellano Law Foundation",
            r"\(awÞhi\(", r"\(awÞhi", r"\(aw\w+",
            r"1a\w+phi1", r"1avvphi1", r"ℒαwρhi৷", r"ℒαwρhi",
            r"1awp\+\+i1", r"1wphi1"
        ]
        for pattern in watermarks:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return text

    def process_linear_footnotes(self, markdown_text):
        """
        Simple Two-Pass Footnote Processing (RESET VERSION):
        
        Pass 1: Detect and collect ALL footnote definitions
        Pass 2: Replace markers with sequential numbers, output consolidated footnotes
        
        Key Feature: Strict validation for "loose" definitions to prevent false positives.
        """
        # 1. Normalize [N] -> [^N] for consistency
        final_text = process_inline_footnotes_simple(markdown_text)
        lines = final_text.split('\n')

        # Regex patterns - IMPORTANT: Allow MULTIPLE '> ' blockquote prefixes for nested blockquotes
        STD_DEF_REGEX = re.compile(r'^(?:(?:>\s*)+)?(?:\s*)\[\^(\d+)\]:\s*(.*)$')  # Standard: [^1]: Content or >> [^1]: Content
        # Loose: "1. Content", "1: Content", or "1 Content" (space only) - all with optional multiple > prefixes
        LOOSE_DEF_REGEX = re.compile(r'^(?:(?:>\s*)+)?(\d+)(?:[\.:]\s*|\s+)(.+)$')
        FN_HEADER_REGEX = re.compile(r'^(?:(?:>\s*)+)?[\s#*]*Footnotes[\s#*]*$', re.I)
        MARKER_REGEX = re.compile(r'\[\^(\d+)\]')

        # Citation patterns that indicate a real footnote
        CITATION_PATTERNS = [
            r'\bSCRA\b', r'\bPhil\.\b', r'\bG\.R\.\b', r'\bvs\.\b', r'\bv\.\b',
            r'\bId\.\b', r'\bIbid\b', r'\bSupra\b', r'\bInfra\b',
            r'\bArt\.\b', r'\bSec\.\b', r'\bNo\.\b', r'\bRep\.\b',
            r'\d{4}\b',  # Years like 1994
            r'\bp\.\s*\d+',  # Page numbers
        ]
        
        def is_likely_footnote_content(text):
            """Check if text looks like a footnote definition (contains citations)."""
            for pattern in CITATION_PATTERNS:
                if re.search(pattern, text, re.I):
                    return True
            return False
        
        def is_section_header(text):
            """Check if text looks like a section header (ALL CAPS, short, structural)."""
            # Remove markdown formatting
            clean = re.sub(r'[\*_\[\]\(\)]', '', text).strip()
            # Check if all uppercase and short
            if len(clean) < 5:
                return False  # Too short to be a section header
            words = clean.split()
            if len(words) > 6:
                return False  # Too long to be a header
            # Check if ALL CAPS
            alpha_chars = [c for c in clean if c.isalpha()]
            if alpha_chars and all(c.isupper() for c in alpha_chars):
                return True
            return False

        # --- Pass 1: Collect Definitions ---
        def_map = {}  # {original_id: content}
        definition_line_indices = set()
        in_fn_section = False
        fn_section_start = -1
        
        for idx, line in enumerate(lines):
            clean = line.strip()
            
            # Detect footnote section header
            if FN_HEADER_REGEX.match(clean):
                in_fn_section = True
                fn_section_start = idx
                definition_line_indices.add(idx)
                continue
            
            # Standard definition: [^N]: Content
            m_std = STD_DEF_REGEX.match(line)
            if m_std:
                oid = m_std.group(1)
                content = m_std.group(2)
                # Strip all leading blockquote markers from content
                content = re.sub(r'^(?:>\s*)+', '', content).strip()
                def_map[oid] = content
                definition_line_indices.add(idx)
                continue
            
            # Loose definition: N. Content
            m_loose = LOOSE_DEF_REGEX.match(line)
            if m_loose:
                oid = m_loose.group(1)
                content = m_loose.group(2)
                
                # Simplified validation: Accept unless it's clearly a section header
                # Section headers are: ALL CAPS, short, structural text (like "EXECUTIVE SUMMARY")
                accept = not is_section_header(content)
                
                if accept:
                    # Strip all leading blockquote markers from content
                    content = re.sub(r'^(?:>\s*)+', '', content).strip()
                    def_map[oid] = content
                    definition_line_indices.add(idx)
                    continue

        # --- Pass 2: Replace Markers & Renumber ---
        new_lines = []
        final_footnotes = []  # [(original_id, new_id, content)] - track original IDs to prevent duplicates
        marker_counter = 1
        oid_to_new_id = {}  # Map original ID to assigned new ID
        
        for idx, line in enumerate(lines):
            if idx in definition_line_indices:
                continue  # Skip definition lines
            
            # Find and replace all markers in this line
            def replace_marker(match):
                nonlocal marker_counter
                oid = match.group(1)
                
                # Check if we've already processed this footnote
                if oid in oid_to_new_id:
                    # Reuse the existing new ID
                    return f"[^{oid_to_new_id[oid]}]"
                
                # First time seeing this footnote - assign new ID
                content = def_map.get(oid, f"Missing citation for footnote {oid}")
                
                new_id = str(marker_counter)
                marker_counter += 1
                
                oid_to_new_id[oid] = new_id
                final_footnotes.append((oid, new_id, content))
                return f"[^{new_id}]"
            
            new_line = MARKER_REGEX.sub(replace_marker, line)
            new_lines.append(new_line)

        # --- Output Assembly ---
        output = "\n".join(new_lines).strip()
        
        if final_footnotes:
            output += "\n\n---\n\n### Footnotes\n\n"
            for oid, new_id, content in final_footnotes:
                output += f"[^{new_id}]: {content}\n\n"
        
        return output




    def extract_metadata(self, soup, clean_text_content, raw_html=None):
        # VERSION: 1112 (Updated for user feedback)
        """Extracts detailed metadata for Frontmatter."""
        meta = {
            'Case Number': None,
            'Date': None,
            'Title': None,
            'Decided by': None, # Renamed from Division
            'Ponente': None,
            'Vote': None,
            'Opinions': None
        }

        # Pre-clean text content (Manual strip of >)
        lines = clean_text_content.splitlines()
        cleaned_lines = []
        for line in lines:
            # Remove > and leading whitespace
            # handle ' > text' or '> text'
            clean = line.strip().lstrip('>').strip()
            if clean:
                cleaned_lines.append(clean)
        
        clean_text_content = "\n".join(cleaned_lines)
        
        # 1. Decided by (En Banc or Division)
        for i in range(min(20, len(cleaned_lines))):
            line = cleaned_lines[i].upper()
            if "EN BANC" in line:
                meta['Decided by'] = "En Banc"
                break
            if "DIVISION" in line:
                cleaned_line = re.sub(r'[^\w\s]', '', line).strip()
                meta['Decided by'] = cleaned_line.title()
                break
        
        # 1. Date & Case Number (Moved up for logic dependency)
        header_info = self.extract_header_info_from_body(soup)
        meta['Case Number'] = header_info.get('case_number')
        meta['Date'] = header_info.get('date')

        # Determine Rules based on Date (Cutoff: Jan 24, 2023)
        use_2023_rules = False
        if meta['Date']:
            try:
                dt = datetime.strptime(meta['Date'].replace(",", ""), "%B %d %Y")
                if dt >= datetime(2023, 1, 24):
                    use_2023_rules = True
            except:
                pass # Default to False (2005 rules) if date parse fails

        # 2. Decided by (En Banc or Division)
        for i in range(min(20, len(cleaned_lines))):
            line = cleaned_lines[i].upper()
            if "EN BANC" in line:
                meta['Decided by'] = "En Banc"
                break
            if "DIVISION" in line:
                cleaned_line = re.sub(r'[^\w\s]', '', line).strip()
                meta['Decided by'] = cleaned_line.title()
                break
        
        # 3. Short Title (Petitioner v. Respondent)
        vs_match = re.search(r'(.+?)\s+(?:vs\.?|versus)\s+(.+?)(?:$|\n)', clean_text_content, re.IGNORECASE | re.MULTILINE)
        if vs_match:
            petitioner_raw = vs_match.group(1).split('\n')[-1].strip()
            respondent_raw = vs_match.group(2).split('\n')[0].strip()
            
            def clean_party(name):
                # Basic cleanup only
                name = re.sub(r'[\*_]', '', name)
                name = name.replace('\\', '')
                name = re.sub(r'(?i)\b(Petitioner|Respondent|Plaintiff|Defendant|Accused|Appellee|Appellant)s?\b', '', name)
                # Remove punctuation/spaces from end aggressively
                name = re.sub(r'[\s.,]+$', '', name.strip())
                return name.title()
            
            def get_short_party_name(full_name, is_2023):
                name = clean_party(full_name)
                name_lower = name.lower()

                # 1. Government / Criminal
                if "people of the philippines" in name_lower:
                    return "People"
                if "republic of the philippines" in name_lower:
                    return "Republic"
                
                # 2. Entities / Offices
                # List of words that imply it's an organization or office, not a person
                entity_keywords = [
                    "inc.", "corp.", "co.", "ltd.", "corporation", "incorporated", "company", 
                    "association", "organization", "bank", "commission", "university", 
                    "republic", "province", "city", "municipality", "commissioner", 
                    "collector", "director", "office", "department", "bureau", "agency",
                    "government", "insular"
                ]
                
                if any(k in name_lower for k in entity_keywords):
                    # 2023 Rule: Omit words "The" at start
                    if is_2023 and name_lower.startswith("the "):
                        return name[4:] # Strip "The "
                    return name # Return full name for entities
                
                # 3. Persons - Extract Surname
                # Remove suffixes
                suffixes = ["jr.", "sr.", "iii", "iv", "v", "vi", "esq.", "ph.d"]
                tokens = name.split()
                if not tokens: return name

                # Pop suffixes
                while tokens and tokens[-1].lower().rstrip('.') in suffixes:
                    tokens.pop()
                
                if not tokens: return name
                
                # Compound Surnames (De, La, Del, Van, Von)
                # Check 2nd to last token
                if len(tokens) >= 2:
                    second_last = tokens[-2].lower()
                    if second_last in ["de", "del", "van", "von"]:
                        # e.g. De Cruz
                        return " ".join(tokens[-2:])
                    if second_last == "la" and len(tokens) >= 3 and tokens[-3].lower() == "de":
                        # e.g. De La Cruz
                        return " ".join(tokens[-3:])
                
                # Fallback: Last token
                return tokens[-1]

            p_short = get_short_party_name(petitioner_raw, use_2023_rules)
            r_short = get_short_party_name(respondent_raw, use_2023_rules)

            # Force "v." separator and Title Case (names already title/mixed)
            short_title = f"{p_short} v. {r_short}"
            meta['Title'] = short_title # Storing in 'Title' key but it represents Short Title now

        # 4. Ponente
        # Strategy: Look for "DECISION" or "RESOLUTION"
        start_index = -1
        for i, line in enumerate(cleaned_lines):
            # Allow for **D E C I S I O N** or similar, OR **OPINION** types
            if re.match(r'^[\*#]*\s*D\s*E\s*C\s*I\s*S\s*I\s*O\s*N\s*[\*#]*$', line, re.IGNORECASE) or \
               re.match(r'^[\*#]*\s*R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N\s*[\*#]*$', line, re.IGNORECASE) or \
               re.match(r'^[\*#]*\s*(?:[A-Z\s]+)?O\s*P\s*I\s*N\s*I\s*O\s*N\s*[\*#]*$', line, re.IGNORECASE):
                start_index = i
                break
        
        if start_index != -1:
            # Look at next 5 lines
            for i in range(start_index + 1, min(start_index + 6, len(cleaned_lines))):
                candidate = cleaned_lines[i]
                # Regex for: **TIJAM, J.:**  or **TIJAM, *J.*
                # Capture "NAME" and "TITLE" allowing for markdown junk in between
                # Fix: Include hyphens and spaces in name group for "LEONARDO-DE CASTRO"
                ponente_match = re.search(r'(?:\*\*|\*|^)([A-Z\.\-\s]+)(?:,|\s+)(?:[\*_]*\s*)+(C\.?J\.?|J\.?)', candidate)
                if ponente_match:
                    name_part = ponente_match.group(1).strip()
                    suffix_part = ponente_match.group(2).strip()
                    
                    clean_name = name_part.replace('*', '').replace('_', '')
                    clean_name = clean_name.title()
                    
                    meta['Ponente'] = f"{clean_name}, {suffix_part}"
                    break
        
        # Fallback Ponente 1: "Penned by..."
        if not meta['Ponente']:
             penned_match = re.search(r'Penned by (?:Associate Justice)?\s*([A-Z\.\s,]+)', clean_text_content, re.IGNORECASE)
             if penned_match:
                 meta['Ponente'] = penned_match.group(1).strip()

        # Fallback Ponente 2: End of Text (Signature Block)
        if not meta['Ponente']:
            for i in range(len(cleaned_lines) - 1, max(0, len(cleaned_lines) - 50), -1):
                line = cleaned_lines[i].strip()
                # Robust Regex for: **TORRES, *J.:*** (Markdown, optional colons/periods)
                # Matches: Star/Underscore + Name + Spacer + Title + Spacer + Optional Colon + Star/Underscore
                match = re.search(r'^[\*_]*([A-Z\.\s\-]+)[\*_]*,\s*[\*_]*(?:J\.|C\.J\.|Chief Justice|Associate Justice)[\.]?[\*_]*[:]?[\*_]*$', line)
                if match:
                    name = match.group(1).strip()
                    if len(name) > 3 and "CONCUR" not in name and "CERTIFICATION" not in name:
                        meta['Ponente'] = name.title() + ", J." # Assume J. if found here without specific title
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
                    pass # Ignore decision line for opinions list
                else:
                    parsed_opinions.append(line_text)

        if parsed_opinions:
            meta['Opinions'] = "\n".join(parsed_opinions)
        else:
            # Fallback
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



    def remove_lawphil_watermarks(self, text):
        watermarks = [
            r"The Lawphil Project - Arellano Law Foundation",
            r"\(awÞhi\(", r"\(awÞhi", r"\(aw\w+",
            r"1a\w+phi1", r"1avvphi1", r"ℒαwρhi৷", r"ℒαwρhi"
        ]
        for pattern in watermarks:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return text



    def process_file(self, html_path, metadata=None, overwrite=False):
        try:
            # Read File
            with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()

            # 1. Extract Metadata
            head_meta = self.extract_metadata_from_head(html_content)
            soup = BeautifulSoup(html_content, 'html.parser')
            soup = self.clean_soup_dom(soup)
            body_info = self.extract_header_info_from_body(soup)
            
            case_number = head_meta.get('case_number') or body_info.get('case_number')
            title = head_meta.get('title') or "Unknown Title"
            date = body_info.get('date')

            # --- FALLBACKS ---
            if not date:
                # Path based fallback
                path_parts = Path(html_path).parts
                found_year = None
                found_month = None
                for part in reversed(path_parts):
                    if part.isdigit() and len(part) == 4:
                        found_year = part
                    if part.lower() in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]:
                        found_month = part.capitalize()
                
                if found_year:
                    date = f"{found_month if found_month else 'January'} 01, {found_year}"

            if not case_number or case_number == "Unknown":
                base_name = Path(html_path).stem.replace(".pdf", "")
                prefix_map = {"gr": "G.R. No. ", "am": "A.M. No. ", "ac": "A.C. No. ", "bm": "B.M. No. "}
                match = re.search(r"^([a-z]+)[_-]([\w-]+)", base_name, re.IGNORECASE)
                if match and match.group(1).lower() in prefix_map:
                    case_number = f"{prefix_map[match.group(1).lower()]}{match.group(2).replace('_', '-')}"
                else:
                    case_number = "Unknown"

            # Date Normalization
            try:
                # Remove comma to handle "August 20, 2024" vs "August 20 2024"
                clean_date_str = date.replace(",", "")
                dt = datetime.strptime(clean_date_str, "%B %d %Y")
                formatted_date = dt.strftime("%Y-%m-%d")
                file_date = f"{dt.strftime('%B')}_{dt.day:02d}_{dt.year}"
                year_str = str(dt.year)
            except:
                formatted_date = date
                file_date = "Unknown_Date"
                year_str = "Unknown"

            # 4. Generate Output Path
            safe_case_number = re.sub(r'[<>:"/\\|?*]', '_', str(case_number)).strip()
            filename = f"{safe_case_number}_{file_date}.md"
            output_path = self.output_dir / year_str / filename
            
            if output_path.exists() and not overwrite:
                return {'status': 'skipped', 'error': 'File exists', 'path': str(html_path)}

            # 5. Convert Content
            markdown_body = self.clean_and_convert(html_content, soup)
            
            # 6. Save
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_body)

            entry = {
                "source_html": str(html_path),
                "case_number": case_number,
                "date": formatted_date,
                "title": title,
                "output_md": str(output_path)
            }
            
            return {
                'status': 'success',
                'entry': entry,
                'case_key': f"{case_number}|{formatted_date}",
                'content_hash': hashlib.md5(markdown_body.encode()).hexdigest(),
                'path': str(html_path)
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'status': 'failed',
                'file_path': html_path,
                'error': str(e)
            }

    def run_full_conversion(self, workers=1, clean=False, start_year=None, end_year=None, overwrite=False, file_list=None):
        if clean and self.output_dir.exists():
            shutil.rmtree(self.output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        html_files = []
        if file_list:
            with open(file_list, 'r') as f:
                 html_files = [Path(line.strip()) for line in f if line.strip()]
        else:
            if not DOWNLOADS_DIR.exists():
                print(f"Error: Source directory {DOWNLOADS_DIR} does not exist.")
                return

            for root, _, files in os.walk(DOWNLOADS_DIR):
                path_parts = Path(root).parts
                year = None
                for part in path_parts:
                    if part.isdigit() and len(part) == 4:
                        year = int(part)
                        break
                
                # Filter by Year
                if year:
                    if start_year and year < start_year: continue
                    if end_year and year > end_year: continue

                for file in files:
                    if file.endswith(".html"):
                        html_files.append(Path(root) / file)

        print(f"Queueing {len(html_files)} files...")
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            # Pass self.output_dir to the wrapper so workers know where to write
            futures = {executor.submit(process_file_wrapper, p, None, overwrite, str(self.output_dir)): p for p in html_files}
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res['status'] == 'success':
                    print(f"✅ {res['entry']['case_number']}")
                    self.manifest.append(res['entry'])
                elif res['status'] == 'failed':
                    print(f"❌ {res['error']}")
                elif res['status'] == 'skipped':
                     print(f"⏭️ {Path(res['path']).name}")

        manifest_path = self.output_dir / "conversion_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2)

def process_file_wrapper(html_path, metadata, overwrite, output_dir=None):
    # Re-instantiate converter per process, passing output_dir explicitly
    converter = CaseConverter(output_dir)
    return converter.process_file(html_path, metadata, overwrite)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--start-year', type=int, help='Start year filter')
    parser.add_argument('--end-year', type=int, help='End year filter')
    parser.add_argument('--output-dir', type=str, help='Custom output directory')
    args = parser.parse_args()
    
    CaseConverter(output_dir=args.output_dir).run_full_conversion(
        workers=args.workers, 
        overwrite=args.overwrite,
        start_year=args.start_year,
        end_year=args.end_year
    )
