import React from 'react';
import { BookOpen, Brain, Search, Scale } from 'lucide-react';

const About = () => {
    return (
        <div className="max-w-4xl mx-auto px-6 py-12">
            {/* Hero Section */}
            <div className="text-center mb-16">
                <div className="flex justify-center mb-6">
                    <div className="p-4 bg-blue-100 dark:bg-blue-900/30 rounded-2xl">
                        <Scale className="w-16 h-16 text-blue-600 dark:text-blue-400" />
                    </div>
                </div>
                <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
                    Philippine Bar Reviewer
                </h1>
                <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
                    Your comprehensive companion for mastering the Philippine Bar Examinations.
                    Designed to help you study smarter, not harder.
                </p>
            </div>

            {/* Features Grid */}
            <div className="grid md:grid-cols-3 gap-8 mb-16">
                <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
                    <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center mb-6">
                        <Search className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
                        Smart Search
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400">
                        Instantly find questions across all subjects and years. Filter by topic, year, or keyword to focus your review.
                    </p>
                </div>

                <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
                    <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center mb-6">
                        <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
                        Flashcard Mode
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400">
                        Test your recall with interactive flashcards. Perfect for memorizing key doctrines and provisions on the go.
                    </p>
                </div>

                <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
                    <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-xl flex items-center justify-center mb-6">
                        <Brain className="w-6 h-6 text-green-600 dark:text-green-400" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
                        Mock Bar
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400">
                        Simulate the actual exam experience with randomized mock tests. Build stamina and confidence for the big day.
                    </p>
                </div>
            </div>

            {/* Mission / Disclaimer */}
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-2xl p-8 border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                    About This Project
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-4">
                    This application aggregates past Philippine Bar Examination questions and answers from various sources, including the UPLC and other legal resources. It is intended for educational purposes to assist law students and bar reviewees.
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-500">
                    Disclaimer: While we strive for accuracy, please verify all answers with the latest jurisprudence and laws. This tool is a study aid and not a substitute for official legal advice or primary sources.
                </p>
            </div>

        </div>
    );
};

export default About;
