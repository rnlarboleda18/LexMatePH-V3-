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

/** Maps DB / digest subject strings to the 8 canonical bar subjects (same rules as App.jsx). */
export function normalizeBarSubject(raw) {
  const t = typeof raw === 'string' ? raw.trim() : '';
  if (CANONICAL.includes(t)) return t;
  const s = (raw || '').toLowerCase();
  // CSC / civil service (administrative & public employment) — Bar syllabus under Labor, not Civil Law
  if (s.includes('civil service') || s.includes('civil-service') || /\bcsc\b/.test(s)) {
    return 'Labor Law';
  }
  if (s.includes('civil')) return 'Civil Law';
  if (s.includes('commercial') || s.includes('mercantile')) return 'Commercial Law';
  if (s.includes('criminal') || s.includes('penal')) return 'Criminal Law';
  if (s.includes('labor') || s.includes('social legislat')) return 'Labor Law';
  if (s.includes('ethics') || s.includes('judicial ethics')) return 'Legal Ethics';
  if (s.includes('political') || s.includes('constitutional')) return 'Political Law';
  if (s.includes('remedial') || s.includes('procedure')) return 'Remedial Law';
  if (s.includes('taxation') || s.includes('tax')) return 'Taxation Law';
  return t;
}
