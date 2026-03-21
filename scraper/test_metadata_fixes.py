import re
import unittest
from datetime import datetime

# Improt the class (mocking context if needed, but we can test the regex logic directly first)
# Actually, better to import the methods or copy them for isolated testing if we can't easily import the class without dependencies.
# Given the complexity, I'll copy the relevant methods into this test script for "Whitebox" testing of the LOGIC, 
# then I will apply the fix to the actual file.

class TestMetadataExtraction(unittest.TestCase):

    def test_ponente_regex(self):
        # Current Logic (Simulated) vs New Logic
        candidate = "**LEONARDO-DE CASTRO, *J.:***"
        
        # OLD REGEX (Defective)
        old_pattern = r'(?:\*\*|\*|^)([A-Z\.]+)(?:,|\s+)(?:[\*_]*\s*)+(C\.?J\.?|J\.?)'
        old_match = re.search(old_pattern, candidate)
        print(f"Old Ponente Match: {old_match.groups() if old_match else 'None'}")
        
        # NEW REGEX ( Proposed)
        # Added \- to the name group
        new_pattern = r'(?:\*\*|\*|^)([A-Z\.\-\s]+)(?:,|\s+)(?:[\*_]*\s*)+(C\.?J\.?|J\.?)'
        new_match = re.search(new_pattern, candidate)
        print(f"New Ponente Match: {new_match.groups() if new_match else 'None'}")
        
        self.assertIsNotNone(new_match, "Should match hyphenated names")
        self.assertEqual(new_match.group(1), "LEONARDO-DE CASTRO")

    def test_case_number_date_coupling(self):
        # Case: "G.R. No. 197250            July 17, 2013"
        # The comma is missing, so the naive extract might fail or grab everything.
        
        text = "G.R. No. 197250            July 17, 2013"
        info = {'case_number': None, 'date': None}
        
        # OLD LOGIC SIMULATION (Roughly)
        # If "G.R." in text... clean_no = text...
        clean_no = text.replace("[", "").replace("]", "").strip()
        # It would capture the whole thing because it's under 50 chars?
        # "G.R. No. 197250            July 17, 2013" is ~40 chars.
        print(f"Old Case Number logic would capture: '{clean_no}'")
        
        # NEW LOGIC PROPOSAL
        # 1. Try to split by date if found at end
        date_pattern = r'([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})'
        date_match = re.search(date_pattern, clean_no)
        
        final_case_no = clean_no
        if date_match:
             # If the date is at the end, strip it
             found_date = date_match.group(1)
             print(f"Found date in case number: {found_date}")
             final_case_no = clean_no.replace(found_date, "").strip()
        
        print(f"New Case Number logic would capture: '{final_case_no}'")
        
        self.assertEqual(final_case_no, "G.R. No. 197250")

    def test_ponente_via_opinion_header(self):
        # Case: G.R. No. 264071
        # Header is "SEPARATE CONCURRING OPINION", followed by "**CAGUIOA, *J.:***"
        
        lines = [
            "EN BANC",
            "[ G.R. No. 264071, August 13, 2024 ]",
            "SEPARATE CONCURRING OPINION",
            "**CAGUIOA, *J.:***"
        ]
        
        # Current Logic Simulation:
        start_index = -1
        for i, line in enumerate(lines):
             if re.match(r'^[\*#]*\s*D\s*E\s*C\s*I\s*S\s*I\s*O\s*N\s*[\*#]*$', line, re.IGNORECASE) or \
                re.match(r'^[\*#]*\s*R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N\s*[\*#]*$', line, re.IGNORECASE):
                 start_index = i
                 break
        
        print(f"Start Index for Opinion: {start_index}") # Should be -1 currently
        
        # PROPOSED LOGIC: Add OPINION check
        # Broad enough to catch SEPARATE CONCURRING OPINION
        for i, line in enumerate(lines):
             # Simplified regex for testing concept (ignoring spaces since simplified)
             # In implementation I'll use regex similar to DECISION
             if "OPINION" in line and len(line) < 50: 
                 start_index = i
                 break
        
        print(f"New Start Index: {start_index} (Line: {lines[start_index]})")
        
        extracted_ponente = None
        if start_index != -1:
             candidate = lines[start_index + 1]
             # Using the FIXED regex from previous step
             new_pattern = r'(?:\*\*|\*|^)([A-Z\.\-\s]+)(?:,|\s+)(?:[\*_]*\s*)+(C\.?J\.?|J\.?)'
             match = re.search(new_pattern, candidate)
             if match:
                 extracted_ponente = f"{match.group(1).strip()}, {match.group(2).strip()}"

        print(f"Extracted Ponente: {extracted_ponente}")
        self.assertEqual(extracted_ponente, "CAGUIOA, J.")

    def test_fallback_ponente_markdown(self):
        # Case: G.R. No. L-299 (1901)
        # No "DECISION" header, just signature at bottom.
        # Line: "**TORRES, *J.:***"
        
        lines = [
            "Content of the case...",
            "Respectfully submitted.",
            "**TORRES, *J.:***"
        ]
        
        # Current Logic Simulation (Fallback Ponente 2)
        # Checks last 50 lines.
        # Regex: r'^([A-Z\.\s]+),\s*(?:J\.|C\.J\.|Chief Justice|Associate Justice)\.?\s*$'
        
        print("Testing Fallback Ponente with Markdown...")
        found = False
        meta_ponente = None
        
        clean_lines_reversed = reversed(lines)
        for line in clean_lines_reversed:
            clean_line = line.strip()
            # OLD REGEX (Defective for markdown)
            match = re.search(r'^([A-Z\.\s]+),\s*(?:J\.|C\.J\.|Chief Justice|Associate Justice)\.?\s*$', clean_line)
            if match:
                print("Old Regex Matched!")
                found = True
                break
        
        if not found:
            print("Old Regex Failed.")

        # PROPOSED LOGIC: Strip markdown or use robust regex
        # Robust regex: Allow [*_]* at start, end, and around title. Allow colon at end.
        # r'^[\*_]*([A-Z\.\s\-]+)[\*_]*,\s*[\*_]*(?:J\.|C\.J\.|Chief Justice|Associate Justice)[\.]?[\*_]*[:]?[\*_]*$'
        
        robust_pattern = r'^[\*_]*([A-Z\.\s\-]+)[\*_]*,\s*[\*_]*(?:J\.|C\.J\.|Chief Justice|Associate Justice)[\.]?[\*_]*[:]?[\*_]*$'
        
        for line in reversed(lines):
            clean_line = line.strip()
            match = re.search(robust_pattern, clean_line)
            if match:
                 name = match.group(1).strip()
                 # Clean up name if it has internal markdown? regex group 1 is [A-Z\.\s\-] so it should be cleanish.
                 meta_ponente = f"{name}, J." # Simplified assignment
                 break
        
        print(f"New Regex Extracted: {meta_ponente}")
        self.assertEqual(meta_ponente, "TORRES, J.")

    def test_case_number_wide_gap(self):
        # Case: "G.R. No. L-299            October 29, 1901"
        # Failed to decouple date.
        
        raw_val = "G.R. No. L-299            October 29, 1901"
        clean_no = raw_val
        
        # Logic check
        print(f"Testing Wide Gap: '{clean_no}'")
        
        # New Logic from previous fix
        date_match_coupled = re.search(r'([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})$', clean_no)
        if date_match_coupled:
            extracted_date = date_match_coupled.group(1)
            print(f"Matched Date: '{extracted_date}'")
            clean_no = clean_no.replace(extracted_date, "").strip()
        else:
            print("Failed to match date at end.")
            
        print(f"Result: '{clean_no}'")
        self.assertEqual(clean_no, "G.R. No. L-299")



if __name__ == '__main__':
    unittest.main()
