import pandas as pd
import os

FINAL_FILE = 'data/Doctrinal Cases_Final.xlsx'
ORIGINAL_FILE = 'data/Doctrinal Cases.xlsx'
OUTPUT_FILE = 'data/Doctrinal Cases_Corrected.xlsx'

def fix_subjects():
    if not os.path.exists(FINAL_FILE) or not os.path.exists(ORIGINAL_FILE):
        print("Input files not found.")
        return

    print(f"Loading original data from {ORIGINAL_FILE}...")
    xls_original = pd.ExcelFile(ORIGINAL_FILE)
    
    print(f"Loading final data from {FINAL_FILE}...")
    xls_final = pd.ExcelFile(FINAL_FILE)
    
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        for sheet_name in xls_final.sheet_names:
            print(f"Processing sheet: {sheet_name}")
            
            # Load data
            df_final = pd.read_excel(xls_final, sheet_name=sheet_name)
            
            if sheet_name in xls_original.sheet_names:
                df_original = pd.read_excel(xls_original, sheet_name=sheet_name)
                
                # Ensure Case Title is string and stripped for matching
                df_final['Case Title Match'] = df_final['Case Title'].astype(str).str.strip().str.lower()
                df_original['Case Title Match'] = df_original['Case Title'].astype(str).str.strip().str.lower()
                
                # Create a mapping dictionary from original data: Case Title -> Subject
                # We use the first occurrence if duplicates exist (though duplicates shouldn't exist ideally)
                subject_map = dict(zip(df_original['Case Title Match'], df_original['Subject']))
                
                # Update Subject in final df
                def get_correct_subject(row):
                    title = row['Case Title Match']
                    if title in subject_map:
                        return subject_map[title]
                    return row['Subject'] # Fallback to existing if not found
                
                df_final['Subject'] = df_final.apply(get_correct_subject, axis=1)
                
                # Drop helper column
                df_final = df_final.drop(columns=['Case Title Match'])
                
                print(f"  Updated subjects for {len(df_final)} rows.")
            else:
                print(f"  Warning: Sheet {sheet_name} not found in original file. Keeping existing subjects.")
            
            # Save to new file
            df_final.to_excel(writer, sheet_name=sheet_name, index=False)
            
    print(f"Saved corrected data to {OUTPUT_FILE}")

if __name__ == "__main__":
    fix_subjects()
