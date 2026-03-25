import React, { useState } from 'react';

const SCORE_COLORS = {
    high: { bar: 'bg-green-500', text: 'text-green-400', border: 'border-green-500/30', bg: 'bg-green-500/10' },
    mid: { bar: 'bg-yellow-500', text: 'text-yellow-400', border: 'border-yellow-500/30', bg: 'bg-yellow-500/10' },
    low: { bar: 'bg-red-500', text: 'text-red-400', border: 'border-red-500/30', bg: 'bg-red-500/10' },
};

const getColorLevel = (pct) => {
    if (pct >= 75) return 'high'; // Passing threshold 2026 is 75%
    if (pct >= 50) return 'mid';  // Passing sub threshold
    return 'low';
};

const SUBJECT_WEIGHTS = [
    { key: 'POLITICAL', label: 'Political & Public International Law', weight: 0.15 },
    { key: 'COMMERCIAL', label: 'Commercial & Taxation Laws', weight: 0.20 },
    { key: 'TAXATION', label: 'Commercial & Taxation Laws', weight: 0.20 },
    { key: 'CIVIL', label: 'Civil Law; Land Titles & Deeds', weight: 0.20 },
    { key: 'LAND TITLES', label: 'Civil Law; Land Titles & Deeds', weight: 0.20 },
    { key: 'LABOR', label: 'Labor Law & Social Legislation', weight: 0.10 },
    { key: 'CRIMINAL', label: 'Criminal Law', weight: 0.10 },
    { key: 'REMEDIAL', label: 'Remedial Law; Ethics', weight: 0.25 },
    { key: 'ETHICS', label: 'Remedial Law; Ethics', weight: 0.25 }
];

const getWeightForLabel = (label = '') => {
    const check = label.toUpperCase();
    const match = SUBJECT_WEIGHTS.find(w => check.includes(w.key));
    return match ? match.weight : 0.20; // Default fallback to 20%
};

const ScoreCard = ({ result, index, question, expanded, onToggle }) => {
    if (!result) return null;

    const max = 5;
    const pct = ((result.score / max) * 100);
    const colors = SCORE_COLORS[getColorLevel(pct)];

    return (
        <div className={`border ${colors.border} ${colors.bg} rounded-2xl overflow-hidden transition-all shadow-md`}>
            {/* Card Header */}
            <button onClick={onToggle} className="w-full flex items-center justify-between p-5 text-left hover:bg-white/5 transition">
                <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-xl border-2 ${colors.border} flex items-center justify-center`}>
                        <span className="font-mono font-bold text-sm text-white">{index + 1}</span>
                    </div>
                    <div>
                        <p className="text-xs text-white/40 uppercase tracking-widest">{question?.subject || `Question ${index + 1}`}</p>
                        <p className="text-white font-medium text-sm mt-0.5 line-clamp-1">Answer Preview</p>
                    </div>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                    <div className="text-right">
                        <p className={`text-2xl font-bold font-mono ${colors.text}`}>{result.score.toFixed(1)}</p>
                        <p className="text-xs text-white/30">out of 5 pts</p>
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
                            <span>Rating</span><span>{pct.toFixed(0)}%</span>
                        </div>
                        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className={`h-full ${colors.bar} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                        </div>
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

const LexifyResults = ({ results, questions, totalTime, onReturnToDashboard, examLabel, error }) => {
    const [expandedIdx, setExpandedIdx] = useState(null);

    const validResults = results.filter(Boolean);
    const totalScore = validResults.reduce((acc, r) => acc + (r?.score || 0), 0); // Out of 100 possible (20 questions * 5)
    const maxPossible = questions.length * 5;
    
    // Layer A - Raw % Score
    const rawScorePct = maxPossible > 0 ? (totalScore / maxPossible) * 100 : 0;
    
    // Layer B - Weight Factor
    const weightFactor = getWeightForLabel(examLabel);
    const weightedContribution = rawScorePct * weightFactor;

    const passingThreshold = 75.0;
    const isDisqualified = rawScorePct < 50.0;

    const totalColors = SCORE_COLORS[rawScorePct >= passingThreshold ? 'high' : rawScorePct >= 50 ? 'mid' : 'low'];

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
                <span className="text-sm text-white/50 font-serif">2026 Grading System #SuccessAchievedthroughMerit</span>
                <button onClick={onReturnToDashboard} className="px-4 py-1.5 text-sm bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition">
                    Return to Dashboard
                </button>
            </div>

            <div className="flex-1 overflow-y-auto">
                {/* Global Error Banner */}
                {error && (
                    <div className="max-w-2xl mx-auto mt-6 bg-red-500/20 border border-red-500/40 rounded-xl px-5 py-3 text-red-300 text-xs flex items-center gap-3">
                        <span className="text-xl">⚠️</span>
                        <div>
                            <p className="font-bold text-red-400">System Warning during Grading</p>
                            <p className="opacity-80">{error}</p>
                        </div>
                    </div>
                )}

                {/* Total Score Header */}
                <div className="bg-gradient-to-b from-[#16213e] to-[#0a0a1a] py-12 px-8 text-center border-b border-white/10">
                    <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold border ${totalColors.border} ${totalColors.bg} mb-6`}>
                        <span className={totalColors.text}>2026 RAW SUBJECT SCORE</span>
                    </div>
                    <div className={`text-7xl font-bold font-mono mb-2 ${totalColors.text}`}>
                        {rawScorePct.toFixed(1)}%
                    </div>
                    <p className="text-white/40 text-sm mt-1 uppercase tracking-wider">
                        Layer B Contribution: {weightedContribution.toFixed(2)} pts (Weight: {(weightFactor * 100).toFixed(0)}%)
                    </p>

                    {/* Disqualification Flag Banner */}
                    {isDisqualified && (
                        <div className="mt-5 max-w-md mx-auto bg-red-500/20 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-xs flex items-center gap-2 justify-center">
                            <span>🚨 Disqualification Rule: Raw score is &lt; 50% (Rule 138)</span>
                        </div>
                    )}

                    {/* Passing Indicator */}
                    {!isDisqualified && rawScorePct >= passingThreshold && (
                        <div className="mt-5 max-w-sm mx-auto bg-green-500/20 border border-green-500/30 rounded-xl px-4 py-2 text-green-400 text-xs flex items-center gap-2 justify-center">
                            <span>✅ Above 2026 Passing Threshold ({passingThreshold}%)</span>
                        </div>
                    )}

                    {/* Stats row */}
                    <div className="flex justify-center gap-8 mt-8 text-sm">
                        <div><p className="text-white/30 text-xs uppercase tracking-widest">Questions</p><p className="font-bold">{questions.length}</p></div>
                        <div><p className="text-white/30 text-xs uppercase tracking-widest">Answered</p><p className="font-bold">{validResults.length}</p></div>
                        <div><p className="text-white/30 text-xs uppercase tracking-widest">Time Used</p><p className="font-bold">{totalTime ? formatTime(totalTime) : '—'}</p></div>
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
