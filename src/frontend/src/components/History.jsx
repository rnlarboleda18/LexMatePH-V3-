import React, { useState, useEffect } from 'react';
import { getSubjectColor } from '../utils/colors';
import { ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';

const History = ({ userInfo }) => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedRow, setExpandedRow] = useState(null);

    useEffect(() => {
        const fetchHistory = async () => {
            if (!userInfo) {
                setLoading(false);
                return;
            }

            try {
                const response = await fetch('/api/history');
                if (!response.ok) throw new Error('Failed to fetch history');
                const data = await response.json();
                setHistory(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchHistory();
    }, [userInfo]);

    const toggleRow = (id) => {
        if (expandedRow === id) {
            setExpandedRow(null);
        } else {
            setExpandedRow(id);
        }
    };

    if (!userInfo) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-center">
                <AlertCircle size={48} className="text-gray-400 mb-4" />
                <h3 className="text-xl font-bold text-gray-700 dark:text-gray-300">Please Log In</h3>
                <p className="text-gray-500 dark:text-gray-400 mt-2">
                    You need to be logged in to view your exam history.
                </p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-lg text-center">
                Error: {error}
            </div>
        );
    }

    if (history.length === 0) {
        return (
            <div className="text-center py-20 text-gray-500 dark:text-gray-400">
                <p className="text-xl font-medium">No history found.</p>
                <p className="mt-2">Take a Mock Exam to see your results here!</p>
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">My Exam History</h2>
            
            <div className="bg-white dark:bg-dark-card rounded-xl shadow-sm border border-lex overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-lex">
                            <tr>
                                <th className="px-6 py-4 text-sm font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                                <th className="px-6 py-4 text-sm font-semibold text-gray-500 uppercase tracking-wider">Subject</th>
                                <th className="px-6 py-4 text-sm font-semibold text-gray-500 uppercase tracking-wider">Score</th>
                                <th className="px-6 py-4 text-sm font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-4 text-sm font-semibold text-gray-500 uppercase tracking-wider">Details</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                            {history.map((item) => {
                                const isPass = item.score >= 75;
                                const date = new Date(item.date).toLocaleDateString(undefined, {
                                    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                });
                                const colorClass = getSubjectColor(item.subject);
                                const textColor = colorClass.split(' ').find(c => c.startsWith('text-'));

                                return (
                                    <React.Fragment key={item.id}>
                                        <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                                            <td className="px-6 py-4 text-sm text-gray-700 dark:text-gray-300 whitespace-nowrap">
                                                {date}
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`text-sm font-bold ${textColor}`}>
                                                    {item.subject}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`text-sm font-bold ${isPass ? 'text-green-600' : 'text-red-600'}`}>
                                                    {item.score}%
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`px-2 py-1 rounded-full text-xs font-bold ${isPass ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                                    {isPass ? 'PASSED' : 'FAILED'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <button
                                                    onClick={() => toggleRow(item.id)}
                                                    className="text-gray-400 hover:text-blue-500 transition-colors"
                                                >
                                                    {expandedRow === item.id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                                </button>
                                            </td>
                                        </tr>
                                        {expandedRow === item.id && (
                                            <tr className="bg-gray-50 dark:bg-gray-800/20">
                                                <td colSpan="5" className="px-6 py-6">
                                                    <div className="space-y-4">
                                                        <div>
                                                            <h4 className="text-sm font-bold text-blue-600 dark:text-blue-400 uppercase mb-2">AI Feedback</h4>
                                                            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap text-sm leading-relaxed">
                                                                {item.feedback}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default History;
