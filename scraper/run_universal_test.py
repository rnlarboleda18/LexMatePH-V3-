
import os
import random
from pathlib import Path
from lawphil_convert_html_to_markdown import CaseConverter

# Setup Paths
SOURCE_ROOT = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")
OUTPUT_ROOT = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\MD\test_universal")
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

def run_test():
    converter = CaseConverter(output_dir=OUTPUT_ROOT)
    
    results = {
        'success': [],
        'failed': [],
        'skipped': [] # Should not happen with overwrite=True
    }
    
    years = range(1901, 2026)
    
    print(f"Starting Universal Coverage Test (1901-2025)...")
    
    for year in years:
        year_dir = SOURCE_ROOT / str(year)
        if not year_dir.exists():
            print(f"Year {year}: [MISSING DIRECTORY]")
            continue
            
        html_files = list(year_dir.glob("*.html"))
        if not html_files:
            print(f"Year {year}: [NO FILES]")
            continue
            
        # Pick one random file
        target_file = random.choice(html_files)
        
        print(f"Testing {year}: {target_file.name}...")
        
        try:
            res = converter.process_file(target_file, overwrite=True)
            if res['status'] == 'success':
                results['success'].append(f"{year}: {res['entry']['case_number']}")
                print(f"  -> Success")
            else:
                results['failed'].append(f"{year}: {target_file.name} - {res.get('error')}")
                print(f"  -> FAILED: {res.get('error')}")
                
        except Exception as e:
            results['failed'].append(f"{year}: {target_file.name} - {str(e)}")
            print(f"  -> CRASH: {e}")

    print("\n" + "="*50)
    print(f"Test Complete.")
    print(f"Success: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    
    if results['failed']:
        print("\nFailures:")
        for f in results['failed']:
            print(f)
            
if __name__ == "__main__":
    run_test()
