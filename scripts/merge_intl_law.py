import pandas as pd
import os

INPUT_FILE = 'data/Doctrinal Cases_Corrected.xlsx'
OUTPUT_FILE = 'data/Doctrinal Cases_Merged.xlsx'

def merge_intl_law():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        return

    print(f"Loading {INPUT_FILE}...")
    xl = pd.ExcelFile(INPUT_FILE)
    
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        for sheet_name in xl.sheet_names:
            print(f"Processing sheet: {sheet_name}")
            df = xl.parse(sheet_name)
            
            # Check if this sheet contains International Law cases
            # The sheet name might be "Political Law and Intl Law" (from original) or "International Law" (if I split it? No, I didn't split sheets, just subjects)
            # But wait, fix_subjects.py updated the 'Subject' column, but kept the original sheet structure (which was merged).
            # So the sheet "Political Law and Intl Law" contains both subjects.
            
            if 'Subject' in df.columns:
                # Identify International Law rows
                # Check for "International Law" or "Int'l Law"
                mask_intl = df['Subject'].isin(['International Law', "Int'l Law"])
                
                if mask_intl.any():
                    print(f"  Found {mask_intl.sum()} International Law cases.")
                    
                    # Set source_label to 'PIC'
                    df.loc[mask_intl, 'source_label'] = 'PIC'
                    
                    # Change Subject to 'Political Law'
                    df.loc[mask_intl, 'Subject'] = 'Political Law'
                    
            # Save to new file
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
    print(f"Saved merged data to {OUTPUT_FILE}")

if __name__ == "__main__":
    merge_intl_law()
