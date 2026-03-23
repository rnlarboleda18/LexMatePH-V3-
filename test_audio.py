import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from blueprints.audio_provider import _get_text_for_codal

text, err = _get_text_for_codal("8", "fc")
print("Text found:", repr(text))
print("Error:", repr(err))
