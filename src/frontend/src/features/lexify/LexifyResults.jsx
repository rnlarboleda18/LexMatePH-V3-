import React, { useState } from 'react';

const SCORE_COLORS = {
    high: { bar: 'bg-green-500', text: 'text-green-400', border: 'border-green-500/30', bg: 'bg-green-500/10' },
    mid: { bar: 'bg-yellow-500', text: 'text-yellow-400', border: 'border-yellow-500/30', bg: 'bg-yellow-500/10' },
    low: { bar: 'bg-red-500', text: 'text-red-400', border: 'border-red-500/30', bg: 'bg-red-500/10' },
};

const getColorLevel = (pct) => {
    if (pct >= 70) return 'high';
    if (pct >= 40) return 'mid';
    return 'low';
};

const ScoreCard = ({ result, index, question, expanded, onToggle }) => {
    if (!result) return null;

    const max = 5;
    const pct = ((result.score / max) * 100);
    const colors = SCORE_COLORS[getColorLevel(pct)];

    return (
        <div className={`border ${colors.border} ${colors.bg} rounded-2xl overflow-hidden transition-all`}>
            {/* Card Header */}
            <button onClick={onToggle} className="w-full flex items-center justify-between p-5 text-left hover:bg-white/5 transition">
                <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-xl border-2 ${colors.border} flex items-center justify-center`}>
                        <span className="font-mono font-bold text-sm text-white">{index + 1}</span>
                    </div>
                    <div>
                        <p className="text-xs text-white/40 uppercase tracking-widest">{question?.subject || `Question ${index + 1}`}</p>
                        <p className="text-white font-medium text-sm mt-0.5 line-clamp-1">{question?.text?.substring(0, 90)}...</p>
                    </div>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                    <div className="text-right">
                        <p className={`text-2xl font-bold font-mono ${colors.text}`}>{result.score.toFixed(1)}</p>
                        <p className="text-xs text-white/30">out of {max}%</p>
                    </div>
                    <span className="text-white/40">{expanded ? '▲' : '▼'}</span>
                </div>
            </button>

            {/* Expanded Detail */}
            {expanded && (
                <div className="px-5 pb-5 space-y-4 border-t border-white/10 pt-4">
                    {/* Score Bar */}
                    <div>
                        <div className="flex justify-between text-xs text-white/40 mb-1">
                            <span>Score</span><span>{pct.toFixed(0)}%</span>
                        </div>
                        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className={`h-full ${colors.bar} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                        </div>
                    </div>

                    {/* Breakdown */}
                    <div className="grid grid-cols-3 gap-3 text-center">
                        {[
                            { label: 'Conclusion', key: 'conclusion', max: 1 },
                            { label: 'Legal Basis', key: 'legal_basis', max: 2 },
                            { label: 'Application', key: 'application', max: 2 },
                        ].map(({ label, key, max: m }) => {
                            const val = result.breakdown?.[key] ?? 0;
                            const p = (val / m) * 100;
                            const c = SCORE_COLORS[getColorLevel(p)];
                            return (
                                <div key={key} className="bg-white/5 rounded-xl p-3">
                                    <p className={`text-lg font-bold font-mono ${c.text}`}>{val.toFixed(1)}<span className="text-xs text-white/30">/{m}%</span></p>
                                    <p className="text-xs text-white/40">{label}</p>
                                </div>
                            );
                        })}
                    </div>

                    {/* AI Feedback */}
                    {result.feedback && (
                        <div className="bg-white/5 rounded-xl p-4 text-sm text-white/70 leading-relaxed">
                            <p className="text-xs font-bold text-white/40 uppercase tracking-widest mb-2">AI Feedback</p>
                            {result.feedback}
                        </div>
                    )}
                    {result.comparison_highlight && (
                        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 text-sm text-blue-300 leading-relaxed">
                            <p className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-2">Key Comparison</p>
                            {result.comparison_highlight}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

const LexifyResults = ({ results, questions, totalTime, onReturnToDashboard }) => {
    const [expandedIdx, setExpandedIdx] = useState(null);

    const validResults = results.filter(Boolean);
    const totalScore = validResults.reduce((acc, r) => acc + (r?.score || 0), 0);
    const maxPossible = questions.length * 5;
    const totalPct = maxPossible > 0 ? (totalScore / maxPossible) * 100 : 0;
    const totalColors = SCORE_COLORS[getColorLevel(totalPct)];

    const formatTime = (secs) => {
        const h = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        const s = secs % 60;
        return `${h}h ${m}m ${s}s`;
    };

    return (
        <div className="fixed inset-0 z-[100] bg-[#0a0a1a] text-white flex flex-col overflow-hidden">
            {/* Top Bar */}
            <div className="h-14 bg-[#16213e] border-b border-white/10 flex items-center justify-between px-6 select-none shrink-0">
                <span className="font-bold text-[#e94560] tracking-widest">LEXIFY</span>
                <span className="text-sm text-white/50 font-serif">Exam Results — AI Graded</span>
                <button onClick={onReturnToDashboard} className="px-4 py-1.5 text-sm bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition">
                    Return to Dashboard
                </button>
            </div>

            <div className="flex-1 overflow-y-auto">
                {/* Total Score Header */}
                <div className="bg-gradient-to-b from-[#16213e] to-[#0a0a1a] py-12 px-8 text-center border-b border-white/10">
                    <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold border ${totalColors.border} ${totalColors.bg} mb-6`}>
                        <span className={totalColors.text}>AI GRADED RESULT</span>
                    </div>
                    <div className={`text-7xl font-bold font-mono mb-2 ${totalColors.text}`}>
                        {totalScore.toFixed(1)}
                        <span className="text-2xl text-white/20">/{maxPossible}%</span>
                    </div>
                    <p className="text-white/40 text-lg">{totalPct.toFixed(1)}% Total Score</p>

                    {/* Score bar */}
                    <div className="max-w-md mx-auto mt-6">
                        <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                            <div className={`h-full ${totalColors.bar} rounded-full transition-all`} style={{ width: `${totalPct}%` }} />
                        </div>
                    </div>

                    {/* Stats row */}
                    <div className="flex justify-center gap-8 mt-8 text-sm">
                        <div><p className="text-white/30 text-xs uppercase tracking-widest">Questions</p><p className="font-bold">{questions.length}</p></div>
                        <div><p className="text-white/30 text-xs uppercase tracking-widest">Answered</p><p className="font-bold">{validResults.length}</p></div>
                        <div><p className="text-white/30 text-xs uppercase tracking-widest">Time Used</p><p className="font-bold">{totalTime ? formatTime(totalTime) : '—'}</p></div>
                    </div>

                    <div className="mt-8 max-w-sm mx-auto bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 text-xs text-amber-300 text-left">
                        <strong>Disclaimer:</strong> This AI grading is for practice purposes only and does not reflect official Bar Exam scores. Results are generated by Gemini AI based on the provided suggested answers.
                    </div>
                </div>

                {/* Per-Question Results */}
                <div className="max-w-3xl mx-auto px-6 py-8 space-y-4">
                    <h2 className="text-sm font-bold text-white/40 uppercase tracking-widest mb-4">Per-Question Breakdown</h2>
                    {questions.map((q, i) => (
                        <ScoreCard
                            key={i}
                            index={i}
                            question={q}
                            result={results[i]}
                            expanded={expandedIdx === i}
                            onToggle={() => setExpandedIdx(expandedIdx === i ? null : i)}
                        />
                    ))}
                </div>

                {/* Footer CTA */}
                <div className="text-center py-12">
                    <button onClick={onReturnToDashboard} className="px-10 py-3 bg-[#e94560] hover:bg-[#c73652] text-white font-bold rounded-xl transition shadow-lg shadow-[#e94560]/20 active:scale-95">
                        Return to Dashboard
                    </button>
                </div>
            </div>
        </div>
    );
};

export default LexifyResults;
