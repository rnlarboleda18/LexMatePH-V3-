import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Scale, Globe, Briefcase, FileText, Users, Sword, BookOpen,
  ChevronRight, ChevronDown, ChevronLeft, BookMarked, Brain, AlertTriangle,
  Gavel, Lightbulb, Star, Clock, CheckCircle2, Circle,
  ExternalLink, Tag, AlertCircle,
} from 'lucide-react';
import PurpleGlassAmbient from './PurpleGlassAmbient';
import CardVioletInnerWash from './CardVioletInnerWash';
import { apiUrl } from '../utils/apiUrl';

// ── Subject definitions ────────────────────────────────────────────────────────

const SUBJECTS = [
  { id: 'political',  label: 'Political & PIL',    fullLabel: 'Political and Public International Law',      weight: '15%', icon: Globe,     color: 'text-blue-600 dark:text-blue-400',    bgActive: 'border-blue-600 dark:border-blue-400 text-blue-700 dark:text-blue-300' },
  { id: 'commercial', label: 'Commercial & Tax',   fullLabel: 'Commercial and Taxation Laws',                weight: '20%', icon: Briefcase, color: 'text-emerald-600 dark:text-emerald-400', bgActive: 'border-emerald-600 dark:border-emerald-400 text-emerald-700 dark:text-emerald-300' },
  { id: 'civil',      label: 'Civil Law & Land',   fullLabel: 'Civil Law and Land Titles and Deeds',         weight: '20%', icon: FileText,  color: 'text-violet-600 dark:text-violet-400',  bgActive: 'border-violet-600 dark:border-violet-400 text-violet-700 dark:text-violet-300' },
  { id: 'labor',      label: 'Labor & Social',     fullLabel: 'Labor Law and Social Legislation',            weight: '10%', icon: Users,     color: 'text-amber-600 dark:text-amber-400',    bgActive: 'border-amber-600 dark:border-amber-400 text-amber-700 dark:text-amber-300' },
  { id: 'criminal',   label: 'Criminal Law',       fullLabel: 'Criminal Law',                                weight: '10%', icon: Sword,     color: 'text-rose-600 dark:text-rose-400',      bgActive: 'border-rose-600 dark:border-rose-400 text-rose-700 dark:text-rose-300' },
  { id: 'remedial',   label: 'Remedial & Ethics',  fullLabel: 'Remedial Law, Legal and Judicial Ethics',     weight: '25%', icon: BookOpen,  color: 'text-indigo-600 dark:text-indigo-400',  bgActive: 'border-indigo-600 dark:border-indigo-400 text-indigo-700 dark:text-indigo-300' },
];

const EXAM_DATE = 'September 6, 9 & 13, 2026';

// ── Confidence badge ───────────────────────────────────────────────────────────

const CONFIDENCE_STYLES = {
  'db-sourced':       'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  'search-grounded':  'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  'ai-synthesized':   'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
};
const CONFIDENCE_LABELS = {
  'db-sourced':       'DB-sourced',
  'search-grounded':  'Search-grounded',
  'ai-synthesized':   'AI-synthesized',
};

function ConfidenceBadge({ value }) {
  if (!value) return null;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${CONFIDENCE_STYLES[value] ?? 'bg-gray-100 text-gray-600'}`}>
      <CheckCircle2 size={9} />
      {CONFIDENCE_LABELS[value] ?? value}
    </span>
  );
}

// ── Key Provisions list ────────────────────────────────────────────────────────

function ProvisionList({ provisions }) {
  if (!provisions?.length) return null;
  return (
    <div className="space-y-2">
      {provisions.map((p, i) => (
        <div key={i} className="rounded-lg border border-lex bg-white/40 px-3 py-2.5 dark:bg-zinc-800/40">
          <div className="flex items-start gap-2">
            <BookMarked size={13} className="mt-0.5 shrink-0 text-violet-500" />
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">{p.label}</p>
              {p.text && (
                <p className="mt-1 text-xs leading-relaxed text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                  {p.text.length > 600 ? p.text.slice(0, 600) + '…' : p.text}
                </p>
              )}
              {p.source_url && (
                <a
                  href={p.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 inline-flex items-center gap-1 text-[10px] text-violet-500 hover:underline"
                >
                  <ExternalLink size={9} />
                  Source
                </a>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Case card ─────────────────────────────────────────────────────────────────

function CaseCard({ c, onCaseClick }) {
  const isEnBanc = c.division === 'En Banc';
  return (
    <div
      className="group cursor-pointer rounded-lg border border-lex bg-white/40 px-3 py-2.5 transition-colors hover:bg-white/70 dark:bg-zinc-800/40 dark:hover:bg-zinc-800/70"
      onClick={() => onCaseClick?.(c)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            {isEnBanc && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-rose-100 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-rose-700 dark:bg-rose-900/40 dark:text-rose-300">
                <Star size={8} /> En Banc
              </span>
            )}
            {c.significance_category && c.significance_category !== 'ORDINARY' && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-100 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                <Lightbulb size={8} /> {c.significance_category}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-sm font-semibold text-gray-800 group-hover:text-violet-700 dark:text-gray-100 dark:group-hover:text-violet-300">
            {c.short_title || c.gr_number}
          </p>
          {c.gr_number && (
            <p className="text-[11px] text-gray-400 dark:text-gray-500">
              {c.gr_number}{c.date ? ` · ${c.date?.slice(0, 10)}` : ''}
              {c.ponente ? ` · J. ${c.ponente}` : ''}
            </p>
          )}
        </div>
        <ChevronRight size={14} className="mt-1 shrink-0 text-gray-300 group-hover:text-violet-400" />
      </div>
      {c.main_doctrine && (
        <p className="mt-1.5 text-xs leading-relaxed text-gray-600 dark:text-gray-300 line-clamp-3">
          {c.main_doctrine}
        </p>
      )}
      {c.bar_trap && (
        <div className="mt-1.5 flex items-start gap-1 rounded bg-rose-50 px-2 py-1 dark:bg-rose-900/20">
          <AlertTriangle size={10} className="mt-0.5 shrink-0 text-rose-500" />
          <p className="text-[11px] text-rose-700 dark:text-rose-300">{c.bar_trap}</p>
        </div>
      )}
      {c.separate_opinions?.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {c.separate_opinions.map((op, i) => (
            <span key={i} className="inline-flex items-center gap-0.5 rounded-full border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[9px] font-medium text-indigo-700 dark:border-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
              {op.cited_in_syllabus && <span className="font-bold">[SYLLABUS] </span>}
              {op.type}: J. {op.justice}
            </span>
          ))}
        </div>
      )}
      {c.connector && (
        <p className="mt-1.5 text-[11px] italic text-indigo-600 dark:text-indigo-400">{c.connector}</p>
      )}
    </div>
  );
}

// ── Bar Questions ─────────────────────────────────────────────────────────────

function parseBarQuestion(q) {
  // Separate question from answer — handle synthetic questions where AI packed
  // both into the text field with a "SUGGESTED ANSWER:" separator.
  let questionText = q.text || '';
  let answerText   = q.answer || null;
  if (!answerText) {
    const sepIdx = questionText.toUpperCase().indexOf('SUGGESTED ANSWER:');
    if (sepIdx !== -1) {
      answerText   = questionText.slice(sepIdx).trim();
      questionText = questionText.slice(0, sepIdx).trim();
    }
  }
  return { questionText, answerText };
}

function BarQuestions({ questions }) {
  const [open, setOpen] = useState(null);
  if (!questions?.length) return null;
  const isSynthetic = (q) => String(q.year || '').toLowerCase().includes('synthetic') || q.institution === 'AI-generated';
  return (
    <div className="space-y-2">
      {questions.map((q, i) => {
        const { questionText, answerText } = parseBarQuestion(q);
        const synthetic = isSynthetic(q);
        return (
          <div key={i} className="overflow-hidden rounded-lg border border-lex bg-white/40 dark:bg-zinc-800/40">
            <button
              className="flex w-full items-start justify-between gap-2 px-3 py-3 text-left"
              onClick={() => setOpen(open === i ? null : i)}
            >
              <div className="min-w-0 flex-1">
                <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                  {q.year && (
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${synthetic ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300' : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'}`}>
                      {q.year}
                    </span>
                  )}
                  {synthetic && (
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:bg-zinc-700 dark:text-gray-400">
                      AI-Generated
                    </span>
                  )}
                  {!synthetic && q.institution && (
                    <span className="text-[10px] text-gray-400 dark:text-gray-500">{q.institution}</span>
                  )}
                </div>
                <p className="text-sm leading-relaxed text-gray-800 dark:text-gray-100">{questionText}</p>
              </div>
              <div className="mt-0.5 shrink-0">
                {open === i
                  ? <ChevronDown size={14} className="text-gray-400" />
                  : <ChevronRight size={14} className="text-gray-400" />}
              </div>
            </button>
            {open === i && answerText && (
              <div className="border-t border-lex bg-gray-50/60 px-3 py-3 dark:bg-zinc-900/40">
                <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-violet-600 dark:text-violet-400">Suggested Answer</p>
                <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-200">
                  <ReactMarkdown>
                    {answerText.replace(/^SUGGESTED ANSWER:\s*/i, '')}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Content panel ─────────────────────────────────────────────────────────────

function ContentPanel({ subject, topic, onCaseClick }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!topic) { setDetail(null); return; }
    setLoading(true);
    setError(null);
    fetch(apiUrl(`/api/reviewer/${subject}/${topic.id}`))
      .then(r => r.json())
      .then(d => { setDetail(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [subject, topic?.id]);

  if (!topic) {
    return (
      <div className="flex h-full min-h-[300px] items-center justify-center rounded-xl border border-lex bg-white/60 p-8 text-center dark:bg-zinc-900/60">
        <div>
          <BookOpen size={32} className="mx-auto mb-3 text-gray-300 dark:text-gray-600" />
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Select a topic to start reviewing</p>
        </div>
      </div>
    );
  }

  const data = detail ?? topic;
  const isEmpty = !data.doctrine_md && !data.distinctions_md && !data.memory_aid
               && !data.key_provisions?.length && !data.key_cases?.length;

  return (
    <div className="relative min-w-0 overflow-hidden rounded-xl border border-lex bg-white shadow-sm dark:bg-zinc-900">
      <div className="pointer-events-none absolute inset-0"><CardVioletInnerWash /></div>
      <div className="relative z-[1]">

        {/* Topic header */}
        <div className="border-b border-lex px-5 py-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                {topic.roman_num}{topic.sub_letter ? `.${topic.sub_letter}` : ''}
              </p>
              <h2 className="text-base font-black tracking-tight text-gray-900 dark:text-white sm:text-lg">
                {topic.topic_heading}
              </h2>
              {topic.sub_heading && (
                <p className="mt-0.5 text-sm font-medium text-gray-500 dark:text-gray-400">{topic.sub_heading}</p>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <ConfidenceBadge value={data.confidence} />
              {data.status === 'draft' && (
                <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-gray-500 dark:bg-zinc-700 dark:text-gray-400">
                  <Circle size={8} /> Draft
                </span>
              )}
            </div>
          </div>
        </div>

        {loading && (
          <div className="px-5 py-8 text-center text-sm text-gray-400">Loading…</div>
        )}
        {error && (
          <div className="px-5 py-4 text-sm text-rose-600 dark:text-rose-400">Error: {error}</div>
        )}

        {!loading && isEmpty && (
          <div className="px-5 py-8 text-center">
            <Clock size={28} className="mx-auto mb-2 text-gray-300 dark:text-gray-600" />
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Content being prepared</p>
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">This topic's reviewer material is being generated.</p>
          </div>
        )}

        {!loading && !isEmpty && (
          <div className="space-y-6 px-5 py-5">

            {/* Key Provisions */}
            {data.key_provisions?.length > 0 && (
              <section>
                <SectionHeader icon={BookMarked} label="Key Provisions" />
                <ProvisionList provisions={data.key_provisions} />
              </section>
            )}

            {/* Doctrine */}
            {data.doctrine_md && (
              <section>
                <SectionHeader icon={Scale} label="Doctrine & Discussion" />
                <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-200 leading-relaxed">
                  <ReactMarkdown>{data.doctrine_md}</ReactMarkdown>
                </div>
              </section>
            )}

            {/* Distinctions */}
            {data.distinctions_md && (
              <section>
                <SectionHeader icon={AlertTriangle} label="Key Distinctions & Bar Traps" color="text-rose-500" />
                <div className="rounded-lg border border-rose-200 bg-rose-50/60 p-4 dark:border-rose-800/50 dark:bg-rose-900/10">
                  <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-200">
                    <ReactMarkdown>{data.distinctions_md}</ReactMarkdown>
                  </div>
                </div>
              </section>
            )}

            {/* Memory Aid */}
            {data.memory_aid && (
              <section>
                <SectionHeader icon={Brain} label="Memory Aid" color="text-indigo-500" />
                <div className="rounded-lg border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-800/50 dark:bg-indigo-900/10">
                  <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-200">
                    <ReactMarkdown>{data.memory_aid}</ReactMarkdown>
                  </div>
                </div>
              </section>
            )}

            {/* Key Cases */}
            {data.key_cases?.length > 0 && (
              <section>
                <SectionHeader icon={Gavel} label={`Key Cases (${data.key_cases.length})`} />
                <div className="space-y-2">
                  {data.key_cases.map((c, i) => (
                    <CaseCard key={c.id ?? c.gr_number ?? i} c={c} onCaseClick={onCaseClick} />
                  ))}
                </div>
              </section>
            )}

            {/* Bar Questions */}
            {data.bar_questions?.length > 0 && (
              <section>
                <SectionHeader icon={AlertCircle} label={`Past Bar Questions (${data.bar_questions.length})`} color="text-amber-500" />
                <BarQuestions questions={data.bar_questions} />
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ icon: Icon, label, color = 'text-violet-500' }) {
  return (
    <div className="mb-2.5 flex items-center gap-2">
      <Icon size={14} className={color} />
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">{label}</h3>
    </div>
  );
}

// ── Topic tree ─────────────────────────────────────────────────────────────────

function TopicTree({ topics, selectedId, onSelect, subjectColor }) {
  // Group by roman_num
  const groups = topics.reduce((acc, t) => {
    if (!acc[t.roman_num]) acc[t.roman_num] = { heading: t.topic_heading, items: [] };
    acc[t.roman_num].items.push(t);
    return acc;
  }, {});

  const [collapsed, setCollapsed] = useState({});

  const toggle = (roman) => setCollapsed(c => ({ ...c, [roman]: !c[roman] }));

  if (!topics.length) {
    return (
      <div className="px-3 py-6 text-center text-xs text-gray-400 dark:text-gray-500">
        No topics available yet.
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {Object.entries(groups).map(([roman, group]) => (
        <div key={roman}>
          {/* Roman numeral group header */}
          <button
            onClick={() => toggle(roman)}
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left transition-colors hover:bg-white/60 dark:hover:bg-zinc-700/60"
          >
            <span className={`w-5 shrink-0 text-center text-[11px] font-black ${subjectColor}`}>{roman}</span>
            <span className="flex-1 truncate text-xs font-semibold text-gray-700 dark:text-gray-300">
              {group.heading}
            </span>
            {collapsed[roman]
              ? <ChevronRight size={12} className="shrink-0 text-gray-400" />
              : <ChevronDown size={12} className="shrink-0 text-gray-400" />
            }
          </button>

          {/* Sub-topics */}
          {!collapsed[roman] && group.items.map((t) => {
            const isSelected = t.id === selectedId;
            const hasContent = t.status === 'published' || !!t.generated_at;
            return (
              <button
                key={t.id}
                onClick={() => onSelect(t)}
                className={`flex w-full items-start gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs transition-colors ${
                  isSelected
                    ? 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200'
                    : 'text-gray-600 hover:bg-white/60 dark:text-gray-400 dark:hover:bg-zinc-700/60'
                }`}
              >
                <span className="mt-0.5 w-5 shrink-0 text-center text-[10px] font-bold text-gray-400">
                  {t.sub_letter ?? '–'}
                </span>
                <span className="flex-1 leading-snug">{t.sub_heading || t.topic_heading}</span>
                {hasContent
                  ? <CheckCircle2 size={10} className="mt-0.5 shrink-0 text-emerald-500" />
                  : <Circle size={10} className="mt-0.5 shrink-0 text-gray-300 dark:text-gray-600" />
                }
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function Bar2026({ onCaseClick }) {
  const [activeTab, setActiveTab] = useState('criminal');
  const [topics, setTopics] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [topicsError, setTopicsError] = useState(null);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishMsg, setPublishMsg] = useState(null);
  const [showTopicTree, setShowTopicTree] = useState(true);

  const active = SUBJECTS.find(s => s.id === activeTab) ?? SUBJECTS[0];

  const draftCount = topics.filter(t => t.status === 'draft').length;

  // Fetch topics when subject changes
  useEffect(() => {
    setTopics([]);
    setSelectedTopic(null);
    setTopicsError(null);
    setTopicsLoading(true);
    setPublishMsg(null);
    setShowTopicTree(true);

    fetch(apiUrl(`/api/reviewer/${activeTab}?all=1`))
      .then(r => {
        if (r.status === 401 || r.status === 403) {
          setIsAdmin(false);
          return fetch(apiUrl(`/api/reviewer/${activeTab}`));
        }
        setIsAdmin(true);
        return r;
      })
      .then(r => r.json())
      .then(data => {
        setTopics(data.topics ?? []);
        setTopicsLoading(false);
      })
      .catch(e => {
        setTopicsError(e.message);
        setTopicsLoading(false);
      });
  }, [activeTab]);

  const handleSelectTopic = useCallback((t) => {
    setSelectedTopic(t);
    if (window.innerWidth < 768) setShowTopicTree(false);
  }, []);

  const handlePublishAll = useCallback(() => {
    if (!window.confirm(`Publish all ${draftCount} draft topics for ${active.fullLabel}?`)) return;
    setPublishing(true);
    setPublishMsg(null);
    fetch(apiUrl('/api/reviewer/publish'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject: activeTab, publish_all: true, status: 'published' }),
    })
      .then(r => r.json())
      .then(data => {
        setPublishMsg(`Published ${data.updated ?? 0} topics.`);
        setTopics(prev => prev.map(t => ({ ...t, status: 'published' })));
      })
      .catch(e => setPublishMsg(`Error: ${e.message}`))
      .finally(() => setPublishing(false));
  }, [activeTab, draftCount, active.fullLabel]);

  // Auto-select first topic
  useEffect(() => {
    if (topics.length > 0 && !selectedTopic) {
      setSelectedTopic(topics[0]);
    }
  }, [topics]);

  return (
    <PurpleGlassAmbient showAmbient className="min-h-screen w-full min-w-0 pb-8 font-sans text-gray-900 dark:text-gray-100">
      <div className="mx-auto w-full min-w-0 max-w-7xl px-3 py-4 sm:px-5 sm:py-5 lg:px-6">

        {/* Header */}
        <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-purple-700 shadow-md shadow-violet-900/30">
              <Scale size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-gray-900 dark:text-white sm:text-2xl">
                BAR 2026 Reviewer
              </h1>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                Philippine Bar Examination · {EXAM_DATE}
              </p>
            </div>
          </div>
          <div className="mt-1 flex items-center gap-2 rounded-lg border border-lex bg-white/70 px-3 py-1.5 shadow-sm backdrop-blur-sm dark:bg-zinc-900/70 sm:mt-0">
            <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">Format</span>
            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">20 essay questions · 75% passing</span>
          </div>
        </div>

        {/* Subject tab bar */}
        <div className="mb-4 flex gap-0.5 overflow-x-auto rounded-xl border border-lex bg-white/60 p-1 shadow-sm backdrop-blur-sm dark:bg-zinc-900/60 no-scrollbar">
          {SUBJECTS.map(({ id, label, weight, icon: Icon, color, bgActive }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`relative flex shrink-0 flex-col items-center gap-0.5 rounded-lg border-b-2 px-3 py-2 text-center text-xs font-semibold transition-all sm:flex-row sm:gap-2 sm:text-sm ${
                activeTab === id
                  ? `bg-white shadow-sm dark:bg-zinc-800 ${bgActive}`
                  : 'border-transparent text-gray-500 hover:bg-white/60 hover:text-gray-700 dark:text-zinc-400 dark:hover:bg-zinc-800/60 dark:hover:text-zinc-200'
              }`}
            >
              <Icon size={15} className={activeTab === id ? color : ''} />
              <span className="leading-tight">{label}</span>
              <span className={`text-[10px] font-bold ${activeTab === id ? color : 'text-gray-400 dark:text-zinc-500'}`}>
                {weight}
              </span>
            </button>
          ))}
        </div>

        {/* Two-column layout */}
        <div className="flex flex-col gap-3 min-h-[400px] md:flex-row md:min-h-[600px]">

          {/* Topic Tree — left sidebar */}
          <div className="relative w-full overflow-hidden rounded-xl border border-lex bg-white/70 shadow-sm backdrop-blur-sm dark:bg-zinc-900/70 md:w-56 md:shrink-0 lg:w-64">
            <div className="pointer-events-none absolute inset-0"><CardVioletInnerWash /></div>
            <div className="relative z-[1]">
              <div className="border-b border-lex px-3 py-2.5">
                {/* Header — tappable on mobile to toggle tree */}
                <button
                  className="flex w-full items-center justify-between md:cursor-default md:pointer-events-none"
                  onClick={() => setShowTopicTree(v => !v)}
                >
                  <div className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider ${active.color}`}>
                    <active.icon size={11} />
                    {active.fullLabel}
                  </div>
                  <span className="md:hidden">
                    {showTopicTree
                      ? <ChevronDown size={14} className="text-gray-400" />
                      : <ChevronRight size={14} className="text-gray-400" />
                    }
                  </span>
                </button>
                {isAdmin && draftCount > 0 && (
                  <div className="mt-2 flex flex-col gap-1">
                    <button
                      onClick={handlePublishAll}
                      disabled={publishing}
                      className="w-full rounded-md bg-emerald-600 px-2 py-1 text-[10px] font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      {publishing ? 'Publishing…' : `Publish All (${draftCount} draft)`}
                    </button>
                    {publishMsg && (
                      <p className="text-[10px] text-emerald-700 dark:text-emerald-400">{publishMsg}</p>
                    )}
                  </div>
                )}
              </div>
              <div className={`overflow-y-auto px-1.5 py-2 max-h-72 md:max-h-[calc(100vh-260px)] ${showTopicTree ? '' : 'hidden md:block'}`}>
                {topicsLoading && (
                  <div className="py-6 text-center text-xs text-gray-400">Loading topics…</div>
                )}
                {topicsError && (
                  <div className="py-4 px-2 text-center text-xs text-rose-500">{topicsError}</div>
                )}
                {!topicsLoading && (
                  <TopicTree
                    topics={topics}
                    selectedId={selectedTopic?.id}
                    onSelect={handleSelectTopic}
                    subjectColor={active.color}
                  />
                )}
              </div>
            </div>
          </div>

          {/* Content panel — right */}
          <div className={`min-w-0 flex-1 md:overflow-y-auto md:max-h-[calc(100vh-220px)] ${showTopicTree ? 'hidden md:block' : 'block'}`}>
            {/* Back to topics — mobile only */}
            <button
              className="mb-3 flex items-center gap-1 text-xs font-semibold text-violet-600 hover:underline dark:text-violet-400 md:hidden"
              onClick={() => setShowTopicTree(true)}
            >
              <ChevronLeft size={14} /> All Topics
            </button>
            <ContentPanel
              subject={activeTab}
              topic={selectedTopic}
              onCaseClick={onCaseClick}
            />
          </div>

        </div>
      </div>
    </PurpleGlassAmbient>
  );
}
