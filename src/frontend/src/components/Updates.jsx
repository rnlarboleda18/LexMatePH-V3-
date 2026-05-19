import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import {
  Twitter,
  Facebook,
  ExternalLink,
  Scale,
  Newspaper,
  ChevronRight,
  ShieldCheck,
  Zap,
  Bookmark,
  Rss,
  Gavel,
} from 'lucide-react';
import FeaturePageShell from './FeaturePageShell';
import { useTwitterTimeline } from '../hooks/useTwitterTimeline';
import { apiUrl } from '../utils/apiUrl';
import { buildUnifiedFeed } from '../utils/scJudiciaryFeed';
import {
  CHROME_INTERACTIVE_TILE_HOVER,
  CHROME_INTERACTIVE_TILE_HOVER_BG,
  CHROME_INTERACTIVE_CHEVRON,
  CHROME_INTERACTIVE_CHEVRON_NUDGE,
} from '../utils/filterChromeClasses';

/** Official SC portal — full decisions index (not LexMate digests). */
const SC_DECISIONS_INDEX = 'https://sc.judiciary.gov.ph/decisions/';

function officialScDecisionUrl(decision) {
  const raw = typeof decision?.sc_url === 'string' ? decision.sc_url.trim() : '';
  if (raw && /^https?:\/\//i.test(raw)) return raw;
  const q = (decision?.case_number || decision?.title || '').trim();
  if (q) return `https://sc.judiciary.gov.ph/?s=${encodeURIComponent(q)}`;
  return SC_DECISIONS_INDEX;
}

const NEWS_LINKS = [
  {
    label: 'Judiciary News',
    desc: 'Press releases',
    icon: Newspaper,
    href: 'https://sc.judiciary.gov.ph/news/',
    accent: 'from-sky-500/20 to-blue-600/5 text-sky-600 dark:text-sky-400',
  },
  {
    label: 'Bar Bulletins',
    desc: 'Official issuances',
    icon: Scale,
    href: 'https://sc.judiciary.gov.ph/bar-matters/',
    accent: 'from-amber-500/20 to-orange-600/5 text-amber-700 dark:text-amber-400',
  },
  {
    label: 'BARISTA',
    desc: 'Candidate portal',
    icon: ShieldCheck,
    href: 'https://sc.judiciary.gov.ph/bar-2026/barista/',
    accent: 'from-emerald-500/20 to-teal-600/5 text-emerald-700 dark:text-emerald-400',
  },
];

/** Iframe `height` and the `height` query param to page.php must match or Meta’s embed crops. */
const FB_PAGE_PLUGIN_HEIGHT = 640;

/**
 * Facebook Page plugin: width 180–500px. A fixed 500 in a ~360px column can clip the header on
 * the right, so we pass the measured host width. `hide_cover` avoids the cover band in the frame.
 */
function buildFacebookPagePluginSrc(widthPx) {
  const w = Math.max(180, Math.min(500, Math.round(widthPx || 400)));
  const base = 'https://www.facebook.com/plugins/page.php';
  const params = new URLSearchParams({
    href: 'https://www.facebook.com/SupremeCourtPhilippines',
    tabs: 'timeline',
    width: String(w),
    height: String(FB_PAGE_PLUGIN_HEIGHT),
    // Narrow columns (typical phone): smaller chrome; Meta recommends for mobile-width embeds.
    small_header: w < 420 ? 'true' : 'false',
    adapt_container_width: 'true',
    hide_cover: 'true',
    show_facepile: 'false',
  });
  const appId = import.meta.env.VITE_FACEBOOK_APP_ID;
  if (appId) params.set('appId', String(appId));
  return `${base}?${params.toString()}`;
}

const bar2026Updates = [
  {
    title: 'Re: End of the Application for the 2026 Bar Examinations',
    date: '9 March 2026',
    type: 'Notice',
    link: 'https://sc.judiciary.gov.ph/re-end-of-the-application-for-the-2026-bar-examinations/',
    cta: 'Read notice',
  },
  {
    title: 'Bar Bulletin No. 2: Application Requirements & Venue Selection',
    date: '8 Dec 2025',
    type: 'Bulletin',
    link: 'https://sc.judiciary.gov.ph/wp-content/uploads/2025/12/2026-BAR-Bar-Bulletin-No-2.pdf',
    cta: 'View PDF',
  },
  {
    title: 'Bar Bulletin No. 1: Conduct, Schedule, & Syllabi',
    date: '16 Oct 2025',
    type: 'Bulletin',
    link: 'https://sc.judiciary.gov.ph/bar-2026/',
    cta: 'Open portal',
  },
  {
    title: 'Frequently Asked Questions (FAQs)',
    date: '16 Dec 2025',
    type: 'FAQ',
    link: 'https://sc.judiciary.gov.ph/wp-content/uploads/2025/12/2026-BAR-FAQs-12-16-2025.pdf',
    cta: 'View PDF',
  },
];

const FILTER_TABS = [
  { id: 'all', label: 'All' },
  { id: 'bar', label: 'Bar & exams' },
  { id: 'news', label: 'News & pleading' },
];

const Updates = ({ isDarkMode = false }) => {
  const [latestDecisions, setLatestDecisions] = useState([]);
  const [loadingDecisions, setLoadingDecisions] = useState(true);
  const [feedItems, setFeedItems] = useState([]);
  const [barFeedItems, setBarFeedItems] = useState([]);
  const [feedLoading, setFeedLoading] = useState(true);
  const [feedError, setFeedError] = useState(null);
  const [feedFilter, setFeedFilter] = useState('all');
  const [fbPluginWidth, setFbPluginWidth] = useState(400);
  const [twitterPanelWidth, setTwitterPanelWidth] = useState(400);
  const fbPluginHostRef = useRef(null);

  const fbIframeSrc = useMemo(() => buildFacebookPagePluginSrc(fbPluginWidth), [fbPluginWidth]);
  const twitterTimelineRef = useRef(null);
  useTwitterTimeline(twitterTimelineRef, [isDarkMode, twitterPanelWidth]);

  useLayoutEffect(() => {
    const el = twitterTimelineRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const apply = (wRaw) => {
      const px = Math.floor(wRaw);
      if (px < 1) return;
      setTwitterPanelWidth((prev) => {
        const next = Math.max(180, Math.min(520, px));
        return prev === next ? prev : next;
      });
    };
    apply(el.getBoundingClientRect().width);
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect?.width;
      if (w != null) apply(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useLayoutEffect(() => {
    const el = fbPluginHostRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const setFromWidth = (wRaw) => {
      const w = Math.floor(wRaw);
      if (w < 1) return;
      setFbPluginWidth((prev) => {
        const next = Math.max(180, Math.min(500, w));
        return prev === next ? prev : next;
      });
    };
    setFromWidth(el.getBoundingClientRect().width);
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect?.width;
      if (w != null) setFromWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    const url = apiUrl('/api/sc_judiciary_feed?limit=22&include_bar=1&bar_limit=18');
    const fetchJson = () =>
      fetch(url, {
        cache: 'no-store',
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      }).then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          const err = new Error(data?.error || `HTTP ${res.status}`);
          err._data = data;
          throw err;
        }
        return data;
      });

    setFeedLoading(true);
    setFeedError(null);
    (async () => {
      try {
        let data;
        try {
          data = await fetchJson();
        } catch {
          await new Promise((r) => setTimeout(r, 600));
          data = await fetchJson();
        }
        if (cancelled) return;
        if (data?.error && (!data.items || data.items.length === 0)) {
          setFeedError(data.error);
          setFeedItems([]);
          setBarFeedItems([]);
        } else {
          setFeedItems(Array.isArray(data?.items) ? data.items : []);
          setBarFeedItems(Array.isArray(data?.bar_items) ? data.bar_items : []);
        }
      } catch {
        if (!cancelled) {
          setFeedError('network');
          setFeedItems([]);
          setBarFeedItems([]);
        }
      } finally {
        if (!cancelled) setFeedLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    fetch(apiUrl('/api/sc_decisions?limit=3'))
      .then((res) => res.json())
      .then((data) => {
        if (data && data.data) {
          setLatestDecisions(data.data);
        }
        setLoadingDecisions(false);
      })
      .catch((err) => {
        // Decision highlights only — unrelated to feedLoading / sc_judiciary_feed above.
        console.error('Error fetching decisions:', err);
        setLoadingDecisions(false);
      });
  }, []);

  const unifiedFeed = useMemo(() => buildUnifiedFeed(feedItems, barFeedItems), [feedItems, barFeedItems]);

  const visibleFeed = useMemo(() => {
    if (feedFilter === 'bar') return unifiedFeed.filter((x) => x._barHighlight);
    if (feedFilter === 'news') return unifiedFeed.filter((x) => !x._barHighlight);
    return unifiedFeed;
  }, [unifiedFeed, feedFilter]);

  return (
    <FeaturePageShell>
      <div className="animate-in fade-in relative pb-12 duration-700">
        {/* Ambient orbs — same vocabulary as landing / app chrome */}
        <div
          className="pointer-events-none absolute -left-24 top-0 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl dark:bg-violet-600/15"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute right-0 top-48 h-80 w-80 rounded-full bg-sky-400/15 blur-3xl dark:bg-sky-500/10"
          aria-hidden
        />

        <div className="relative mx-auto w-full max-w-7xl space-y-tile">
          {/* Hero */}
          <header className="relative overflow-hidden rounded-lg border border-lex bg-gradient-to-br from-white via-white to-slate-50/60 px-6 py-10 shadow-lg dark:border-lex dark:from-zinc-900 dark:via-zinc-900 dark:to-zinc-950 dark:shadow-[0_24px_80px_-28px_rgba(0,0,0,0.45)] sm:px-10">
            <div className="pointer-events-none absolute -right-16 -top-24 h-56 w-56 rounded-full bg-gradient-to-br from-indigo-400/30 to-fuchsia-500/20 blur-2xl" />
            <div className="pointer-events-none absolute bottom-0 left-1/3 h-32 w-64 rounded-full bg-cyan-400/10 blur-2xl" />
            <div className="relative flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight text-black dark:text-white sm:text-4xl">
                  Updates
                </h1>
                <p className="max-w-xl text-sm leading-relaxed text-slate-600 dark:text-slate-400 sm:text-base">
                  One glass feed for{' '}
                  <span className="font-semibold text-slate-800 dark:text-slate-200">public pleadings & news</span> and{' '}
                  <span className="font-semibold text-amber-800 dark:text-amber-200/90">Bar examination flashes</span>,
                  merged from the same official RSS. Highlights and decisions stay at your side.
                </p>
              </div>
              <a
                href="https://sc.judiciary.gov.ph/feed/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex shrink-0 items-center justify-center gap-2 rounded-2xl border-2 border-lex bg-white px-5 py-3 text-sm font-bold text-slate-800 shadow-md transition hover:border-lex-strong hover:bg-neutral-50 dark:border-lex dark:bg-zinc-800/90 dark:text-white dark:hover:bg-zinc-800"
              >
                <Rss className="h-4 w-4 text-indigo-500" />
                RSS source
                <ExternalLink className="h-4 w-4 opacity-60" />
              </a>
            </div>
          </header>

          <div className="grid min-w-0 grid-cols-1 gap-tile lg:grid-cols-12">
            {/* Main column — unified feed */}
            <div className="min-w-0 space-y-4 lg:col-span-7">
              <section className="relative overflow-hidden rounded-lg border-2 border-lex bg-white p-6 shadow-xl dark:border-lex dark:bg-zinc-900 sm:p-8">
                <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/35">
                      <Rss className="h-6 w-6" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-black dark:text-white sm:text-xl">
                        Judiciary pulse
                      </h2>
                      <p className="text-xs text-slate-500 dark:text-slate-400 sm:text-sm">
                        {unifiedFeed.length} items · sc.judiciary.gov.ph
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 rounded-2xl border-2 border-lex bg-neutral-50 p-1 dark:border-lex dark:bg-zinc-800/80">
                    {FILTER_TABS.map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setFeedFilter(tab.id)}
                        className={`rounded-xl px-3 py-2 text-xs font-bold uppercase tracking-wider transition sm:px-4 ${
                          feedFilter === tab.id
                            ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/25 dark:bg-indigo-500'
                            : 'text-slate-500 hover:bg-white/80 dark:text-slate-400 dark:hover:bg-white/5'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Pinned Bar 2026 — curated, not RSS */}
                <div className="mb-4 rounded-2xl border-2 border-lex bg-gradient-to-r from-amber-500/10 via-white to-transparent p-4 dark:border-lex dark:from-amber-500/10 dark:via-zinc-900 dark:to-zinc-900">
                  <div className="mb-2 flex items-center gap-2 text-amber-900 dark:text-amber-200/90">
                    <Bookmark className="h-4 w-4 shrink-0" />
                    <span className="text-[11px] font-black uppercase tracking-widest">Bar 2026 · pinned</span>
                  </div>
                  <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                    {bar2026Updates.map((u, i) => (
                      <a
                        key={i}
                        href={u.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`min-w-[200px] max-w-[260px] shrink-0 rounded-xl border-2 border-lex bg-white p-3 text-left shadow-sm dark:border-lex dark:bg-zinc-800/90 ${CHROME_INTERACTIVE_TILE_HOVER}`}
                      >
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{u.date}</p>
                        <p className="mt-1 line-clamp-2 text-xs font-bold text-slate-900 dark:text-white">{u.title}</p>
                        <span className="mt-2 inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-amber-700 dark:text-amber-400">
                          {u.cta} <ChevronRight className="h-3 w-3" />
                        </span>
                      </a>
                    ))}
                  </div>
                </div>

                {feedLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className="h-24 animate-pulse rounded-2xl border-2 border-lex bg-neutral-100 dark:border-lex dark:bg-zinc-800/60"
                      />
                    ))}
                  </div>
                ) : feedError && unifiedFeed.length === 0 ? (
                  <div className="rounded-2xl border-2 border-lex bg-white p-8 text-center dark:border-lex dark:bg-zinc-900">
                    <p className="font-semibold text-slate-800 dark:text-slate-200">Could not load the live feed.</p>
                    <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Try the portal directly.</p>
                    <a
                      href="https://sc.judiciary.gov.ph/news/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-indigo-600 dark:text-indigo-400"
                    >
                      Open Judiciary News <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                ) : visibleFeed.length === 0 ? (
                  <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">
                    No items in this filter.
                  </p>
                ) : (
                  <ul className="relative space-y-2 border-l-2 border-lex pl-6 dark:border-lex">
                    {visibleFeed.map((item, idx) => (
                      <li key={`${item.link}-${idx}`} className="relative">
                        <span className="absolute -left-[1.35rem] top-5 h-2.5 w-2.5 rounded-full border-2 border-lex bg-indigo-500 shadow dark:border-lex dark:bg-indigo-400" />
                        <a
                          href={item.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`group block overflow-hidden rounded-2xl border-2 border-lex bg-white p-4 shadow-sm dark:border-lex dark:bg-zinc-800/80 sm:p-5 ${CHROME_INTERACTIVE_TILE_HOVER} ${CHROME_INTERACTIVE_TILE_HOVER_BG} dark:hover:bg-zinc-800`}
                        >
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            {item._barHighlight ? (
                              <span className="rounded-full bg-amber-500/15 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-amber-800 dark:bg-amber-500/20 dark:text-amber-200">
                                Bar & exams
                              </span>
                            ) : (
                              <span className="rounded-full bg-sky-500/15 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-sky-800 dark:bg-sky-500/20 dark:text-sky-200">
                                News & pleading
                              </span>
                            )}
                            <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                              {item.pub_date || '—'}
                            </span>
                            {item.categories?.[0] && (
                              <span className="truncate text-[10px] font-semibold text-slate-500 dark:text-slate-400">
                                · {item.categories[0]}
                              </span>
                            )}
                          </div>
                          <h3 className="text-sm font-bold leading-snug text-slate-900 transition group-hover:text-indigo-600 dark:text-white dark:group-hover:text-indigo-300 sm:text-base">
                            {item.title}
                          </h3>
                          {item.snippet && (
                            <p className="mt-2 line-clamp-2 text-xs text-slate-600 dark:text-slate-400">{item.snippet}</p>
                          )}
                          <div className="mt-3 flex items-center gap-1 text-xs font-bold text-slate-400 transition group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                            Read on SC site <ChevronRight className={CHROME_INTERACTIVE_CHEVRON_NUDGE} />
                          </div>
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>

            {/* Rail */}
            <aside className="min-w-0 space-y-3 lg:col-span-5">
              <div className="relative overflow-hidden rounded-lg border-2 border-lex bg-white p-6 shadow-xl dark:border-lex dark:bg-zinc-900 sm:p-8">
                <div className="mb-3 flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/30">
                    <Gavel className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-black dark:text-white">Decision highlights</h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Official SC site · not LexMate digests</p>
                  </div>
                </div>

                {loadingDecisions ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-28 animate-pulse rounded-2xl bg-white/40 dark:bg-slate-800/40" />
                    ))}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {latestDecisions.map((decision) => (
                      <a
                        key={decision.id}
                        href={officialScDecisionUrl(decision)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`block rounded-2xl border-2 border-lex bg-white p-4 dark:border-lex dark:bg-zinc-800/90 ${CHROME_INTERACTIVE_TILE_HOVER} ${CHROME_INTERACTIVE_TILE_HOVER_BG} dark:hover:bg-zinc-800`}
                      >
                        <div className="mb-2 flex flex-wrap gap-2">
                          <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-white">
                            {decision.date_str}
                          </span>
                          <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                            {decision.case_number}
                          </span>
                        </div>
                        <p className="line-clamp-2 text-sm font-bold text-slate-900 dark:text-white">{decision.title}</p>
                        <p className="mt-2 line-clamp-1 text-xs text-slate-500 dark:text-slate-400">
                          <Zap className="mr-1 inline h-3 w-3 text-amber-500" />
                          {decision.ponente}
                        </p>
                      </a>
                    ))}
                    <a
                      href={SC_DECISIONS_INDEX}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-600 py-3.5 text-xs font-black uppercase tracking-widest text-white shadow-lg shadow-indigo-600/25 transition hover:bg-indigo-500"
                    >
                      Full index <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 gap-tile sm:grid-cols-3 lg:grid-cols-1">
                {NEWS_LINKS.map((item) => {
                  const Icon = item.icon;
                  return (
                    <a
                      key={item.href}
                      href={item.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`group flex items-center gap-3 rounded-2xl border-2 border-lex bg-gradient-to-br p-4 shadow-md dark:border-lex ${item.accent} dark:from-zinc-800/80 dark:to-transparent ${CHROME_INTERACTIVE_TILE_HOVER}`}
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border-2 border-lex bg-white dark:border-lex dark:bg-zinc-800/80">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 text-left">
                        <p className="text-sm font-bold text-slate-900 dark:text-white">{item.label}</p>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">{item.desc}</p>
                      </div>
                      <ChevronRight className={CHROME_INTERACTIVE_CHEVRON} />
                    </a>
                  );
                })}
              </div>

              <div className="min-w-0 overflow-hidden rounded-lg border-2 border-lex bg-white shadow-xl dark:border-lex dark:bg-zinc-900">
                <div className="min-w-0 border-b-2 border-lex bg-gradient-to-br from-slate-900 to-slate-800 px-4 py-5 text-white sm:px-5 sm:py-6 dark:border-lex dark:from-slate-950 dark:to-black">
                  <div className="mb-2 flex items-center gap-2">
                    <Twitter className="h-5 w-5 text-sky-400" />
                    <h3 className="text-base font-bold">Social</h3>
                  </div>
                  <p className="text-xs text-slate-400">PIO on X · Facebook (iframes may be blocked by extensions)</p>
                  <div className="mt-4 grid grid-cols-2 gap-tile">
                    <a
                      href="https://x.com/SCPh_PIO"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-center gap-2 rounded-xl border border-slate-600/80 bg-slate-800/60 py-2.5 text-xs font-bold transition hover:bg-slate-700/80"
                    >
                      <Twitter className="h-4 w-4" /> X
                    </a>
                    <a
                      href="https://www.facebook.com/SupremeCourtPhilippines"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-center gap-2 rounded-xl border border-slate-600/80 bg-slate-800/60 py-2.5 text-xs font-bold transition hover:bg-slate-700/80"
                    >
                      <Facebook className="h-4 w-4" /> Meta
                    </a>
                  </div>
                </div>
                <div className="min-w-0 space-y-2 bg-slate-50/80 p-2 sm:p-3 dark:bg-slate-950/50">
                  <div
                    ref={twitterTimelineRef}
                    role="region"
                    aria-label="Supreme Court PIO posts on X"
                    className="min-h-[420px] w-full min-w-0 max-w-full overflow-x-auto overflow-y-hidden rounded-2xl border-2 border-lex bg-white dark:border-lex dark:bg-black"
                  >
                    <a
                      key={`${twitterPanelWidth}-${isDarkMode ? 'd' : 'l'}`}
                      className="twitter-timeline"
                      data-width={String(twitterPanelWidth)}
                      data-height="580"
                      data-theme={isDarkMode ? 'dark' : 'light'}
                      data-lang="en"
                      href="https://twitter.com/SCPh_PIO?ref_src=twsrc%5Etfw"
                    >
                      Posts by @SCPh_PIO
                    </a>
                  </div>
                  <div
                    ref={fbPluginHostRef}
                    className="w-full min-w-0 max-w-full overflow-hidden rounded-lg border border-lex bg-white dark:border-lex dark:bg-zinc-900"
                  >
                    <div className="sm:hidden border-b border-lex bg-gradient-to-r from-indigo-50 to-white p-4 dark:border-lex dark:from-indigo-950/50 dark:to-zinc-900">
                      <p className="text-xs font-semibold text-slate-800 dark:text-slate-100">Supreme Court on Facebook</p>
                      <p className="mt-1 text-[11px] leading-snug text-slate-600 dark:text-slate-400">
                        Embedded timelines often fail on mobile browsers (tracking protection). Open the official page
                        below—this always works.
                      </p>
                      <a
                        href="https://www.facebook.com/SupremeCourtPhilippines"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-[#1877F2] py-3 text-sm font-bold text-white shadow-md transition hover:bg-[#166FE5]"
                      >
                        <Facebook className="h-5 w-5 shrink-0" aria-hidden />
                        Open in Facebook
                      </a>
                    </div>
                    <iframe
                      key={fbIframeSrc}
                      title="Supreme Court of the Philippines on Facebook"
                      src={fbIframeSrc}
                      width="100%"
                      height={FB_PAGE_PLUGIN_HEIGHT}
                      frameBorder="0"
                      allowFullScreen={true}
                      loading="eager"
                      referrerPolicy="strict-origin-when-cross-origin"
                      allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
                      className="block w-full min-w-0 max-w-full border-0 align-top bg-white dark:bg-zinc-900"
                    />
                  </div>
                  <p className="text-center text-[10px] text-slate-500 dark:text-slate-500">
                    Desktop embed still blank? Set <code className="text-indigo-600 dark:text-indigo-400">VITE_FACEBOOK_APP_ID</code>{' '}
                    and add your site domain in the Meta app settings.
                  </p>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-lg border-2 border-amber-400/30 bg-gradient-to-br from-amber-500 via-amber-400 to-orange-500 p-6 text-white shadow-2xl">
                <div className="pointer-events-none absolute -right-8 -top-8 opacity-25">
                  <Zap className="h-24 w-24 rotate-12" />
                </div>
                <h4 className="relative text-lg font-bold">Instant alerts</h4>
                <p className="relative mt-1 text-sm font-medium text-amber-50/95">
                  Coming soon: notifications for Bar bulletins and doctrinal shifts.
                </p>
                <span className="relative mt-4 inline-block rounded-xl bg-white/95 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-amber-600 shadow">
                  Get notified
                </span>
              </div>
            </aside>
          </div>
        </div>
      </div>
    </FeaturePageShell>
  );
};

export default Updates;