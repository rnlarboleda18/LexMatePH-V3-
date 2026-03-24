import React, { useRef, useEffect } from 'react';

const LexifyWorkspace = ({ question, currentIndex, userAnswer, setUserAnswer, totalQuestions, onPrev, onNext, spellCheck, isFlagged, onToggleFlag }) => {
    const editorRef = useRef(null);

    useEffect(() => {
        if (editorRef.current && editorRef.current.innerHTML !== userAnswer) {
            editorRef.current.innerHTML = userAnswer || "";
        }
    }, [currentIndex, userAnswer]); // added userAnswer to dependency for sync

    const handleInput = () => {
        if (editorRef.current) {
            setUserAnswer(editorRef.current.innerHTML);
        }
    };

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

    const applyHighlight = () => {
        const selection = window.getSelection();
        if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return;
        try {
            const range = selection.getRangeAt(0);
            const span = document.createElement('span');
            span.style.backgroundColor = '#fff200'; // Yellow Highlight
            range.surroundContents(span);
            selection.removeAllRanges();
            if (editorRef.current) setUserAnswer(editorRef.current.innerHTML);
        } catch (e) {}
    };

    if (!question) return <div className="flex-1 flex items-center justify-center text-slate-400">Loading Question...</div>;

    const plainText = userAnswer ? userAnswer.replace(/<[^>]*>?/gm, '').replace(/&nbsp;/g, ' ') : '';
    const charCount = plainText.length;

    return (
        <div className="flex-1 flex flex-col min-w-0 bg-white relative overflow-hidden font-sans">

            {/* PANE 1: Question Area Item 5 & 6 */}
            <div className="h-1/2 border-bottom border-[#d5dbe1] flex flex-col bg-white">
                {/* Question Header Item 6 */}
                <div className="flex items-center gap-4 px-6 py-2 bg-white border-b border-[#e5e9ed]">
                    <span className="text-sm font-bold text-slate-800 flex items-center gap-1 cursor-pointer">
                        Question {currentIndex + 1} <span className="text-[10px] text-slate-500">▾</span>
                    </span>

                    {/* Pill Flag Trigger */}
                    <button
                        onClick={onToggleFlag}
                        className={`px-3 py-1 text-[10px] font-bold uppercase rounded-full shadow-sm transition-all ${
                            isFlagged 
                                ? 'bg-[#f7941d] text-white hover:bg-[#e08518]' 
                                : 'bg-[#e5e9ed] text-slate-600 hover:bg-slate-200'
                        }`}
                    >
                        {isFlagged ? 'UNFLAG QUESTION' : 'FLAG QUESTION'}
                    </button>

                    {/* Highlight Tool Item 6/7 */}
                    <div className="flex items-center gap-1 ml-auto">
                        <button onClick={applyHighlight} className="p-1 rounded hover:bg-slate-100 text-slate-500" title="Highlight">
                            <span className="text-sm">✏️</span>
                        </button>
                        <button onClick={() => alert('Eraser tool clicked')} className="p-1 rounded hover:bg-slate-100 text-slate-500" title="Eraser">
                            <span className="text-sm">🧼</span>
                        </button>
                    </div>
                </div>

                {/* Question Text Item 5 */}
                <div className="flex-1 p-6 overflow-y-auto text-[15px] leading-relaxed text-slate-800 select-text font-serif bg-white">
                    <p className="whitespace-pre-wrap">{question.text}</p>
                    {question.subQuestions && question.subQuestions.map((sub, i) => (
                        <p key={i} className="whitespace-pre-wrap mt-6 pt-6 border-t border-[#e5e9ed]">{sub.text}</p>
                    ))}
                </div>
            </div>

            {/* PANE 2: Answer Editor area Item 8 & 9 */}
            <div className="flex-1 flex flex-col bg-[#f4f6f8] border-t-2 border-[#d5dbe1]">
                
                {/* Formatting Toolbar Item 8 */}
                <div className="flex items-center gap-1 px-4 py-1 bg-[#eaeef1] border-b border-[#d5dbe1] shrink-0 text-slate-700">
                    <div className="bg-white border border-[#c9d2db] rounded px-2 py-1 flex items-center gap-1 text-xs cursor-pointer">
                        Arial <span className="scale-75 text-slate-400">▾</span>
                    </div>
                    <div className="bg-white border border-[#c9d2db] rounded px-2 py-1 flex items-center gap-1 text-xs cursor-pointer">
                        12pt <span className="scale-75 text-slate-400">▾</span>
                    </div>
                    <div className="bg-white border border-[#c9d2db] rounded px-2 py-1 flex items-center gap-1 text-xs cursor-pointer">
                        Format <span className="scale-75 text-slate-400">▾</span>
                    </div>

                    <div className="w-px h-4 bg-slate-300 mx-1" />

                    {['✂️', '🎨', '↩️', '↪️'].map((icon, i) => (
                        <button key={i} className="p-1 hover:bg-white rounded hover:shadow-sm">
                            <span className="text-sm">{icon}</span>
                        </button>
                    ))}

                    <div className="w-px h-4 bg-slate-300 mx-1" />

                    <button onClick={() => handleFormat('bold')} className="font-bold px-1.5 hover:bg-white rounded">B</button>
                    <button onClick={() => handleFormat('italic')} className="italic px-1.5 hover:bg-white rounded">I</button>
                    <button onClick={() => handleFormat('underline')} className="underline px-1.5 hover:bg-white rounded">U</button>
                </div>

                {/* Answer Editor Area */}
                <div className="flex-1 bg-white border-b border-[#d5dbe1] overflow-hidden relative">
                    <div
                        ref={editorRef}
                        contentEditable={true}
                        spellCheck={spellCheck}
                        onInput={handleInput}
                        onKeyDown={handleKeyDown}
                        className="w-full h-full outline-none text-[15px] leading-relaxed text-slate-900 overflow-y-auto p-6 font-serif"
                    />
                </div>

                {/* Status Bar / Character Count Item 9 */}
                <div className="flex items-center px-4 py-1.5 bg-[#eaeef1] text-xs text-slate-600 font-semibold shrink-0">
                    Essay Answer <span className="text-[10px] scale-90 mx-1">📄</span> {charCount}/100000 characters
                </div>

                {/* Bottom Navigation Item 10 */}
                <div className="h-14 bg-[#d5e1ee] flex items-center justify-between px-6 shrink-0 font-sans">
                    <div className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                        {currentIndex + 1} OF {totalQuestions} QUESTIONS <span className="mx-2 text-slate-400">|</span> <span className="text-slate-500 font-normal">VERSION 2M 9.2</span>
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={onPrev}
                            disabled={currentIndex === 0}
                            className="h-10 px-8 text-sm font-bold bg-[#202936] text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#1a212c] transition-colors"
                        >
                            Previous
                        </button>
                        <button
                            onClick={onNext}
                            disabled={currentIndex === totalQuestions - 1}
                            className="h-10 px-10 text-sm font-bold bg-[#3fa9f5] text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2c98e2] transition-colors"
                        >
                            Next
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LexifyWorkspace;
