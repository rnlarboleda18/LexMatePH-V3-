import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

from blueprints.audio_provider import _get_text_for_codal

def test():
    try:
        # content_id = 3 for Standalone Principles row
        text, err = _get_text_for_codal(3, code_id='const')
        if err:
            print(f"Error: {err}")
        else:
            print("\n--- EXACT RETURNED TEXT FOR STANDALONE ROW 3 ---")
            print(text)
    except Exception as e:
        print(f"Exception: {e}")

test()
