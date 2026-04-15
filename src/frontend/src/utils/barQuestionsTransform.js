import { normalizeBarSubject, barQuestionSubjectRaw } from './subjectNormalize';

/**
 * Normalizes API subjects and builds the balanced interleaved list used by Bar Questions / Lexify.
 */
export function buildBalancedQuestions(data) {
  const groupedData = [];
  let currentParent = null;
  const subPartRegex = /^([\(]?([a-z]|[0-9]+[a-z]|[ivx]+)[\.\)]|[QA]\d+[a-z][:.]?)/i;

  for (const q of data) {
    // `barQuestionSubjectRaw` picks granular strand on combined papers only; otherwise keeps `subject`.
    q.subject = normalizeBarSubject(barQuestionSubjectRaw(q));
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

  // Stable order (newest year first, then id) — per-subject shuffle made filtered Bar browse feel random.
  Object.keys(subjects).forEach((key) => {
    subjects[key].sort((a, b) => {
      const yb = Number(b.year) || 0;
      const ya = Number(a.year) || 0;
      if (yb !== ya) return yb - ya;
      return (Number(a.id) || 0) - (Number(b.id) || 0);
    });
  });

  const balancedQuestions = [];
  const canonicalOrder = [
    'Civil Law',
    'Commercial Law',
    'Criminal Law',
    'Labor Law',
    'Legal Ethics',
    'Political Law',
    'Remedial Law',
    'Taxation Law',
  ];
  const subjectKeys = [
    ...canonicalOrder.filter((k) => subjects[k]?.length),
    ...Object.keys(subjects)
      .filter((k) => !canonicalOrder.includes(k))
      .sort((a, b) => a.localeCompare(b)),
  ];
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
