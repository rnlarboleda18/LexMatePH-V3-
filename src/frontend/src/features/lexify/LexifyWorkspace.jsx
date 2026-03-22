import React, { useRef, useEffect } from 'react';

// Using a simple contenteditable div as a lightweight Quill.js alternative to strictly control attributes
const LexifyWorkspace = ({ question, currentIndex, userAnswer, setUserAnswer }) => {
    const editorRef = useRef(null);

    // Initial content setup
    useEffect(() => {
        if (editorRef.current && editorRef.current.innerHTML !== userAnswer) {
            editorRef.current.innerHTML = userAnswer || "";
        }
    }, [currentIndex]); // Only on question change

    const handleInput = () => {
        if (editorRef.current) {
            setUserAnswer(editorRef.current.innerHTML);
        }
    };

    // Keyboard Shortcuts for Basic Formatting
    const handleKeyDown = (e) => {
        if (e.ctrlKey || e.metaKey) {
            if (e.key === 'b') { e.preventDefault(); document.execCommand('bold', false, null); }
            if (e.key === 'i') { e.preventDefault(); document.execCommand('italic', false, null); }
            if (e.key === 'u') { e.preventDefault(); document.execCommand('underline', false, null); }
        }
    };

    const handleFormat = (command) => {
        document.execCommand(command, false, null);
        if (editorRef.current) { editorRef.current.focus(); }
    };

    // Very basic highlight implementation
    const applyHighlight = () => {
        const selection = window.getSelection();
        if (!selection.rangeCount) return;
        const range = selection.getRangeAt(0);
        const span = document.createElement('span');
        span.style.backgroundColor = 'yellow';
        span.className = 'lexify-highlight';
        range.surroundContents(span);
        selection.removeAllRanges();
    };

    if (!question) return <div className="flex-1 flex items-center justify-center">Loading Question...</div>;

    const charCount = userAnswer ? userAnswer.replace(/<[^>]*>?/gm, '').length : 0;

    return (
        <div className="flex-1 flex flex-col min-w-0 bg-white shadow-inner relative">
            
            {/* Split Pane 1: Question Area (Top) */}
            <div className="h-1/2 border-b border-gray-300 flex flex-col bg-[#fcfcfc]">
                {/* Header / Tools for Question */}
                <div className="flex items-center justify-between p-2 bg-gray-100 border-b border-gray-200">
                    <span className="font-bold text-gray-700 uppercase tracking-widest text-xs">Question {currentIndex + 1}</span>
                    <div className="flex gap-2">
                        <button onClick={applyHighlight} className="px-2 py-1 bg-yellow-100 border border-yellow-300 text-yellow-800 text-xs rounded hover:bg-yellow-200 flex items-center gap-1" title="Highlight Selection">
                            <span className="w-3 h-3 bg-yellow-400 inline-block rounded-full"></span> Highlight
                        </button>
                    </div>
                </div>
                
                {/* Scrollable Document Area (No standard text selection allowed except for programmatic highlighting) */}
                <div 
                    className="flex-1 p-8 overflow-y-auto text-lg leading-relaxed text-gray-800 select-text" 
                    style={{ userSelect: 'text' }}
                >
                    <p className="whitespace-pre-wrap">{question.text}</p>
                    {question.subQuestions && question.subQuestions.map((sub, i) => (
                      <p key={i} className="whitespace-pre-wrap mt-6 pt-6 border-t border-gray-200">
                        {sub.text}
                      </p>
                    ))}
                </div>
            </div>

            {/* Split Pane 2: Answer Editor (Bottom) */}
            <div className="flex-1 flex flex-col bg-white">
                {/* Formatting Toolbar */}
                <div className="flex items-center justify-between p-2 bg-gray-100 border-b border-gray-200">
                    <div className="flex items-center gap-1">
                        <button onClick={() => handleFormat('bold')} className="w-8 h-8 font-bold border border-transparent hover:border-gray-300 hover:bg-white rounded">B</button>
                        <button onClick={() => handleFormat('italic')} className="w-8 h-8 italic font-serif border border-transparent hover:border-gray-300 hover:bg-white rounded">I</button>
                        <button onClick={() => handleFormat('underline')} className="w-8 h-8 underline border border-transparent hover:border-gray-300 hover:bg-white rounded">U</button>
                        <div className="w-px h-6 bg-gray-300 mx-2"></div>
                        <button onClick={() => handleFormat('insertUnorderedList')} className="px-2 h-8 text-sm border border-transparent hover:border-gray-300 hover:bg-white rounded" title="Bullet List">&bull; List</button>
                    </div>
                    
                    <div className="text-xs text-gray-500 flex items-center gap-4">
                        <span>{charCount} / 100,000 characters</span>
                        <div className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-green-500"></span>
                            Auto-Saved
                        </div>
                    </div>
                </div>

                {/* The Isolated ContentEditable Area (No Spellcheck) */}
                <div className="flex-1 p-6 relative">
                    <div 
                        ref={editorRef}
                        contentEditable={true}
                        spellCheck={false}
                        onInput={handleInput}
                        onKeyDown={handleKeyDown}
                        className="w-full h-full outline-none text-lg leading-relaxed text-gray-900 overflow-y-auto"
                        placeholder="Type your answer here..."
                    />
                </div>
            </div>

        </div>
    );
};

export default LexifyWorkspace;
