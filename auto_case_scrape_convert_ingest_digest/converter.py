"""
Supreme Court HTML to Markdown Converter (Lawphil Specific Optimized) - Table Fix + No LLM
CONSOLIDATED & MODIFIED FOR AUTO-PIPELINE (TARGETED MODE)
"""

import os
import json
import shutil
import re
import argparse
import concurrent.futures
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Directories
SC_SCRAPER_DIR = Path(os.getenv("SC_SCRAPER_DIR", "./sc_scraper"))
DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./data/MD/lawphil"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def flow_is_descendant(node, ancestor):
    """Checks if node is a descendant of ancestor."""
    for parent in node.parents:
        if parent == ancestor:
            return True
    return False

class CaseConverter:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def clean_soup_dom(self, soup):
        if soup.head: soup.head.decompose()
        for tag in soup(["script", "style", "link", "meta", "iframe", "img"]):
            tag.decompose()

        # Lawphil Table Unwrap Logic (Simplified for Auto-Runner)
        lawphil_table = soup.find('table', id='lwphl') or soup.find('table', attrs={'width': '800'})
        content_block = lawphil_table

        if content_block:
            # Move footnotes
            all_notes = soup.find_all('nt') + soup.find_all('a', class_='nt')
            for tag in all_notes:
                container = tag.find_parent('p') or tag.parent
                if container and not flow_is_descendant(container, content_block):
                    if content_block.name == 'table':
                        content_block.append(container)
                    else:
                        content_block.append(container)

            if content_block.name == 'table':
                # Unwrap table
                inner_html = "".join([str(x) for x in content_block.find_all('td')])
                soup = BeautifulSoup(inner_html, 'html.parser')

        # Clean artifacts
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if len(text) < 300 and ("The Lawphil Project" in text or "Arellano Law Foundation" in text):
                p.decompose()

        return soup

    def extract_and_destroy_footnotes(self, soup):
        footnotes = {}
        candidates = soup.find_all('nt') + soup.find_all('a', class_='nt')
        for tag in candidates:
            ref_num = tag.get_text().strip()
            if not ref_num: continue
            
            parent = tag.parent
            if parent and parent.name == 'p':
                full_text = parent.get_text().strip()
                if full_text.startswith(ref_num):
                    content = full_text[len(ref_num):].strip()
                    content = re.sub(r'^[\.\,\)\s]+', '', content)
                    footnotes[ref_num] = content
                    parent.decompose()
        return footnotes

    def clean_and_convert(self, html_content, soup=None):
        if not soup:
            soup = BeautifulSoup(html_content, "html.parser")
            soup = self.clean_soup_dom(soup)
        
        extracted_footnotes = self.extract_and_destroy_footnotes(soup)

        # Handle remaining markers
        for tag in soup.find_all('nt') + soup.find_all('a', class_='nt'):
            text = tag.get_text().strip()
            if text: tag.replace_with(f"FOOTNOTE_REF_{text}_END")
            else: tag.decompose()

        text = md(str(soup), heading_style="ATX", strip=['img', 'a', 'table', 'thead', 'tbody', 'th', 'tr', 'td', 'center', 'div'])
        text = re.sub(r'FOOTNOTE[_\\]*REF[_\\]*(.+?)[_\\]*END', r'[^\1]', text)
        
        # Post-clean lines
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            if "The Lawphil Project" in line: continue
            if "Arellano Law" in line: continue
            cleaned_lines.append(line)
            
        final_text = '\n'.join(cleaned_lines)
        final_text = re.sub(r'\n{3,}', '\n\n', final_text)
        
        # Inject citations
        final_text = self.process_inline_footnotes(final_text, extracted_footnotes)
        return final_text.strip()

    def process_inline_footnotes(self, markdown_text, html_footnotes=None):
        if not html_footnotes: return markdown_text
        footnotes = html_footnotes.copy()

        def replace_marker(match):
            marker_id = match.group(1)
            if marker_id in footnotes:
                content = footnotes[marker_id].replace('\n', ' ').strip()
                # Basic junk filter
                if re.match(r'^(id|ibid|supra|rollo|tsn|see|note)\b', content, re.IGNORECASE):
                    return ""
                return f' <span class="smart-citation">({content})</span>'
            return ""

        return re.sub(r'\[\^(\d+)\]', replace_marker, markdown_text)

def run_conversion(converter, f):
    try:
        with open(f, 'r', encoding='utf-8', errors='replace') as file:
            html = file.read()
        md_text = converter.clean_and_convert(html)
        
        rel_path = f.relative_to(DOWNLOADS_DIR)
        save_path = converter.output_dir / rel_path.with_suffix('.md')
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as file:
            file.write(md_text)
        logging.info(f"Converted: {f.name}")
    except Exception as e:
        logging.error(f"Failed {f.name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", help="Path to target list", default=r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\auto_case_scrape_convert_ingest_digest\target_list.txt")
    args = parser.parse_args()
    
    converter = CaseConverter()

    # Priority List Logic
    priority_files = []
    if os.path.exists(args.targets):
        with open(args.targets, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
        
        logging.info("Scanning for TARGET files only...")
        # Since we have 64k files, rglob is slow. 
        # But we know structure: data/lawphil_html/YYYY/gr_XXXX_YYYY.html
        
        # Optimization: Scan only relevant years if possible? 
        # For now, let's just do the rglob once because we have to find them.
        all_files = list(DOWNLOADS_DIR.rglob("*.html"))
        
        for line in lines:
            # Extract case no: "151358"
            match = re.search(r'(?:G\.R\.|A\.M\.|A\.C\.|B\.M\.).+?([0-9\-\s]+)', line)
            if match:
                 num_part = match.group(1).replace('.', '').strip()
                 # Normalize filename search
                 for fpath in all_files:
                     if num_part in fpath.name.replace('_', ' '):
                         priority_files.append(fpath)
                         break

    if priority_files:
        logging.info(f"Found {len(priority_files)} target files to convert.")
        with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_conversion, converter, f) for f in priority_files]
            for future in concurrent.futures.as_completed(futures):
                pass
        logging.info("Target Conversion Complete.")
    else:
        logging.warning("No targets found in target_list.txt or no matching files found. Exiting.")
