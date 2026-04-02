import {
    Landmark,
    ScrollText,
    Briefcase,
    Gavel,
    HardHat,
    Scale,
    ClipboardList,
    Calculator,
    BookOpen,
    Layers,
} from 'lucide-react';
import { normalizeBarSubject } from './subjectNormalize';

/** One distinctive Lucide icon per canonical bar subject (flashcards / browse UI). */
const SUBJECT_ICONS = {
    'Political Law': Landmark,
    'Civil Law': ScrollText,
    'Commercial Law': Briefcase,
    'Criminal Law': Gavel,
    'Labor Law': HardHat,
    'Legal Ethics': Scale,
    'Remedial Law': ClipboardList,
    'Taxation Law': Calculator,
};

/** @param {string} rawSubject - DB or display subject string */
export function getSubjectIconComponent(rawSubject) {
    const key = normalizeBarSubject(rawSubject) || rawSubject;
    if (!key || key === '—') return BookOpen;
    return SUBJECT_ICONS[key] || BookOpen;
}

/** Icon for “all subjects / random” decks */
export function AllSubjectsIcon(props) {
    return <Layers {...props} />;
}

/**
 * Renders the subject icon; inherits text color from parent when className omits text-*.
 */
export function SubjectIcon({ subject, className = 'h-5 w-5 shrink-0', strokeWidth = 2, ...rest }) {
    const Icon = getSubjectIconComponent(subject);
    return <Icon className={className} strokeWidth={strokeWidth} aria-hidden {...rest} />;
}
