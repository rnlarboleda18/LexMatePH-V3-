import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

from blueprints.audio_provider import _apply_custom_pronunciations

text = "ARTICLE I. National Territory\n\nARTICLE II. Declaration of Principles"
clean = _apply_custom_pronunciations(text)
print("\n--- ROMAN NUMERAL CONVERSION TEST ---")
print(clean)
if "ARTICLE 1" in clean and "ARTICLE 2" in clean:
    print("SUCCESS")
else:
    print("FAILURE")
