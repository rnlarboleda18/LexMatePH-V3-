import React, { useState } from 'react';

const LexifyCalculator = ({ onClose }) => {
    const [input, setInput] = useState('');
    const [result, setResult] = useState('');

    const handleButtonClick = (value) => {
        if (value === '=') {
            try {
                // Safe eval or simple parser (eval is fine for a sandboxed calculation widget)
                setResult(eval(input.replace(/×/g, '*').replace(/÷/g, '/')).toString());
            } catch (error) {
                setResult('Error');
            }
        } else if (value === 'C') {
            setInput('');
            setResult('');
        } else if (value === '⌫') {
            setInput(input.slice(0, -1));
        } else {
            setInput(input + value);
        }
    };

    return (
        <div className="fixed bottom-6 right-[460px] z-[150] w-64 bg-[#1e293b] border border-white/10 shadow-2xl rounded-2xl flex flex-col overflow-hidden font-sans select-none">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-slate-800 cursor-move">
                <div className="flex items-center gap-2">
                    <span className="text-sm">🧮</span>
                    <span className="text-xs font-bold text-white uppercase tracking-wider">Calculator</span>
                </div>
                <button onClick={onClose} className="p-1 hover:bg-white/10 rounded text-white/60 hover:text-white transition">
                    ✕
                </button>
            </div>

            {/* Display */}
            <div className="p-4 bg-[#0f172a] text-right flex flex-col justify-end min-h-[70px]">
                <div className="text-sm text-slate-400 font-mono truncate">{input || '0'}</div>
                <div className="text-xl font-bold text-green-400 font-mono truncate mt-1">{result}</div>
            </div>

            {/* Keypad */}
            <div className="grid grid-cols-4 gap-1 p-2 bg-[#1e293b]">
                {['C', '⌫', '÷', '×', '7', '8', '9', '-', '4', '5', '6', '+', '1', '2', '3', '=', '0', '.'].map((btn) => {
                    const isSpecial = ['C', '⌫', '÷', '×', '-', '+', '='].includes(btn);
                    return (
                        <button
                            key={btn}
                            onClick={() => handleButtonClick(btn)}
                            className={`p-3 text-sm font-semibold rounded-xl transition-colors ${
                                btn === '=' 
                                    ? 'bg-[#3fa9f5] hover:bg-[#2c98e2] text-white col-span-1' 
                                    : isSpecial 
                                        ? 'bg-slate-700 hover:bg-slate-600 text-[#3fa9f5]' 
                                        : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                            }`}
                        >
                            {btn}
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default LexifyCalculator;
