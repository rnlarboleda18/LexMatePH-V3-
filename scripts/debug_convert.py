import fitz, re

doc = fitz.open(r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\1. ROC Civil Procedure as amended 2019.pdf')
found = False

for page_num in range(len(doc)):
    page = doc[page_num]
    d = page.get_text("dict", flags=32768)
    for block in d.get("blocks", []):
        if "lines" not in block: continue
        
        # coord filter
        if "bbox" in block:
            y0 = block["bbox"][1]
            y1 = block["bbox"][3]
            if y0 > 690 or y1 < 65: continue
            
        block_text = ""
        for line in block["lines"]:
            line_text = ""
            for span in line.get("spans", []):
                span_text = span.get("text", "")
                if not span_text.strip():
                     line_text += span_text
                     continue
                char_flags = span.get("char_flags", 0)
                is_underlined = (char_flags & 2) != 0
                cleaned = span_text
                if is_underlined: cleaned = f"**{cleaned}**"
                line_text += cleaned
            if line_text.strip(): block_text += line_text + " "
            
        cleaned_block_text = block_text.strip().replace("\n", " ")
        if "Affi" in cleaned_block_text and "dismissal" in cleaned_block_text:
            print("--- BEFORE ALL ---")
            print(repr(cleaned_block_text))
            
            # Regex Tracing
            cbt = cleaned_block_text.replace("****", "")
            print("--- AFTER 4-STAR REPL ---")
            print(repr(cbt))
            
            cbt = re.sub(r'\*\*([a-zA-Z0-9]+)\*\*([a-zA-Z0-9]+)', r'**\1\2**', cbt)
            print("--- AFTER REGEX 1 (START SPLIT) ---")
            print(repr(cbt))
            
            cbt = re.sub(r'([a-zA-Z0-9]+)\*\*([a-zA-Z0-9]+)', r'**\1\2', cbt)
            print("--- AFTER REGEX 2 (MID SPLIT) ---")
            print(repr(cbt))
            
            cbt = re.sub(r'\*\*(\s+)\*\*', r'\1', cbt)
            print("--- AFTER REGEX 3 (SPACE MERGE) ---")
            print(repr(cbt))
            
            found = True
            break
    if found: break
if not found:
    print("NOT FOUND AT ALL")
