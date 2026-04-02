import fitz

doc = fitz.open(r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC\1. ROC Civil Procedure as amended 2019.pdf')

found = False
for page_num in range(len(doc)):
    page = doc[page_num]
    text_dict = page.get_text("dict", flags=32768)
    
    for block in text_dict.get("blocks", []):
        if "lines" not in block: continue
        block_text = "".join(["".join([s["text"] for s in l["spans"]]) for l in block["lines"]])
        
        if "Affi" in block_text and "dismissal" in block_text:
            print(f"--- FOUND ON PAGE {page_num} ---")
            print("Block Text:", repr(block_text.strip().replace("\n", " ")))
            print("Block BBox:", block["bbox"])
            
            # Inspect drawings on this page
            drawings = page.get_drawings()
            print(f"Total Drawings on page: {len(drawings)}")
            for d in drawings:
                # Check for straight lines (drawings with subpaths and "line")
                if d["type"] in ["l", "rect", "line"]:
                     print("Drawing type:", d["type"], d["rect"])
                elif "items" in d:
                     for item in d["items"]:
                         if item[0] == "l": # line
                             line_coords = item[1:]
                             # line: p1, p2
                             print(f"Line: {line_coords}")
            found = True
            break
    if found: break

if not found:
    print("Affi + dismissal block NOT FOUND on any page with standard look.")
