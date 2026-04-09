import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Twitter,
  Facebook,
  ExternalLink,
  Bell,
  Scale,
  FileText,
  Newspaper,
  ChevronRight,
  Info,
  ShieldCheck,
  Zap,
  Bookmark,
  Rss
} from 'lucide-react';
import FeaturePageShell from './FeaturePageShell';
import { apiUrl } from '../utils/apiUrl';

const TWITTER_WIDGET_SRC = 'https://platform.twitter.com/widgets.js';
const TWITTER_WIDGET_ID = 'twitter-wjs';

const NEWS_LINKS = [
  {
    label: 'Judiciary News',
    desc: 'Latest press releases',
    icon: Newspaper,
    href: 'https://sc.judiciary.gov.ph/news/',
    iconWrapClass:
      'p-4 bg-blue-500/10 text-blue-600 rounded-2xl mb-4 group-hover:scale-110 transition-transform w-fit',
    ctaClass:
      'text-[10px] font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 flex items-center gap-2'
  },
  {
    label: 'Bar Bulletins',
    desc: 'Official issuances',
    icon: Scale,
    href: 'https://sc.judiciary.gov.ph/bar-matters/',
    iconWrapClass:
      'p-4 bg-amber-500/10 text-amber-600 rounded-2xl mb-4 group-hover:scale-110 transition-transform w-fit',
    ctaClass:
      'text-[10px] font-black uppercase tracking-widest text-amber-600 dark:text-amber-400 flex items-center gap-2'
  },
  {
    label: 'BARISTA Portal',
    desc: 'Candidate login',
    icon: ShieldCheck,
    href: 'https://sc.judiciary.gov.ph/bar-2026/barista/',
    iconWrapClass:
      'p-4 bg-emerald-500/10 text-emerald-600 rounded-2xl mb-4 group-hover:scale-110 transition-transform w-fit',
    ctaClass:
      'text-[10px] font-black uppercase tracking-widest text-emerald-600 dark:text-emerald-400 flex items-center gap-2'
  }
];

function buildFacebookPagePluginSrc() {
  const base = 'https://www.facebook.com/plugins/page.php';
  const params = new URLSearchParams({
    href: 'https://www.facebook.com/SupremeCourtPhilippines',
    tabs: 'timeline',
    width: '340',
    height: '500',
    small_header: 'true',
    adapt_container_width: 'true',
    hide_cover: 'false',
    show_facepile: 'false'
  });
  const appId = import.meta.env.VITE_FACEBOOK_APP_ID;
  if (appId) params.set('appId', String(appId));
  return `${base}?${params.toString()}`;
}

const Updates = ({ onOpenSupremeDecisions, isDarkMode = false }) => {
  const [latestDecisions, setLatestDecisions] = useState([]);
  const [loadingDecisions, setLoadingDecisions] = useState(true);
  const [feedItems, setFeedItems] = useState([]);
  const [barFeedItems, setBarFeedItems] = useState([]);
  const [feedLoading, setFeedLoading] = useState(true);
  const [feedError, setFeedError] = useState(null);

  const twitterWrapRef = useRef(null);
  const fbIframeSrc = useMemo(() => buildFacebookPagePluginSrc(), []);

  useEffect(() => {
    let cancelled = false;
    setFeedLoading(true);
    setFeedError(null);
    fetch(apiUrl('/api/sc_judiciary_feed?limit=10&include_bar=1&bar_limit=8'))
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return;
        if (data?.error && (!data.items || data.items.length === 0)) {
          setFeedError(data.error);
          setFeedItems([]);
          setBarFeedItems([]);
        } else {
          setFeedItems(Array.isArray(data?.items) ? data.items : []);
          setBarFeedItems(Array.isArray(data?.bar_items) ? data.bar_items : []);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFeedError('network');
          setFeedItems([]);
          setBarFeedItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) setFeedLoading(false);
      });
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
        console.error('Error fetching decisions:', err);
        setLoadingDecisions(false);
      });
  }, []);

  useEffect(() => {
    const container = twitterWrapRef.current;
    if (!container) return;

    const applyTheme = () => {
      const anchor = container.querySelector('a.twitter-timeline');
      if (anchor) {
        anchor.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
      }
    };

    const loadWidgets = () => {
      applyTheme();
      if (window.twttr?.widgets?.load) {
        try {
          window.twttr.widgets.load(container);
        } catch (e) {
          console.warn('Twitter widgets.load failed:', e);
        }
      }
    };

    applyTheme();

    const existing = document.getElementById(TWITTER_WIDGET_ID);
    if (window.twttr?.widgets) {
      loadWidgets();
      return undefined;
    }

    if (existing) {
      existing.addEventListener('load', loadWidgets);
      return () => existing.removeEventListener('load', loadWidgets);
    }

    const script = document.createElement('script');
    script.id = TWITTER_WIDGET_ID;
    script.src = TWITTER_WIDGET_SRC;
    script.async = true;
    script.charset = 'utf-8';
    script.onload = loadWidgets;
    document.body.appendChild(script);

    return () => {
      script.onload = null;
    };
  }, [isDarkMode]);

  const bar2026Updates = [
    {
      title: 'Re: End of the Application for the 2026 Bar Examinations',
      date: '9 March 2026',
      type: 'Notice',
      link: 'https://sc.judiciary.gov.ph/re-end-of-the-application-for-the-2026-bar-examinations/',
      cta: 'Read notice'
    },
    {
      title: 'Bar Bulletin No. 2: Application Requirements & Venue Selection',
      date: '8 Dec 2025',
      type: 'Bulletin',
      link: 'https://sc.judiciary.gov.ph/wp-content/uploads/2025/12/2026-BAR-Bar-Bulletin-No-2.pdf',
      cta: 'View PDF'
    },
    {
      title: 'Bar Bulletin No. 1: Conduct, Schedule, & Syllabi',
      date: '16 Oct 2025',
      type: 'Bulletin',
      link: 'https://sc.judiciary.gov.ph/bar-2026/',
      cta: 'Open portal'
    },
    {
      title: 'Frequently Asked Questions (FAQs)',
      date: '16 Dec 2025',
      type: 'FAQ',
      link: 'https://sc.judiciary.gov.ph/wp-content/uploads/2025/12/2026-BAR-FAQs-12-16-2025.pdf',
      cta: 'View PDF'
    }
  ];

  const openArchive = () => {
    if (typeof onOpenSupremeDecisions === 'function') {
      onOpenSupremeDecisions();
    }
  };

  return (
    <FeaturePageShell
      icon={Newspaper}
      title="Updates"
      subtitle="SC news, Bar 2026 resources & social feeds"
    >
      <div className="animate-in fade-in space-y-12 pb-12 duration-700">
        {/* Live feed from official RSS (refreshed on the server on a short TTL) */}
        <section>
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
            <div>
              <h2 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                <Rss className="text-sky-500" size={32} />
                Latest from <span className="text-sky-500">sc.judiciary.gov.ph</span>
              </h2>
              <p className="text-slate-500 dark:text-slate-400 mt-1">
                Pulled from the Court&apos;s public RSS feed — updates when they publish new posts.
              </p>
            </div>
            <a
              href="https://sc.judiciary.gov.ph/feed/"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-2.5 bg-white dark:bg-slate-800 text-slate-900 dark:text-white rounded-xl border border-slate-200 dark:border-slate-700 font-bold text-sm shadow-sm hover:shadow-md hover:bg-slate-50 dark:hover:bg-slate-700 transition-all flex items-center gap-2 group"
            >
              RSS source <ExternalLink size={16} className="opacity-70" />
            </a>
          </div>

          {feedLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-28 bg-slate-100 dark:bg-slate-800/50 rounded-2xl animate-pulse" />
              ))}
            </div>
          ) : feedError && feedItems.length === 0 ? (
            <div className="glass rounded-2xl border p-8 text-center text-slate-600 dark:text-slate-400">
              <p className="font-semibold mb-2">Could not load the live feed right now.</p>
              <p className="text-sm mb-4">You can still open the site or RSS directly.</p>
              <a
                href="https://sc.judiciary.gov.ph/news/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sky-600 dark:text-sky-400 font-bold text-sm"
              >
                Open Judiciary News <ExternalLink size={14} />
              </a>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {feedItems.map((item, idx) => (
                <a
                  key={`${item.link}-${idx}`}
                  href={item.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="glass group relative p-5 rounded-2xl border transition-all duration-300 hover:-translate-y-1 hover:shadow-lg overflow-hidden text-left"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider shrink-0">
                      {item.pub_date || '—'}
                    </span>
                    {item.categories?.[0] && (
                      <span className="text-[10px] font-bold text-sky-600/80 dark:text-sky-400/90 truncate max-w-[50%]">
                        {item.categories[0]}
                      </span>
                    )}
                  </div>
                  <h3 className="font-bold text-slate-900 dark:text-white text-sm line-clamp-2 leading-snug group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
                    {item.title}
                  </h3>
                  {item.snippet && (
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">{item.snippet}</p>
                  )}
                  <div className="mt-3 flex items-center text-xs font-bold text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 gap-1">
                    Read on SC site <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
                  </div>
                </a>
              ))}
            </div>
          )}

          {!feedLoading && barFeedItems.length > 0 && (
            <div className="mt-10 pt-10 border-t border-slate-200/80 dark:border-slate-700/80">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
                <Scale className="text-amber-500 shrink-0" size={22} />
                Bar examination headlines
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Same RSS feed, filtered for Bar-related posts (bulletins, candidates, exams).
              </p>
              <div className="flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory scrollbar-hide">
                {barFeedItems.map((item, idx) => (
                  <a
                    key={`bar-${item.link}-${idx}`}
                    href={item.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="snap-start shrink-0 w-[min(100%,280px)] glass p-4 rounded-2xl border transition-all hover:border-amber-400/40 hover:shadow-md text-left"
                  >
                    <p className="text-[10px] font-bold text-slate-400 mb-2 line-clamp-1">{item.pub_date}</p>
                    <p className="text-sm font-bold text-slate-900 dark:text-white line-clamp-3 leading-snug">
                      {item.title}
                    </p>
                    <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-amber-600 dark:text-amber-400">
                      Open <ChevronRight size={12} />
                    </span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Bar 2026 Featured Section */}
        <section>
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
            <div>
              <h2 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                <Bookmark className="text-amber-500" size={32} />
                Bar 2026 <span className="text-amber-500">Special Section</span>
              </h2>
              <p className="text-slate-500 dark:text-slate-400 mt-1">
                Official alerts, bulletins, and candidate resources.
              </p>
            </div>
            <a
              href="https://sc.judiciary.gov.ph/bar-2026/"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-2.5 bg-white dark:bg-slate-800 text-slate-900 dark:text-white rounded-xl border border-slate-200 dark:border-slate-700 font-bold text-sm shadow-sm hover:shadow-md hover:bg-slate-50 dark:hover:bg-slate-700 transition-all flex items-center gap-2 group"
            >
              Access Portal{' '}
              <ExternalLink size={16} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </a>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {bar2026Updates.map((update, idx) => (
              <a
                key={idx}
                href={update.link}
                target="_blank"
                rel="noopener noreferrer"
                className="glass group relative p-6 rounded-2xl border transition-all duration-500 hover:-translate-y-2 hover:shadow-[0_20px_50px_rgba(0,0,0,0.1)] dark:hover:shadow-[0_20px_50px_rgba(255,255,255,0.05)] overflow-hidden"
              >
                <div className="absolute -right-4 -top-4 w-24 h-24 bg-amber-500/10 rounded-full blur-2xl group-hover:bg-amber-500/20 transition-colors" />

                <div className="flex items-center justify-between mb-4">
                  <div
                    className={`p-2 rounded-lg ${
                      update.type === 'Notice'
                        ? 'bg-blue-500/10 text-blue-600'
                        : update.type === 'Bulletin'
                          ? 'bg-amber-500/10 text-amber-600'
                          : 'bg-purple-500/10 text-purple-600'
                    }`}
                  >
                    {update.type === 'Notice' ? (
                      <Bell size={18} />
                    ) : update.type === 'Bulletin' ? (
                      <FileText size={18} />
                    ) : (
                      <Info size={18} />
                    )}
                  </div>
                  <span className="text-[10px] font-bold text-slate-400">{update.date}</span>
                </div>

                <h3 className="font-bold text-slate-900 dark:text-white text-sm line-clamp-3 leading-snug group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors mb-4">
                  {update.title}
                </h3>

                <div className="flex items-center text-xs font-bold text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 transition-colors uppercase tracking-widest gap-1">
                  {update.cta} <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
                </div>
              </a>
            ))}
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          <div className="lg:col-span-8 space-y-12">
            <div className="glass rounded-[2.5rem] p-8 md:p-10 shadow-xl border-white/50 dark:border-white/5 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-10 opacity-5 rotate-12 pointer-events-none">
                <Scale size={200} />
              </div>

              <div className="flex items-center justify-between mb-10">
                <div className="flex items-center gap-4">
                  <div className="p-4 bg-indigo-500 text-white rounded-2xl shadow-lg shadow-indigo-500/30">
                    <Scale size={28} />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-slate-900 dark:text-white">Supreme Decision Highlights</h3>
                    <p className="text-slate-500 dark:text-slate-400">
                      Newly released jurisprudence from the En Banc & Divisions.
                    </p>
                  </div>
                </div>
              </div>

              {loadingDecisions ? (
                <div className="space-y-6">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-40 bg-slate-100 dark:bg-slate-800/50 rounded-3xl animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="space-y-6">
                  {latestDecisions.map((decision) => (
                    <div
                      key={decision.id}
                      role="button"
                      tabIndex={0}
                      onClick={openArchive}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          openArchive();
                        }
                      }}
                      className="group p-8 bg-white/40 dark:bg-slate-800/20 backdrop-blur-sm rounded-3xl border border-white/60 dark:border-white/5 hover:bg-white dark:hover:bg-slate-800/40 hover:scale-[1.01] hover:shadow-xl transition-all duration-300 cursor-pointer"
                    >
                      <div className="flex flex-wrap items-center gap-3 mb-4">
                        <span className="px-3 py-1 bg-indigo-500 text-white text-[10px] font-black uppercase tracking-[0.2em] rounded-full">
                          {decision.date_str}
                        </span>
                        <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">
                          {decision.case_number}
                        </span>
                      </div>

                      <h4 className="text-xl font-bold text-slate-900 dark:text-white mb-4 leading-tight group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                        {decision.title}
                      </h4>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400 font-semibold">
                          <span className="flex items-center gap-2 italic">
                            <Zap size={14} className="text-amber-500" /> {decision.ponente}
                          </span>
                          {decision.division && (
                            <span className="hidden md:flex items-center gap-2 opacity-60">• {decision.division}</span>
                          )}
                        </div>
                        <div className="p-2 bg-indigo-500/0 text-indigo-500 group-hover:bg-indigo-500/10 rounded-full transition-all">
                          <ChevronRight size={20} />
                        </div>
                      </div>
                    </div>
                  ))}

                  <button
                    type="button"
                    onClick={openArchive}
                    className="w-full py-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-3xl font-black uppercase tracking-widest shadow-xl shadow-indigo-600/20 hover:shadow-indigo-600/40 hover:-translate-y-1 transition-all flex items-center justify-center gap-3"
                  >
                    View Jurisprudence Archive <Scale size={20} />
                  </button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {NEWS_LINKS.map((item) => {
                const Icon = item.icon;
                return (
                  <a
                    key={item.href}
                    href={item.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="glass p-6 rounded-3xl border group transition-all duration-300 hover:-translate-y-1 hover:shadow-lg"
                  >
                    <div className={item.iconWrapClass}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <h4 className="font-bold text-slate-900 dark:text-white mb-1">{item.label}</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">{item.desc}</p>
                    <div className={item.ctaClass}>
                      Browse <ExternalLink size={12} />
                    </div>
                  </a>
                );
              })}
            </div>
          </div>

          <div className="lg:col-span-4 space-y-8">
            <div className="glass rounded-[2.5rem] overflow-hidden shadow-xl border-white/50 dark:border-white/5">
              <div className="p-8 bg-gradient-to-br from-slate-900 to-slate-800 dark:from-slate-900 dark:to-black text-white">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 bg-white/10 rounded-lg">
                    <Twitter size={24} className="text-sky-400" />
                  </div>
                  <h3 className="text-xl font-bold">Social Intelligence</h3>
                </div>
                <p className="text-slate-400 text-sm mb-8">Follow official real-time updates from the Supreme Court PIO.</p>
                <div className="grid grid-cols-2 gap-4">
                  <a
                    href="https://x.com/SCPh_PIO"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 py-3 bg-white/10 hover:bg-white/20 rounded-2xl border border-white/10 transition-colors text-sm font-bold"
                  >
                    <Twitter size={16} /> Official X
                  </a>
                  <a
                    href="https://www.facebook.com/SupremeCourtPhilippines"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 py-3 bg-white/10 hover:bg-white/20 rounded-2xl border border-white/10 transition-colors text-sm font-bold"
                  >
                    <Facebook size={16} /> Facebook
                  </a>
                </div>
              </div>

              <div className="bg-slate-50 dark:bg-[#0d1117] p-4 relative">
                <div
                  id="twitter-timeline-host"
                  ref={twitterWrapRef}
                  className="scrollbar-hide min-h-[400px]"
                >
                  <a
                    className="twitter-timeline"
                    data-height="580"
                    data-theme={isDarkMode ? 'dark' : 'light'}
                    data-chrome="noheader nofooter noborders transparent"
                    href="https://twitter.com/SCPh_PIO"
                  >
                    Tweets by @SCPh_PIO
                  </a>
                </div>
                <p className="text-center text-xs text-slate-500 dark:text-slate-400 mt-3 px-2">
                  If the timeline does not appear (blocked third-party scripts or login walls), use{' '}
                  <a href="https://x.com/SCPh_PIO" target="_blank" rel="noopener noreferrer" className="text-sky-500 font-semibold">
                    Official X
                  </a>
                  .
                </p>

                <div className="mt-6">
                  <iframe
                    src={fbIframeSrc}
                    width="100%"
                    height="500"
                    style={{ border: 'none', overflow: 'hidden', borderRadius: '16px' }}
                    scrolling="no"
                    frameBorder="0"
                    allowFullScreen={true}
                    loading="lazy"
                    allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
                    title="Supreme Court Philippines Facebook"
                  />
                </div>
              </div>
            </div>

            <div className="p-8 bg-amber-500 rounded-[2.5rem] text-white relative overflow-hidden shadow-2xl animate-float">
              <div className="absolute top-0 right-0 p-6 opacity-20 -rotate-12">
                <Zap size={100} />
              </div>
              <h4 className="text-xl font-bold mb-2">Want Instant Alerts?</h4>
              <p className="text-amber-100 text-sm mb-6 font-medium">
                Coming soon: Smart notifications for Bar bulletins and doctrinal shifts.
              </p>
              <div className="flex items-center gap-3">
                <div className="px-5 py-2.5 bg-white text-amber-600 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg">
                  Get Notified
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </FeaturePageShell>
  );
};

export default Updates;
