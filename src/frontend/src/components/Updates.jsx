import React, { useEffect, useState } from 'react';
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
  Bookmark
} from 'lucide-react';
import FeaturePageShell from './FeaturePageShell';

const Updates = () => {
  const [latestDecisions, setLatestDecisions] = useState([]);
  const [loadingDecisions, setLoadingDecisions] = useState(true);

  useEffect(() => {
    // Load Twitter Widgets
    const script = document.createElement("script");
    script.src = "https://platform.twitter.com/widgets.js";
    script.async = true;
    document.body.appendChild(script);

    // Refresh widgets periodically to ensure they load in SPA
    const interval = setInterval(() => {
      if (window.twttr && window.twttr.widgets) {
        window.twttr.widgets.load();
      }
    }, 2000);

    // Fetch latest SC decisions
    fetch('/api/sc_decisions?limit=3')
      .then(res => res.json())
      .then(data => {
        if (data && data.data) {
          setLatestDecisions(data.data);
        }
        setLoadingDecisions(false);
      })
      .catch(err => {
        console.error("Error fetching decisions:", err);
        setLoadingDecisions(false);
      });

    return () => {
      clearInterval(interval);
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  const bar2026Updates = [
    { title: "Re: End of the Application for the 2026 Bar Examinations", date: "9 March 2026", type: "Notice", link: "https://sc.judiciary.gov.ph/re-end-of-the-application-for-the-2026-bar-examinations/" },
    { title: "Bar Bulletin No. 2: Application Requirements & Venue Selection", date: "8 Dec 2025", type: "Bulletin", link: "https://sc.judiciary.gov.ph/wp-content/uploads/2025/12/2026-BAR-Bar-Bulletin-No-2.pdf" },
    { title: "Bar Bulletin No. 1: Conduct, Schedule, & Syllabi", date: "16 Oct 2025", type: "Bulletin", link: "https://sc.judiciary.gov.ph/bar-2026/" },
    { title: "Frequently Asked Questions (FAQs)", date: "16 Dec 2025", type: "FAQ", link: "https://sc.judiciary.gov.ph/wp-content/uploads/2025/12/2026-BAR-FAQs-12-16-2025.pdf" }
  ];

  return (
    <FeaturePageShell
      icon={Newspaper}
      title="Updates"
      subtitle="SC news, Bar 2026 resources & social feeds"
    >
      <div className="animate-in fade-in space-y-12 pb-12 duration-700">
        {/* Bar 2026 Featured Section */}
        <section>
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
            <div>
              <h2 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                <Bookmark className="text-amber-500" size={32} />
                Bar 2026 <span className="text-amber-500">Special Section</span>
              </h2>
              <p className="text-slate-500 dark:text-slate-400 mt-1">Official alerts, bulletins, and candidate resources.</p>
            </div>
            <a 
              href="https://sc.judiciary.gov.ph/bar-2026/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="px-6 py-2.5 bg-white dark:bg-slate-800 text-slate-900 dark:text-white rounded-xl border border-slate-200 dark:border-slate-700 font-bold text-sm shadow-sm hover:shadow-md hover:bg-slate-50 dark:hover:bg-slate-700 transition-all flex items-center gap-2 group"
            >
              Access Portal <ExternalLink size={16} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
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
                <div className="absolute -right-4 -top-4 w-24 h-24 bg-amber-500/10 rounded-full blur-2xl group-hover:bg-amber-500/20 transition-colors"></div>
                
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-2 rounded-lg ${
                    update.type === 'Notice' ? 'bg-blue-500/10 text-blue-600' : 
                    update.type === 'Bulletin' ? 'bg-amber-500/10 text-amber-600' : 
                    'bg-purple-500/10 text-purple-600'
                  }`}>
                    {update.type === 'Notice' ? <Bell size={18} /> : update.type === 'Bulletin' ? <FileText size={18} /> : <Info size={18} />}
                  </div>
                  <span className="text-[10px] font-bold text-slate-400">{update.date}</span>
                </div>
                
                <h3 className="font-bold text-slate-900 dark:text-white text-sm line-clamp-3 leading-snug group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors mb-4">
                  {update.title}
                </h3>
                
                <div className="flex items-center text-xs font-bold text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 transition-colors uppercase tracking-widest gap-1">
                  View PDF <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
                </div>
              </a>
            ))}
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          {/* Main Content: Case Highlights & News */}
          <div className="lg:col-span-8 space-y-12">
            
            {/* Case Highlights Card */}
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
                    <p className="text-slate-500 dark:text-slate-400">Newly released jurisprudence from the En Banc & Divisions.</p>
                  </div>
                </div>
              </div>

              {loadingDecisions ? (
                <div className="space-y-6">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="h-40 bg-slate-100 dark:bg-slate-800/50 rounded-3xl animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="space-y-6">
                  {latestDecisions.map((decision) => (
                    <div 
                      key={decision.id}
                      onClick={() => window.location.hash = `#supreme_decisions`}
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
                            <span className="hidden md:flex items-center gap-2 opacity-60">
                              • {decision.division}
                            </span>
                          )}
                        </div>
                        <div className="p-2 bg-indigo-500/0 text-indigo-500 group-hover:bg-indigo-500/10 rounded-full transition-all">
                          <ChevronRight size={20} />
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  <button 
                    onClick={() => window.location.hash = '#supreme_decisions'}
                    className="w-full py-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-3xl font-black uppercase tracking-widest shadow-xl shadow-indigo-600/20 hover:shadow-indigo-600/40 hover:-translate-y-1 transition-all flex items-center justify-center gap-3"
                  >
                    View Jurisprudence Archive <Scale size={20} />
                  </button>
                </div>
              )}
            </div>

            {/* News & Bullets Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                { label: 'Judiciary News', desc: 'Latest press releases', icon: <Newspaper />, href: 'https://sc.judiciary.gov.ph/news/', color: 'blue' },
                { label: 'Bar Bulletins', desc: 'Official issuances', icon: <Scale />, href: 'https://sc.judiciary.gov.ph/bar-matters/', color: 'amber' },
                { label: 'BARISTA Portal', desc: 'Candidate login', icon: <ShieldCheck />, href: 'https://sc.judiciary.gov.ph/bar-2026/barista/', color: 'emerald' }
              ].map((item, i) => (
                <a 
                  key={i}
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="glass p-6 rounded-3xl border group transition-all duration-300 hover:-translate-y-1 hover:shadow-lg"
                >
                  <div className={`p-4 bg-${item.color}-500/10 text-${item.color}-500 rounded-2xl mb-4 group-hover:scale-110 transition-transform w-fit`}>
                    {item.icon}
                  </div>
                  <h4 className="font-bold text-slate-900 dark:text-white mb-1">{item.label}</h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">{item.desc}</p>
                  <div className={`text-[10px] font-black uppercase tracking-widest text-${item.color}-600 dark:text-${item.color}-400 flex items-center gap-2`}>
                    Browse <ExternalLink size={12} />
                  </div>
                </a>
              ))}
            </div>
          </div>

          {/* Sidebar: Social Media & Widgets */}
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
                  <a href="https://x.com/SCPh_PIO" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 py-3 bg-white/10 hover:bg-white/20 rounded-2xl border border-white/10 transition-colors text-sm font-bold">
                    <Twitter size={16} /> Official X
                  </a>
                  <a href="https://www.facebook.com/SupremeCourtPhilippines" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 py-3 bg-white/10 hover:bg-white/20 rounded-2xl border border-white/10 transition-colors text-sm font-bold">
                    <Facebook size={16} /> Facebook
                  </a>
                </div>
              </div>
              
              <div className="bg-slate-50 dark:bg-[#0d1117] p-4 relative">
                {/* X/Twitter embedded timeline via official publish widget */}
                <div id="twitter-container" className="scrollbar-hide">
                  <a
                    className="twitter-timeline"
                    data-height="580"
                    data-theme={document.documentElement.classList.contains('dark') ? 'dark' : 'light'}
                    data-chrome="noheader nofooter noborders transparent"
                    href="https://twitter.com/SCPh_PIO"
                  >
                    {/* Fallback shown while widget loads or if blocked */}
                    <div className="flex flex-col items-center justify-center py-16 gap-5 text-slate-400">
                      <Twitter size={40} className="text-sky-500 opacity-60" />
                      <p className="text-sm font-semibold text-slate-500">Loading SC PIO feed…</p>
                      <a
                        href="https://x.com/SCPh_PIO"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-white text-sm font-bold transition-all shadow-lg shadow-sky-500/30 hover:scale-105"
                      >
                        <ExternalLink size={14} /> View on X
                      </a>
                    </div>
                  </a>
                </div>

                {/* Facebook embed */}
                <div className="mt-6">
                  <iframe
                    src="https://www.facebook.com/plugins/page.php?href=https%3A%2F%2Fwww.facebook.com%2FSupremeCourtPhilippines&tabs=timeline&width=340&height=500&small_header=true&adapt_container_width=true&hide_cover=false&show_facepile=false&appId"
                    width="100%"
                    height="500"
                    style={{ border: 'none', overflow: 'hidden', borderRadius: '16px' }}
                    scrolling="no"
                    frameBorder="0"
                    allowFullScreen={true}
                    allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
                    title="Supreme Court Philippines Facebook"
                  ></iframe>
                </div>
              </div>
            </div>

            {/* Newsletter/Alert Suggestion */}
            <div className="p-8 bg-amber-500 rounded-[2.5rem] text-white relative overflow-hidden shadow-2xl animate-float">
              <div className="absolute top-0 right-0 p-6 opacity-20 -rotate-12">
                <Zap size={100} />
              </div>
              <h4 className="text-xl font-bold mb-2">Want Instant Alerts?</h4>
              <p className="text-amber-100 text-sm mb-6 font-medium">Coming soon: Smart notifications for Bar bulletins and doctrinal shifts.</p>
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
