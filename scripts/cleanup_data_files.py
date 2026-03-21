import os

files_to_delete = [
    'data/Doctrinal Cases.xlsx',
    'data/Doctrinal Cases_Combined.xlsx',
    'data/Doctrinal Cases_Corrected.xlsx',
    'data/Doctrinal Cases_Final.xlsx',
    'data/Doctrinal Cases_Final_Temp.xlsx',
    'data/Doctrinal Cases_Merged.xlsx',
    'data/Doctrinal Cases_Output.xlsx',
    'data/Doctrinal Cases_Output_Temp.xlsx',
    'data/Doctrinal Cases_Recovered.xlsx',
    'data/Doctrinal Cases_with_Digests.xlsx'
]

for file_path in files_to_delete:
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Deleted: {file_path}")
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
    else:
        print(f"Not found (skipped): {file_path}")

print("Cleanup complete.")
