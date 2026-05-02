import React, { useCallback, useMemo, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { normalizeFullTextMarkdownForGfm, repairUtf8Latin1Mojibake } from '../utils/fullTextMarkdown';

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

export const SmartLink = React.memo(({ text, onCaseClick, plain }) => {
    if (!text) return null;
    if (plain) return <span>{text}</span>;
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

const SmartLinkWrapper = React.memo(({ children, onCaseClick, linkless }) => {
    if (linkless) {
        if (typeof children === 'string') return <span>{children}</span>;
        if (Array.isArray(children)) {
            return (
                <>
                    {children.map((child, idx) => {
                        if (typeof child === 'string') return <span key={idx}>{child}</span>;
                        return <React.Fragment key={idx}>{child}</React.Fragment>;
                    })}
                </>
            );
        }
        return <>{children}</>;
    }
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

/** Renders GFM/MD links and footnote refs as non-interactive text (case digest + full text). */
function MarkdownLinkAsSpan({ children, className, node: _n, href: _h, rel: _r, target: _t, download: _d, ref, ...rest }) {
    return (
        <span
            ref={ref}
            className={['text-inherit', 'no-underline', 'font-inherit', 'not-italic', 'cursor-text', className]
                .filter(Boolean)
                .join(' ')}
            {...rest}
        >
            {children}
        </span>
    );
}

/** Flatten React node children to plain string (for full-text SC caption heuristics). */
function plainTextFromChildren(children) {
    if (children == null) return '';
    if (typeof children === 'string' || typeof children === 'number') return String(children);
    if (Array.isArray(children)) return children.map(plainTextFromChildren).join('');
    if (typeof children === 'object' && children !== null && 'props' in children) {
        return plainTextFromChildren(children.props?.children);
    }
    return '';
}

/**
 * After caption lines (first division, docket, party lines split across 2+ blocks, ### Decision)
 * the next line is the ponente or the opening of the discussion — keep left. Up to
 * `SC_CAPTION_MAX_BLOCKS` earlier blocks are centered unless this matches.
 * (Seven lines = indices 0–6, e.g. division + docket + several party lines + ### Decision.)
 */
const SC_CAPTION_MAX_BLOCKS = 8;

/** Title line for the disposition (often `### Decision` / `### Resolution` after the party caption). */
function isScDecisionOrResolutionTitle(plain) {
    const t = plain.replace(/\s+/g, ' ').trim();
    return /^(Decision|Resolution)\s*$/i.test(t);
}

function isScPonenteOrBodyStartLine(plain) {
    const t = plain.replace(/\s+/g, ' ').trim();
    if (t.length < 4) return false;
    if (/^Before the Court\b/i.test(t)) return true;
    if (t.length > 500) return false;
    // Sole justice / per curiam byline: e.g. "…, J.:" or "…, C.J.:" at end of the block
    if (/,\s*(?:J\.J?\.|J\.|C\.J\.|A\.J\.)\s*:\s*$/i.test(t)) return true;
    return false;
}

/**
 * @param {object} [options]
 * @param {boolean} [options.scFullTextCaption] – full text: center SC E-Lib caption (p + h1–h6)
 * @param {React.MutableRefObject<number> | null} [options.pIdxRef] – block index; reset each render
 * @param {React.MutableRefObject<boolean> | null} [options.scCaptionEndRef] – set true when ponente/“Before the Court” seen; all later lines stay left
 * @param {boolean} [options.linkless] – no &lt;a&gt; or SmartLink highlights (digest and full text use true)
 */
function useMarkdownComponents(onCaseClick, includeTables, options = {}) {
    const { scFullTextCaption = false, pIdxRef = null, scCaptionEndRef = null, linkless = true } = options;

    const onHashLinkClick = useCallback((e) => {
        const a = e.currentTarget;
        const href = a.getAttribute('href');
        if (!href || !href.startsWith('#')) return;
        if (scrollInPageHashIntoView(a, href)) {
            e.preventDefault();
        }
    }, []);

    return useMemo(() => {
        /**
         * Full-text `prose text-justify` on the parent overrides `text-center` on children.
         * Up to `SC_CAPTION_MAX_BLOCKS` top-level p / headings: center with `!text-center` + `not-prose`
         * unless the line is ponente (…, J.:) or the opening "Before the Court…".
         */
        const getCaptionTextAlign = (children) => {
            if (!pIdxRef || !scFullTextCaption) return 'text-left';
            if (scCaptionEndRef?.current) {
                pIdxRef.current += 1;
                return 'text-left';
            }
            const plain = plainTextFromChildren(children);
            const i = pIdxRef.current;
            pIdxRef.current += 1;
            if (isScPonenteOrBodyStartLine(plain)) {
                if (scCaptionEndRef) scCaptionEndRef.current = true;
                return 'text-left';
            }
            // Standalone "Decision" / "Resolution" stays centered even when past the general cap (7th+ line).
            if (isScDecisionOrResolutionTitle(plain) && !scCaptionEndRef?.current) {
                return 'not-prose !text-center';
            }
            if (i >= SC_CAPTION_MAX_BLOCKS) {
                if (scCaptionEndRef) scCaptionEndRef.current = true;
                return 'text-left';
            }
            return 'not-prose !text-center';
        };

        const H = (Tag, sizeClass) =>
            function CenterAwareHeading({ children }) {
                const a = getCaptionTextAlign(children);
                return (
                    <Tag
                        className={`mb-2 font-bold text-gray-900 dark:text-gray-100 ${sizeClass} ${a}`}
                    >
                        <SmartLinkWrapper onCaseClick={onCaseClick} linkless={linkless}>
                            {children}
                        </SmartLinkWrapper>
                    </Tag>
                );
            };

        const base = {
            p: ({ children }) => {
                const a = getCaptionTextAlign(children);
                return (
                    <div className={`mb-4 text-gray-800 dark:text-gray-200 leading-relaxed max-w-none ${a}`}>
                        <SmartLinkWrapper onCaseClick={onCaseClick} linkless={linkless}>
                            {children}
                        </SmartLinkWrapper>
                    </div>
                );
            },
            h1: H('h1', 'text-2xl'),
            h2: H('h2', 'text-xl'),
            h3: H('h3', 'text-lg'),
            h4: H('h4', 'text-base'),
            h5: H('h5', 'text-sm'),
            h6: H('h6', 'text-sm'),
            strong: ({ children }) => <strong className="font-bold text-gray-900 dark:text-gray-100">{children}</strong>,
            ul: ({ children }) => <ul className="mb-4 list-disc pl-5 space-y-2 text-gray-800 dark:text-gray-200">{children}</ul>,
            li: ({ children }) => (
                <li className="pl-1 leading-relaxed">
                    <SmartLinkWrapper onCaseClick={onCaseClick} linkless={linkless}>
                        {children}
                    </SmartLinkWrapper>
                </li>
            ),
        };
        const linkAsSpan = linkless ? { a: MarkdownLinkAsSpan } : {};
        if (!includeTables) {
            return { ...base, ...linkAsSpan };
        }
        return {
            ...base,
            a: linkless
                ? MarkdownLinkAsSpan
                : ({ href, children, node: _node, ...props }) => {
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
            tr: ({ children }) => <tr className="border-b border-lex">{children}</tr>,
            th: ({ children }) => (
                <th className="border border-gray-300 px-2 py-2 align-top font-semibold dark:border-gray-600">{children}</th>
            ),
            td: ({ children }) => (
                <td className="border border-gray-200 px-2 py-2 align-top dark:border-gray-700">
                    <SmartLinkWrapper onCaseClick={onCaseClick} linkless={linkless}>
                        {children}
                    </SmartLinkWrapper>
                </td>
            ),
        };
    }, [onCaseClick, includeTables, onHashLinkClick, scFullTextCaption, pIdxRef, scCaptionEndRef, linkless]);
}

/** Digest sections (facts, issues, ruling, ratio) — no GFM tables. */
export const DigestMarkdownText = React.memo(({ content, variant = 'default', contextRef }) => {
    const processedContent = useMemo(() => {
        if (!content) return content;
        let p = repairUtf8Latin1Mojibake(content);
        if (variant === 'facts') {
            p = p.replace(/([^\n])\n(\*\*.*?\*\*[:?])/g, '$1\n\n$2');
        }
        return p;
    }, [content, variant]);

    const components = useMarkdownComponents(undefined, false);

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
 * Full decision text from `full_text_md` — always `normalizeFullTextMarkdownForGfm` + remark-gfm
 * (tables, footnotes, etc.). Kept separate from digest markdown so CaseDecisionModal cannot drop
 * this pipeline by accident.
 */
export const CaseFullTextMarkdown = React.memo(({ content }) => {
    const fullTextPIdx = useRef(0);
    const scCaptionEndRef = useRef(false);

    const processedContent = useMemo(
        () => (content ? normalizeFullTextMarkdownForGfm(content) : content),
        [content]
    );

    const components = useMarkdownComponents(undefined, true, {
        scFullTextCaption: true,
        pIdxRef: fullTextPIdx,
        scCaptionEndRef,
        linkless: true,
    });

    if (!content) return null;

    // Reset before each full-text parse so SC caption heuristics restart.
    fullTextPIdx.current = 0;
    scCaptionEndRef.current = false;
    return (
        <div className="text-gray-800 dark:text-gray-200 leading-relaxed text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                {processedContent}
            </ReactMarkdown>
        </div>
    );
});
