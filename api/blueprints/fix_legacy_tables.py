filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\blueprints\audio_provider.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Normalize
content_norm = content.replace('\r\n', '\n')

target = """    LEGACY_TABLES = {
        'rpc': 'rpc_codal',
        'civ': 'civ_codal',
        'labor': 'labor_codal',
        'const': 'const_codal',
        'fc': 'const_codal', # Family Code is inside const_codal with FC- prefix
    }"""

replacement = """    LEGACY_TABLES = {
        'rpc': 'rpc_codal',
        'civ': 'civ_codal',
        'labor': 'labor_codal',
        'const': 'consti_codal',
        'fc': 'consti_codal', # Family Code is inside consti_codal with FC- prefix
    }"""

if target in content_norm:
    content_new = content_norm.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("Replace complete")
else:
    # Try with 4 spaces instead of 4 spaces indent if it differs
    print("Target not found exactly")
