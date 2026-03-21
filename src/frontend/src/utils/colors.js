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
    return subjectColors[subject] || "text-gray-500 border-gray-500";
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
    return subjectAnswerColors[subject] || "bg-gray-50 dark:bg-gray-800/50 border-gray-100 dark:border-gray-800";
};
