/**
 * Normalizes API subjects and builds the balanced interleaved list used by Bar Questions / Lexify.
 */

export function buildBalancedQuestions(data) {
  const normalizeSubject = (raw) => {
    const s = (raw || '').toLowerCase();
    if (s.includes('civil')) return 'Civil Law';
    if (s.includes('commercial') || s.includes('mercantile')) return 'Commercial Law';
    if (s.includes('criminal') || s.includes('penal')) return 'Criminal Law';
    if (s.includes('labor') || s.includes('social legislat')) return 'Labor Law';
    if (s.includes('ethics') || s.includes('judicial ethics')) return 'Legal Ethics';
    if (s.includes('political') || s.includes('constitutional')) return 'Political Law';
    if (s.includes('remedial') || s.includes('procedure')) return 'Remedial Law';
    if (s.includes('taxation') || s.includes('tax')) return 'Taxation Law';
    return raw;
  };

  const groupedData = [];
  let currentParent = null;
  const subPartRegex = /^([\(]?([a-z]|[0-9]+[a-z]|[ivx]+)[\.\)]|[QA]\d+[a-z][:.]?)/i;

  for (const q of data) {
    q.subject = normalizeSubject(q.subject);
    const qText = q.text.trim();
    const aText = (q.answer || '').trim();
    const isSub = subPartRegex.test(qText) || subPartRegex.test(aText);
    const canGroup = currentParent && currentParent.year === q.year && currentParent.subject === q.subject;

    if (isSub && canGroup) {
      if (!currentParent.subQuestions) currentParent.subQuestions = [];
      currentParent.subQuestions.push(q);
    } else {
      currentParent = { ...q, subQuestions: [] };
      groupedData.push(currentParent);
    }
  }

  const subjects = {};
  groupedData.forEach((q) => {
    if (!subjects[q.subject]) subjects[q.subject] = [];
    subjects[q.subject].push(q);
  });

  Object.keys(subjects).forEach((key) => {
    for (let i = subjects[key].length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [subjects[key][i], subjects[key][j]] = [subjects[key][j], subjects[key][i]];
    }
  });

  const balancedQuestions = [];
  const subjectKeys = Object.keys(subjects);
  let maxCount = 0;
  subjectKeys.forEach((key) => {
    maxCount = Math.max(maxCount, subjects[key].length);
  });

  for (let i = 0; i < maxCount; i++) {
    subjectKeys.forEach((key) => {
      if (subjects[key][i]) balancedQuestions.push(subjects[key][i]);
    });
  }

  return balancedQuestions;
}
