const CANONICAL = [
  'Civil Law',
  'Commercial Law',
  'Criminal Law',
  'Labor Law',
  'Legal Ethics',
  'Political Law',
  'Remedial Law',
  'Taxation Law',
];

/**
 * Raw label used to bucket a bar question into the 8 canonical subjects.
 *
 * `subject` is often the combined exam-paper title (e.g. "Commercial and Taxation Laws").
 * `sub_topic` is usually the granular strand (e.g. "Taxation"). When both normalize differently,
 * trust `sub_topic` only if `subject` looks like a combined paper; otherwise trust `subject`
 * so a bad `sub_topic` row does not override a correct `subject`.
 */
export function barQuestionSubjectRaw(q) {
  if (!q || typeof q !== 'object') return '';
  const subject = typeof q.subject === 'string' ? q.subject.trim() : '';
  const st = q.sub_topic;
  const rawSt = st != null && String(st).trim() !== '' ? String(st).trim() : '';
  if (!rawSt) return subject;
  if (!subject) return rawSt;

  const normSubject = normalizeBarSubject(subject);
  const normSubTopic = normalizeBarSubject(rawSt);
  if (normSubject === normSubTopic) return subject;

  const subjectLooksCombined = /\band\b/i.test(subject) && subject.length > 24;
  if (subjectLooksCombined) return rawSt;
  return subject;
}

/** Canonical 8 bar labels for a question row (uses sub_topic when set). */
export function normalizeBarQuestionSubject(q) {
  return normalizeBarSubject(barQuestionSubjectRaw(q));
}

/**
 * Maps DB / digest subject strings to the 8 canonical bar subjects.
 * Order matters for combined exam titles (e.g. "Commercial and Taxation Laws").
 */
export function normalizeBarSubject(raw) {
  const t = typeof raw === 'string' ? raw.trim() : '';
  if (CANONICAL.includes(t)) return t;
  const s = (raw || '').toLowerCase();
  // CSC / civil service (administrative & public employment) — Bar syllabus under Labor, not Civil Law
  if (s.includes('civil service') || s.includes('civil-service') || /\bcsc\b/.test(s)) {
    return 'Labor Law';
  }
  // Word-boundary style checks: avoid "penalties"→penal, "belabor"→labor, "apolitical"→political, etc.
  if (/\bcommercial\b/.test(s) || /\bmercantile\b/.test(s)) return 'Commercial Law';
  if (/\bcriminal\b/.test(s) || /\bpenal\b/.test(s)) return 'Criminal Law';
  if (/\blabor\b/.test(s) || s.includes('social legislat')) return 'Labor Law';
  if (/\bethics\b/.test(s) || s.includes('judicial ethics')) return 'Legal Ethics';
  if (/\bpolitical\b/.test(s) || /\bconstitutional\b/.test(s)) return 'Political Law';
  if (/\bremedial\b/.test(s) || /\bprocedure\b/.test(s) || /\brules of court\b/.test(s)) {
    return 'Remedial Law';
  }
  if (s.includes('practical exercise')) return 'Remedial Law';
  // Land Titles paper (Day 2 AM) — before generic "civil" so combined titles still bucket to Civil Law
  if (s.includes('land title')) return 'Civil Law';
  if (s.includes('taxation') || /\btax\b/.test(s)) return 'Taxation Law';
  if (/\bcivil\b/.test(s)) return 'Civil Law';
  return t;
}
