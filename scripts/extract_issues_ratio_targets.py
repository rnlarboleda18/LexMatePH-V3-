import re

def extract_issues_ratio_targets():
    input_file = "non_compliant_issues_ratio.txt"
    output_file = "target_fix_issues_ratio.txt"
    
    selected_ids = []
    
    try:
        with open(input_file, 'r') as f:
            for line in f:
                if not line.strip(): continue
                
                # Format: "Case 12345: Reason..."
                match_id = re.search(r"Case (\d+):", line)
                if match_id:
                    selected_ids.append(match_id.group(1))
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(selected_ids))
            
        print(f"Extracted {len(selected_ids)} IDs for Issues/Ratio fix.")
        print(f"Saved to {output_file}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_issues_ratio_targets()
