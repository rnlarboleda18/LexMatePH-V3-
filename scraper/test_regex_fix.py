import re

def test_regex():
    prefix_pattern = r'(?:G\.\s*R\.?|A\.\s*C\.?|A\.\s*M\.?|B\.\s*M\.?|Adj\.\s*Res\.?|Adm\.\s*Case|Adm\.\s*Matter|UNAV|UDK)'
    
    test_cases = [
        "A.M. No. 08-1-16-SC - THE RULE ON THE WRIT OF HABEAS DATA",
        "A.M. No. MTJ-05-1610 - Dr. Jose S. Luna v. Judge Eduardo H. Mirafuente",
        "G.R. No. 12345",
        "G.R. No. 12345, January 1, 2000",
        "A.C. No. 1234. July 1, 2000",
        "UDK 12345 - Title",
        "G.R No. 12345",
        "G.R. Nos. 141011 & 141028 - Title Here",
        "G.R. NOS. 141104 & 148763 - ATLAS CONSOLIDATED vs COMMISSIONER",
        "A.M. Nos. 12-34-SC & 56-78-SC - Consolidated Admin Matters"
    ]
    
    # OLD REGEX (Simulation)
    print("--- OLD REGEX ---")
    old_regex = rf'({prefix_pattern}\s*(?:No\.?)?\s*[^,:]+)'
    for text in test_cases:
        match = re.search(old_regex, text, re.IGNORECASE)
        if match:
            print(f"'{text}' -> '{match.group(1)}'")
        else:
            print(f"'{text}' -> NO MATCH")

    # NEW REGEX
    print("\n--- NEW REGEX ---")
    # Stop at ' - ', ' – ', ',', ':', or End of String
    # handling the prefix, optional No., then content until separator
    new_regex = rf'({prefix_pattern}\s*(?:No\.?)?\s*.*?(?=\s+[-–]\s+|[,:]|$))'
    
    for text in test_cases:
        match = re.search(new_regex, text, re.IGNORECASE)
        if match:
            print(f"'{text}' -> '{match.group(1)}'")
        else:
            print(f"'{text}' -> NO MATCH")

if __name__ == "__main__":
    test_regex()
