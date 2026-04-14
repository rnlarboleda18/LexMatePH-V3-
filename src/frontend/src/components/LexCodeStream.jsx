import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import ArticleNode from './ArticleNode';
import { toTitleCase } from '../utils/textUtils';
import { useLexPlay } from '../features/lexplay/useLexPlay';
import { lexCache } from '../utils/cache';
import { CODAL_LEXCACHE_REVISION, stripLegacyCodexArticleRunIn } from '../utils/codalMarkdown';
import { Play, Loader2 } from 'lucide-react';

const INITIAL_CHUNK = 30; // articles to render at first load

// Convert integer to Roman numeral for chapter/title headings
const intToRoman = (num) => {
    const val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1];
    const syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I'];
    let result = '';
    for (let i = 0; i < val.length; i++) {
        while (num >= val[i]) {
            result += syms[i];
            num -= val[i];
        }
    }
    return result;
};

const CodalStream = ({ code = 'RPC', bookNum, titleNum, hideDocHeader = false, onJurisprudenceClick, onAmendmentClick, targetArticleId }) => {
    const [articles, setArticles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isAddingAll, setIsAddingAll] = useState(false);
    
    const { 
        activePlaylistId, 
        savedPlaylists, 
        addBulkToSpecificPlaylist, 
        loadSavedPlaylist,
        setIsDrawerOpen 
    } = useLexPlay();

    const apiCode = code.toLowerCase();

    // Map code to full title
    const codeTitles = {
        'RPC': 'THE REVISED PENAL CODE',
        'CIV': 'THE CIVIL CODE OF THE PHILIPPINES',
        'CONST': '1987 Philippine Constitution',
        'FC': 'Family Code of the Philippines',
        'LABOR': 'Labor Code of the Philippines',
        'ROC': 'Rules of Court of the Philippines',
        'RCC': 'REVISED CORPORATION CODE OF THE PHILIPPINES',
    };
    const mainTitle = codeTitles[code.toUpperCase()] || code;
    const centerLayout = false; // Left-aligned by default to match body text flow

    // Optional subtitle shown under the main title
    const codeSubtitles = {
        'CIV': 'Republic Act No. 386, as amended',
        'RPC': 'Act No. 3815, as amended',
        'LABOR': 'Presidential Decree No. 442, as amended',
        'FC': 'Executive Order No. 209, as amended',
        'ROC': 'As amended, 2019',
        'RCC': 'Republic Act No. 11232, as amended',
    };
    const docSubtitle = codeSubtitles[code.toUpperCase()] || null;

    // All codes (that have a real title) get a document header block except labor
    // which uses Book headers as the structural anchor
    const showDocHeader = !!codeTitles[code.toUpperCase()];

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            
            const cacheKey =
                (titleNum ? `${apiCode}_title_${titleNum}` : bookNum ? `${apiCode}_book_${bookNum}` : `${apiCode}_all`) +
                (['rcc', 'civ', 'labor', 'rpc', 'fc'].includes(apiCode) ? CODAL_LEXCACHE_REVISION : '');

            const fetcher = async () => {
                let url = '';
                if (titleNum) {
                    url = `/api/${apiCode}/title/${titleNum}`;
                    const res = await fetch(url);
                    if (!res.ok) throw new Error('Failed to fetch codal data');
                    return await res.json();
                } else if (bookNum) {
                    url = `/api/${apiCode}/book/${bookNum}`;
                    const res = await fetch(url);
                    if (!res.ok) throw new Error('Failed to fetch codal data');
                    return await res.json();
                } else {
                    if (code === 'RPC') {
                        const [res1, res2] = await Promise.all([
                            fetch(`/api/rpc/book/1`),
                            fetch(`/api/rpc/book/2`)
                        ]);
                        const data1 = res1.ok ? await res1.json() : [];
                        const data2 = res2.ok ? await res2.json() : [];
                        return [...data1, ...data2];
                    } else if (code === 'CIV') {
                        const [res0, res1, res2, res3, res4] = await Promise.all([
                            fetch(`/api/civ/preliminary`),
                            fetch(`/api/civ/book/1`),
                            fetch(`/api/civ/book/2`),
                            fetch(`/api/civ/book/3`),
                            fetch(`/api/civ/book/4`)
                        ]);
                        const data0 = res0.ok ? await res0.json() : [];
                        const data1 = res1.ok ? await res1.json() : [];
                        const data2 = res2.ok ? await res2.json() : [];
                        const data3 = res3.ok ? await res3.json() : [];
                        const data4 = res4.ok ? await res4.json() : [];
                        return [...data0, ...data1, ...data2, ...data3, ...data4];
                    } else if (apiCode === 'roc') {
                        const res = await fetch(`/api/roc/all`);
                        return res.ok ? await res.json() : [];
                    } else if (apiCode === 'const') {
                        const res = await fetch(`/api/const/book/1`);
                        return res.ok ? await res.json() : [];
                    } else if (apiCode === 'fc') {
                        const res = await fetch(`/api/fc/all`);
                        return res.ok ? await res.json() : [];
                    } else if (apiCode === 'labor') {
                        const [res0, res1, res2, res3, res4, res5, res6, res7] = await Promise.all([
                            fetch(`/api/labor/books/preliminary`),
                            fetch(`/api/labor/books/1`),
                            fetch(`/api/labor/books/2`),
                            fetch(`/api/labor/books/3`),
                            fetch(`/api/labor/books/4`),
                            fetch(`/api/labor/books/5`),
                            fetch(`/api/labor/books/6`),
                            fetch(`/api/labor/books/7`)
                        ]);
                        const allData = [];
                        for (const res of [res0, res1, res2, res3, res4, res5, res6, res7]) {
                            if (res.ok) {
                                const data = await res.json();
                                if (data.articles) allData.push(...data.articles);
                            }
                        }
                        return allData;
                    } else if (code === 'RCC') {
                        const res = await fetch('/api/codex/versions?short_name=RCC');
                        if (!res.ok) {
                            let msg = `Codex HTTP ${res.status}`;
                            try {
                                const err = await res.json();
                                if (err && typeof err.detail === 'string' && err.detail) msg = err.detail;
                                else if (err && typeof err.error === 'string' && err.error) msg = err.error;
                            } catch {
                                /* ignore */
                            }
                            throw new Error(msg);
                        }
                        const json = await res.json();
                        return (json.articles || []).map((a) => {
                            const num = a.article_num ?? a.article_number ?? a.key_id;
                            const raw = a.content_md || a.content || '';
                            const content_md = stripLegacyCodexArticleRunIn(raw, num);
                            return {
                                ...a,
                                article_num: num,
                                content_md,
                            };
                        });
                    }
                }
                return [];
            };

            try {
                await lexCache.swr('codals', cacheKey, fetcher, (data) => {
                    setArticles(data || []);
                    setLoading(false);
                });
            } catch (err) {
                console.error(err);
                setError(err.message);
                setLoading(false);
            }
        };

        fetchData();
    }, [code, bookNum, titleNum, apiCode]);

    // Progressive rendering ΓÇö start with CHUNK_SIZE articles, load more on scroll
    // MUST BE BEFORE EARLY RETURNS because React requires hooks to be called consistently
    const [visibleCount, setVisibleCount] = useState(INITIAL_CHUNK);
    const sentinelRef = useRef(null);

    // Reset visible count whenever the articles change (new codal opened)
    useEffect(() => { setVisibleCount(INITIAL_CHUNK); }, [articles]);

    const loadMore = useCallback(() => {
        setVisibleCount(prev => Math.min(prev + 50, articles.length));
    }, [articles.length]);

    // When an external targetArticleId is provided (e.g. from TOC click),
    // ensure that chunk is loaded so we can scroll to it.
    useEffect(() => {
        if (!targetArticleId || articles.length === 0) return;
        const targetIndex = articles.findIndex(a => 
            a.id === targetArticleId || 
            String(a.article_num || a.article_number) === String(targetArticleId)
        );
        if (targetIndex >= visibleCount) {
            setVisibleCount(Math.min(targetIndex + 20, articles.length)); // Load enough to show it plus a buffer
        }
    }, [targetArticleId, articles.length, visibleCount]);

    useEffect(() => {
        const sentinel = sentinelRef.current;
        if (!sentinel) return;
        const observer = new IntersectionObserver(
            (entries) => { if (entries[0].isIntersecting) loadMore(); },
            { rootMargin: '800px' }  // start loading 800px before reaching bottom
        );
        observer.observe(sentinel);
        return () => observer.disconnect();
    }, [loadMore]);

    // Pre-process articles to extract section headers from content if section_label is missing
    const processedArticles = useMemo(() => articles.map(art => {
        if (!art.section_label && art.content_md) {
            // Check if content starts with a section header
            const sectionMatch = art.content_md.match(/^##\s+SECTION\s+\d+\s+(.+)$/m);
            if (sectionMatch) {
                // Extract section text and assign to section_label
                return {
                    ...art,
                    section_label: sectionMatch[0].replace(/^##\s+/, ''), // Full matched line without ##
                };
            }
        }
        return art;
    }), [articles]);

    if (loading) return <div className="p-8 text-center text-gray-500 animate-pulse">Loading Codal Stream...</div>;
    if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;
    if (articles.length === 0) return <div className="p-8 text-center text-gray-400">No articles found.</div>;

    return (
        <div className="mx-auto min-w-0 max-w-full px-4 pb-8 pt-0 [overflow-wrap:anywhere] [word-break:break-word]">
            <div className="min-w-0 max-w-full">
                {/* Main Document Title ΓÇö shown only when not already shown in a parent toolbar */}
                {showDocHeader && !hideDocHeader && (
                    <div className="text-center mb-6 relative">
                        <h1 className="text-3xl font-extrabold text-gray-900 dark:text-gray-100 tracking-wide font-sans uppercase">
                            {mainTitle}
                        </h1>
                        <div className="flex justify-center items-center gap-4 mt-3">
                            {docSubtitle && (
                                <p className="text-sm font-semibold text-amber-700 dark:text-amber-400 tracking-widest uppercase">
                                    {docSubtitle}
                                </p>
                            )}
                            {processedArticles.length > 0 && (
                                <button
                                    onClick={async () => {
                                        let targetId = activePlaylistId || (savedPlaylists[0]?.id);
                                        if (!targetId) {
                                            alert("Please create a playlist first in the LexPlay drawer.");
                                            setIsDrawerOpen(true);
                                            return;
                                        }
                                        setIsAddingAll(true);
                                        const payloadItems = processedArticles.map(a => {
                                            const currentArtNum = a.article_num || a.article_number || a.key_id || a.id;
                                            return {
                                                content_id: String(currentArtNum),
                                                content_type: 'codal',
                                                code_id: code.toUpperCase(), // e.g RPC
                                                title: /^(article|preamble|section|rule)/i.test(String(currentArtNum))
                                                    ? toTitleCase(String(currentArtNum), code && code.toUpperCase() === 'ROC' ? ['SECTION', 'RULE'] : [])
                                                    : `Article ${currentArtNum || ''}`,
                                                subtitle: a.article_title || mainTitle
                                            };
                                        });
                                        await addBulkToSpecificPlaylist(targetId, payloadItems);
                                        // Force load to ensure state sync even if it was the first add
                                        await loadSavedPlaylist(targetId);
                                        setIsAddingAll(false);
                                        setIsDrawerOpen(true);
                                    }}
                                    disabled={isAddingAll}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-100 hover:bg-purple-200 text-purple-700 dark:bg-purple-900/30 dark:hover:bg-purple-900/50 dark:text-purple-300 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors disabled:opacity-50"
                                >
                                    {isAddingAll ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />}
                                    {isAddingAll ? 'Adding...' : 'Play Entire Codal'}
                                </button>
                            )}
                        </div>
                    </div>
                )}
                {processedArticles.slice(0, visibleCount).map((art, index) => {
                    const prevArt = processedArticles[index - 1] || {};
                    const headersToRender = [];

                    // Render Book Header if shifted or explicitly set
                    // SKIP for Article 0 (Preamble) as it has its own custom header
                    // SKIP if the book_label duplicates the main document title (already shown at top)
                    const normalizeTitle = (s) => (s || '').replace(/[^a-z0-9]/gi, '').toLowerCase();
                    const foldAlnum = (s) => (s || '').replace(/[^a-z0-9]+/gi, '').toLowerCase();
                    const mainTitleNorm = normalizeTitle(mainTitle);

                    // Client-side rule cleaner ensures immediate formatting regardless of backend caching
                    const cleanRomanRules = (text) => {
                        if (!text) return text;
                        return text.replace(/\bRule\s+([IVXLCDM]+)\b/ig, (match, roman) => {
                            const romVal = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000};
                            let val = 0;
                            const s = roman.toUpperCase();
                            for (let i = 0; i < s.length; i++) {
                                if (i > 0 && romVal[s[i]] > romVal[s[i - 1]]) {
                                    val += romVal[s[i]] - 2 * romVal[s[i - 1]];
                                } else {
                                    val += romVal[s[i]];
                                }
                            }
                            return `Rule ${val}`;
                        });
                    };

                    const formatHeader = (text) => {
                        let proc = toTitleCase(text);
                        if (code && code.toLowerCase() === 'roc') {
                            proc = cleanRomanRules(proc);
                        }
                        return proc;
                    };

                    let bookHdr = null;
                    let chapterHdr = null;
                    let sectionHdr = null;
                    let ruleHdr = null;
                    let titleHdr = null;

                    if (String(art.article_num) !== '0') {
                        if (art.book_label && art.book_label !== prevArt.book_label) {
                            if (!art.book_label.toUpperCase().includes('PRELIMINARY')) {
                                const bookPrefix = code.toLowerCase() === 'roc' ? 'Part' : 'Book';
                                const cleanLabel = toTitleCase(art.book_label);
                                const bookText = cleanLabel.toUpperCase().includes(bookPrefix.toUpperCase())
                                    ? cleanLabel
                                    : art.book ? `${bookPrefix} ${art.book} - ${cleanLabel}` : cleanLabel;
                                const bookNorm = normalizeTitle(bookText);
                                if (!mainTitleNorm.includes(bookNorm) && !bookNorm.includes(mainTitleNorm)) {
                                    bookHdr = { type: 'BOOK', text: bookText };
                                }
                            }
                        } else if (!art.book_label && art.book && art.book !== prevArt.book) {
                            const bookPrefix = code.toLowerCase() === 'roc' ? 'Part' : 'Book';
                            bookHdr = { type: 'BOOK', text: `${bookPrefix} ${art.book}` };
                        }
                    }

                    const isConstStream = code.toLowerCase() === 'const';
                    const isRocStream = code.toLowerCase() === 'roc';

                    if (art.chapter_label && art.chapter_label !== prevArt.chapter_label) {
                        const cleanLabel = formatHeader(art.chapter_label);
                        const chapterText = (cleanLabel.toUpperCase().startsWith('CHAPTER'))
                            ? cleanLabel
                            : (art.chapter_num && parseInt(art.chapter_num) > 0)
                                ? `Chapter ${intToRoman(parseInt(art.chapter_num))} - ${cleanLabel}`
                                : cleanLabel;
                        chapterHdr = { type: 'CHAPTER', text: chapterText };
                    }

                    if (chapterHdr && art.article_title && !isRocStream) {
                        const chTail = chapterHdr.text.replace(/^Chapter\s+[IVXLCDM]+\s*-\s*/i, '').trim();
                        if (chTail && foldAlnum(chTail) === foldAlnum(art.article_title)) {
                            chapterHdr = null;
                        }
                    }

                    if (!isConstStream && art.section_label && art.section_label !== prevArt.section_label) {
                        sectionHdr = { type: 'SECTION', text: formatHeader(art.section_label) };
                    }

                    if (isRocStream && art.title_num != null && art.title_num !== prevArt.title_num) {
                        ruleHdr = { type: 'RULE', text: `Rule ${art.title_num}` };
                    }

                    // For all structured codals: use title_num (integer) when available so a single
                    // NULL-title_label article (e.g. Art 274) does not reset the "seen" state and
                    // cause the title to be re-announced for the very next article.
                    const hasTitleNum = art.title_num != null;
                    const prevHasTitleNum = prevArt.title_num != null;
                    const titleTrigger = (hasTitleNum || isRocStream)
                        ? (art.title_num != null && art.title_num !== prevArt.title_num)
                        : (art.title_label && art.title_label !== prevArt.title_label);
                    if (String(art.article_num) !== '0' && art.title_label && titleTrigger) {
                        const cleanLabel = formatHeader(art.title_label);
                        const titleText = (cleanLabel.toUpperCase().startsWith('TITLE'))
                            ? cleanLabel
                            : (art.title_num && parseInt(art.title_num) > 0 && !isRocStream)
                                ? `Title ${intToRoman(parseInt(art.title_num))} - ${cleanLabel}`
                                : cleanLabel;
                        const dup = [bookHdr, chapterHdr, sectionHdr].some(
                            h => h && normalizeTitle(h.text) === normalizeTitle(titleText)
                        );
                        const stripTitleRomanPrefix = (s) => String(s || '').replace(/^Title\s+[IVXLCDM]+\s*-\s*/i, '').trim();
                        const titleTail = stripTitleRomanPrefix(titleText);
                        const artTitle = (art.article_title || '').trim();
                        const titleDupesArticle =
                            !isRocStream &&
                            artTitle &&
                            foldAlnum(titleTail) === foldAlnum(artTitle);
                        if (!dup && !titleDupesArticle) {
                            titleHdr = { type: 'TITLE', text: titleText };
                        }
                    }

                    if (String(art.article_num) === '0' && art.title_label) {
                        headersToRender.push({ type: 'PREAMBLE', text: art.title_label });
                    }
                    if (bookHdr) headersToRender.push(bookHdr);

                    // RPC / CIV / Labor: Title (major division) before Chapter / Section
                    if (isRocStream) {
                        if (chapterHdr) headersToRender.push(chapterHdr);
                        if (sectionHdr) headersToRender.push(sectionHdr);
                        if (ruleHdr) headersToRender.push(ruleHdr);
                        if (titleHdr) headersToRender.push(titleHdr);
                    } else {
                        if (titleHdr) headersToRender.push(titleHdr);
                        if (chapterHdr) headersToRender.push(chapterHdr);
                        if (sectionHdr) headersToRender.push(sectionHdr);
                    }

                    if (art.group_header && art.group_header !== prevArt.group_header) {
                        const parts = art.group_header.split('\n');
                        parts.forEach((p, idx) => {
                            const type = idx === 0 ? 'BOOK' : 'TITLE';
                            headersToRender.push({ type, text: formatHeader(p) });
                        });
                    }

                    return (
                        <div key={art.id} className="mb-4 min-w-0 max-w-full">
                            {/* Render Hoisted Headers */}
                            {headersToRender.map((h, i) => {
                                let sizeClass = "text-[16px]";
                                let colorClass = "text-gray-900 dark:text-gray-200 font-bold";
                                const isRoc = code && code.toUpperCase() === 'ROC';
                                const isConst = code && code.toUpperCase() === 'CONST';
                                const skipKeywords = isRoc ? ['SECTION', 'RULE'] : isConst ? ['SECTION'] : [];

                                if (h.type === 'SECTION') {
                                    sizeClass = "text-[16px]";
                                    colorClass = "text-gray-900 dark:text-gray-300 font-bold";
                                }
                                else if (h.type === 'RULE' || h.type === 'CHAPTER' || h.type === 'TITLE' || h.type === 'BOOK' || h.type === 'PREAMBLE') {
                                    sizeClass = "text-[16px]";
                                }

                                return (
                                    <div key={i} className={`my-2 ${ (h.type === 'BOOK' || h.type === 'TITLE' || h.type === 'PREAMBLE' || h.type === 'CHAPTER' || h.type === 'SECTION' || h.type === 'RULE') ? 'text-center border-b-[1px] border-gray-100 dark:border-gray-800 pb-1 mb-4' : '' }`}>
                                        {/* Add Main Header just once before the Preamble or First Book */}
                                        {h.type === 'PREAMBLE' && (
                                            <h1 className="text-[16px] font-extrabold text-gray-900 dark:text-gray-100 mb-2 tracking-wide font-sans">
                                                {toTitleCase(mainTitle, skipKeywords)}
                                            </h1>
                                        )}

                                        <h2 className={`font-sans ${colorClass} ${sizeClass} tracking-wide whitespace-pre-line leading-tight`}>
                                            {toTitleCase(h.text.replace(/\n\s*\n/g, '\n'), skipKeywords)}
                                        </h2>
                                    </div>
                                );
                            })}

                            <ArticleNode
                                article={art}
                                showElements={false}
                                centerLayout={centerLayout}
                                onToggleJurisprudence={onJurisprudenceClick}
                                onToggleAmendment={onAmendmentClick}
                                codeId={code.toLowerCase()}
                            />
                        </div>
                    );
                })}
                {/* Sentinel for progressive loading (or in this case, the one-time big load) */}
                {visibleCount < processedArticles.length && (
                    <div ref={sentinelRef} className="py-6 text-center text-xs text-gray-400 dark:text-gray-600 animate-pulse">
                        Loading all remaining {processedArticles.length - visibleCount} articles...
                    </div>
                )}
                {/* Invisible sentinel always present so observer can watch end of list */}
                <div ref={visibleCount >= processedArticles.length ? sentinelRef : null} />
            </div>
        </div>
    );
};

export default CodalStream;
