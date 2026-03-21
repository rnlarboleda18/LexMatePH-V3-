
import re
from bs4 import BeautifulSoup

def clean_case_number(case_number):
    """Clean case number"""
    if not case_number: return None
    case_number = re.sub(r'[\.\s,:-]*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+.*$', '', case_number, flags=re.IGNORECASE)
    case_number = re.sub(r'[,\s]+$', '', case_number)
    case_number = re.sub(r'\.+$', '.', case_number)
    return case_number.strip()

def extract_case_number_simulation(text):
    prefixes = [
        r'G\.?\s*R\.?', r'A\.?\s*C\.?', r'A\.?\s*M\.?', r'B\.?\s*M\.?', 
        r'Adj\.?\s*Res\.?', r'Adm\.?\s*Case', r'Adm\.?\s*Matter', 
        r'UNAV', r'UDK', r'OCA', r'I\.?P\.?I\.?', r'R\.?T\.?J\.?',
        r'Misc\.?\s*Bar', r'Nos?\.?'
    ]
    prefix_group = "|".join(prefixes)
    prefix_pattern = f"(?:\\b(?:{prefix_group}))(?=\\W|$)"

    # The regex from the current script (UPDATED)
    pattern = re.compile(f"({prefix_pattern}" + r".*?)(?=\s+-\s+|\s+vs\.?\s+|\s+v\.?\s+|\s+[A-Z][a-z]+ \d{1,2}, \d{4}|\s*$)", re.IGNORECASE | re.DOTALL)
    
    match = pattern.search(text)
    if match:
        raw_case = match.group(1)
        print(f"Raw Match: '{raw_case}'")
        cleaned = clean_case_number(raw_case)
        print(f"Cleaned: '{cleaned}'")
        return cleaned
    else:
        print("No match found.")
        return None

# Test Cases
print("--- Test Case 1: User Reported ---")
text1 = "G.R. No. 268399 - FRANCHESKA ALEEN BALABA BUBAN, PETITIONER, VS. NILO DELA PEÑA, RESPONDENT."
extract_case_number_simulation(text1)

print("\n--- Test Case 2: Standard Format ---")
text2 = "G.R. No. 12345 - People v. X"
extract_case_number_simulation(text2)

print("\n--- Test Case 3: ChanRobles Date Suffix ---")
text3 = "G.R. No. 12345, January 1, 2024"
extract_case_number_simulation(text3)
