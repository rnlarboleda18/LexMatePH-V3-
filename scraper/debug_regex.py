import re
import pathlib

filenames = [
    "gr_211833_2015.html",
    "ac_10110_2024.html", 
    "am_rtj-24-055.html",
    "gr_250636_caguioa.html",
    "gr_267487_2023.html"
]

def test_regex():
    for fname in filenames:
        print(f"\nTesting: {fname}")
        
        # Strategy 1: Standard "prefix_number_year"
        match = re.search(r"^([a-z]+)[_-]([\w-]+)[_-]\d{4}", fname, re.IGNORECASE)
        
        # Strategy 2: Loose "prefix_number" (catches caguioa.html, missing year suffix)
        if not match:
            match = re.search(r"^([a-z]+)[_-]([\w-]+)", fname, re.IGNORECASE)

        print(f"  Match: {match}")
        if match:
            group1, group2 = match.groups()
            print(f"  Groups: prefix='{group1}', num='{group2}'")
        else:
            print("  NO MATCH")

if __name__ == "__main__":
    test_regex()
