import React, { useRef, useEffect } from 'react';

const LexifyWorkspace = ({ question, currentIndex, userAnswer, setUserAnswer, totalQuestions, onPrev, onNext, spellCheck }) => {
    const editorRef = useRef(null);

    // Restore answer content when switching questions
    useEffect(() => {
        if (editorRef.current && editorRef.current.innerHTML !== userAnswer) {
            editorRef.current.innerHTML = userAnswer || "";
        }
    }, [currentIndex]);

    const handleInput = () => {
        if (editorRef.current) {
            setUserAnswer(editorRef.current.innerHTML);
        }
    };

    // Ctrl/Cmd keyboard shortcuts for formatting
    const handleKeyDown = (e) => {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 'b': e.preventDefault(); document.execCommand('bold', false, null); break;
                case 'i': e.preventDefault(); document.execCommand('italic', false, null); break;
                case 'u': e.preventDefault(); document.execCommand('underline', false, null); break;
                default: break;
            }
        }
    };

    const handleFormat = (command, value = null) => {
        document.execCommand(command, false, value);
        if (editorRef.current) editorRef.current.focus();
    };

    // Highlight selected text yellow (Examplify feature)
    const applyHighlight = () => {
        const selection = window.getSelection();
        if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return;
        try {
            const range = selection.getRangeAt(0);
            const span = document.createElement('span');
            span.style.backgroundColor = 'rgba(250,204,21,0.4)';
            span.className = 'lexify-highlight';
            range.surroundContents(span);
            selection.removeAllRanges();
            if (editorRef.current) setUserAnswer(editorRef.current.innerHTML);
        } catch (e) {
            // May fail when selection spans multiple elements
        }
    };

    if (!question) return <div className="flex-1 flex items-center justify-center text-white/30">Loading Question...</div>;

    // Strip HTML tags for character/word count
    const plainText = userAnswer ? userAnswer.replace(/<[^>]*>?/gm, '').replace(/&nbsp;/g, ' ') : '';
    const charCount = plainText.length;
    const wordCount = plainText.trim() ? plainText.trim().split(/\s+/).length : 0;
    const isNearLimit = charCount > 90000;

    return (
        <div className="flex-1 flex flex-col min-w-0 bg-white shadow-inner relative overflow-hidden">

            {/* PANE 1: Question Area (Top Half) */}
            <div className="h-1/2 border-b-2 border-gray-200 flex flex-col bg-[#fafafa]">
                {/* Question Header */}
                <div className="flex items-center justify-between px-5 py-2.5 bg-gray-100 border-b border-gray-200">
                    <span className="font-bold text-gray-600 uppercase tracking-widest text-xs font-serif">
                        Question {currentIndex + 1} of {totalQuestions}
                        {question.subject && <span className="ml-2 font-normal text-gray-400">— {question.subject}</span>}
                    </span>
                    <button
                        onClick={applyHighlight}
                        className="px-2.5 py-1 bg-yellow-100 border border-yellow-300 text-yellow-800 text-xs rounded-lg hover:bg-yellow-200 transition flex items-center gap-1.5"
                        title="Highlight selected text"
                    >
                        🖊 Highlight
                    </button>
                </div>

                {/* Question Text */}
                <div className="flex-1 p-8 overflow-y-auto text-base leading-relaxed text-gray-800 select-text" style={{ fontFamily: '"Times New Roman", Times, serif' }}>
                    <p className="whitespace-pre-wrap">{question.text}</p>
                    {question.subQuestions && question.subQuestions.map((sub, i) => (
                        <p key={i} className="whitespace-pre-wrap mt-6 pt-6 border-t border-gray-200">{sub.text}</p>
                    ))}
                </div>
            </div>

            {/* PANE 2: Answer Editor (Bottom Half) */}
            <div className="flex-1 flex flex-col bg-white">
                
                {/* Formatting Toolbar */}
                <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200 shrink-0">
                    <div className="flex items-center gap-0.5">
                        {/* Text Formatting */}
                        <button onClick={() => handleFormat('bold')}         className="w-8 h-8 font-bold font-serif border border-transparent hover:border-gray-300 hover:bg-white rounded text-gray-700 text-sm" title="Bold (Ctrl+B)">B</button>
                        <button onClick={() => handleFormat('italic')}       className="w-8 h-8 italic font-serif border border-transparent hover:border-gray-300 hover:bg-white rounded text-gray-700 text-sm" title="Italic (Ctrl+I)">I</button>
                        <button onClick={() => handleFormat('underline')}    className="w-8 h-8 underline border border-transparent hover:border-gray-300 hover:bg-white rounded text-gray-700 text-sm" title="Underline (Ctrl+U)">U</button>
                        <div className="w-px h-5 bg-gray-300 mx-1.5" />
                        {/* Superscript / Subscript */}
                        <button onClick={() => handleFormat('superscript')}  className="w-8 h-8 border border-transparent hover:border-gray-300 hover:bg-white rounded text-gray-700 text-xs" title="Superscript">x²</button>
                        <button onClick={() => handleFormat('subscript')}    className="w-8 h-8 border border-transparent hover:border-gray-300 hover:bg-white rounded text-gray-700 text-xs" title="Subscript">x₂</button>
                        <div className="w-px h-5 bg-gray-300 mx-1.5" />
                        {/* Lists */}
                        <button onClick={() => handleFormat('insertUnorderedList')} className="px-2.5 h-8 text-xs border border-transparent hover:border-gray-300 hover:bg-white rounded text-gray-700" title="Bullet List">• List</button>
                        <button onClick={() => handleFormat('insertOrderedList')}   className="px-2.5 h-8 text-xs border border-transparent hover:border-gray-300 hover:bg-white rounded text-gray-700" title="Numbered List">1. List</button>
                    </div>

                    {/* Right: Word/Char count + autosave status */}
                    <div className="flex items-center gap-4 text-xs text-gray-400 shrink-0">
                        <span className={isNearLimit ? 'text-orange-500 font-bold' : ''}>
                            {wordCount} words · <span className={isNearLimit ? 'text-orange-500' : ''}>{charCount.toLocaleString()} / 100,000</span> chars
                        </span>
                        <div className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-green-500" />
                            Auto-Saved
                        </div>
                    </div>
                </div>

                {/* Answer Editor Area */}
                <div className="flex-1 overflow-hidden relative p-0">
                    {(!userAnswer || plainText.trim() === '') && (
                        <div className="absolute top-6 left-8 text-gray-300 pointer-events-none text-base font-serif leading-relaxed select-none">
                            Type your answer here...
                        </div>
                    )}
                    <div
                        ref={editorRef}
                        contentEditable={true}
                        spellCheck={spellCheck}
                        onInput={handleInput}
                        onKeyDown={handleKeyDown}
                        className="w-full h-full outline-none text-base leading-relaxed text-gray-900 overflow-y-auto p-6"
                        style={{ fontFamily: '"Times New Roman", Times, serif', minHeight: '100%' }}
                    />
                </div>

                {/* Bottom Navigation */}
                <div className="flex items-center justify-between px-6 py-3 bg-gray-50 border-t border-gray-200 shrink-0">
                    <button
                        onClick={onPrev}
                        disabled={currentIndex === 0}
                        className="flex items-center gap-2 px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition text-gray-600"
                    >
                        ← Previous
                    </button>
                    <span className="text-xs text-gray-400">{currentIndex + 1} / {totalQuestions}</span>
                    <button
                        onClick={onNext}
                        disabled={currentIndex === totalQuestions - 1}
                        className="flex items-center gap-2 px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition text-gray-600"
                    >
                        Next →
                    </button>
                </div>
            </div>
        </div>
    );
};

export default LexifyWorkspace;
