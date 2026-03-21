import os
import re
import sys
from bs4 import BeautifulSoup
from markdownify import MarkdownConverter, markdownify as md

class LawphilConverter(MarkdownConverter):
    """
    Custom MarkdownConverter for Lawphil.
    Extends markdownify to handle specific Lawphil formatting quirks.
    """
    def convert_tr(self, el, text, convert_as_inline):
        # Flatten simple rows if they are just layout
        return text + "\n"

    def convert_td(self, el, text, convert_as_inline):
        # flattened = text.strip()
        # return flattened + "\n\n"
        return text + "\n"

class CaseConverter:
    def __init__(self):
        pass

    def normalize_footnotes(self, soup):
        """
        Converts Lawphil <nt> tags to standard [N] markers.
        """
        # Find both <nt> tags and <a class="nt"> tags
        candidates = soup.find_all('nt') + soup.find_all('a', class_='nt') + soup.find_all('sup')
        
        for tag in candidates:
            ref_num = tag.get_text().strip()
            if not ref_num: continue
            
            # Simple replacement: <nt>1</nt> -> [1]
            tag.replace_with(f"[{ref_num}]")

    def clean_soup(self, soup):
        """
        Aggressively cleans the DOM to isolate the case content.
        """
        # 1. Remove obvious junk
        for tag in soup.find_all(['script', 'style', 'iframe', 'form', 'input', 'button', 'link', 'meta']):
            tag.decompose()
            
        # 2. Remove Lawphil Header/Logo tables & Search Bars
        for table in soup.find_all('table'):
            text = table.get_text().strip().lower()
            
            # Check length to avoid deleting main wrapper table
            # Main content is usually huge (>2000 chars)
            if len(text) > 2000:
                continue

            if "lawphil project" in text and "arellano law foundation" in text:
                table.decompose()
            elif "search queries" in text or "search result" in text:
                 table.decompose()
            elif "today is" in text and "constitution" in text: # Specific Lawphil "Today is..." bar
                 table.decompose()

        # 3. Remove "Search Results" specific noise
        for div in soup.find_all('div'):
             if "search" in div.get_text().lower():
                 pass

        # 4. Remove Copyright lines and unwanted footers
        for p in soup.find_all('p'):
            text = p.get_text().strip().lower()
            if "copyright" in text and "lawphil" in text:
                p.decompose()
            if "designed by" in text:
                p.decompose()

        return soup

    def remove_lawphil_watermarks(self, text):
        watermarks = [
            r"The Lawphil Project - Arellano Law Foundation",
            r"\(awÞhi\(", r"\(awÞhi", r"\(aw\w+",
            r"1a\w+phi1", r"1avvphi1", r"ℒαwρhi৷", r"ℒαwρhi",
            r"1awp\+\+i1", r"1wphi1", r"Lawphil"
        ]
        for pattern in watermarks:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return text

    def format_header(self, text):
        """
        Post-process to fix run-on headers.
        """
        # 1. Force newline before G.R. No. if it's following text
        text = re.sub(r'(?<=\S)\s+(G\.R\. No\.)', r'\n\n\1', text)
        
        # 2. Force newline around "vs." in header area (first 3000 chars)
        header_limit = 3000
        header_text = text[:header_limit]
        rest_text = text[header_limit:]
        
        # Case-insensitive "vs." with spacing
        header_text = re.sub(r'(?<=\S)\s+(vs\.|versus)\s+', r'\n\nvs.\n\n', header_text, flags=re.IGNORECASE)
        
        return header_text + rest_text

    def format_body_spacing(self, text):
        """
        Improves spacing for body content (lists, sections).
        """
        # 1. Justice Names (NAME, J.:) -> Newline
        text = re.sub(r'(?<=\S)\s+([A-Z]+, J\.:)', r'\n\n\1', text)
        
        # 2. Roman Numeral Headers (I. Title, II. Title)
        # Match I. II. III. IV. V. VI. VII. VIII. IX. X. followed by Capital
        roman_pattern = r'(?:^|\s)((?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+[A-Z])'
        text = re.sub(roman_pattern, r'\n\n\1', text)
        
        # 3. Alpha List Items (A. Title, B. Title) - Conservative to avoid names like A.B. Cruz
        # Require A. followed by Space and Capital word (longer than 1 char)
        alpha_pattern = r'(?<=\.)\s+([A-Z]\.\s+[A-Z][a-z]{2,})' 
        text = re.sub(alpha_pattern, r'\n\n\1', text)
        
        # 4. Numbered Lists (1. Item, 2. Item)
        # Conservative: 1. followed by Space and Capital
        num_pattern = r'(?<=\.)\s+(\d+\.\s+[A-Z])'
        text = re.sub(num_pattern, r'\n\n\1', text)

        # 5. Global G.R. No. inline fix (moved from header limit)
        # Ensure G.R. No. and number are on the same line everywhere
        text = re.sub(r'(G\.R\. No\.)\s+(\d+)', r'\1 \2', text)

        return text

    def clean_preamble(self, text):
        """
        Removes everything before and including 'Republic of the Philippines... Manila'.
        """
        # Regex to match the header and everything before it
        # "Republic of the Philippines" ... "Manila"
        # Match dot-all until Manila
        pattern = r'.*?Republic of the Philippines\s+SUPREME COURT\s+Manila\s*'
        
        match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            # Return everything AFTER the match
            return text[match.end():]
            
        # Fallback: simple string find if regex fails (unlikely if standard)
        marker = "Republic of the Philippines"
        if marker in text:
            index = text.find(marker)
            return text[index + len(marker):].strip()
            
        return text

    def format_header_alignment(self, text):
        """
        Wraps the header block (Petitioners vs Respondents) in <center> tags.
        Heuristic: Everything from start until 'JUSTICE, J.:' or 'D E C I S I O N'.
        """
        # Potential separators indicating start of body
        separators = [
             r'\n+\s*[A-Z\s]+,\s*J\.:',      # Justice name (MENDOZA, J.:)
             r'\n+\s*(?:D\s+E\s+C\s+I\s+S\s+I\s+O\s+N|R\s+E\s+S\s+O\s+L\s+U\s+T\s+I\s+O\s+N)', # Spaced Title
             r'\n+\s*x\s+x\s+x'             # x x x separator
        ]
        
        split_index = -1
        
        for sep in separators:
            match = re.search(sep, text)
            if match:
                # Found the earliest separator
                split_index = match.start()
                break
        
        if split_index > 0:
            header = text[:split_index].strip()
            body = text[split_index:]
            # Wrap header in center, ensure newlines for markdown safety
            return f"<center>\n\n{header}\n\n</center>{body}"
            
        return text

    def process_file(self, file_path, output_path):
        print(f"Processing: {file_path}")
        
        # Custom Encoding Logic:
        # Lawphil files often have <meta charset="windows-1252"> but contain UTF-8 content.
        # BS4 respects the meta tag, causing Mojibake (Â§ etc).
        # We must try to decode as UTF-8 first, and force it if plausible.
        
        with open(file_path, 'rb') as f:
            content_bytes = f.read()

        html_content = None
        
        # 1. Try Strict UTF-8
        try:
            html_content = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # 2. Heuristic: Is it UTF-8 with a few errors, or real CP1252?
            # Check for common Mojibake patterns if we decode as CP1252:
            # \xc2\xa7 (UTF-8 section) -> Â§ (CP1252)
            # \xc2\xa0 (UTF-8 nbsp)    -> Â (CP1252) + nbsp
            # \xc3\xb1 (UTF-8 ñ)       -> Ã± (CP1252)
            
            try:
                # Decode as 1252 to check for patterns
                preview = content_bytes.decode('cp1252', errors='replace')
                
                mojibake_count = 0
                mojibake_count += preview.count('Â§')
                mojibake_count += preview.count('Â\xa0')
                mojibake_count += preview.count('Ã±')
                mojibake_count += preview.count('Ã©')
                
                if mojibake_count > 0:
                    # It's likely UTF-8 with some glitches
                    html_content = content_bytes.decode('utf-8', errors='replace')
                else:
                    # It's likely real CP1252
                    html_content = preview
            except:
                 # Fallback
                 html_content = content_bytes.decode('cp1252', errors='replace')

        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. Normalize Footnotes BEFORE cleaning (so they don't get lost if inside something weird)
        self.normalize_footnotes(soup)
        
        # 2. Clean DOM
        soup = self.clean_soup(soup)
        
        # 3. Convert to Markdown
        # strip=['table'] unwraps tables which is what we want for Lawphil's layout-heavy pages
        # blocked_tags: remove these tags COMPLETELY (content included) - none for now, stripped above
        # Preserve center tags (remove 'center' from strip)
        # Also removing 'b', 'i' etc to confirm if we want rich text? 
        # User only asked for center. Let's start with center.
        text = md(str(soup), heading_style="ATX", 
                  strip=['img', 'a', 'table', 'tbody', 'thead', 'tr', 'td', 'font', 'span', 'div', 'dir', 'b', 'i', 'u']) 

        # Post-Processing
        
        # 0. Clean Preamble
        text = self.clean_preamble(text)
        
        # 0.1 Clean dangling closing center tags (if preamble cut opened one)
        text = re.sub(r'^\s*</center>', '', text, flags=re.MULTILINE).strip()

        # 0.15 Remove Lawphil Watermarks
        text = self.remove_lawphil_watermarks(text)
        
        # 0.2 Format Header Alignment (Center the title block)
        text = self.format_header_alignment(text)
        
        # 1. Clean excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 2. Clean blockquote artifacts
        text = re.sub(r'(?:^>\s*\n){2,}', '>\n', text, flags=re.MULTILINE)
        
        # 2.5 Clean Mojibake (UTF-8 C2 A0 misinterpreted as Windows-1252 Â + NBSP)
        text = text.replace('\u00c2\u00a0', ' ')
        text = text.replace('Â\xa0', ' ') # Redundant but safe
        
        # 3. Format Header
        text = self.format_header(text)
        
        # 4. Format Body Spacing
        text = self.format_body_spacing(text)

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f"Saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lawphil_converter_html_to_md.py <html_file> [output_dir]")
        sys.exit(1)
        
    fpath = sys.argv[1]
    converter = CaseConverter()
    
    # Determine output path
    base_name = os.path.basename(fpath)
    name_no_ext = os.path.splitext(base_name)[0]
    
    if len(sys.argv) >= 3:
        out_dir = sys.argv[2]
    else:
        out_dir = os.path.join(os.path.dirname(fpath), "..", "converted_md")

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    out_path = os.path.join(out_dir, f"{name_no_ext}.md")
    
    converter.process_file(fpath, out_path)
