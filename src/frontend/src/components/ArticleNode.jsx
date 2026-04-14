import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Info, Gavel, FileSignature, X, Headphones } from 'lucide-react';
import { useLexPlayApi } from '../features/lexplay/useLexPlay';
import { toTitleCase } from '../utils/textUtils';
import {
    collapseBlankLinesInPipeTables,
    extractRccLeadingShortTitle,
    fixStrayQuotationArtifacts,
    repairRccBrokenIncorporatorPipeHeaders,
    repairRccListMidItemLineBreaks,
    rccSectionNumberFromArticleNum,
    rccSectionNumberDisplayWithPeriod,
    shieldGfmTables,
} from '../utils/codalMarkdown';
import { RPC_ARTICLE_266_BODY_MD, isCorruptedRpcArticle266Body } from '../data/rpcArticle266Fallback';

/** RCC chrome: remove trailing dash glue (E-Library “Title. -” before body). */
function cleanRccSectionHeaderFragment(s) {
    if (s == null || s === '') return '';
    return String(s)
        .replace(/\u00a0/g, ' ')
        .replace(/\.\s*[-–—]\s*$/u, '.')
        .replace(/\s*[-–—]\s*$/u, '')
        .trim();
}

const ArticleNode = React.memo(({ article, highlight, showElements = true, showHistory = false, hiddenPhrases = [], centerLayout = false, onToggleJurisprudence, onToggleAmendment, codeId }) => {
    if (!article) return null;
    const [isHistoryOpen, setIsHistoryOpen] = useState(false);

    // --- HOOKS MUST BE CALLED TOP-LEVEL ---
    const { playNow } = useLexPlayApi();
    const docCode = (codeId || article?.code_id || "").toLowerCase();
    const isRcc = docCode === 'rcc' || (article?.code_id || '').toLowerCase() === 'rcc';
    const rccSectionLabel = 'Section';

    const hasContent = !!(article.content_md || 
                  (article.elements && article.elements !== '[]') || 
                  (article.amendments && article.amendments !== '[]') ||
                  (article.amendment_links && article.amendment_links.length > 0));

    const skipKeywords =
        docCode === 'rcc'
            ? ['SECTION', 'TITLE', 'CHAPTER']
            : ['roc', 'const'].includes(docCode)
              ? ['SECTION', 'RULE']
              : [];

    const handleAddToPlaylist = (e) => {
        e.stopPropagation();

        const numStr = String(article.article_num || '');
        const provLabel = docCode === 'rcc' ? 'Section' : 'Article';
        let displayTitle = /^(article|preamble|section|rule)/i.test(numStr)
            ? toTitleCase(numStr, skipKeywords)
            : docCode === 'rcc'
              ? `Section ${rccSectionNumberDisplayWithPeriod(numStr)}`
              : `${provLabel} ${numStr}`;
        if (numStr === '0') displayTitle = docCode === 'rcc' ? 'Preliminary Section' : 'Preliminary Article';

        const codexNames = {
            'rpc': 'Revised Penal Code',
            'civ': 'Civil Code of the Philippines',
            'rcc': 'Revised Corporation Code',
            'fc': 'Family Code',
            'roc': 'Rules of Court',
            'const': 'The 1987 Philippine Constitution',
            'labor': 'Labor Code of the Philippines',
            'tax': 'National Internal Revenue Code',
            'cpg': 'Code of Professional Responsibility',
            'admin': 'Administrative Code',
            'spl': 'Special Penal Laws'
        };

        const docName = codexNames[docCode] || 'Philippine Law';
        let subtitle = docName;
        
        if (docCode === 'const') {
            const articleHeader = article.title_label || '';
            
            if (displayTitle.toLowerCase().includes('preamble') || articleHeader.toLowerCase().includes('preamble')) {
                displayTitle = "Preamble";
            } else {
                // title_label is like "ARTICLE II\nDeclaration of Principles and State Policies"
                const headerLines = articleHeader.split('\n');
                const articleMatch = headerLines[0].match(/(ARTICLE\s+[A-Z0-9-]+)/i);
                const chapTitle = headerLines[1] ? headerLines[1].trim() : '';

                if (articleMatch) {
                    const articleLabel = toTitleCase(articleMatch[1]); // "Article II"
                    if (displayTitle.toUpperCase().startsWith('ARTICLE')) {
                        // displayTitle is already the article label (chapter headers / standalone articles)
                        // Build "Article I. National Territory" instead of "Article I, Article I"
                        displayTitle = chapTitle
                            ? `${articleLabel}. ${chapTitle}`
                            : articleLabel;
                    } else {
                        // displayTitle is "Section 5" ΓÇö prepend article label for context
                        displayTitle = `${articleLabel}, ${displayTitle}`;
                    }
                }
            }
        } else {
            // General Codal Fallback - Append the specific item's title (if any) directly to the main display track
            if (article.article_title) {
                 // Remove any trailing periods on the display title for neat concatenation
                 displayTitle = `${displayTitle.replace(/\.$/, '')}. ${toTitleCase(article.article_title, skipKeywords)}`;
            }
        }

        playNow({
            id: article.key_id || article.id || article.version_id || article.article_num,
            code_id: codeId || article.code_id || null,
            type: 'codal',
            title: displayTitle,
            subtitle: subtitle
        });
    };

    let contentToDisplay = article.content_md || '';
    contentToDisplay = fixStrayQuotationArtifacts(contentToDisplay);
    contentToDisplay = contentToDisplay
        .replace(/\*Provided,\*\s*That/gi, '*Provided,* That')
        .replace(/\*Provided,\s*further,\*\s*That/gi, '*Provided, further,* That')
        .replace(/:\s*Provided,\s*That(?=\s|[A-Za-z(])/gi, ': Provided, That ')
        .replace(/:\s*Provided,\s*further,\s*That(?=\s|[A-Za-z(])/gi, ': Provided, further, That ');

    const articleNumKey = String(article.article_num ?? article.article_number ?? '').trim();
    const normArticleKey = (s) => {
        const m = String(s || '').match(/(?:article|section)\s+([\d]+(?:-[a-z]+)?)/i);
        return m ? m[1].toLowerCase() : String(s || '').toLowerCase().replace(/\s+/g, '');
    };

    const isRpcLike = (codeId || '').toLowerCase() === 'rpc' || (article?.code_id || '').toLowerCase() === 'rpc';

    // Stale DB: Article 266 row sometimes still opens with a 266-A fragment; recover real Art. 266 body.
    // Never clear the whole article: the strict \n\n anchor often fails (single newlines, OCR spacing).
    if (isRpcLike && articleNumKey === '266') {
        let t = contentToDisplay.trimStart();
        if (/^"?\s*Article\s+266-A\./i.test(t)) {
            const phrase = 'the crime of slight physical injuries';
            const ix = contentToDisplay.toLowerCase().indexOf(phrase);
            if (ix !== -1) {
                contentToDisplay = contentToDisplay.slice(ix).trimStart();
            } else {
                for (let i = 0; i < 25 && /^"?\s*Article\s+266-A\./i.test(contentToDisplay.trimStart()); i++) {
                    contentToDisplay = contentToDisplay.replace(/^[^\n]*(?:\n|$)/, '').trimStart();
                }
            }
        }
    }

    if (isRpcLike && articleNumKey === '266' && isCorruptedRpcArticle266Body(contentToDisplay)) {
        contentToDisplay = RPC_ARTICLE_266_BODY_MD;
    }

    // GLOBAL PRE-PROCESS: The DB stores enumeration markers as backslash-escaped parens, e.g. \(2\).
    // Un-escape all \(X\) patterns to (X) so all downstream regex splitting works correctly.
    contentToDisplay = contentToDisplay.replace(/\\\(([^)]*)\\\)/g, '($1)');

    // Strip section headers that were mistakenly included in content during ingestion
    // These should be rendered separately via section_label, not embedded in content
    contentToDisplay = contentToDisplay.replace(/^##\s+SECTION\s+\d+\s+.+$/gm, '').trim();

    // Strip a leading H1 that looks like a document title (e.g. "# THE REVISED PENAL CODE")
    // These duplicate the document-title header now shown at the top of CodalStream.
    // Safe rule: strip H1 lines at the very start that do NOT begin with "Article", "Section", or "Art."
    contentToDisplay = contentToDisplay.replace(/^#\s+(?!Article|Section|Art\.)[^\n]+\n?/, '').trim();

    // Force nested enumerations that are incorrectly fused (either on the same line or via a single \n)
    // to become independent paragraph building-blocks so they can each receive their own cascading indent styling.
    // SKIP for Constitution: the Constitution-specific rendering block handles all splitting itself.
    // (Running these rules on Constitution breaks Section headers by splitting SECTION 12. (1) into two paragraphs,
    //  and also causes false positives like "provided with one." being treated as an ordinal marker.)
    const _isConstForPreProc = (codeId || article?.code_id || '').toLowerCase() === 'const';
    if (!_isConstForPreProc) {
        let preShield = contentToDisplay;
        if (isRcc) {
            preShield = repairRccBrokenIncorporatorPipeHeaders(preShield);
        }
        const { protectedText, restore } = shieldGfmTables(preShield);
        contentToDisplay = restore(
            protectedText
                // 1. Break before embedded bracketed markers like `[(b)` wedged mid-sentence
                .replace(/([a-zA-Z0-9.,;:!?])\s+(\[\s*\([a-zA-Z0-9]{1,3}\)\s*)/g, '$1\n\n$2')
                // 2. Break before unbracketed markers like `(a)` that are only separated by a single newline
                .replace(/([a-zA-Z0-9.,;:!?])\s*\n\s*(\([a-zA-Z0-9]{1,3}\)\s+)/g, '$1\n\n$2')
                // 3. Break before unbracketed markers like `(b)` wedged directly on the same line after a sentence ender
                .replace(/([.;:])\s+(\([a-zA-Z0-9]{1,3}\)\s+)/g, '$1\n\n$2')
                // 4. Break before digit-dot markers like `2.` wedged directly on the same line after a sentence ender
                .replace(/([.;:])\s+(\d{1,3}\.\s+)/g, '$1\n\n$2')
                // 5. Break before word-based ordinals like `First.` wedged on the same line or separated by single newline
                .replace(
                    /([a-zA-Z0-9.,;:!?])\s*\n?\s*((?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\.\s+)/gi,
                    '$1\n\n$2',
                ),
        );
    }

    // --- SMART HEADER EXTRACTION ---
    // Detect if content starts with an embedded header (e.g., "**Article 266-A...")
    // If so, extract it to render with proper H3 styling, and remove from body to avoid duplication.
    let customHeaderNode = null;
    const hasEmbeddedHeader = contentToDisplay.trim().startsWith('**Article') || contentToDisplay.trim().startsWith('**Section');

    if (hasEmbeddedHeader) {
        // Split first paragraph (Header line) from rest
        const parts = contentToDisplay.split(/\n\n+/);
        const headerBlock = parts[0];

        // Regex to separate Bold Title from Intro Text
        // Matches: "**Article 266-A. Title.** - Intro text..."
        const match = headerBlock.match(/^(\*\*.*?\*\*)(.*)$/s);

        if (match) {
            const boldPart = match[1].replace(/\*\*/g, ''); // Strip markdown
            let introPart = match[2].trim();

            // Clean run-in separator ("- ") since we are breaking to a new line
            if (introPart.startsWith('-')) {
                introPart = introPart.substring(1).trim();
            }

            const embeddedKey = normArticleKey(boldPart);
            const rowKey = normArticleKey(isRcc ? `${rccSectionLabel} ${articleNumKey}` : `Article ${articleNumKey}`);
            const isConstArticle = codeId === 'const' || (article?.code_id && article.code_id.toLowerCase() === 'const');
            const redundantEmbedded =
                embeddedKey &&
                rowKey &&
                embeddedKey === rowKey &&
                String(article.article_num) !== '0' &&
                !String(article.article_num || '').includes('Header') &&
                !String(article.article_num || '').includes('Subheader') &&
                !isConstArticle;

            if (redundantEmbedded) {
                customHeaderNode = null;
                const restOfBody = parts.slice(1).join('\n\n');
                contentToDisplay = introPart ? `${introPart}\n\n${restOfBody}` : restOfBody;
            } else {
                customHeaderNode = (
                    <h3 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 font-sans !my-0 inline align-baseline">
                        {toTitleCase(boldPart, skipKeywords)}
                    </h3>
                );

                const restOfBody = parts.slice(1).join('\n\n');
                contentToDisplay = introPart ? `${introPart}\n\n${restOfBody}` : restOfBody;
            }
        } else {
            // Fallback: Just render the whole first block as H3
            customHeaderNode = (
                <h3 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 font-sans !my-0 inline align-baseline">
                    {toTitleCase(headerBlock.replace(/\*\*/g, ''), skipKeywords)}
                </h3>
            );
            contentToDisplay = parts.slice(1).join('\n\n');
        }
    }

    // Run-in "Article 266-A...." (no **) duplicates the H3; only strip for suffixed articles.
    // Plain "266"/"267" often use one line "Article 266. Title. - The crime..." — stripping would delete the body.
    if (
        isRpcLike &&
        articleNumKey &&
        /^[\d]+-[A-Za-z]+$/.test(articleNumKey) &&
        String(article.article_num) !== '0' &&
        !String(article.article_num || '').includes('Header')
    ) {
        const esc = articleNumKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const runInLine = new RegExp(`^"?\\s*Article\\s+${esc}\\.[^\\n]*(?:\\n|$)`, 'i');
        for (let i = 0; i < 3 && runInLine.test(contentToDisplay.trimStart()); i++) {
            contentToDisplay = contentToDisplay.replace(runInLine, '').trimStart();
        }
    }

    const {
        id,
        key_id,
        article_num,
        article_number,
        article_suffix,
        article_title,
        content_md,
        elements,
        amendments,
        structural_map,
        footnotes
    } = article;

    const currentArtNum = article_num || article_number;
    const stableId = id || currentArtNum;
    const lookup_id = key_id || String(currentArtNum);

    const parsedElements = typeof elements === 'string' ? JSON.parse(elements) : elements;
    let parsedAmendments = typeof amendments === 'string' ? JSON.parse(amendments) : amendments;
    const parsedStructuralMap = typeof structural_map === 'string' ? JSON.parse(structural_map) : structural_map;
    const parsedFootnotes = typeof footnotes === 'string' ? JSON.parse(footnotes) : footnotes;

    // --- PRE-PROCESS MARKDOWN FOOTNOTES ---
    // The ingested content has raw text like "... promulgation. [1]\n".
    // We want to turn this into a standard Markdown link so `ReactMarkdown` can parse it.
    // We will convert `[1]` -> `[1](#footnote-1)`
    contentToDisplay = contentToDisplay.replace(/\[(\d+)\]/g, '[$1](#footnote-$1)');

    let rccInlineLeadTitle = null;
    if (
        isRcc &&
        !customHeaderNode &&
        currentArtNum != null &&
        String(currentArtNum) !== '0' &&
        !String(currentArtNum).includes('Header') &&
        !String(currentArtNum).includes('Subheader')
    ) {
        const ex = extractRccLeadingShortTitle(contentToDisplay);
        if (ex.lead) {
            rccInlineLeadTitle = ex.lead;
            contentToDisplay = ex.body;
        }
        contentToDisplay = repairRccListMidItemLineBreaks(contentToDisplay);
    }
    const rccSectionNumDisplay = isRcc
        ? rccSectionNumberDisplayWithPeriod(currentArtNum)
        : String(currentArtNum ?? '').trim();

    // Unify Legacy Civil Code/Statutes (stored in separate relational db and served as amendment_links)
    // into the same structure used by the modern Const/RPC embedded JSON payload.
    if (article.amendment_links && article.amendment_links.length > 0) {
        if (!parsedAmendments) parsedAmendments = [];
        const legacyMapped = article.amendment_links.map(am => ({
            id: am.amendment_law,
            date: am.valid_from,
            description: am.description
        }));
        // Avoid duplicate rendering if the item was already migrated
        legacyMapped.forEach(leg => {
            if (!parsedAmendments.some(ex => ex.id === leg.id)) {
                parsedAmendments.push(leg);
            }
        });
    }

    const isAmended = parsedAmendments && parsedAmendments.length > 0;

    // Rainbow Band Logic
    const rainbowColors = [
        'bg-red-600',
        'bg-orange-500',
        'bg-yellow-400',
        'bg-green-500',
        'bg-blue-500',
        'bg-indigo-500',
        'bg-violet-500'
    ];

    const addedArticleColor = 'bg-teal-500';

    const getBandColor = (sourceId) => {
        if (sourceId === -1) return addedArticleColor;
        return rainbowColors[sourceId % rainbowColors.length];
    };

    // Keep track of which footnote popover is open
    const [activeFootnoteMarker, setActiveFootnoteMarker] = useState(null);

    // Bypassing empty articles AFTER all hooks have been initialized
    if (!hasContent) return null;

    const generalLinkCount = (article.paragraph_links && article.paragraph_links['-1']) || 0;
    const isConstCode = codeId === 'const' || (article?.code_id && article.code_id.toLowerCase() === 'const');
    const hasDynamicTitle = (!(!article_num || String(article_num).includes('Header') || String(article_num).includes('Subheader'))) && !isConstCode;
    const hasHeaderContent = isAmended || customHeaderNode || (String(article_num) === '0') || hasDynamicTitle || generalLinkCount > 0;

    // Early segment detection for spacing
    const isRocArticle = (codeId && ['roc', 'rpc'].includes(String(codeId).toLowerCase())) || (article && article.code_id && ['roc', 'rpc'].includes(String(article.code_id).toLowerCase()));
    const firstSegment = isRocArticle ? contentToDisplay.split('\n')[0] : contentToDisplay.split(/\n\n+/)[0];
    const cleanFirstSeg = typeof firstSegment === 'string' ? firstSegment.trim() : '';
    const isFirstSegSubHeader = isConstCode && 
                               cleanFirstSeg.length > 2 && 
                               cleanFirstSeg.length < 65 && 
                               !cleanFirstSeg.endsWith('.') &&
                               !/^(SECTION|ARTICLE|PREAMBLE)/i.test(cleanFirstSeg) &&
                               !cleanFirstSeg.includes('(');

    return (
        <div id={`article-${stableId}`} className="group relative mt-4 min-w-0 max-w-full">

            {/* Main Content Area with Floated Badge */}
            {hasHeaderContent && (
                <div className="max-w-full min-w-0 text-[16px] font-sans leading-relaxed text-gray-800 dark:text-gray-200">

                {/* Floating Badge */}
                <div className="flex flex-col mb-1 relative">
                    <div className={`flex items-center gap-2 ${centerLayout ? 'justify-center' : ''}`}>
                        {isAmended && (
                            <button
                                type="button"
                                onClick={() => setIsHistoryOpen(prev => !prev)}
                                className="text-orange-500 hover:text-orange-600 dark:text-orange-400 dark:hover:text-orange-300 transition-colors cursor-pointer"
                                title="View Amendment History"
                            >
                                <Info size={20} />
                            </button>
                        )}




                        {customHeaderNode ? customHeaderNode : (
                            String(article_num) === '0' ? (
                                <h3 className="text-[16px] font-bold text-gray-900 dark:text-gray-100 font-sans !my-0 inline align-baseline">
                                    {isRcc ? 'Preliminary Section' : 'Preliminary Article'}
                                </h3>
                            ) : (
                                <h3
                                    className={
                                        rccInlineLeadTitle
                                            ? `flex min-w-0 flex-1 flex-row flex-nowrap items-baseline gap-x-1.5 overflow-x-auto text-[16px] font-bold font-sans !my-0 text-gray-900 dark:text-gray-100 ${centerLayout ? 'justify-center text-center' : 'text-left'}`
                                            : isRcc && article_title
                                              ? `flex min-w-0 flex-1 flex-row flex-nowrap items-baseline gap-x-1.5 overflow-x-auto text-[16px] font-bold font-sans !my-0 text-gray-900 dark:text-gray-100 ${centerLayout ? 'justify-center text-center' : 'text-left'}`
                                              : `text-[16px] font-bold text-gray-900 dark:text-gray-100 font-sans !my-0 inline align-baseline ${centerLayout ? 'text-center w-full' : 'text-left'}`
                                    }
                                >
                                    {/* Smart prefix: RCC uses "Section"; omit if article_num already includes a structural label */}
                                    {(!article_num || String(article_num).includes('Header') || String(article_num).includes('Subheader')) ? null :
                                        (codeId === 'const' || (article.code_id && article.code_id.toLowerCase() === 'const')) ? null :
                                        /^(article|preamble|section|rule)/i.test(String(article_num)) &&
                                        !(isRcc && /^section\s+/i.test(String(article_num)))
                                            ? (() => {
                                                let displayNum = String(article_num);
                                                if (codeId === 'roc' || (article.code_id && article.code_id.toLowerCase() === 'roc')) {
                                                    displayNum = displayNum.replace(/^Rule\s+[^,]+,\s*/i, '');
                                                }
                                                if (!article_title) return toTitleCase(displayNum, skipKeywords);
                                                // Deduplicate: If Title equals Num (e.g. PREAMBLE == PREAMBLE), hide Title
                                                if (displayNum.trim().toUpperCase() === String(article_title).trim().toUpperCase()) {
                                                    return toTitleCase(displayNum, skipKeywords);
                                                }
                                                return toTitleCase(`${displayNum}. ${article_title}`, skipKeywords);
                                            })()
                                            : (() => {
                                                if (rccInlineLeadTitle) {
                                                    const lead = cleanRccSectionHeaderFragment(rccInlineLeadTitle);
                                                    const label = `${rccSectionLabel}\u00a0${rccSectionNumDisplay}`;
                                                    return (
                                                        <>
                                                            <span className="shrink-0 whitespace-nowrap font-bold">{label}</span>
                                                            <span className="min-w-0 flex-1 font-bold leading-snug">
                                                                {toTitleCase(lead, skipKeywords)}
                                                            </span>
                                                        </>
                                                    );
                                                }
                                                if (isRcc) {
                                                    const prefix = `Section ${rccSectionNumberFromArticleNum(currentArtNum)}`;
                                                    const prefixDotted = `${prefix}.`;
                                                    const titUp = String(article_title || '').trim().toUpperCase();
                                                    if (
                                                        article_title &&
                                                        (titUp.startsWith(prefixDotted.toUpperCase()) ||
                                                            titUp.startsWith(`${prefix.toUpperCase()} `) ||
                                                            titUp.startsWith(`${prefix.toUpperCase()}.`))
                                                    ) {
                                                        return toTitleCase(
                                                            cleanRccSectionHeaderFragment(article_title),
                                                            skipKeywords,
                                                        );
                                                    }
                                                    const tail = cleanRccSectionHeaderFragment(article_title || '');
                                                    if (tail) {
                                                        return (
                                                            <>
                                                                <span className="shrink-0 whitespace-nowrap font-bold">
                                                                    {`${rccSectionLabel}\u00a0${rccSectionNumDisplay}`}
                                                                </span>
                                                                <span className="min-w-0 flex-1 font-bold leading-snug">
                                                                    {toTitleCase(tail, skipKeywords)}
                                                                </span>
                                                            </>
                                                        );
                                                    }
                                                    return (
                                                        <span className="font-bold">
                                                            {`${rccSectionLabel}\u00a0${rccSectionNumDisplay}`}
                                                        </span>
                                                    );
                                                }
                                                const prefix = `Article ${article_num}`;
                                                if (article_title && String(article_title).trim().toUpperCase().startsWith(prefix.toUpperCase())) {
                                                    return toTitleCase(article_title, skipKeywords);
                                                }
                                                return toTitleCase(`${prefix}. ${article_title || ''}`, skipKeywords);
                                            })()
                                    }
                                    {/* General concept gavel icon */}
                                    {(() => {
                                        const generalLinkCount = (article.paragraph_links && article.paragraph_links['-1']) || 0;
                                        // SUPPRESS for Constitution: These are combined into Paragraph 0 inline gavel
                                        if (generalLinkCount > 0 && !isConstCode) {
                                            return (
                                                <span
                                                    className="inline-flex items-center gap-1 ml-2 cursor-pointer text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors"
                                                    // Header click - General concept (-1)
                                                    onClick={() => {
                                                        if (typeof onToggleJurisprudence === 'function') {
                                                            onToggleJurisprudence(lookup_id, -1);
                                                        }
                                                    }}
                                                    title={`${generalLinkCount} general concept cases`}
                                                >
                                                    <Gavel size={16} className="inline" />
                                                    <span className="text-sm font-semibold">{generalLinkCount}</span>
                                                </span>
                                            );
                                        }
                                        return null;
                                    })()}

                                    {/* LexPlay Button moved to end of article */}
                                </h3>
                            )
                        )}
                    </div>

                    {/* Amendment History (Floating Popover) */}
                    {isAmended && isHistoryOpen && (
                        <>
                            {/* Mobile backdrop to close on tap outside */}
                            <div className="fixed inset-0 z-40 sm:hidden" onClick={() => setIsHistoryOpen(false)} />
                            <div className="fixed inset-x-4 top-1/4 sm:inset-auto sm:absolute sm:top-8 sm:left-0 z-50 sm:w-[500px] max-w-full bg-white dark:bg-gray-800 p-4 rounded-xl shadow-2xl border border-orange-200 dark:border-orange-900/50 animate-in fade-in zoom-in-95 duration-200">
                                <div className="flex justify-between items-start mb-3">
                                <h4 className="text-xs font-bold text-orange-600 dark:text-orange-400 uppercase flex items-center gap-2">
                                    <Info size={14} /> Amendment History
                                </h4>
                                <button
                                    onClick={() => setIsHistoryOpen(false)}
                                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
                                >
                                    <X size={16} />
                                </button>
                            </div>

                            <div className="max-h-[300px] overflow-y-auto space-y-3 pr-1 custom-scrollbar">
                                {[...parsedAmendments].reverse().map((am, idx) => (
                                    <div key={idx} className="text-xs text-gray-700 dark:text-gray-300">
                                        <div className="font-semibold text-orange-700 dark:text-orange-300 mb-1 flex justify-between">
                                            <span>{am.id || am.law || 'Unknown Law'}</span>
                                            <span className="text-gray-500 dark:text-gray-500 font-normal">{am.date || 'No Date'}</span>
                                        </div>
                                        <div className="bg-orange-50 dark:bg-orange-900/10 p-2.5 rounded border border-orange-100 dark:border-orange-900/20 leading-relaxed">
                                            {am.description || am.summary || 'No Description'}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        </>
                    )}
                </div>
                </div>
            )}

            {/* Content Area - Split into Paragraphs/Segments */}
            <div className={`${isFirstSegSubHeader ? 'mt-0' : 'mt-3'}`}>
                {(() => {
                    const isRoc = (codeId && codeId.toLowerCase() === 'roc') || (article?.code_id && article.code_id.toLowerCase() === 'roc');
                    const isRpc = (codeId && codeId.toLowerCase() === 'rpc') || (article?.code_id && article.code_id.toLowerCase() === 'rpc');
                    const isRocOrRpc = isRoc || isRpc;
                    const isConst = (codeId && codeId.toLowerCase() === 'const') || (article?.code_id && article.code_id.toLowerCase() === 'const');
                    
                    let segments = [];
                    if (isRocOrRpc) {
                        const rawLines = collapseBlankLinesInPipeTables(contentToDisplay).split('\n');
                        let currentSegment = '';
                        const isTableLine = (line) => line.trim().startsWith('|');
                        for (let li = 0; li < rawLines.length; li++) {
                            const rLine = rawLines[li];
                            if (rLine.trim() === '') {
                                if (currentSegment.trim().startsWith('|')) {
                                    let j = li + 1;
                                    while (j < rawLines.length && rawLines[j].trim() === '') j++;
                                    if (j < rawLines.length && isTableLine(rawLines[j])) {
                                        continue;
                                    }
                                }
                                if (currentSegment) segments.push(currentSegment);
                                segments.push('');
                                currentSegment = '';
                                continue;
                            }
                            const stripped = rLine.replace(/^[\u200C\u00A0\s]*/, '');
                            const isMarkerLine = /^(\(?[a-z0-9ivx]{1,3}[\.\)]|(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\.)/i.test(stripped);
                            const isHeaderLine = rLine.trim().startsWith('#');
                            const rowIsTable = isTableLine(rLine);

                            if (isMarkerLine || isHeaderLine) {
                                // Special handling for ROC: Don't break if it's just a (n) marker alone,
                                // as it likely belongs to the previous paragraph as a suffix.
                                if (stripped.toLowerCase() === '(n)' && currentSegment) {
                                    currentSegment += " " + stripped;
                                } else {
                                    if (currentSegment) segments.push(currentSegment);
                                    currentSegment = rLine;
                                }
                            } else if (rowIsTable) {
                                // For tables, preserve newlines and don't merge into text paragraphs
                                if (currentSegment && !currentSegment.trim().startsWith('|')) {
                                    segments.push(currentSegment);
                                    currentSegment = rLine;
                                } else {
                                    currentSegment = (currentSegment ? currentSegment + "\n" : "") + rLine;
                                }
                            } else {
                                if (currentSegment) {
                                    // If previous segment was a table, start new or append newline?
                                    // Usually if it's not a marker and not a table, it's a follow-on paragraph text
                                    if (currentSegment.trim().startsWith('|')) {
                                        segments.push(currentSegment);
                                        currentSegment = rLine;
                                    } else {
                                        currentSegment += " " + stripped;
                                    }
                                } else {
                                    currentSegment = rLine;
                                }
                            }
                        }
                        if (currentSegment) segments.push(currentSegment);
                    } else {
                        // For Constitution, if a new line starts with an enumeration like `(1)` or `(a)`,
                        // we enforce a double newline so it is parsed as an independent paragraph segment.
                        let processedContent = contentToDisplay;
                        if (isConst) {
                            // CONSTITUTION SPLITTING RULES:
                            // The general pre-processor is SKIPPED for Constitution (see above).
                            // Here we handle all splitting ourselves:
                            // - (1) must stay INLINE with "SECTION N." ΓÇö DO NOT split it
                            // - (2), (3), (a), (b), etc. must each be their own paragraph

                            // Step 1: Un-escape any remaining \(X\) ΓåÆ (X) (global un-escape already ran but just in case)
                            processedContent = processedContent.replace(/\\\(([^)]*)\\\)/g, '($1)');

                            // Step 2: Split on (2)+ or (b)+ that appear after a newline
                            processedContent = processedContent.replace(/\n\s*(\([2-9a-z]\))/g, '\n\n$1');

                            // Step 3: Split on (2)+ or (b)+ that are still inline after a sentence end
                            processedContent = processedContent.replace(/([.!?])\s+(\([2-9]\)|\([b-z]\))(?=\s)/g, '$1\n\n$2');
                        }

                        segments = processedContent.split(/\n\n+/);
                        
                        // Strip remaining inner single newlines to ensure clean paragraph wrapping
                        if (isConst) {
                            segments = segments.map(s => s.replace(/\n/g, ' ').replace(/\r/g, ''));
                        }
                    }

                    // --- Post-Processing: ROC specific clean-up ---
                    if (isRocOrRpc) {
                        const merged = [];
                        for (let i = 0; i < segments.length; i++) {
                            const seg = segments[i];
                            const clean = typeof seg === 'string' ? seg.trim().toLowerCase() : '';
                            
                            // 1. Filter out empty spacing segments for ROC to ensure tight packing
                            if (clean === '') continue;

                            // 2. Merge standalone (n) suffixes into previous paragraph
                            if (clean === '(n)' && merged.length > 0) {
                                let targetIdx = merged.length - 1;
                                // Skip trailing empty spacing segments (should be none now due to filter above)
                                while (targetIdx >= 0 && typeof merged[targetIdx] === 'string' && merged[targetIdx].trim() === '') {
                                    targetIdx--;
                                }
                                if (targetIdx >= 0) {
                                    merged[targetIdx] = (merged[targetIdx] + " " + seg.trim()).trim();
                                    continue;
                                }
                            }
                            merged.push(seg);
                        }
                        segments = merged;
                    }

                    // Determine if this is an "Added Article" (e.g. "266-A")
                    // Check article_suffix OR if article_num string has digits followed by a letter (e.g. "266-A")
                    const isAddedArticle = article_suffix || (
                        typeof article_num === 'string' &&
                        /\d+[-]?([A-Za-z]+)$/.test(article_num) &&
                        !article_num.toUpperCase().includes('SECTION')
                    );

                    const baseId = isAddedArticle ? -1 : 0;
                    const globalSources = [baseId];

                    let lastSubstantiveIdx = segments.length - 1;
                    if (lastSubstantiveIdx >= 0) {
                        const lastCleanStr = typeof segments[lastSubstantiveIdx] === 'string' ? segments[lastSubstantiveIdx].trim().toUpperCase() : '';
                        if (lastCleanStr.startsWith('RATIFIED')) {
                            lastSubstantiveIdx = lastSubstantiveIdx - 1;
                        }
                    }

                    // Track last indentation level so continuation paragraphs (no marker) inherit it
                    let lastEnumLevel = 0;
                    // Track numeric context separately so ordinals don't pollute the "am I nested?" check
                    let lastNumericEnumLevel = 0;

                    return segments.map((segment, segIdx) => {
                        if (isRocOrRpc && typeof segment === 'string' && segment.trim() === '') {
                            // Explicit vertical spacing for intentional source blank lines
                            return <div key={`${lookup_id}-${segIdx}`} className="h-4" />;
                        }

                        let activeSources = [...globalSources];
                        const hasMap = parsedStructuralMap && Array.isArray(parsedStructuralMap) && parsedStructuralMap.length > 0;

                        if (hasMap) {
                            if (parsedStructuralMap[segIdx]) {
                                activeSources = parsedStructuralMap[segIdx];
                            }
                        } else if (isAmended) {
                            // If Added Article (Teal Base), skip the first amendment (Creation) in the visual stack
                            // so the *next* amendment starts at Orange (Source 1).
                            const visualAmendments = isAddedArticle ? parsedAmendments.slice(1) : parsedAmendments;
                            activeSources = [baseId, ...visualAmendments.map((_, i) => i + 1)];
                        }

                        if (activeSources.some(s => s > 0)) {
                            activeSources = activeSources.filter(s => s !== 0);
                        }

                        activeSources = [...new Set(activeSources)];

                        let hasBands = activeSources.length > 0;

                        // Whole-segment GFM pipe tables: skip line-anchored transforms — they break `| --- |`
                        // separator rows (`^(\d+)\.` matches `| - |` middle cells in some widths) and confuse remark-gfm.
                        const segmentIsGfmPipeTableBlock =
                            typeof segment === 'string' &&
                            (() => {
                                const nonempty = segment.split('\n').filter((ln) => ln.trim());
                                if (nonempty.length < 2) return false;
                                return nonempty.every((ln) => {
                                    const t = ln.trim();
                                    return t.startsWith('|') && (t.match(/\|/g) || []).length >= 2;
                                });
                            })();

                        // Detect Sub-Headers (e.g. "Principles", "A. Common Provisions")
                        let renderSegment = segment;
                        if (typeof segment === 'string' && !segmentIsGfmPipeTableBlock) {
                            // Strip redundant "CHAPTER II - CHAPTER TWO:" or "TITLE I - TITLE ONE:"
                            renderSegment = segment.replace(/^(TITLE|CHAPTER|BOOK)\s+[IVXLCDM]+\s*-\s+(TITLE|CHAPTER|BOOK)\s+[A-Z]+:\s*/i, '').trim();
                            // Inhibit ReactMarkdown from converting "1." or "1)" into list node blocks (which strips the number)
                            renderSegment = renderSegment.replace(/^(\d+)\.\s/gm, '$1.\u00A0 ');
                            // Escape parenthesis-style enumerations: 1) a) b) etc ΓÇö ReactMarkdown eats these as list items
                            renderSegment = renderSegment.replace(/^(\d+|[a-zA-Z])\)\s/gm, '$1)\u00A0');

                            // Title Case structural prefixes if they are ALL CAPS (e.g. "SECTION 1" -> "Section 1")
                            renderSegment = renderSegment.replace(/^(SECTION)\s+(\d+|[IVXLCDM]+)/i, (m) => toTitleCase(m, skipKeywords));
                        }
                        const cleanSeg = typeof renderSegment === 'string' ? renderSegment.trim() : '';
                        const isSubHeader = String(article_num) !== '0' &&
                                           cleanSeg.length > 2 && 
                                           cleanSeg.length < 120 && 
                                           !cleanSeg.endsWith('.') &&
                                           !cleanSeg.endsWith(':') &&
                                           !cleanSeg.endsWith(';') &&
                                           !cleanSeg.endsWith(',') &&
                                           !cleanSeg.endsWith('-') && // dash = continuation marker, not a heading
                                           !/^(SECTION|ARTICLE|PREAMBLE)/i.test(cleanSeg) &&
                                           !/^(\d+|[a-zA-Z])[\.\)]/i.test(cleanSeg) && // Don't treat markers 1. or a) as headers
                                           !cleanSeg.includes('(') &&
                                           !isRpc &&
                                           (isConst || isRoc || cleanSeg === cleanSeg.toUpperCase());

                        // Disable color bands for markdown headers and subheaders
                        if (isSubHeader || (typeof segment === 'string' && segment.trim().startsWith('#'))) {
                            hasBands = false;
                        }
                        // Detect Indentation Level for Cascading Enumeration
                        const indentationLevel = (() => {
                            if (!cleanSeg || isSubHeader) return 0;
                            
                            // High priority: calculate from leading whitespaces (4 spaces = 1 level, OR 3 for ROC)
                            // Match regular spaces, non-breaking spaces (\u00A0), and zero-width (\u200C)
                            const leadingMatch = segment.match(/^[\u200C\u00A0\s]*/);
                            const totalSpaces = leadingMatch ? leadingMatch[0].length : 0;
                            
                            const step = isRoc ? 3 : 4;
                            if (totalSpaces >= step * 3) return 3;
                            if (totalSpaces >= step * 2) return 2;
                            if (totalSpaces >= step) return 1;

                            // Fallback to regex (for documents without explicit space indentation)
                            const textForIndent = cleanSeg.replace(/^(?:\[\d+\]\([^)]+\)\s*)*\[?\s*/, '');

                            // RPC/ROC hierarchy: outer Arabic 1. / 1) first, then lettered (a) / a) nested under it,
                            // then parenthetical (1), then roman (i). Higher level number = more ml-* (was inverted before).
                            if (/^\d+[\.\)]([\s\u00A0]|$)/.test(textForIndent)) return 1;
                            if (/^(\([a-z]\)|[a-z][\.\)])([\s\u00A0]|$)/i.test(textForIndent)) return 2;
                            if (/^\(\d+\)([\s\u00A0]|$)/.test(textForIndent)) return 3;
                            if (/^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\.([\s\u00A0]|$)/i.test(textForIndent)) {
                                return 3;
                            }
                            if (/^\([ivxl]+\)([\s\u00A0]|$)/i.test(textForIndent)) return 4;
                            return 0;
                        })();

                        // RCC: continuation lines without a marker used to inherit list indent forever, so
                        // follow-on paragraphs ("Except as provided…") were mis-indented. Only inherit when the
                        // segment does not look like a new full prose block (long, sentence case, not (a) line).
                        const looksLikeLetteredOrSubnumberedLine =
                            /^\(\s*[a-z]{1,2}\)\s/i.test(cleanSeg) || /^[a-z]\)\s/i.test(cleanSeg);
                        const rccProseOutdent =
                            isRcc &&
                            cleanSeg.length >= 48 &&
                            /^[A-Z]/.test(cleanSeg) &&
                            !looksLikeLetteredOrSubnumberedLine;

                        const shouldInheritEnumIndent =
                            indentationLevel === 0 &&
                            lastEnumLevel > 0 &&
                            cleanSeg &&
                            !isSubHeader &&
                            !cleanSeg.startsWith('#') &&
                            !rccProseOutdent;

                        const effectiveLevel = shouldInheritEnumIndent ? lastEnumLevel : indentationLevel;

                        // Update tracker ΓÇö reset on section headers, update on new markers
                        if (cleanSeg.startsWith('#')) {
                            lastEnumLevel = 0;
                            lastNumericEnumLevel = 0;
                        } else if (indentationLevel > 0) {
                            lastEnumLevel = indentationLevel;
                            // Only update numeric context if it's a decimal/letter marker, NOT an ordinal
                            if (!/^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\.[\s\u00A0]/i.test(cleanSeg)) {
                                lastNumericEnumLevel = indentationLevel;
                            }
                        } else if (rccProseOutdent) {
                            lastEnumLevel = 0;
                            lastNumericEnumLevel = 0;
                        }

                        // Simple cascading indentation via Tailwind padding classes
                        let indentClass = "";
                        if (!isConst) {
                            indentClass = isRocOrRpc ? (
                                effectiveLevel === 1 ? "ml-2 sm:ml-3" :
                                effectiveLevel === 2 ? "ml-3 sm:ml-6" :
                                effectiveLevel === 3 ? "ml-4 sm:ml-9" :
                                effectiveLevel === 4 ? "ml-5 sm:ml-12" : ""
                            ) : (
                                effectiveLevel === 1 ? "ml-4" :
                                effectiveLevel === 2 ? "ml-8" :
                                effectiveLevel === 3 ? "ml-12" :
                                effectiveLevel === 4 ? "ml-16" : ""
                            );
                        }

                        // Bands reserve left rail; indentation (cascade) still applies to body text
                        const paddingClass = hasBands ? "pl-6 sm:pl-7" : "";

                        // Determine link count for this paragraph
                        const paragraphIndex = baseId + segIdx;
                        let linkCount = (article.paragraph_links && article.paragraph_links[String(paragraphIndex)]) || 0;

                        // FOR CONSTITUTION: Combine general concept (-1) links into the first paragraph (0) 
                        // as requested by user to avoid redundant top-left icons.
                        if (isConst && segIdx === 0 && article.paragraph_links && article.paragraph_links['-1']) {
                            linkCount += article.paragraph_links['-1'];
                        }

                        // Compact margins for enumerated items (Level 1+) vs substantive paragraphs
                        let marginClass = effectiveLevel > 0 ? "mb-1.5" : "mb-5 text-justify";
                        if (isConst) {
                            // Constitution: proper 1 space (mb-4) between purely substantive structural blocks
                            marginClass = "mb-4 text-justify";
                        }

                        return (
                            <div key={segIdx} className={`relative ${paddingClass} group/segment ${marginClass}`}>
                                {hasBands && (
                                    <div className="absolute left-0 top-0 bottom-0 flex flex-row gap-[2px]">
                                        {activeSources.map((sourceId, idx) => {
                                            const colorClass = getBandColor(sourceId);
                                            return (
                                                <div key={idx} className={`h-full w-1 ${colorClass}`} title={`Source ${sourceId}`} />
                                            );
                                        })}
                                    </div>
                                )}
                                <div
                                    className={`prose dark:prose-invert relative min-w-0 max-w-full break-words font-sans text-[16px] leading-relaxed text-gray-800 dark:text-gray-200 [overflow-wrap:anywhere] ${indentClass} ${isSubHeader ? 'mt-0 mb-1 text-center font-bold tracking-wide text-gray-900 dark:text-gray-200 text-[16px]' : ''}`}
                                >
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            pre: ({ node, ...props }) => <div className="not-prose pl-4" {...props} />,
                                            table: ({ node, children, ...props }) => (
                                                <div className="not-prose my-4 max-w-full overflow-x-auto overscroll-x-contain rounded-lg border border-gray-200/90 bg-white/70 shadow-sm [-webkit-overflow-scrolling:touch] dark:border-gray-600/80 dark:bg-slate-900/55">
                                                    <table
                                                        className="w-full max-w-full border-collapse text-left text-sm leading-snug text-gray-800 dark:text-gray-200"
                                                        {...props}
                                                    >
                                                        {children}
                                                    </table>
                                                </div>
                                            ),
                                            thead: ({ node, ...props }) => <thead className="bg-gray-100/95 dark:bg-slate-800/90" {...props} />,
                                            tbody: ({ node, ...props }) => <tbody {...props} />,
                                            tr: ({ node, ...props }) => (
                                                <tr className="border-b border-gray-200 last:border-b-0 dark:border-gray-700" {...props} />
                                            ),
                                            th: ({ node, ...props }) => (
                                                <th
                                                    className="break-normal border border-gray-200 px-3 py-2 text-left align-top text-xs font-semibold uppercase tracking-wide text-gray-900 [overflow-wrap:normal] [word-break:normal] dark:border-gray-600 dark:text-gray-100"
                                                    {...props}
                                                />
                                            ),
                                            td: ({ node, ...props }) => (
                                                <td
                                                    className="break-words border border-gray-200 px-3 py-2 align-top text-[15px] dark:border-gray-600"
                                                    {...props}
                                                />
                                            ),
                                            code: ({ node, inline, className, children, ...props }) => {
                                                return (
                                                    <span className={`${inline ? 'font-mono bg-gray-100 dark:bg-gray-800 rounded px-1' : 'block whitespace-pre-wrap font-sans'}`} {...props}>
                                                        {children}
                                                    </span>
                                                );
                                            },
                                            a: ({ node, href, children, ...props }) => {
                                                if (href && href.startsWith('#footnote-')) {
                                                    const marker = href.replace('#footnote-', '');
                                                    let footnoteText = "Footnote text not found.";
                                                    if (parsedFootnotes && Array.isArray(parsedFootnotes)) {
                                                        const fn = parsedFootnotes.find(f => f.marker === marker);
                                                        if (fn) footnoteText = fn.text;
                                                    }

                                                    const isOpen = activeFootnoteMarker === marker;

                                                    return (
                                                        <span className="relative inline-block ml-1 align-super -mt-1 group/footnote z-20">
                                                            <button
                                                                onClick={(e) => {
                                                                    e.preventDefault();
                                                                    e.stopPropagation();
                                                                    setActiveFootnoteMarker(isOpen ? null : marker);
                                                                }}
                                                                className="inline-flex items-center justify-center min-w-[1.2rem] h-[1.2rem] px-1 text-[10px] font-bold text-white bg-indigo-500 hover:bg-indigo-600 rounded shadow-sm hover:shadow-md transition-all cursor-pointer"
                                                                title={`Footnote ${marker}`}
                                                            >
                                                                {marker}
                                                            </button>

                                                            {isOpen && (
                                                                <>
                                                                    {/* Mobile backdrop to close on tap outside */}
                                                                    <div className="fixed inset-0 z-40 sm:hidden" onClick={(e) => { e.preventDefault(); e.stopPropagation(); setActiveFootnoteMarker(null); }} />
                                                                    <div className="fixed inset-x-4 top-1/3 sm:inset-auto sm:absolute sm:bottom-full sm:left-1/2 sm:-translate-x-1/2 sm:mb-2 max-w-full sm:w-80 bg-white dark:bg-gray-800 p-4 rounded-xl shadow-2xl border border-indigo-200 dark:border-indigo-900/50 animate-in fade-in zoom-in-95 duration-200 z-50 text-left cursor-default" onClick={e => e.stopPropagation()}>
                                                                        <div className="flex justify-between items-center mb-2">
                                                                            <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 capitalize flex items-center gap-1">
                                                                                <Info size={14} className="inline" /> Footnote {marker}
                                                                            </span>
                                                                            <button
                                                                                onClick={(e) => {
                                                                                    e.preventDefault();
                                                                                    e.stopPropagation();
                                                                                    setActiveFootnoteMarker(null);
                                                                                }}
                                                                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                                                                            >
                                                                                <X size={14} />
                                                                            </button>
                                                                        </div>
                                                                        <div className="text-sm font-sans font-normal text-gray-700 dark:text-gray-300 leading-relaxed max-h-48 overflow-y-auto custom-scrollbar">
                                                                            {footnoteText}
                                                                        </div>
                                                                    </div>
                                                                </>
                                                            )}
                                                        </span>
                                                    );
                                                }
                                                return <a href={href} className="text-blue-600 hover:underline" {...props}>{children}</a>;
                                            },
                                            h3: ({ node, children, ...props }) => (
                                                <h3 className={`font-bold text-gray-900 dark:text-white mt-6 mb-3 text-lg ${centerLayout ? 'text-center' : 'text-left'}`} {...props}>{children}</h3>
                                            ),
                                            p: ({ node, children, ...props }) => {
                                                const isLastSegment = segIdx === lastSubstantiveIdx;
                                                const segmentsArr = React.Children.toArray(children);
                                                const firstChild = segmentsArr[0];
                                                const textContent = typeof firstChild === 'string' ? firstChild : '';
                                                
                                                const isRocArticle = (codeId && ['roc', 'rpc'].includes(codeId.toLowerCase())) || (article?.code_id && ['roc', 'rpc'].includes(article.code_id.toLowerCase()));
                                                
                                                if (isRocArticle) {
                                                    // Detect leading whitespace (\u200C is protector, \u00A0 is indent space)
                                                    const leadingMatch = textContent.match(/^[\u200C\u00A0\s]*/);
                                                    const leadingSpaces = leadingMatch ? leadingMatch[0] : '';
                                                    const strippedFromLeading = textContent.substring(leadingSpaces.length);
                                                    
                                                     // Check for enumeration markers
                                                     // We EXCLUDE ordinals from the inner p-renderer's hanging indent entirely
                                                     // so they just rely on the outer PL-X classes and wrap normally.
                                                     const baseMarkerMatch = strippedFromLeading.trim().match(/^(\(?[a-z0-9ivx]{1,3}[\.\)])/i);
                                                     
                                                      const hasMarker = !!baseMarkerMatch;
                                                      const nestedOffset = 0; // Handled by outer classes now
                                                     
                                                     // Constants for alignment
                                                     const indentationPerSpace = 0.5; // rem
                                                     
                                                     let markerWidth = 0;
                                                     if (hasMarker) {
                                                         const mText = baseMarkerMatch ? `${baseMarkerMatch[1]} ` : '';
                                                         markerWidth = mText.length * 0.35; // Approx 0.35rem per char
                                                         if (markerWidth < 1.0) markerWidth = 1.0;
                                                         if (markerWidth > 3.5) markerWidth = 3.5; // clamp
                                                     }
                                                     
                                                     // Calculate cascading indentation based on the NUMBER of \u00A0 characters
                                                     const spaceCount = (leadingSpaces.match(/\u00A0/g) || []).length;
                                                     const cascadingOffset = spaceCount * indentationPerSpace;
                                                     
                                                     // Total padding = offset + markerWidth + nestedOffset
                                                     let finalPadding = hasMarker
                                                         ? cascadingOffset + markerWidth + nestedOffset
                                                         : cascadingOffset + nestedOffset;
                                                     // Mobile: deep NBSP-indented RPC blocks can exceed viewport; cap inset (rem)
                                                     finalPadding = Math.min(finalPadding, 6);
                                                    const finalIndent = hasMarker ? `-${Math.min(markerWidth, 2.5)}rem` : '0';
                                                    
                                                    // Clean up the first child (strip leading spaces)
                                                    const cleanSegments = [...segmentsArr];
                                                    cleanSegments[0] = strippedFromLeading;

                                                    return (
                                                        <p
                                                            {...props}
                                                            className={`!m-0 max-w-full whitespace-pre-wrap break-words [overflow-wrap:anywhere] ${isSubHeader ? "text-center font-bold text-gray-900 dark:text-gray-200 tracking-wide text-[16px]" : ""}`}
                                                            style={{
                                                                paddingLeft: isSubHeader ? '0' : `${finalPadding}rem`,
                                                                textIndent: isSubHeader ? '0' : finalIndent,
                                                                maxWidth: '100%',
                                                                overflowWrap: 'anywhere',
                                                                wordBreak: 'break-word',
                                                            }}
                                                        >
                                                             {cleanSegments}
                                                             {"\u00A0"}
                                                             {linkCount > 0 && (
                                                                <span
                                                                    className="inline-flex items-center ml-3 px-2 py-0.5 bg-purple-50 dark:bg-purple-900/40 rounded border border-purple-200 dark:border-purple-800/60 cursor-pointer hover:bg-purple-100 dark:hover:bg-purple-900/60 shadow-sm transition-colors align-middle"
                                                                    style={{ gap: '0.35rem' }}
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        if (onToggleJurisprudence) onToggleJurisprudence(lookup_id, paragraphIndex);
                                                                    }}
                                                                    title={`${linkCount} cited cases linked to this paragraph`}
                                                                >
                                                                    <div className="flex-shrink-0 flex items-center justify-center text-purple-600 dark:text-purple-400">
                                                                        <Gavel size={14} />
                                                                    </div>
                                                                    <div className="text-[11.5px] font-bold whitespace-nowrap leading-none flex items-center justify-center mt-[1px] text-purple-600 dark:text-purple-400" style={{ textIndent: '0' }}>
                                                                        {linkCount}
                                                                    </div>
                                                                </span>
                                                            )}

                                                             {isLastSegment && (article.id || article.key_id) && !isSubHeader && (
                                                                 <button
                                                                     type="button"
                                                                     onClick={handleAddToPlaylist}
                                                                     className="inline-flex items-center justify-center ml-2 cursor-pointer text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors bg-purple-50 dark:bg-purple-900/20 p-1 rounded-full border border-purple-200 dark:border-purple-800 shadow-sm hover:scale-105 align-baseline"
                                                                     title="Add to LexPlay Playlist"
                                                                 >
                                                                     <Headphones size={14} />
                                                                 </button>
                                                             )}
                                                        </p>
                                                    );
                                                }

                                                // Fallback for standard paragraphs
                                                return (
                                                    <p
                                                        {...props}
                                                        className={`!m-0 max-w-full whitespace-pre-wrap break-words [overflow-wrap:anywhere] ${isSubHeader ? 'text-center font-bold tracking-wide text-gray-900 dark:text-gray-200 text-[16px]' : 'text-justify'}`}
                                                        style={{ maxWidth: '100%', overflowWrap: 'anywhere', wordBreak: 'break-word' }}
                                                    >
                                                         {children}
                                                         {"\u00A0"}
                                                         {linkCount > 0 && (
                                                            <span
                                                                className="inline-flex items-center ml-3 px-2 py-0.5 bg-purple-50 dark:bg-purple-900/40 rounded border border-purple-200 dark:border-purple-800/60 cursor-pointer hover:bg-purple-100 dark:hover:bg-purple-900/60 shadow-sm transition-colors align-middle"
                                                                style={{ gap: '0.35rem' }}
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        if (onToggleJurisprudence) onToggleJurisprudence(lookup_id, paragraphIndex);
                                                                    }}
                                                                    title={`${linkCount} cited cases linked to this paragraph`}
                                                                >
                                                                    <div className="flex-shrink-0 flex items-center justify-center text-purple-600 dark:text-purple-400">
                                                                        <Gavel size={14} />
                                                                    </div>
                                                                    <div className="text-[11.5px] font-bold whitespace-nowrap leading-none flex items-center justify-center mt-[1px] text-purple-600 dark:text-purple-400" style={{ textIndent: '0' }}>
                                                                        {linkCount}
                                                                    </div>
                                                                </span>
                                                            )}

                                                             {isLastSegment && (article.id || article.key_id) && !isSubHeader && (
                                                                 <button
                                                                     type="button"
                                                                     onClick={handleAddToPlaylist}
                                                                     className="inline-flex items-center justify-center ml-2 cursor-pointer text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors bg-purple-50 dark:bg-purple-900/20 p-1 rounded-full border border-purple-200 dark:border-purple-800 shadow-sm hover:scale-105 align-baseline"
                                                                     title="Add to LexPlay Playlist"
                                                                 >
                                                                     <Headphones size={14} />
                                                                 </button>
                                                             )}
                                                    </p>
                                                );
                                            },
                                            ul: ({ node, children, ...props }) => {
                                                const isRocArticle = (codeId && ['roc', 'rpc'].includes(String(codeId).toLowerCase())) || (article && article.code_id && ['roc', 'rpc'].includes(String(article.code_id).toLowerCase()));
                                                if (isRocArticle) return <div className="block">{children}</div>;
                                                return <ul {...props} className="!list-none !m-0 !p-0" style={{ listStyle: 'none' }}>{children}</ul>;
                                            },
                                            ol: ({ node, children, ...props }) => {
                                                const isRocArticle = (codeId && ['roc', 'rpc'].includes(String(codeId).toLowerCase())) || (article && article.code_id && ['roc', 'rpc'].includes(String(article.code_id).toLowerCase()));
                                                if (isRocArticle) return <div className="block">{children}</div>;
                                                return <ol {...props} className="!list-none !m-0 !p-0" style={{ listStyle: 'none' }}>{children}</ol>;
                                            },
                                            li: ({ node, children, ...props }) => {
                                                const isRocArticle = (codeId && ['roc', 'rpc'].includes(String(codeId).toLowerCase())) || (article && article.code_id && ['roc', 'rpc'].includes(String(article.code_id).toLowerCase()));
                                                if (isRocArticle) return <span className="block">{children}</span>;
                                                return (
                                                    <li {...props} className="whitespace-pre-wrap !m-0 !list-none !before:content-none" style={{ paddingLeft: '2.5rem', textIndent: '-2.5rem', listStyle: 'none' }}>
                                                        <span className="!before:content-none">{children}</span>
                                                    </li>
                                                );
                                            },
                                        }}
                                    >
                                    {isSubHeader ? toTitleCase(renderSegment, skipKeywords) : renderSegment}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        );
                    });
                })()}
            </div>



            {/* Elements Box */}
            {showElements && parsedElements && parsedElements.length > 0 && (
                <div className="mt-4 bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                    <h4 className="text-[16px] font-bold text-gray-700 dark:text-gray-300 mb-2">Elements of the Crime</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 dark:text-gray-300">
                        {parsedElements.map((el, idx) => (
                            <li key={idx}>{el}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
});

export default ArticleNode;
