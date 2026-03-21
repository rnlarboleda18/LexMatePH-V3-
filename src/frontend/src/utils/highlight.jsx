import React from 'react';

/**
 * Highlights parts of the text that match the search query.
 * Case-insensitive.
 * 
 * @param {string} text - The text to display.
 * @param {string} query - The search query to highlight.
 * @returns {React.ReactNode} - The text with highlighted spans.
 */
export const HighlightText = ({ text, query }) => {
    if (!query || !text) return text;

    // Escape special regex characters to prevent errors
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    
    const parts = text.split(new RegExp(`(${escapedQuery})`, 'gi'));
    
    return parts.map((part, index) =>
        part.toLowerCase() === query.toLowerCase() ? (
            <span key={index} className="bg-yellow-200 dark:bg-yellow-900/60 dark:text-yellow-100 font-semibold rounded px-0.5">
                {part}
            </span>
        ) : (
            part
        )
    );
};
