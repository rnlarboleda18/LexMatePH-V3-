/**
 * Bar-subject and digest **content** colors (badges, cards, doctrine panels).
 * App chrome uses white / black / grey + subtle purple (`filterChromeClasses.js`);
 * subject pills in modals and digest doctrine panels always use the palette below.
 */

import { normalizeBarQuestionSubject, normalizeBarSubject } from './subjectNormalize';

/** Canonical Bar subject key → same classes as `subjectColors` (modals, cards). */
export function getSubjectColorForBarQuestion(question) {
    if (!question || typeof question !== 'object') return getSubjectColor('Political Law');
    return getSubjectColor(normalizeBarQuestionSubject(question));
}

/** Free-text subject line (e.g. doctrinal index) → canonical key, then pill classes. */
export function getSubjectColorForRawSubject(raw) {
    const key = normalizeBarSubject(typeof raw === 'string' ? raw : '');
    return getSubjectColor(key || 'Political Law');
}

export const subjectColors = {
    "Political Law": "text-purple-500 border-purple-500 shadow-purple-500/50",
    "Political Law and Intl Law": "text-purple-500 border-purple-500 shadow-purple-500/50",
    "International Law": "text-purple-500 border-purple-500 shadow-purple-500/50",
    "Labor Law": "text-yellow-500 border-yellow-500 shadow-yellow-500/50",
    "Labor Law and Social Legislatio": "text-yellow-500 border-yellow-500 shadow-yellow-500/50",
    "Civil Law": "text-blue-500 border-blue-500 shadow-blue-500/50",
    "Taxation Law": "text-orange-500 border-orange-500 shadow-orange-500/50",
    "Mercantile Law": "text-cyan-500 border-cyan-500 shadow-cyan-500/50",
    "Commercial Law": "text-cyan-500 border-cyan-500 shadow-cyan-500/50",
    "Commercial and Taxation Law": "text-cyan-500 border-cyan-500 shadow-cyan-500/50",
    "Criminal Law": "text-red-500 border-red-500 shadow-red-500/50",
    "Remedial Law": "text-pink-500 border-pink-500 shadow-pink-500/50",
    "Remedial Law and Legal Ethics": "text-pink-500 border-pink-500 shadow-pink-500/50",
    "Legal Ethics": "text-green-500 border-green-500 shadow-green-500/50",
};

export const getSubjectColor = (subject) => {
    return subjectColors[subject] || 'text-neutral-600 border-neutral-400 shadow-neutral-500/20';
};

export const subjectAnswerColors = {
    "Political Law": "bg-purple-50 dark:bg-purple-900/20 border-purple-100 dark:border-purple-900/30",
    "Labor Law": "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-100 dark:border-yellow-900/30",
    "Civil Law": "bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-900/30",
    "Taxation Law": "bg-orange-50 dark:bg-orange-900/20 border-orange-100 dark:border-orange-900/30",
    "Mercantile Law": "bg-cyan-50 dark:bg-cyan-900/20 border-cyan-100 dark:border-cyan-900/30",
    "Commercial Law": "bg-cyan-50 dark:bg-cyan-900/20 border-cyan-100 dark:border-cyan-900/30",
    "Criminal Law": "bg-red-50 dark:bg-red-900/20 border-red-100 dark:border-red-900/30",
    "Remedial Law": "bg-pink-50 dark:bg-pink-900/20 border-pink-100 dark:border-pink-900/30",
    "Legal Ethics": "bg-green-50 dark:bg-green-900/20 border-green-100 dark:border-green-900/30",
};

export const getSubjectAnswerColor = (subject) => {
    return subjectAnswerColors[subject] || "bg-gray-50 dark:bg-gray-800/50 border-lex";
};

/** Map free-text / Primary: … subject strings to a bar subject key for theming. */
export const normalizeSubjectForColor = (subject) => {
    if (!subject) return "Political Law";
    let s = subject.toString();
    const primaryMatch = s.match(/Primary:\s*([^;]+)/i);
    if (primaryMatch) s = primaryMatch[1];

    if (s.includes("Political") || s.includes("Constitutional") || s.includes("Admin") || s.includes("Election") || s.includes("Public Corp")) return "Political Law";
    if (s.includes("Labor")) return "Labor Law";
    if (s.includes("Civil") || s.includes("Family") || s.includes("Property") || s.includes("Succession") || s.includes("Obligations")) return "Civil Law";
    if (s.includes("Taxation") || s.includes("Tax")) return "Taxation Law";
    if (s.includes("Commercial") || s.includes("Mercantile") || s.includes("Corporate") || s.includes("Insurance") || s.includes("Transportation")) return "Commercial Law";
    if (s.includes("Criminal")) return "Criminal Law";
    if (s.includes("Remedial") || s.includes("Procedure") || s.includes("Evidence")) return "Remedial Law";
    if (s.includes("Ethics") || s.includes("Legal Ethics") || s.includes("Judicial")) return "Legal Ethics";

    return "Political Law";
};

/** Gradient / stripe / icon classes for the Main Doctrine card in CaseDecisionModal (full Tailwind strings for purge). */
export const subjectMainDoctrinePanelClasses = {
    "Political Law": {
        card: "from-purple-50/60 to-white/40 dark:from-purple-950/30 dark:to-slate-900/40",
        stripe: "from-purple-400 to-violet-600 dark:from-purple-500 dark:to-violet-500",
        title: "from-purple-600 to-violet-600 dark:from-purple-400 dark:to-violet-400",
        icon: "text-purple-500 dark:text-purple-400",
    },
    "Labor Law": {
        card: "from-yellow-50/60 to-white/40 dark:from-yellow-950/25 dark:to-slate-900/40",
        stripe: "from-yellow-400 to-amber-600 dark:from-yellow-500 dark:to-amber-500",
        title: "from-yellow-600 to-amber-600 dark:from-yellow-400 dark:to-amber-400",
        icon: "text-yellow-500 dark:text-yellow-400",
    },
    "Civil Law": {
        card: "from-blue-50/60 to-white/40 dark:from-slate-800/60 dark:to-slate-900/40",
        stripe: "from-blue-400 to-indigo-600 dark:from-blue-500 dark:to-indigo-500",
        title: "from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400",
        icon: "text-blue-500 dark:text-blue-400",
    },
    "Taxation Law": {
        card: "from-orange-50/60 to-white/40 dark:from-orange-950/25 dark:to-slate-900/40",
        stripe: "from-orange-400 to-amber-600 dark:from-orange-500 dark:to-amber-500",
        title: "from-orange-600 to-amber-600 dark:from-orange-400 dark:to-amber-400",
        icon: "text-orange-500 dark:text-orange-400",
    },
    "Commercial Law": {
        card: "from-cyan-50/60 to-white/40 dark:from-cyan-950/25 dark:to-slate-900/40",
        stripe: "from-cyan-400 to-teal-600 dark:from-cyan-500 dark:to-teal-500",
        title: "from-cyan-600 to-teal-600 dark:from-cyan-400 dark:to-teal-400",
        icon: "text-cyan-500 dark:text-cyan-400",
    },
    "Criminal Law": {
        card: "from-red-50/60 to-white/40 dark:from-red-950/25 dark:to-slate-900/40",
        stripe: "from-red-400 to-rose-600 dark:from-red-500 dark:to-rose-500",
        title: "from-red-600 to-rose-600 dark:from-red-400 dark:to-rose-400",
        icon: "text-red-500 dark:text-red-400",
    },
    "Remedial Law": {
        card: "from-pink-50/60 to-white/40 dark:from-pink-950/25 dark:to-slate-900/40",
        stripe: "from-pink-400 to-fuchsia-600 dark:from-pink-500 dark:to-fuchsia-500",
        title: "from-pink-600 to-fuchsia-600 dark:from-pink-400 dark:to-fuchsia-400",
        icon: "text-pink-500 dark:text-pink-400",
    },
    "Legal Ethics": {
        card: "from-green-50/60 to-white/40 dark:from-green-950/25 dark:to-slate-900/40",
        stripe: "from-green-400 to-emerald-600 dark:from-green-500 dark:to-emerald-500",
        title: "from-green-600 to-emerald-600 dark:from-green-400 dark:to-emerald-400",
        icon: "text-green-500 dark:text-green-400",
    },
};

export const getSubjectMainDoctrinePanelClasses = (subject) => {
    const key = normalizeSubjectForColor(subject);
    return subjectMainDoctrinePanelClasses[key] || subjectMainDoctrinePanelClasses["Political Law"];
};
