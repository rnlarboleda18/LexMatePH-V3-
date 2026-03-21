
path = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\SupremeDecisions.jsx"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_mode = False
facts_updated = False

# We want to remove the garbage I added:
# // ... inside SupremeDecisions component ...
# <section> 
# ...
# </section>
# This block likely appears right after MarkdownText definition.

for i, line in enumerate(lines):
    # Detect start of garbage
    if "// ... inside SupremeDecisions component ..." in line and "MarkdownText" not in line: 
        # CAUTION: Ensure we are not inside a valid component comment. 
        # The garbage was top-level.
        print(f"Removing garbage line {i+1}: {line.strip()}")
        skip_mode = True
        continue
    
    if skip_mode:
        # Detect end of garbage. It was a </section> and maybe a newline.
        # But wait, I need to be careful not to skip valid code if the garbage ended.
        # The garbage was:
        # <section>
        #    ...
        # </div>
        # </section>
        print(f"Removing garbage line {i+1}: {line.strip()}")
        if line.strip() == "</section>":
            skip_mode = False
        continue

    # Update the ACTUAL usage of digest_facts
    # Look for: <MarkdownText content={selectedDecision.digest_facts} onCaseClick={handleSmartCaseClick} />
    # Replace with: <MarkdownText content={selectedDecision.digest_facts} onCaseClick={handleSmartCaseClick} variant="facts" />
    if "content={selectedDecision.digest_facts}" in line and "MarkdownText" in line and "variant=\"facts\"" not in line:
         print(f"Updating line {i+1}: {line.strip()}")
         new_line = line.replace("handleSmartCaseClick} />", "handleSmartCaseClick} variant=\"facts\" />")
         new_lines.append(new_line)
         facts_updated = True
         continue
         
    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Finished. Facts usage updated: {facts_updated}")
