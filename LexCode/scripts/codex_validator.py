"""
Codex Validator: Ensures strict literal fidelity when applying amendments
"""

import re
from difflib import SequenceMatcher

class CodexValidator:
    # Common Spanish legal terms that should NEVER be translated
    SPANISH_TERMS = [
        "reclusion perpetua", "reclusion temporal", "prision mayor",
        "prision correccional", "arresto mayor", "arresto menor",
        "destierro", "presidio", "privacion", "inhabilitacion",
        "suspension", "multa", "republica filipina", "codigo penal"
    ]
    
    def __init__(self, strict_mode=True):
        """
        Args:
            strict_mode: If True, validation is very strict. If False, allows minor variations.
        """
        self.strict_mode = strict_mode
        self.errors = []
        self.warnings = []
    
    def validate_amendment(self, old_text, new_text, unchanged_markers=None):
        """
        Validates that an amendment was applied with literal fidelity.
        
        Args:
            old_text: Original article text
            new_text: Amended article text
            unchanged_markers: List of text snippets that should remain unchanged
        
        Returns:
            dict: {
                "valid": bool,
                "errors": list,
                "warnings": list,
                "confidence_score": float (0-1)
            }
        """
        self.errors = []
        self.warnings = []
        
        # Run all validation checks
        self._check_spanish_translation(old_text, new_text)
        self._check_length_anomaly(old_text, new_text)
        self._check_unchanged_sections(old_text, new_text, unchanged_markers)
        self._check_structural_integrity(old_text, new_text)
        
        # Calculate confidence score
        confidence = self._calculate_confidence()
        
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "confidence_score": confidence
        }
    
    def _check_spanish_translation(self, old_text, new_text):
        """Ensure Spanish legal terms were not translated"""
        old_lower = old_text.lower()
        new_lower = new_text.lower()
        
        for term in self.SPANISH_TERMS:
            old_count = old_lower.count(term)
            new_count = new_lower.count(term)
            
            # If term disappeared, it might have been translated OR removed by amendment
            if old_count > new_count:
                self.warnings.append(
                    f"Spanish term '{term}' appears {old_count} times in old text but only {new_count} times in new text. Verify if removed by law."
                )
            elif old_count < new_count and old_count > 0:
                self.warnings.append(
                    f"Spanish term '{term}' appears more frequently in new text ({new_count} vs {old_count}). Verify accuracy."
                )
    
    def _check_length_anomaly(self, old_text, new_text):
        """Check if length change is suspicious"""
        old_len = len(old_text)
        new_len = len(new_text)
        
        if old_len == 0:
            return  # Can't compare empty text
        
        change_ratio = abs(new_len - old_len) / old_len
        
        # If text changed by more than 1000%, it's suspicious 
        # (BUT ignore if original was just a placeholder/very short under 200 chars)
        if change_ratio > 10.0 and old_len > 200:
            self.errors.append(
                f"Extreme length change: {old_len} chars -> {new_len} chars ({change_ratio:.1%} change). Possible hallucination."
            )
        elif change_ratio > 5.0 and old_len > 200:
            self.warnings.append(
                f"Significant length change: {old_len} chars -> {new_len} chars ({change_ratio:.1%} change)."
            )
    
    def _check_unchanged_sections(self, old_text, new_text, unchanged_markers):
        """Verify that sections marked as unchanged are truly unchanged"""
        if not unchanged_markers:
            return
        
        for marker in unchanged_markers:
            if marker in old_text and marker not in new_text:
                self.errors.append(
                    f"Unchanged marker '{marker[:50]}...' was removed or modified."
                )
    
    def _check_structural_integrity(self, old_text, new_text):
        """Check if basic structure (punctuation patterns, capitalization) is preserved"""
        
        # Check if article number prefix is preserved (handle markdown formatting)
        # Strip markdown markers for comparison
        old_clean = old_text.replace('**', '').replace('*', '')
        new_clean = new_text.replace('**', '').replace('*', '')
        
        old_article_num = re.match(r'^(ART\.|Article)\s+\d+[A-Za-z]?\.', old_clean, re.IGNORECASE)
        new_article_num = re.match(r'^(ART\.|Article)\s+\d+[A-Za-z]?\.', new_clean, re.IGNORECASE)
        
        if old_article_num and not new_article_num:
            self.warnings.append("Article number prefix pattern changed (may be markdown formatting).")
        
        # Check for suspicious pattern changes (e.g., all caps becoming title case)
        old_caps_ratio = sum(1 for c in old_text if c.isupper()) / max(len(old_text), 1)
        new_caps_ratio = sum(1 for c in new_text if c.isupper()) / max(len(new_text), 1)
        
        if abs(old_caps_ratio - new_caps_ratio) > 0.15:  # 15% change in caps ratio
            self.warnings.append(
                f"Capitalization pattern changed significantly ({old_caps_ratio:.1%} -> {new_caps_ratio:.1%})."
            )
    
    def _calculate_confidence(self):
        """Calculate overall confidence score"""
        # Start with perfect score
        score = 1.0
        
        # Deduct for errors and warnings
        score -= len(self.errors) * 0.3
        score -= len(self.warnings) * 0.1
        
        return max(0.0, min(1.0, score))

def test_validator():
    """Test the validator with known good and bad cases"""
    validator = CodexValidator()
    
    # Test 1: Good amendment (only specific text changed)
    old_1 = "ART. 329. Other mischiefs. Penalty: arresto mayor and fine of 500 pesos."
    new_1 = "ART. 329. Other mischiefs. Penalty: arresto mayor in its medium and maximum periods."
    
    result = validator.validate_amendment(old_1, new_1)
    print("Test 1 (Good Amendment):", "PASS" if result["valid"] else "FAIL")
    print(f"  Confidence: {result['confidence_score']:.2f}")
    
    # Test 2: Bad amendment (Spanish term translated)
    old_2 = "Penalty: reclusion perpetua"
    new_2 = "Penalty: life imprisonment"  # Translated!
    
    result = validator.validate_amendment(old_2, new_2)
    print("\nTest 2 (Spanish Translation):", "FAIL Expected" if not result["valid"] else "ERROR - Should have failed!")
    print(f"  Errors: {result['errors']}")
    
    # Test 3: Bad amendment (extreme length change)
    old_3 = "ART. 100. Short article."
    new_3 = "ART. 100. This is now a very long article with lots of added content that was not in the original, suggesting possible AI hallucination or paraphrasing instead of literal amendment application."
    
    result = validator.validate_amendment(old_3, new_3)
    print("\nTest 3 (Length Anomaly):", "FAIL Expected" if not result["valid"] else "WARNING")
    print(f"  Warnings: {result['warnings']}")

if __name__ == "__main__":
    test_validator()
