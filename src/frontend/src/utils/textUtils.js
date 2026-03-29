/**
 * Converts ALL CAPS strings to Title Case while preserving legal formatting.
 * Only transforms if the string is currently in UPPERCASE.
 */
export const toTitleCase = (str, skipRomanKeywords = []) => {
    if (!str) return str;
    
    // If it contains NO alphabetic letters at all, just numbers/symbols, so skip.
    if (!/[A-Z]/.test(str) && !/[a-z]/.test(str)) return str;

    const smallWords = /^(a|an|and|as|at|but|by|en|for|if|in|of|on|or|the|to|v\.?|via)$/i;
    const romanNumerals = /^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)$/i;
    
    // Map words/digits to Roman numerals for structural numbering (e.g. Chapter One -> Chapter I)
    const numberingMap = {
        'ONE': 'I', 'TWO': 'II', 'THREE': 'III', 'FOUR': 'IV', 'FIVE': 'V',
        'SIX': 'VI', 'SEVEN': 'VII', 'EIGHT': 'VIII', 'NINE': 'IX', 'TEN': 'X',
        'ELEVEN': 'XI', 'TWELVE': 'XII', 'THIRDEEN': 'XIII', 'FOURTEEN': 'XIV', 'FIFTEEN': 'XV',
        '1': 'I', '2': 'II', '3': 'III', '4': 'IV', '5': 'V',
        '6': 'VI', '7': 'VII', '8': 'VIII', '9': 'IX', '10': 'X'
    };

    const reverseMap = {
        'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5',
        'VI': '6', 'VII': '7', 'VIII': '8', 'IX': '9', 'X': '10',
        'XI': '11', 'XII': '12', 'XIII': '13', 'XIV': '14', 'XV': '15'
    };
    
    return str.split(/(\s+|[-.,;:?!/()])/).map((word, index, array) => {
        if (!word.trim() || word.match(/^[-.,;:?!/()]$/)) return word;
        
        // Find actual word index (excluding separators)
        const wordParts = array.slice(0, index).filter(w => w.trim() && !w.match(/^[-.,;:?!/()]$/));
        const wordIndex = wordParts.length;
        
        // Find total number of actual words
        const totalWords = array.filter(w => w.trim() && !w.match(/^[-.,;:?!/()]$/)).length;
        
        const cleanWord = word.trim().toUpperCase();
        
        // 1. Process Structural Numbering
        const prevWord = wordIndex > 0 ? wordParts[wordIndex - 1].toUpperCase() : null;
        const prevSeparator = index > 0 ? array[index - 1] : null;

        if (prevWord && /^(CHAPTER|SECTION|TITLE|BOOK|PART|RULE)$/.test(prevWord)) {
            // Conversion/Preservation logic for numbering
            if (skipRomanKeywords.includes(prevWord)) {
                // If the keyword is skipped (like SECTION in ROC), preserve Arabic/Word as-is
                // OR convert Roman back to Arabic if it was already formatted as Roman in input
                if (reverseMap[cleanWord]) return reverseMap[cleanWord];
                return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
            }
            if (numberingMap[cleanWord]) {
                return numberingMap[cleanWord];
            }
        }

        // 2. Force Existing Roman Numerals to Uppercase (if not explicitly skipped above)
        if (romanNumerals.test(cleanWord)) {
            return word.toUpperCase();
        }

        // 3. Force uppercase for single letter alphabetical subsection suffixes (e.g. 266-A)
        // If there is a hyphen directly before this single character
        if (cleanWord.length === 1 && cleanWord.match(/[A-Z]/) && prevSeparator === '-') {
            return word.toUpperCase();
        }
        
        // Capitalize if first word, last word, or not a small word
        if (wordIndex === 0 || wordIndex === totalWords - 1 || !smallWords.test(word)) {
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        }
        return word.toLowerCase();
    }).join('');
};
