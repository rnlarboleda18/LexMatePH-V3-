import re

def analyze_roc(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all Rules
    rules = re.findall(r'### RULE (\d+)', content)
    # Find all Sections
    sections = re.findall(r'Section (\d+)\.', content)

    print(f"Total Rules found: {len(rules)}")
    print(f"Total Sections found: {len(sections)}")

    # Check for non-sequential rules (simple check)
    rule_nums = [int(r) for r in rules]
    gaps = []
    for i in range(len(rule_nums) - 1):
        if rule_nums[i+1] > rule_nums[i] + 1:
            gaps.append((rule_nums[i], rule_nums[i+1]))
    
    if gaps:
        print("Rule numbering gaps found:", gaps)
    else:
        print("No obvious Rule numbering gaps found.")

    # Check for common artifacts
    artifacts = {
        "Bracketed text": len(re.findall(r'\[.*?\]', content)),
        "Footnote markers": len(re.findall(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]', content)),
        "Wait-for-correction markers": len(re.findall(r'FIXME|TODO|XXX', content)),
        "Malformed headers (no space after ###)": len(re.findall(r'###[^\s]', content))
    }
    
    for k, v in artifacts.items():
        print(f"{k}: {v}")

    # Check for inconsistency in Section title separator
    case1 = len(re.findall(r'Section \d+\. .*? –', content)) # Em-dash
    case2 = len(re.findall(r'Section \d+\. .*? -', content)) # Hyphen
    case3 = len(re.findall(r'Section \d+\. .*?\.', content)) # Just period
    
    print(f"Section titles with em-dash: {case1}")
    print(f"Section titles with hyphen: {case2}")
    print(f"Section titles with just period: {case3}")

analyze_roc('ROC_Combined.md')
