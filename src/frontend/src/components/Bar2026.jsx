import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import ReactMarkdown from 'react-markdown';
import FontSizeControl from './FontSizeControl';
import { useFontSize } from '../hooks/useFontSize';
import {
  Scale, Globe, Briefcase, FileText, Users, Sword, BookOpen,
  ChevronRight, ChevronDown, ChevronLeft, BookMarked, Brain, AlertTriangle,
  Gavel, Lightbulb, Star, Clock, CheckCircle2, Circle,
  ExternalLink, Tag, AlertCircle, List, ScrollText, PenLine, PenOff,
} from 'lucide-react';
import PurpleGlassAmbient from './PurpleGlassAmbient';
import CardVioletInnerWash from './CardVioletInnerWash';
import { apiUrl } from '../utils/apiUrl';
import { BAR_SYLLABUS } from '../data/bar2026Syllabus';
import AnnotationCanvas from './AnnotationCanvas';
import AnnotationToolbar from './AnnotationToolbar';
import { useAnnotations } from '../hooks/useAnnotations';
import { useTopics } from '../hooks/useTopics';

// ── Subject definitions ────────────────────────────────────────────────────────

const SUBJECTS = [
  { id: 'political',  label: 'Political & PIL',    fullLabel: 'Political and Public International Law',      weight: '15%', icon: Globe,     color: 'text-blue-600 dark:text-blue-400',    bgActive: 'border-blue-600 dark:border-blue-400 text-blue-700 dark:text-blue-300' },
  { id: 'commercial', label: 'Commercial & Tax',   fullLabel: 'Commercial and Taxation Laws',                weight: '20%', icon: Briefcase, color: 'text-emerald-600 dark:text-emerald-400', bgActive: 'border-emerald-600 dark:border-emerald-400 text-emerald-700 dark:text-emerald-300' },
  { id: 'civil',      label: 'Civil Law & Land',   fullLabel: 'Civil Law and Land Titles and Deeds',         weight: '20%', icon: FileText,  color: 'text-violet-600 dark:text-violet-400',  bgActive: 'border-violet-600 dark:border-violet-400 text-violet-700 dark:text-violet-300' },
  { id: 'labor',      label: 'Labor & Social',     fullLabel: 'Labor Law and Social Legislation',            weight: '10%', icon: Users,     color: 'text-amber-600 dark:text-amber-400',    bgActive: 'border-amber-600 dark:border-amber-400 text-amber-700 dark:text-amber-300' },
  { id: 'criminal',   label: 'Criminal Law',       fullLabel: 'Criminal Law',                                weight: '10%', icon: Sword,     color: 'text-rose-600 dark:text-rose-400',      bgActive: 'border-rose-600 dark:border-rose-400 text-rose-700 dark:text-rose-300' },
  { id: 'remedial',   label: 'Remedial & Ethics',  fullLabel: 'Remedial Law, Legal and Judicial Ethics',     weight: '25%', icon: BookOpen,  color: 'text-indigo-600 dark:text-indigo-400',  bgActive: 'border-indigo-600 dark:border-indigo-400 text-indigo-700 dark:text-indigo-300' },
  { id: 'sherwin',    label: 'Sherwin',             fullLabel: 'Sherwin',                                     weight: '',    icon: Brain,     color: 'text-purple-600 dark:text-purple-400',  bgActive: 'border-purple-600 dark:border-purple-400 text-purple-700 dark:text-purple-300' },
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

// ── Case digest prefetch cache ─────────────────────────────────────────────────
// Keyed by case id. Stores the Promise so concurrent hovers on the same card
// don't fire duplicate requests.
const _digestPrefetch = new Map();

function prefetchCaseDigest(id) {
  if (!id || _digestPrefetch.has(id)) return;
  _digestPrefetch.set(
    id,
    fetch(apiUrl(`/api/sc_decisions/${id}?digest_only=true`))
      .then((r) => r.json())
      .then((d) => { if (d && !d.error) _digestPrefetch.set(id, d); })
      .catch(() => { _digestPrefetch.delete(id); }),
  );
}

// ── Case card ─────────────────────────────────────────────────────────────────

function CaseCard({ c, onCaseClick }) {
  const isEnBanc = c.division === 'En Banc';

  const handleClick = () => {
    const cached = _digestPrefetch.get(c.id);
    // If prefetch already resolved to the full object, pass it; otherwise pass
    // the minimal card data and let App.jsx's fetch-patch flow fill in the rest.
    const payload = (cached && typeof cached === 'object' && cached.digest_facts)
      ? { ...c, ...cached }
      : c;
    onCaseClick?.(payload);
  };

  return (
    <div
      className="group cursor-pointer rounded-lg border border-lex bg-white/40 px-3 py-2.5 transition-colors hover:bg-white/70 dark:bg-zinc-800/40 dark:hover:bg-zinc-800/70"
      onPointerEnter={() => prefetchCaseDigest(c.id)}
      onClick={handleClick}
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

function BarQuestions({ questions, fontSize = 15 }) {
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
                <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-200" style={{ fontSize: `${fontSize}px` }}>
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
  const { fontSize, increase: increaseFontSize, decrease: decreaseFontSize } = useFontSize();

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
                {topic.topic_path || `${topic.roman_num}${topic.sub_letter ? `.${topic.sub_letter}` : ''}`}
              </p>
              <h2 className="text-base font-black tracking-tight text-gray-900 dark:text-white sm:text-lg">
                {topic.topic_heading}
              </h2>
              {topic.sub_heading && (
                <p className="mt-0.5 text-sm font-medium text-gray-500 dark:text-gray-400">{topic.sub_heading}</p>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <FontSizeControl fontSize={fontSize} onIncrease={increaseFontSize} onDecrease={decreaseFontSize} />
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
                <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-200 leading-relaxed" style={{ fontSize: `${fontSize}px` }}>
                  <ReactMarkdown>{data.doctrine_md}</ReactMarkdown>
                </div>
              </section>
            )}

            {/* Distinctions */}
            {data.distinctions_md && (
              <section>
                <SectionHeader icon={AlertTriangle} label="Key Distinctions & Bar Traps" color="text-rose-500" />
                <div className="rounded-lg border border-rose-200 bg-rose-50/60 p-4 dark:border-rose-800/50 dark:bg-rose-900/10">
                  <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-200" style={{ fontSize: `${fontSize}px` }}>
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
                  <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-200" style={{ fontSize: `${fontSize}px` }}>
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
                  {data.key_cases.map((c, i) => {
                    const nc = c.id != null ? c : { ...c, id: c.case_id };
                    return <CaseCard key={nc.id ?? nc.gr_number ?? i} c={nc} onCaseClick={onCaseClick} />;
                  })}
                </div>
              </section>
            )}

            {/* Bar Questions */}
            {data.bar_questions?.length > 0 && (
              <section>
                <SectionHeader icon={AlertCircle} label={`Past Bar Questions (${data.bar_questions.length})`} color="text-amber-500" />
                <BarQuestions questions={data.bar_questions} fontSize={fontSize} />
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

function TopicTree({ tree, selectedId, onSelect, subjectColor }) {
  const [collapsed, setCollapsed] = useState({});

  const toggle = (id) => setCollapsed(c => ({ ...c, [id]: !c[id] }));

  const renderNode = (node, depth = 0) => {
    const isSelected = node.id === selectedId;
    const hasChildren = node.children && node.children.length > 0;
    const isCollapsed = collapsed[node.topic_path];
    const hasContent = node.status === 'published' || !!node.generated_at;

    // Determine prefix/label based on depth/level
    // Level 1: Roman (I, II)
    // Level 2: Letter (A, B)
    // Level 3: Number (1, 2)
    // Level 4: small letter (a, b)
    // Level 5: small roman (i, ii)
    const label = node.sub_heading || node.topic_heading;

    return (
      <div key={node.topic_path} className="select-none">
        <button
          onClick={() => {
            if (hasChildren && !node.id) {
              toggle(node.topic_path);
            } else {
              onSelect(node);
            }
          }}
          className={`flex w-full items-start gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs transition-colors ${
            isSelected
              ? 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200'
              : 'text-gray-600 hover:bg-white/60 dark:text-gray-400 dark:hover:bg-zinc-700/60'
          }`}
          style={{ paddingLeft: `${10 + depth * 12}px` }}
        >
          <span className={`shrink-0 text-[10px] font-bold ${depth === 0 ? `w-5 text-center ${subjectColor}` : 'w-4 text-gray-400'}`}>
            {node.sub_letter || (depth === 0 ? node.roman_num : '•')}
          </span>
          <span className={`flex-1 leading-snug ${depth === 0 ? 'font-semibold' : ''}`}>{label}</span>
          
          <div className="flex items-center gap-1">
            {hasChildren && (
              <div onClick={(e) => { e.stopPropagation(); toggle(node.topic_path); }} className="cursor-pointer">
                {isCollapsed ? <ChevronRight size={12} className="text-gray-400" /> : <ChevronDown size={12} className="text-gray-400" />}
              </div>
            )}
            {node.id && (
              hasContent
                ? <CheckCircle2 size={10} className="shrink-0 text-emerald-500" />
                : <Circle size={10} className="shrink-0 text-gray-300 dark:text-gray-600" />
            )}
          </div>
        </button>

        {hasChildren && !isCollapsed && (
          <div className="mt-0.5">
            {node.children.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (!tree || !tree.length) {
    return (
      <div className="px-3 py-6 text-center text-xs text-gray-400 dark:text-gray-500">
        No topics available yet.
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {tree.map(node => renderNode(node, 0))}
    </div>
  );
}

// ── Syllabus Panel ────────────────────────────────────────────────────────────

function SyllabusPanel({ subjectId, subjectColor }) {
  const syllabus = BAR_SYLLABUS[subjectId];
  if (!syllabus) return (
    <div className="py-8 text-center text-xs text-gray-400">Syllabus not available.</div>
  );

  return (
    <div className="space-y-4 px-1.5 py-2">
      {/* Weight badge */}
      <div className="flex items-center gap-2">
        <span className={`text-[10px] font-black uppercase tracking-wider ${subjectColor}`}>
          {syllabus.weight} of exam
        </span>
      </div>

      {/* Topics */}
      <div>
        <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
          Topics
        </p>
        <ol className="space-y-1">
          {syllabus.topics.map((topic, i) => (
            <li key={i} className="flex gap-2 text-xs leading-snug text-gray-700 dark:text-gray-300">
              <span className={`shrink-0 text-[10px] font-black ${subjectColor}`}>{i + 1}.</span>
              <span>{topic}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Key Statutes */}
      {syllabus.keyStatutes?.length > 0 && (
        <div>
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
            Key Statutes
          </p>
          <ul className="space-y-0.5">
            {syllabus.keyStatutes.map((s, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[11px] leading-snug text-gray-600 dark:text-gray-400">
                <span className="mt-0.5 shrink-0 text-violet-400">▪</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Landmark Cases */}
      {syllabus.landmarkCases?.length > 0 && (
        <div>
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
            Landmark Cases
          </p>
          <ul className="space-y-1">
            {syllabus.landmarkCases.map((c, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[11px] leading-snug text-gray-600 dark:text-gray-400">
                <Star size={9} className="mt-0.5 shrink-0 text-amber-400" />
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-[9px] text-gray-400 dark:text-gray-600">
        Source: SC/PHILJA BAR 2026 · Cutoff: June 30, 2025
      </p>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function Bar2026({ onCaseClick }) {
  const { getToken } = useAuth();
  const [activeTab, setActiveTab] = useState('criminal');
  
  const { topics, tree, loading: topicsLoading, error: topicsError, refresh } = useTopics(activeTab);
  
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishMsg, setPublishMsg] = useState(null);
  const [showTopicTree, setShowTopicTree] = useState(true);
  const [sidebarView, setSidebarView] = useState('topics'); // 'topics' | 'syllabus'

  // ── Annotation state ───────────────────────────────────────────────────────
  const contentScrollRef      = useRef(null);
  const [isAnnotating,        setIsAnnotating]        = useState(false);
  const [annotationTool,      setAnnotationTool]      = useState('pen');
  const [penColor,            setPenColor]            = useState('#2563eb');
  const [highlighterColor,    setHighlighterColor]    = useState('#4ade80');
  const [annotationWidth,     setAnnotationWidth]     = useState(2);
  const [eraserWidth,         setEraserWidth]         = useState(8);
  const [allowTouchDraw,      setAllowTouchDraw]      = useState(false);

  const {
    strokes, pushStroke, undo, redo, clearAll,
    isSaving, canSave, undoStack, redoStack,
  } = useAnnotations(activeTab, selectedTopic?.id, getToken);

  const active = SUBJECTS.find(s => s.id === activeTab) ?? SUBJECTS[0];

  const draftCount = topics.filter(t => t.status === 'draft').length;

  // Reset selection when subject changes
  useEffect(() => {
    setSelectedTopic(null);
    setPublishMsg(null);
    setShowTopicTree(true);
    setSidebarView('topics');

    // Simple admin check (can be improved to use getToken)
    fetch(apiUrl('/api/reviewer/criminal?all=1'))
      .then(r => setIsAdmin(r.status !== 401 && r.status !== 403))
      .catch(() => setIsAdmin(false));
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
        refresh();
      })
      .catch(e => setPublishMsg(`Error: ${e.message}`))
      .finally(() => setPublishing(false));
  }, [activeTab, draftCount, active.fullLabel, refresh]);

  // Auto-select first topic
  useEffect(() => {
    if (!selectedTopic && topics.length > 0) {
      const firstWithId = topics.find(t => t.id);
      if (firstWithId) {
        setSelectedTopic(firstWithId);
      }
    }
  }, [topics, selectedTopic]);

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

                {/* Topics / Syllabus toggle */}
                <div className="mt-2 flex gap-0.5 rounded-lg border border-lex bg-gray-100/60 p-0.5 dark:bg-zinc-800/60">
                  <button
                    onClick={() => setSidebarView('topics')}
                    className={`flex flex-1 items-center justify-center gap-1 rounded-md py-1 text-[10px] font-bold uppercase tracking-wide transition-all ${
                      sidebarView === 'topics'
                        ? 'bg-white shadow-sm text-violet-700 dark:bg-zinc-700 dark:text-violet-300'
                        : 'text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300'
                    }`}
                  >
                    <List size={10} /> Topics
                  </button>
                  <button
                    onClick={() => setSidebarView('syllabus')}
                    className={`flex flex-1 items-center justify-center gap-1 rounded-md py-1 text-[10px] font-bold uppercase tracking-wide transition-all ${
                      sidebarView === 'syllabus'
                        ? 'bg-white shadow-sm text-violet-700 dark:bg-zinc-700 dark:text-violet-300'
                        : 'text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300'
                    }`}
                  >
                    <ScrollText size={10} /> Syllabus
                  </button>
                </div>
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
              <div className={`overflow-y-auto px-1.5 py-2 max-h-72 md:max-h-[calc(100vh-290px)] ${showTopicTree ? '' : 'hidden md:block'}`}>
                {sidebarView === 'syllabus' ? (
                  <SyllabusPanel subjectId={activeTab} subjectColor={active.color} />
                ) : (
                  <>
                    {topicsLoading && (
                      <div className="py-6 text-center text-xs text-gray-400">Loading topics…</div>
                    )}
                    {topicsError && (
                      <div className="py-4 px-2 text-center text-xs text-rose-500">{topicsError}</div>
                    )}
                    <div className="flex-1 overflow-y-auto px-2 py-2">
                      <TopicTree
                        tree={tree}
                        selectedId={selectedTopic?.id}
                        onSelect={handleSelectTopic}
                        subjectColor={active.color}
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Content panel — right */}
          <div className={`min-w-0 flex-1 ${showTopicTree ? 'hidden md:block' : 'block'}`}>
            {/* Back to topics — mobile only */}
            <button
              className="mb-3 flex items-center gap-1 text-xs font-semibold text-violet-600 hover:underline dark:text-violet-400 md:hidden"
              onClick={() => setShowTopicTree(true)}
            >
              <ChevronLeft size={14} /> All Topics
            </button>

            {/* Scrollable content + annotation canvas layer */}
            <div
              ref={contentScrollRef}
              className="relative md:overflow-y-auto md:max-h-[calc(100vh-220px)]"
              style={isAnnotating ? { touchAction: 'none' } : undefined}
            >
              <ContentPanel
                subject={activeTab}
                topic={selectedTopic}
                onCaseClick={onCaseClick}
              />
              <AnnotationCanvas
                topicId={selectedTopic?.id}
                isAnnotating={isAnnotating}
                currentTool={annotationTool}
                penColor={penColor}
                highlighterColor={highlighterColor}
                currentWidth={annotationWidth}
                eraserWidth={eraserWidth}
                allowTouchDraw={allowTouchDraw}
                strokes={strokes}
                onStrokeComplete={pushStroke}
                scrollContainerRef={contentScrollRef}
              />
            </div>
          </div>

        </div>
      </div>

      {/* ── Annotation mode toggle button — left side, hidden when toolbar is active ── */}
      {selectedTopic && !isAnnotating && (
        <button
          onClick={() => setIsAnnotating(true)}
          title="Annotate this page (S Pen / touch)"
          className="fixed left-2 top-1/2 -translate-y-1/2 z-20 flex h-12 w-12 items-center justify-center rounded-full border border-violet-200 bg-white text-violet-600 shadow-lg shadow-gray-300/60 hover:bg-violet-50 dark:border-violet-700 dark:bg-zinc-800 dark:text-violet-400 dark:hover:bg-zinc-700"
        >
          <PenLine size={20} />
        </button>
      )}

      {/* ── Annotation toolbar (floating, shown when annotating) ── */}
      <AnnotationToolbar
        isAnnotating={isAnnotating}
        currentTool={annotationTool}
        onToolChange={setAnnotationTool}
        penColor={penColor}
        onPenColorChange={setPenColor}
        highlighterColor={highlighterColor}
        onHighlighterColorChange={setHighlighterColor}
        currentWidth={annotationWidth}
        onWidthChange={setAnnotationWidth}
        eraserWidth={eraserWidth}
        onEraserWidthChange={setEraserWidth}
        allowTouchDraw={allowTouchDraw}
        onToggleTouchDraw={() => setAllowTouchDraw(v => !v)}
        onUndo={undo}
        onRedo={redo}
        canUndo={undoStack.length > 0}
        canRedo={redoStack.length > 0}
        isSaving={isSaving}
        canSave={canSave}
        onClear={() => clearAll()}
        onExit={() => setIsAnnotating(false)}
      />

    </PurpleGlassAmbient>
  );
}
