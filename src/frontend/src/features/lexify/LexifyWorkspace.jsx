import React, { useRef, useEffect, useState } from 'react';

const LexifyWorkspace = ({ question, currentIndex, userAnswer, setUserAnswer, totalQuestions, onPrev, onNext, spellCheck, isFlagged, onToggleFlag }) => {
    const editorRef = useRef(null);

    // Dropdown state for toolbar
    const [showFontMenu, setShowFontMenu] = useState(false);
    const [showSizeMenu, setShowSizeMenu] = useState(false);
    const [showFormatMenu, setShowFormatMenu] = useState(false);

    // Current selection tracking to show active text in dropdown
    const [currentFont, setCurrentFont] = useState('Arial');
    const [currentSize, setCurrentSize] = useState('12pt');
    const [currentFormat, setCurrentFormat] = useState('Paragraph');

    useEffect(() => {
        if (editorRef.current && editorRef.current.innerHTML !== userAnswer) {
            editorRef.current.innerHTML = userAnswer || "";
        }
    }, [currentIndex, userAnswer]);

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
        if (editorRef.current) editorRef.current.focus();
        document.execCommand(command, false, value);
    };

    const applyHighlight = () => {
        document.execCommand('backColor', false, '#a7f3d0');
    };

    const removeHighlight = () => {
        document.execCommand('removeFormat');
    };

    if (!question) return <div className="flex-1 flex items-center justify-center text-slate-400">Loading Question...</div>;

    const plainText = userAnswer ? userAnswer.replace(/<[^>]*>?/gm, '').replace(/&nbsp;/g, ' ') : '';
    const charCount = plainText.length;

    return (
        <div className="flex-1 flex flex-col min-w-0 bg-white relative overflow-hidden font-sans">

            {/* PANE 1: Question Area */}
            <div className="h-1/2 border-bottom border-[#d5dbe1] flex flex-col bg-white">
                <div className="flex items-center gap-4 px-6 py-2 bg-white border-b border-[#e5e9ed]">
                    <span className="text-sm font-bold text-slate-800 flex items-center gap-1 cursor-pointer">
                        Question {currentIndex + 1} <span className="text-[10px] text-slate-500">▾</span>
                    </span>

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

                    <div className="flex items-center gap-1">
                        <button 
                            onClick={applyHighlight} 
                            onMouseDown={(e) => e.preventDefault()}
                            className="p-1 rounded hover:bg-slate-100 text-slate-500" 
                            title="Highlight selection"
                        >
                            <span className="text-sm">✏️</span>
                        </button>
                        <button 
                            onClick={removeHighlight} 
                            onMouseDown={(e) => e.preventDefault()}
                            className="p-1 rounded hover:bg-slate-100 text-slate-500" 
                            title="Erase Highlight"
                        >
                            <span className="text-sm">🧼</span>
                        </button>
                    </div>
                </div>

                <div 
                    contentEditable={true} 
                    onKeyDown={(e) => e.preventDefault()} 
                    className="flex-1 p-6 overflow-y-auto text-[15px] leading-relaxed text-slate-800 select-text font-serif bg-white outline-none"
                >
                    <div className="whitespace-pre-wrap">{question.text}</div>
                    {question.subQuestions && question.subQuestions.map((sub, i) => (
                        <div key={i} className="whitespace-pre-wrap mt-6 pt-6 border-t border-[#e5e9ed]">{sub.text}</div>
                    ))}
                </div>
            </div>

            {/* PANE 2: Answer Editor area */}
            <div className="flex-1 flex flex-col bg-[#f4f6f8] border-t-2 border-[#d5dbe1]">
                
                {/* Formatting Toolbar */}
                <div className="flex items-center gap-1 px-4 py-1 bg-[#eaeef1] border-b border-[#d5dbe1] shrink-0 text-slate-700 relative z-50">
                    
                    {/* Font Dropdown */}
                    <div className="relative">
                        <button 
                            onClick={() => { setShowFontMenu(!showFontMenu); setShowSizeMenu(false); setShowFormatMenu(false); }}
                            onMouseDown={(e) => e.preventDefault()}
                            className="bg-white border border-[#c9d2db] rounded px-2 py-1 flex items-center gap-1 text-xs cursor-pointer hover:bg-slate-50 font-sans"
                        >
                            {currentFont} <span className="scale-75 text-slate-400">▾</span>
                        </button>
                        {showFontMenu && (
                            <div className="absolute left-0 top-7 bg-white border border-[#c9d2db] shadow-xl rounded py-1 w-36 z-50 overflow-hidden">
                                {['Arial', 'Times New Roman', 'Courier New', 'Georgia'].map(f => (
                                    <button 
                                        key={f} 
                                        onClick={() => { handleFormat('fontName', f); setCurrentFont(f); setShowFontMenu(false); }}
                                        onMouseDown={(e) => e.preventDefault()}
                                        className="w-full text-left px-4 py-1.5 text-xs hover:bg-[#3fa9f5] hover:text-white transition-colors"
                                        style={{ fontFamily: f }}
                                    >
                                        {f}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Size Dropdown */}
                    <div className="relative">
                        <button 
                            onClick={() => { setShowSizeMenu(!showSizeMenu); setShowFontMenu(false); setShowFormatMenu(false); }}
                            onMouseDown={(e) => e.preventDefault()}
                            className="bg-white border border-[#c9d2db] rounded px-2 py-1 flex items-center gap-1 text-xs cursor-pointer hover:bg-slate-50 font-sans"
                        >
                            {currentSize} <span className="scale-75 text-slate-400">▾</span>
                        </button>
                        {showSizeMenu && (
                            <div className="absolute left-0 top-7 bg-white border border-[#c9d2db] shadow-xl rounded py-1 w-24 z-50 overflow-hidden">
                                {[
                                    { label: '10pt', cmd: '2' },
                                    { label: '12pt', cmd: '3' },
                                    { label: '14pt', cmd: '4' },
                                    { label: '18pt', cmd: '5' }
                                ].map(({ label, cmd }) => (
                                    <button 
                                        key={cmd} 
                                        onClick={() => { handleFormat('fontSize', cmd); setCurrentSize(label); setShowSizeMenu(false); }}
                                        onMouseDown={(e) => e.preventDefault()}
                                        className="w-full text-left px-4 py-1.5 text-xs hover:bg-[#3fa9f5] hover:text-white transition-colors"
                                    >
                                        {label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Format Dropdown */}
                    <div className="relative">
                        <button 
                            onClick={() => { setShowFormatMenu(!showFormatMenu); setShowFontMenu(false); setShowSizeMenu(false); }}
                            onMouseDown={(e) => e.preventDefault()}
                            className="bg-white border border-[#c9d2db] rounded px-2 py-1 flex items-center gap-1 text-xs cursor-pointer hover:bg-slate-50 font-sans"
                        >
                            {currentFormat} <span className="scale-75 text-slate-400">▾</span>
                        </button>
                        {showFormatMenu && (
                            <div className="absolute left-0 top-7 bg-white border border-[#c9d2db] shadow-xl rounded py-1 w-32 z-50 overflow-hidden">
                                {[
                                    { label: 'Paragraph', cmd: 'P' },
                                    { label: 'Heading 1', cmd: 'H1' },
                                    { label: 'Heading 2', cmd: 'H2' },
                                    { label: 'Preformatted', cmd: 'PRE' }
                                ].map(({ label, cmd }) => (
                                    <button 
                                        key={cmd} 
                                        onClick={() => { handleFormat('formatBlock', cmd); setCurrentFormat(label); setShowFormatMenu(false); }}
                                        onMouseDown={(e) => e.preventDefault()}
                                        className="w-full text-left px-4 py-1.5 text-xs hover:bg-[#3fa9f5] hover:text-white transition-colors"
                                    >
                                        {label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="w-px h-4 bg-slate-300 mx-1" />

                    <button onClick={() => handleFormat('cut')} onMouseDown={(e) => e.preventDefault()} className="p-1 hover:bg-white rounded hover:shadow-sm" title="Cut">✂️</button>
                    
                    {/* Color Picker Palette */}
                    <div className="relative flex items-center">
                        <button 
                            onClick={() => document.getElementById('fontColorPicker').click()} 
                            onMouseDown={(e) => e.preventDefault()} 
                            className="p-1 hover:bg-white rounded hover:shadow-sm" 
                            title="Font Color"
                        >
                            🎨
                        </button>
                        <input 
                            id="fontColorPicker"
                            type="color"
                            className="absolute opacity-0 w-0 h-0"
                            onChange={(e) => handleFormat('foreColor', e.target.value)}
                        />
                    </div>

                    <button onClick={() => handleFormat('undo')} onMouseDown={(e) => e.preventDefault()} className="p-1 hover:bg-white rounded hover:shadow-sm" title="Undo">Undo</button>
                    <button onClick={() => handleFormat('redo')} onMouseDown={(e) => e.preventDefault()} className="p-1 hover:bg-white rounded hover:shadow-sm" title="Redo">Redo</button>

                    <div className="w-px h-4 bg-slate-300 mx-1" />

                    <button onClick={() => handleFormat('bold')} onMouseDown={(e) => e.preventDefault()} className="font-bold px-1.5 hover:bg-white rounded text-black" title="Bold">B</button>
                    <button onClick={() => handleFormat('italic')} onMouseDown={(e) => e.preventDefault()} className="italic px-1.5 hover:bg-white rounded" title="Italic">I</button>
                    <button onClick={() => handleFormat('underline')} onMouseDown={(e) => e.preventDefault()} className="underline px-1.5 hover:bg-white rounded" title="Underline">U</button>
                </div>

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

                <div className="flex items-center px-4 py-1.5 bg-[#eaeef1] text-xs text-slate-600 font-semibold shrink-0">
                    Essay Answer <span className="text-[10px] scale-90 mx-1">📄</span> {charCount}/100000 characters
                </div>

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
