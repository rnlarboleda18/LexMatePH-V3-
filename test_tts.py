import re

SPANISH_TERMS = [
    "reclusión perpetua", "reclusion perpetua",
    "reclusión temporal", "reclusion temporal",
    "prisión mayor", "prision mayor",
    "prisión correccional", "prision correccional",
    "arresto mayor",
    "arresto menor",
    "prisión", "prision",
    "arresto",
    "mayor",
    "menor",
    "correccional",
    "reclusión", "reclusion",
    "perpetua",
    "temporal",
    "destierro",
    "fianza"
]

def _apply_custom_pronunciations(text):
    for term in SPANISH_TERMS:
        try:
            text = re.sub(fr'(?i)(?<!__ES_START__)\b({term})\b(?!__ES_END__)', r'__ES_START__\1__ES_END__', text)
        except Exception as e:
            print(f"Error on term {term}: {e}")
            raise
    return text

def test_tts(text):
    print(f"\n--- Original ---")
    print(text)
    
    # 1. Phonetics
    full_text = _apply_custom_pronunciations(text)
    print(f"\n--- After Custom Pronunciations ---")
    print(full_text)
    
    # 2. Chunk processing
    escaped_text = full_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    escaped_text = escaped_text.replace("__ES_START__", "<lang xml:lang='es-MX'>")
    escaped_text = escaped_text.replace("__ES_END__", "</lang>")
    
    print(f"\n--- Final SSML prosody payload ---")
    print(escaped_text)

if __name__ == "__main__":
    try:
        test_tts("The penalty of arresto mayor shall be imposed.")
        test_tts("This involves prisión correccional and reclusión perpetua.")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
