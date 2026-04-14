
import os
import re
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scraper.elib_html_to_markdown import elib_html_to_markdown

INPUT_DIR = "data/sc_elib_html"
OUTPUT_DIR = "data/sc_elib_md"

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def process_inline_footnotes_simple(markdown_text):
    """
    detects [1], [2] etc and converts to [^1], [^2].
    This is enough for standard markdown renderers to handle linking 
    if the definition [^1]: ... is present.
    
    Since we are converting "as written", the definitions should already be 
    at the bottom (or wherever they were in HTML). We just need to make sure 
    the text "[1]" becomes "[^1]" everywhere.
    """
    # Simply replace all [N] with [^N]
    # We use a negative lookbehind/lookahead to avoid double processing if run twice, 
    # but basic regex is fine for this clean pass.
    
    # 1. Inline markers: "text [1] text" -> "text [^1] text"
    # 2. Definitions at bottom: "[1] Definition" -> "[^1]: Definition"
    
    def repl(m):
        return f"[^{m.group(1)}]"
    
    # Replace [123] with [^123]
    text = re.sub(r'\[(\d+)\]', repl, markdown_text)
    
    # Starting a line with [^1] is likely a definition. 
    # Standard markdown expects [^1]: ...
    # So we replace "^[^1] " with "^[^1]: "
    
    def def_repl(m):
        return f"[^{m.group(1)}]:"
        
    text = re.sub(r'^\[\^(\d+)\]\s+', def_repl, text, flags=re.MULTILINE)
    
    return text

def convert_file(filename):
    in_path = os.path.join(INPUT_DIR, filename)
    out_path = os.path.join(OUTPUT_DIR, filename.replace('.html', '.md'))
    
    # Verify input exists
    if not os.path.exists(in_path):
        print(f"Skipping {filename}, not found.")
        return

    try:
        with open(in_path, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()

        stem = filename.replace('.html', '').replace('.htm', '')
        source_url = f"https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/{stem}"
        try:
            doc_id = int(stem)
        except ValueError:
            doc_id = None
        md_text, err = elib_html_to_markdown(raw, source_url=source_url, elib_doc_id=doc_id)
        if err or not md_text:
            print(f"Skipping {filename}: {err or 'empty'}")
            return

        final_text = md_text
        
        # Split into lines
        lines = final_text.split('\n')
        
        # Identify ranges of text and footnote definitions
        # definition_blocks = [ (start_line, end_line), ... ]
        
        # Pass 1: Tag lines as "Definition" or "Text"
        # Definition line regex: ^\[\^\d+\]:
        def_regex = re.compile(r'^\s*\[\^(\d+)\]:', re.MULTILINE)
        
        # We will build segments: Text -> Footnotes -> Text -> Footnotes
        # But E-Lib usually has Text -> Footnotes -> Divider -> Text -> Footnotes
        
        # Let's process globally.
        # Find all occurrences of Definitions.
        # If we see duplicate [^1]:, we know we have sections. 
        # If we only distinct numbers, we are fine.
        
        # Check for duplicates
        all_defs = def_regex.findall(final_text)
        if len(all_defs) != len(set(all_defs)):
            print(f"[{filename}] Duplicate footnotes detected. Renumbering...")
            
            # Robust Renumbering
            new_lines = []
            
            # Split by "Opinion" Headers
            # Updated Regex to anchor both parts to start of line to avoid matching body text
            OPINION_HEADER_REGEX = re.compile(r'^(SEPARATE|CONCURRING|DISSENTING).*OPINION|^R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N\s*$', re.I | re.MULTILINE)
            
            segments = []
            current_seg = []
            
            # Helper to detect header in a line
            def is_opinion_header(line):
                # Check for --- separator + Header? Or just Header?
                # Usually: 
                # ---
                # DISSENTING OPINION
                # Or just DISSENTING OPINION
                
                # Check if line matches regex
                txt = line.strip().replace('*', '').replace('#', '').strip()
                return bool(OPINION_HEADER_REGEX.match(txt))

            for line in lines:
                # If we hit a likely header, we start a new segment
                if is_opinion_header(line):
                     # Start new segment
                     if current_seg:
                         # Check if last line was divider, if so, move it to new?
                         last_line = current_seg[-1] if current_seg else ""
                         if "---" in last_line or "***" in last_line:
                             current_seg.pop()
                             segments.append(current_seg)
                             current_seg = [last_line, line]
                         else:
                             segments.append(current_seg)
                             current_seg = [line]
                     else:
                         current_seg.append(line)
                else:
                    current_seg.append(line)
            segments.append(current_seg)
            
            merged_segments = segments

            # Determine if we need suffixes
            use_suffixes = len(merged_segments) > 1
            
            # Helper to process a chunk
            def process_chunk(chunk_lines, offset_id, use_suffix):
                # chunk_lines contains Text optionally followed by Definitions
                # We need to find the distinct [N] markers in Text and [N]: in Defs
                
                # Separation is tricky. Let's assume the Definitions are at the END of the chunk.
                # Scan backwards for definitions
                def_start = len(chunk_lines)
                gap_count = 0
                GAP_THRESHOLD = 50 # Allow 50 lines of non-def text (continuation) before giving up
                
                for i in range(len(chunk_lines)-1, -1, -1):
                    if def_regex.match(chunk_lines[i]):
                        def_start = i
                        gap_count = 0 # Reset gap count
                    elif not chunk_lines[i].strip():
                        continue
                    else:
                        # Found non-empty, non-def line. 
                        # It might be part of a multi-line footnote.
                        # Check if we have seen definitions recently
                        if def_start < len(chunk_lines): 
                             gap_count += 1
                             if gap_count > GAP_THRESHOLD:
                                 break
                        else:
                             # We haven't seen any definitions yet (from bottom). 
                             pass
                
                # Text is 0..def_start
                # Defs are def_start..end
                
                text_part = "\n".join(chunk_lines[:def_start])
                def_part_lines = chunk_lines[def_start:]
                
                # Create map from Definitions
                # Local ID -> New Global ID
                ws_map = {} 
                
                renumbered_defs = []
                for line in def_part_lines:
                    m = def_regex.match(line)
                    if m:
                        old_id = m.group(1)
                        if use_suffix:
                             new_id = f"{old_id}_{offset_id}"
                        else:
                             new_id = old_id 
                        
                        ws_map[old_id] = new_id
                        # Replace in definition line
                        new_line = re.sub(r'^\s*\[\^' + old_id + r'\]:', f"[^{new_id}]:", line, count=1)
                        renumbered_defs.append(new_line)
                    else:
                        renumbered_defs.append(line)
                
                print(f"Debug Chunk {offset_id}: TextLen={len(text_part)}, DefLines={len(def_part_lines)}, MapSize={len(ws_map)}")
                        
                # Replace in Text
                def text_repl(m):
                    oid = m.group(1)
                    if oid in ws_map:
                         return f"[^{ws_map[oid]}]"
                    else:
                         if use_suffix:
                             return f"[^{oid}_{offset_id}]"
                         else:
                             return f"[^{oid}]"
                
                new_text = re.sub(r'\[\^(\d+)\]', text_repl, text_part)
                
                return new_text.split('\n') + renumbered_defs

            final_lines_accum = []
            seg_idx = 1
            for seg in merged_segments:
                processed = process_chunk(seg, seg_idx, use_suffixes)
                final_lines_accum.extend(processed)
                final_lines_accum.append("\n---\n") # Re-insert separator
                seg_idx += 1
            
            final_text = "\n".join(final_lines_accum)
            
        # 7. Clean Watermarks
        final_text = re.sub(r"The Lawphil Project - Arellano Law Foundation", "", final_text, flags=re.IGNORECASE)
        final_text = re.sub(r"\(awÞhi", "", final_text, flags=re.IGNORECASE)
        final_text = re.sub(r"View printer friendly version", "", final_text, flags=re.IGNORECASE)
        
        # Trim excess whitespace
        final_text = re.sub(r'\n{3,}', '\n\n', final_text).strip()
        final_text = final_text.lstrip()

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(final_text)

    except Exception as e:
        print(f"Error converting {filename}: {e}")
        import traceback
        traceback.print_exc()


import argparse

def main():
    global INPUT_DIR, OUTPUT_DIR
    
    parser = argparse.ArgumentParser(description="Convert SC eLib HTML to Markdown")
    parser.add_argument("--input", default=INPUT_DIR, help="Input directory")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--file", help="Specific file to convert (optional)")
    parser.add_argument("--workers", type=int, default=20, help="Number of worker threads")
    
    args = parser.parse_args()
    
    INPUT_DIR = args.input
    OUTPUT_DIR = args.output
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    if args.file:
        files = [args.file]
    else:
        files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.html')]
    
    print(f"Converting {len(files)} files using {args.workers} workers...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        list(executor.map(convert_file, files))
    print("Done.")

if __name__ == "__main__":
    main()
