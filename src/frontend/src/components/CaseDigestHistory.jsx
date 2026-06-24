import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '@clerk/clerk-react';
import { Sparkles, Clock, AlertCircle, RefreshCw, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { apiUrl } from '../utils/apiUrl';

// Human-readable labels for backend actions
const ACTION_LABELS = {
    'digest': 'Initial Digest',
    'redigest': 'Redigest',
    'smart_backfill': 'Smart Backfill',
    'api_digest': 'Web Ad-Hoc Redigest',
    'digest_pipeline': 'Pipeline Generation',
    'manual_edit': 'Manual Edit'
};

// Human-readable labels for database fields
const FIELD_LABELS = {
    'digest_facts': 'Facts',
    'digest_issues': 'Issues',
    'digest_ruling': 'Ruling',
    'main_doctrine': 'Doctrine',
    'title': 'Title',
    'short_title': 'Short Title',
    'syllabus': 'Syllabus',
    'sc_decided_cases': 'All Fields'
};

const formatAction = (action) => {
    return ACTION_LABELS[action] || action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

const formatField = (field) => {
    return FIELD_LABELS[field] || field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

const formatDateTime = (dateStr) => {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        }) + ' ' + d.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch (e) {
        return dateStr;
    }
};

const formatModelName = (model) => {
    if (!model) return '';
    
    // Split by slash and take the last segment (e.g., publishers/google/models/gemini-3.5-flash -> gemini-3.5-flash)
    let cleanModel = model;
    if (model.includes('/')) {
        const segments = model.split('/');
        cleanModel = segments[segments.length - 1];
    }
    
    const lower = cleanModel.toLowerCase();
    
    if (lower === 'gemini-3.5-flash' || lower === 'gemini_3.5_flash' || lower === 'gemini 3.5 flash') {
        return 'Gemini 3.5 Flash';
    }
    if (lower === 'grok-4.1' || lower === 'grok_4.1' || lower === 'grok 4.1') {
        return 'Grok 4.1';
    }
    if (lower === 'claude-3-5-sonnet' || lower === 'claude-3.5-sonnet') {
        return 'Claude 3.5 Sonnet';
    }
    if (lower === 'gpt-4o' || lower === 'gpt_4o') {
        return 'GPT-4o';
    }
    if (lower === 'gpt-4-turbo' || lower === 'gpt_4_turbo') {
        return 'GPT-4 Turbo';
    }

    return cleanModel
        .replace(/[-_]/g, ' ')
        .replace(/\b([a-z])/g, c => c.toUpperCase());
};

export default function CaseDigestHistory({ caseId, currentModel, mode = 'popover' }) {
    const { getToken } = useAuth();
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isOpen, setIsPopoverOpen] = useState(false);
    const [isTimelineExpanded, setIsTimelineExpanded] = useState(false);
    const popoverRef = useRef(null);

    // Fetch history from backend
    const fetchHistory = async () => {
        if (!caseId) return;
        setLoading(true);
        setError(null);
        try {
            const token = await getToken();
            const headers = {
                'Content-Type': 'application/json'
            };
            if (token) {
                headers['X-Clerk-Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(apiUrl(`/api/ops/cases/${caseId}/digest-history`), {
                headers
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Access denied: Unauthorized. Your login session may have expired or is invalid. Please try logging out and logging back in.');
                }
                if (response.status === 403) {
                    throw new Error('Access denied (Admin only): Your account does not have admin privileges in the database.');
                }
                throw new Error(`Error: ${response.statusText} (Status ${response.status})`);
            }

            const data = await response.json();
            setHistory(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error('Failed to load digest history:', err);
            setError(err.message || 'Failed to load history');
        } finally {
            setLoading(false);
        }
    };

    // Close popover when clicking outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (popoverRef.current && !popoverRef.current.contains(event.target)) {
                setIsPopoverOpen(false);
            }
        }
        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    // Fetch history when popover opens
    const handlePopoverToggle = (e) => {
        e.stopPropagation();
        e.preventDefault();
        const nextState = !isOpen;
        setIsPopoverOpen(nextState);
        if (nextState && history.length === 0 && !loading) {
            fetchHistory();
        }
    };

    // Fetch history when timeline expands
    const handleTimelineToggle = (e) => {
        e.stopPropagation();
        e.preventDefault();
        const nextState = !isTimelineExpanded;
        setIsTimelineExpanded(nextState);
        if (nextState && history.length === 0 && !loading) {
            fetchHistory();
        }
    };

    if (mode === 'popover' || mode === 'header' || mode === 'badge') {
        return (
            <span className="relative inline-block" ref={popoverRef}>
                {mode === 'header' ? (
                    <button
                        onClick={handlePopoverToggle}
                        className="touch-manipulation flex h-6 px-2 sm:px-2.5 sm:h-7 shrink-0 items-center gap-1 sm:gap-1.5 rounded-full border border-violet-200/80 bg-violet-50/90 text-[10px] sm:text-[11px] font-black uppercase tracking-wider text-violet-600 transition-all hover:bg-violet-100 active:scale-95 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-300 dark:hover:bg-violet-900/60 shadow-sm focus:outline-none"
                        title="Click to view AI Digestion Audit History"
                    >
                        <Sparkles size={11} className="inline align-middle animate-pulse text-violet-500" />
                        <span>{formatModelName(currentModel)}</span>
                    </button>
                ) : mode === 'badge' ? (
                    <button
                        onClick={handlePopoverToggle}
                        className="touch-manipulation flex h-[22px] px-2.5 shrink-0 items-center gap-1.5 rounded-full border border-violet-200/80 bg-violet-50/90 text-[10px] font-extrabold uppercase tracking-wide text-violet-600 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-300 transition-all hover:bg-violet-100 active:scale-95 shadow-sm focus:outline-none"
                        title="Click to view AI Digestion Audit History"
                    >
                        <Sparkles size={10} className="inline align-middle animate-pulse text-violet-500 dark:text-violet-400" />
                        <span>{formatModelName(currentModel)}</span>
                    </button>
                ) : (
                    <button
                        onClick={handlePopoverToggle}
                        className="inline-flex items-center gap-1 text-violet-600 dark:text-violet-400 font-bold hover:text-violet-800 dark:hover:text-violet-300 hover:underline transition-colors focus:outline-none"
                        title="Click to view AI Digestion Audit History"
                    >
                        <Sparkles size={10} className="inline align-middle animate-pulse" />
                        <span>{formatModelName(currentModel)}</span>
                    </button>
                )}

                {isOpen && createPortal(
                    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
                        {/* Backdrop with premium blur */}
                        <div 
                            className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity animate-fadeIn"
                            onClick={(e) => {
                                e.stopPropagation();
                                e.preventDefault();
                                setIsPopoverOpen(false);
                            }}
                        />
                        
                        {/* Centered Premium Micro-Modal Card */}
                        <div 
                            className="relative w-full max-w-sm bg-white dark:bg-zinc-900 border border-violet-100 dark:border-zinc-800 rounded-2xl shadow-2xl z-10 p-5 animate-scaleUp text-left"
                            onClick={(e) => {
                                e.stopPropagation();
                            }}
                        >
                            <div className="flex items-center justify-between border-b border-gray-100 dark:border-zinc-800 pb-3 mb-4">
                                <h5 className="text-[12px] font-bold text-gray-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                                    <Clock size={12} className="text-violet-500" />
                                    Digest Audit Log
                                </h5>
                                <div className="flex items-center gap-2">
                                    <button 
                                        onClick={(e) => { e.stopPropagation(); fetchHistory(); }} 
                                        className="text-gray-400 hover:text-violet-600 dark:hover:text-violet-400 transition-colors p-1"
                                        title="Refresh"
                                        disabled={loading}
                                    >
                                        <RefreshCw size={12} className={`${loading ? 'animate-spin' : ''}`} />
                                    </button>
                                    <button 
                                        onClick={(e) => { e.stopPropagation(); setIsPopoverOpen(false); }} 
                                        className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 font-bold transition-colors text-xs p-1"
                                        title="Close"
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>

                            {loading && (
                                <div className="flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400">
                                    <RefreshCw size={24} className="animate-spin text-violet-500 mb-2" />
                                    <span className="text-[11px] font-medium">Fetching history logs...</span>
                                </div>
                            )}

                            {error && (
                                <div className="flex items-center gap-2 text-red-500 dark:text-red-400 py-4 text-[11px] font-medium leading-normal">
                                    <AlertCircle size={14} className="shrink-0" />
                                    <span>{error}</span>
                                </div>
                            )}

                            {!loading && !error && history.length === 0 && (
                                <div className="text-center py-6 text-[11px] text-gray-500 dark:text-gray-400 font-medium">
                                    No history records found.
                                </div>
                            )}

                            {!loading && !error && history.length > 0 && (
                                <div className="max-h-60 overflow-y-auto custom-scrollbar pr-1 flex flex-col gap-3">
                                    {history.map((item, idx) => (
                                        <div 
                                            key={item.id || idx} 
                                            className="text-[11px] border-l-2 border-violet-500/30 hover:border-violet-500 dark:border-zinc-800 dark:hover:border-violet-400 pl-2.5 py-1.5 transition-all hover:bg-neutral-50 dark:hover:bg-zinc-800/40 rounded-r-md"
                                        >
                                            <div className="flex items-center justify-between font-bold text-gray-800 dark:text-zinc-200">
                                                <span className="text-violet-600 dark:text-violet-400">
                                                    {formatAction(item.action)}
                                                </span>
                                                <span className="text-[10px] text-gray-400 dark:text-gray-500 font-normal">
                                                    {formatDateTime(item.created_at || item.created_at_str)}
                                                </span>
                                            </div>
                                            
                                            <div className="mt-1 font-mono text-[10px] text-gray-500 dark:text-gray-400 flex items-center gap-1 flex-wrap">
                                                <Sparkles size={9} className="text-gray-400" />
                                                <span>{item.ai_model || 'Unknown Model'}</span>
                                            </div>

                                            {item.fields_changed && item.fields_changed.length > 0 && (
                                                <div className="mt-1.5 flex flex-wrap gap-1">
                                                    {item.fields_changed.map((field, fIdx) => (
                                                        <span 
                                                            key={fIdx} 
                                                            className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300 border border-violet-100/60 dark:border-violet-900/30"
                                                        >
                                                            {formatField(field)}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>,
                    document.body
                )}
            </span>
        );
    }

    // mode === 'timeline'
    return (
        <div className="w-full max-w-2xl mx-auto mt-6 mb-2 border border-violet-100 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 shadow-sm overflow-hidden">
            <button
                onClick={handleTimelineToggle}
                className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-neutral-50 dark:hover:bg-zinc-800/40 transition-colors border-b border-violet-50 dark:border-zinc-800"
            >
                <span className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider flex items-center gap-2">
                    <Clock size={14} className="text-violet-500" />
                    AI Digestion Audit History
                </span>
                <span className="text-gray-500 dark:text-gray-400">
                    {isTimelineExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </span>
            </button>

            {isTimelineExpanded && (
                <div className="p-4 sm:p-6 bg-neutral-50/50 dark:bg-zinc-900/50 animate-fadeIn">
                    {loading && (
                        <div className="flex flex-col items-center justify-center py-10 text-gray-500 dark:text-gray-400">
                            <RefreshCw size={24} className="animate-spin text-violet-500 mb-3" />
                            <span className="text-xs font-semibold">Loading full digestion timeline...</span>
                        </div>
                    )}

                    {error && (
                        <div className="flex items-center gap-3 text-red-500 dark:text-red-400 py-6 text-xs font-medium leading-normal justify-center">
                            <AlertCircle size={18} className="shrink-0" />
                            <span>{error}</span>
                            <button 
                                onClick={fetchHistory}
                                className="text-violet-600 dark:text-violet-400 font-semibold hover:underline"
                            >
                                Retry
                            </button>
                        </div>
                    )}

                    {!loading && !error && history.length === 0 && (
                        <div className="text-center py-8 text-xs text-gray-500 dark:text-gray-400 font-medium">
                            No history records found for this case.
                        </div>
                    )}

                    {!loading && !error && history.length > 0 && (
                        <div className="relative pl-6 border-l border-gray-200 dark:border-zinc-800 space-y-6 py-2 ml-3">
                            {history.map((item, idx) => (
                                <div key={item.id || idx} className="relative group">
                                    {/* Vertical line node circle */}
                                    <div className="absolute -left-[31px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-white dark:bg-zinc-900 border-2 border-violet-500 shadow-sm group-hover:bg-violet-500 transition-colors duration-200">
                                        <div className="h-1.5 w-1.5 rounded-full bg-violet-500 group-hover:bg-white transition-colors duration-200"></div>
                                    </div>

                                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 border border-gray-100 dark:border-zinc-800/80 bg-white dark:bg-zinc-900 p-4 rounded-xl shadow-sm hover:shadow transition-shadow">
                                        <div className="space-y-1.5">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-violet-100 dark:bg-violet-950/60 text-violet-700 dark:text-violet-300">
                                                    {formatAction(item.action)}
                                                </span>
                                                <span className="text-[11px] font-mono font-bold text-gray-700 dark:text-zinc-300 flex items-center gap-1">
                                                    <Sparkles size={11} className="text-violet-500/80" />
                                                    {item.ai_model || 'Unknown Model'}
                                                </span>
                                            </div>

                                            {item.fields_changed && item.fields_changed.length > 0 && (
                                                <div className="flex flex-wrap gap-1.5 pt-1">
                                                    <span className="text-[10px] text-gray-400 dark:text-gray-500 font-bold self-center mr-1">Modified:</span>
                                                    {item.fields_changed.map((field, fIdx) => (
                                                        <span 
                                                            key={fIdx} 
                                                            className="px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 border border-gray-200/60 dark:border-zinc-700/50"
                                                        >
                                                            {formatField(field)}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>

                                        <div className="text-[11px] text-gray-400 dark:text-gray-500 font-semibold sm:text-right shrink-0 flex items-center gap-1 sm:block">
                                            <Clock size={11} className="inline sm:hidden text-gray-400" />
                                            <span>{formatDateTime(item.created_at || item.created_at_str)}</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
