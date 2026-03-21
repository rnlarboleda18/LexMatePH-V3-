"""
Run Lawphil Converter on 2025 cases with overwrite enabled.
Uses the working CaseConverter from lawphil_convert_html_to_markdown.py
"""
from lawphil_convert_html_to_markdown import CaseConverter, process_file_wrapper
from pathlib import Path
import json
import concurrent.futures
import multiprocessing

HTML_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\MD\lawphil_v2")

def run_2025_conversion():
    """Convert all 2025 cases with overwrite enabled."""
    converter = CaseConverter()
    
    #Target 2025 directory
    year_dir = HTML_DIR / "2025"
    
    if not year_dir.exists():
        print(f"ERROR: Directory not found: {year_dir}")
        return
    
    # Get all HTML files
    all_files = list(year_dir.glob("*.html"))
    
    # Filter out PDF-related HTML files (.pdf.html, .pdf#page=xx.html)
    files = [f for f in all_files if '.pdf' not in f.name]
    
    excluded_count = len(all_files) - len(files)
    total = len(files)
    
    print(f"Found {len(all_files)} total HTML files in 2025 directory")
    print(f"Excluded {excluded_count} PDF-related files (.pdf.html, .pdf#page=xx.html)")
    print(f"Processing {total} clean HTML files")
    print(f"Starting conversion with overwrite=True using 8 parallel workers...")
    print("-" * 80)
    
    success = 0
    failed = 0
    skipped = 0
    
    # Use parallel processing with 8 workers
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_file_wrapper, p, None, True, OUTPUT_DIR): p for p in files}
        
        for idx, future in enumerate(concurrent.futures.as_completed(futures), 1):
            html_path = futures[future]
            result = future.result()
            
            status_icon = "✓" if result['status'] == 'success' else ("⊘" if result['status'] == 'skipped' else "✗")
            
            if result['status'] == 'success':
                success += 1
                case_no = result['entry'].get('case_number', 'N/A')
                filename = Path(result['entry']['output_md']).name
                print(f"[{idx}/{total}] {status_icon} {case_no} → {filename}")
                converter.manifest.append(result['entry'])
            elif result['status'] == 'skipped':
                skipped += 1
                print(f"[{idx}/{total}] {status_icon} Skipped: {html_path.name}")
            else:
                failed += 1
                print(f"[{idx}/{total}] {status_icon} Failed: {html_path.name} - {result.get('error', 'Unknown')}")
    
    print("-" * 80)
    print(f"\nConversion Complete!")
    print(f"  ✓ Success: {success}")
    print(f"  ⊘ Skipped: {skipped}")
    print(f"  ✗ Failed:  {failed}")
    print(f"  Total:    {total}")
    
    # Save manifest
    manifest_file = OUTPUT_DIR / "2025" / "conversion_manifest_2025_overwrite.json"
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(converter.manifest, f, indent=2)
    print(f"\nManifest saved to: {manifest_file}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_2025_conversion()

