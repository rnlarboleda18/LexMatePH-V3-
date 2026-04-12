import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

from blueprints.audio_provider import _get_text_for_codal

def test():
    try:
        # content_id = 10 for Section 7 Article II
        text, err = _get_text_for_codal(10, code_id='const')
        if err:
            print(f"Error: {err}")
        else:
            print("\n--- EXACT RETURNED TEXT FOR SECTION 7 ---")
            print(text)
    except Exception as e:
        print(f"Exception: {e}")

test()
