import React from 'react';
import { getSubjectColor } from '../utils/colors';

const subjects = [
    "Civil Law",
    "Commercial Law",
    "Criminal Law",
    "Labor Law",
    "Legal Ethics",
    "Political Law",
    "Remedial Law",
    "Taxation Law"
];

const FlashcardSetup = ({ onStart }) => {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-dark-card rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="p-8 border-b border-gray-100 dark:border-gray-800 text-center">
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        Flashcard Mode
                    </h2>
                    <p className="text-gray-500 dark:text-gray-400">
                        Select a subject to practice or choose Random for a mix.
                    </p>
                </div>

                {/* Content - Grid of Options */}
                <div className="flex-1 overflow-y-auto p-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {/* Random Option */}
                        <button
                            onClick={() => onStart(null)}
                            className="group p-6 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-700 hover:border-primary hover:bg-primary/5 transition-all text-left flex flex-col gap-2"
                        >
                            <span className="text-lg font-bold text-gray-900 dark:text-white group-hover:text-primary transition-colors">
                                🎲 Random / All Subjects
                            </span>
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                                Mix of questions from all 8 bar subjects.
                            </span>
                        </button>

                        {/* Subject Options */}
                        {subjects.map((subject) => {
                            const colorClass = getSubjectColor(subject);
                            const textColor = colorClass.split(' ').find(c => c.startsWith('text-'));
                            const borderColor = colorClass.split(' ').find(c => c.startsWith('border-'));

                            return (
                                <button
                                    key={subject}
                                    onClick={() => onStart(subject)}
                                    className={`group p-6 rounded-xl border-2 ${borderColor} bg-white dark:bg-gray-800/50 hover:brightness-110 transition-all text-left flex flex-col gap-2 shadow-sm hover:shadow-md`}
                                >
                                    <span className={`text-lg font-bold ${textColor}`}>
                                        {subject}
                                    </span>
                                    <span className="text-sm text-gray-500 dark:text-gray-400">
                                        Practice questions specifically for {subject}.
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex justify-center">
                    <button
                        onClick={() => onStart('CANCEL')}
                        className="px-6 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium transition-colors shadow-sm"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
};

export default FlashcardSetup;
