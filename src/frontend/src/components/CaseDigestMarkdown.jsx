import React, { useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { normalizeFullTextMarkdownForGfm } from '../utils/fullTextMarkdown';

export const SMART_LINK_REGEX = /(G\.R\. Nos?\.\s?\d+[\w\,&\s-]*)|(Republic Act No\.\s?\d+)/gi;

const MODAL_SCROLL_CLASS = 'lex-modal-scroll';

/** Escape an HTML id for use in `querySelector("#…")` (subset safe for footnote ids). */
function escapeCssIdFragment(id) {
    if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
        return CSS.escape(id);
    }
    return id.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

/**
 * GFM footnote refs use in-page # anchors; the case modal scrolls inside `.lex-modal-scroll`,
 * so the browser often does not scroll the footnote into view. Resolve the target inside
 * that subtree (or document) and scroll it into the visible modal.
 */
function scrollInPageHashIntoView(anchorEl, hash) {
    if (!hash || hash === '#' || typeof document === 'undefined') return false;
    const raw = hash.startsWith('#') ? hash.slice(1) : hash;
    let id = raw;
    try {
        id = decodeURIComponent(raw);
    } catch {
        id = raw;
    }
    if (!id) return false;

    const scrollRoot = anchorEl.closest(`.${MODAL_SCROLL_CLASS}`);
    const pick = (root) => {
        if (!root) return null;
        try {
            return root.querySelector(`#${escapeCssIdFragment(id)}`);
        } catch {
            return null;
        }
    };

    const target = pick(scrollRoot) || pick(document) || document.getElementById(id);
    if (!target) return false;

    target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    return true;
}

export const SmartLink = React.memo(({ text, onCaseClick }) => {
    if (!text) return null;
    const parts = text.split(SMART_LINK_REGEX).filter((p) => p !== undefined);

    if (parts.length === 1) return <span>{text}</span>;

    return (
        <span>
            {parts.map((part, i) => {
                const isMatch = typeof part === 'string' && part.match(SMART_LINK_REGEX);
                if (isMatch) {
                    return (
                        <span
                            key={i}
                            className="text-blue-600 dark:text-amber-400 cursor-pointer hover:underline font-medium relative group"
                            onClick={(e) => {
                                e.stopPropagation();
                                if (onCaseClick) onCaseClick(part);
                            }}
                        >
                            {part}
                        </span>
                    );
                }
                return <span key={i}>{part}</span>;
            })}
        </span>
    );
});

const SmartLinkWrapper = React.memo(({ children, onCaseClick }) => {
    if (typeof children === 'string') return <SmartLink text={children} onCaseClick={onCaseClick} />;
    if (Array.isArray(children)) {
        return (
            <>
                {children.map((child, idx) => {
                    if (typeof child === 'string') return <SmartLink key={idx} text={child} onCaseClick={onCaseClick} />;
                    return <React.Fragment key={idx}>{child}</React.Fragment>;
                })}
            </>
        );
    }
    return <>{children}</>;
});

function useMarkdownComponents(onCaseClick, includeTables) {
    const onHashLinkClick = useCallback((e) => {
        const a = e.currentTarget;
        const href = a.getAttribute('href');
        if (!href || !href.startsWith('#')) return;
        if (scrollInPageHashIntoView(a, href)) {
            e.preventDefault();
        }
    }, []);

    return useMemo(() => {
        const base = {
            p: ({ children }) => (
                <div className="mb-4 text-gray-800 dark:text-gray-200 leading-relaxed text-left">
                    <SmartLinkWrapper onCaseClick={onCaseClick}>{children}</SmartLinkWrapper>
                </div>
            ),
            strong: ({ children }) => <strong className="font-bold text-gray-900 dark:text-gray-100">{children}</strong>,
            ul: ({ children }) => <ul className="mb-4 list-disc pl-5 space-y-2 text-gray-800 dark:text-gray-200">{children}</ul>,
            li: ({ children }) => (
                <li className="pl-1 leading-relaxed">
                    <SmartLinkWrapper onCaseClick={onCaseClick}>{children}</SmartLinkWrapper>
                </li>
            ),
        };
        if (!includeTables) return base;
        return {
            ...base,
            a: ({ href, children, node: _node, ...props }) => {
                if (typeof href === 'string' && href.startsWith('#')) {
                    return (
                        <a
                            {...props}
                            href={href}
                            onClick={onHashLinkClick}
                            className={[props.className, 'text-blue-700 underline-offset-2 hover:underline dark:text-amber-400']
                                .filter(Boolean)
                                .join(' ')}
                        >
                            {children}
                        </a>
                    );
                }
                return (
                    <a {...props} href={href}>
                        {children}
                    </a>
                );
            },
            table: ({ children }) => (
                <div className="my-4 w-full overflow-x-auto">
                    <table className="min-w-full border-collapse border border-gray-300 text-left text-sm dark:border-gray-600">
                        {children}
                    </table>
                </div>
            ),
            thead: ({ children }) => <thead className="bg-gray-100 dark:bg-gray-800/80">{children}</thead>,
            tbody: ({ children }) => <tbody>{children}</tbody>,
            tr: ({ children }) => <tr className="border-b border-gray-200 dark:border-gray-700">{children}</tr>,
            th: ({ children }) => (
                <th className="border border-gray-300 px-2 py-2 align-top font-semibold dark:border-gray-600">{children}</th>
            ),
            td: ({ children }) => (
                <td className="border border-gray-200 px-2 py-2 align-top dark:border-gray-700">
                    <SmartLinkWrapper onCaseClick={onCaseClick}>{children}</SmartLinkWrapper>
                </td>
            ),
        };
    }, [onCaseClick, includeTables, onHashLinkClick]);
}

/** Digest sections (facts, issues, ruling, ratio) — no GFM tables. */
export const DigestMarkdownText = React.memo(({ content, onCaseClick, variant = 'default', contextRef }) => {
    const processedContent = useMemo(() => {
        if (!content) return content;
        let p = content;
        if (variant === 'facts') {
            p = p.replace(/([^\n])\n(\*\*.*?\*\*[:?])/g, '$1\n\n$2');
        }
        return p;
    }, [content, variant]);

    const components = useMarkdownComponents(onCaseClick, false);

    if (!content) return null;

    return (
        <div ref={contextRef} className="text-gray-800 dark:text-gray-200 leading-relaxed text-left text-sm">
            <ReactMarkdown remarkPlugins={[]} components={components}>
                {processedContent}
            </ReactMarkdown>
        </div>
    );
});

/**
 * Full decision text from `full_text_md` — always remark-gfm (tables, footnotes, etc.)
 * plus `normalizeFullTextMarkdownForGfm`. Kept separate from digest markdown so footer/layout
 * edits in CaseDecisionModal cannot drop this pipeline by accident.
 *
 * Content over PLAIN_TEXT_THRESHOLD characters is shown as plain preformatted text instead of
 * running through the remark parser, which would block the main thread for multi-second hangs on
 * very long SC decisions (100 KB+). A notice is shown so the user understands why formatting
 * differs from the digest view.
 */
const PLAIN_TEXT_THRESHOLD = 80_000;

export const CaseFullTextMarkdown = React.memo(({ content, onCaseClick }) => {
    const processedContent = useMemo(() => {
        if (!content) return content;
        // Skip the normalization pipeline for very long content to avoid quadratic regex cost
        if (content.length > PLAIN_TEXT_THRESHOLD) return content;
        return normalizeFullTextMarkdownForGfm(content);
    }, [content]);

    const components = useMarkdownComponents(onCaseClick, true);

    if (!content) return null;

    // Large SC decisions (100 KB+) would freeze the browser if parsed by remark; render as
    // plain text with a notice instead.
    if (processedContent.length > PLAIN_TEXT_THRESHOLD) {
        return (
            <div className="text-gray-800 dark:text-gray-200 text-left text-sm">
                <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
                    This decision is very long. Showing as plain text to keep the app responsive. Formatting may differ from the digest view.
                </p>
                <pre className="whitespace-pre-wrap break-words leading-relaxed font-sans">
                    {processedContent}
                </pre>
            </div>
        );
    }

    return (
        <div className="text-gray-800 dark:text-gray-200 leading-relaxed text-left text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                {processedContent}
            </ReactMarkdown>
        </div>
    );
});
