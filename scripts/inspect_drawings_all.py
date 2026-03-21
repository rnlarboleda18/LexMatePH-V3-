import fitz

doc = fitz.open(r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\1. ROC Civil Procedure as amended 2019.pdf')

page = doc[6] # Page index 6
drawings = page.get_drawings()

# Write items detail to inspect
with open(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\drawings_debug.txt", "w") as f:
    f.write(f"Total Drawings on page 6: {len(drawings)}\n")
    for i, d in enumerate(drawings):
        f.write(f"Drawing {i}: type={d['type']}, rect={d['rect']}\n")
        if "items" in d:
            for item in d["items"]:
                if item[0] == "l":
                    f.write(f"  Line: {item[1:]}\n")

print("Drawings written to drawings_debug.txt")
