import re

def apply_fixes(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove Rule 144 block
    # It starts with ### RULE 144 and goes until the next RULE header or significant section
    # Based on observation, it's followed by "GENERAL PROVISION" then "### RULE 72"
    content = re.sub(r'### RULE 144.*?### RULE 72', '### RULE 72', content, flags=re.DOTALL)

    # 2. Fix encoding artifacts (Mojibake)
    content = content.replace('â€“', '–')
    content = content.replace('â€”', '—')
    content = content.replace('â€™', "'")
    content = content.replace('â€œ', '"')
    content = content.replace('â€\x9d', '"')

    # 3. Fix Technical Typos
    typos = {
        r'\bnest succeeding\b': 'next succeeding',
        r'\baffidavit filled\b': 'affidavit filed',
        r'\bwithout excused\b': 'without excuse',
        r'it shall be appoint': 'it shall appoint',
        r'it may be appoint': 'it may appoint',
        r'the fact that the affirms': 'the fact that he affirms'
    }
    for pattern, replacement in typos.items():
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

    # 4. Clean up redundant RULE markers
    # Find cases where "### RULE X" appears twice without another "### RULE Y" in between
    def remove_redundant_rules(text):
        rules = sorted(set(re.findall(r'### RULE\s+(\d+)', text)), key=int, reverse=True)
        for rule_num in rules:
            pattern = rf'### RULE\s+{rule_num}'
            matches = list(re.finditer(pattern, text))
            if len(matches) > 1:
                # Keep the first match, remove subsequent ones that have no other ### RULE in between
                first_pos = matches[0].end()
                for match in reversed(matches[1:]):
                    between = text[first_pos:match.start()]
                    if '### RULE' not in between:
                        # Replace match with spaces (same length) to keep offsets valid for this loop
                        # but actually we are reversed now so it's even safer to just slice
                        text = text[:match.start()] + text[match.end():]
        return text

    content = remove_redundant_rules(content)
    # Clean up excess whitespace left by replacement
    content = re.sub(r' {4,}', '\n', content)

    # 5. Standardize Section Separators
    # Standardize 'Section X. Title. - ' or 'Section X. Title. – ' to 'Section X. Title. — '
    # Note: We use a dash/em-dash/en-dash sequence
    content = re.sub(r'(Section \d+\. .*?\.) [—–-] ', r'\1 — ', content)

    # 6. Remove footnote markers (numerical superscripts)
    # Common ones: ¹, ², ³, etc.
    content = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]', '', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    apply_fixes('ROC_Combined.md')
    print("Fixes applied successfully.")
