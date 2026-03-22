import React, { useState, useEffect } from 'react';
import LexifySidebar from './LexifySidebar';
import LexifyWorkspace from './LexifyWorkspace';
import LexifyControls from './LexifyControls';

const LexifyApp = ({ questions, onClose }) => {
    // 0: Pre-Assessment, 1: Lock Check (Orange), 2: Active Exam, 3: Success Screen (Green), 4: Hidden/Paused
    const [examState, setExamState] = useState(0); 
    const [currentIndex, setCurrentIndex] = useState(0);
    const [userAnswers, setUserAnswers] = useState({});
    const [flaggedQuestions, setFlaggedQuestions] = useState(new Set());
    
    // Simulate Lockdown logic
    useEffect(() => {
        if (examState === 2) {
            const handleVisibilityChange = () => {
                if (document.hidden) {
                    alert('SECURITY VIOLATION: You switched tabs or minimized the window. In a real exam, this would be reported.');
                    // In a strictly enforced app, we might change state to 4 (Hidden/Locked)
                }
            };
            document.addEventListener('visibilitychange', handleVisibilityChange);
            return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
        }
    }, [examState]);

    const handleStartExam = () => {
        setExamState(1);
        setTimeout(() => setExamState(2), 2000); // Simulate Orange Check
        
        // Fullscreen API request
        const elem = document.documentElement;
        if (elem.requestFullscreen) {
            elem.requestFullscreen().catch(err => console.log('Fullscreen blocked:', err));
        }
    };

    const handleSubmit = async () => {
        const unanswered = questions.length - Object.keys(userAnswers).length;
        if (unanswered > 0) {
            if (!window.confirm(`You have ${unanswered} unanswered questions. Are you sure you want to submit?`)) {
                return;
            }
        }
        
        // Final Security Checkpoint
        const confirmCheck = window.confirm("I confirm I have completed my exam and am ready to submit for AI grading.");
        if (confirmCheck) {
            setExamState(3); // Green Screen
            // Exiting fullscreen
            if (document.fullscreenElement) {
                document.exitFullscreen().catch(err => console.log(err));
            }
            
            // ToDo: Make API Call to /api/lexify_grade here or in a separate step
        }
    };

    const handleExit = () => {
        if (window.confirm("Are you sure you want to exit the exam? All unsubmitted progress will be lost.")) {
            if (document.fullscreenElement) {
                document.exitFullscreen().catch(err => console.log(err));
            }
            onClose();
        }
    };

    // Screens
    if (examState === 0) {
        return (
            <div className="fixed inset-0 z-[100] bg-white text-black flex flex-col items-center justify-center p-8">
                <h1 className="text-4xl font-bold mb-6">Pre-Assessment Notice</h1>
                <p className="max-w-2xl text-lg text-center mb-8">
                    Welcome to the Lexify Environment. This simulates the official Examplify testing browser.
                    Once you start, your browser will attempt to enter fullscreen. Do not switch tabs or minimize the window.
                </p>
                <div className="flex gap-4">
                    <button onClick={onClose} className="px-6 py-2 bg-gray-200 rounded">Cancel</button>
                    <button onClick={handleStartExam} className="px-6 py-2 bg-blue-600 text-white font-bold rounded">Next &gt; Secure Mode</button>
                </div>
            </div>
        );
    }

    if (examState === 1) {
        return (
            <div className="fixed inset-0 z-[100] bg-orange-500 text-white flex flex-col items-center justify-center p-8">
                <h1 className="text-4xl font-bold mb-4 animate-pulse">STOP: SECURITY CHECK</h1>
                <p className="text-xl">Enforcing Lockdown... Closing background processes...</p>
            </div>
        );
    }

    if (examState === 3) {
        return (
            <div className="fixed inset-0 z-[100] bg-green-500 text-white flex flex-col items-center justify-center p-8">
                <h1 className="text-5xl font-bold mb-4">SUCCESS!</h1>
                <p className="text-2xl mb-8">Exam file securely uploaded.</p>
                <button onClick={onClose} className="px-8 py-3 bg-white text-green-700 font-bold rounded shadow-lg">Return to Dashboard</button>
            </div>
        );
    }

    if (examState === 4) {
        return (
            <div className="fixed inset-0 z-[100] bg-[#1e293b] text-white flex flex-col items-center justify-center p-8">
                <h1 className="text-4xl font-bold mb-4">EXAM HIDDEN</h1>
                <p className="text-xl mb-8">Your exam is paused and hidden from view.</p>
                <button onClick={() => setExamState(2)} className="px-8 py-3 bg-blue-600 text-white font-bold rounded shadow-lg hover:bg-blue-500 transition-colors">Resume Exam</button>
            </div>
        );
    }

    // Active Exam State (examState === 2)
    // Three-pane strict layout
    return (
        <div className="fixed inset-0 z-[100] bg-[#f5f5f5] text-black flex flex-col overflow-hidden font-serif" style={{ fontFamily: '"Times New Roman", Times, serif' }}>
            {/* Top Bar Navigation */}
            <LexifyControls 
                onSubmit={handleSubmit} 
                onHide={() => setExamState(4)} 
                onExit={handleExit}
                answeredCount={Object.keys(userAnswers).length} 
                totalCount={questions.length} 
            />

            <div className="flex flex-1 overflow-hidden mt-14">
                {/* Left Sidebar: Navigation Circles */}
                <LexifySidebar 
                    questions={questions}
                    currentIndex={currentIndex}
                    setCurrentIndex={setCurrentIndex}
                    userAnswers={userAnswers}
                    flaggedQuestions={flaggedQuestions}
                    setFlaggedQuestions={setFlaggedQuestions}
                />

                {/* Right Area: Workspace (Question Top, Editor Bottom) */}
                <LexifyWorkspace 
                    question={questions[currentIndex]}
                    currentIndex={currentIndex}
                    userAnswer={userAnswers[currentIndex] || ""}
                    setUserAnswer={(val) => setUserAnswers({ ...userAnswers, [currentIndex]: val })}
                />
            </div>
        </div>
    );
};

export default LexifyApp;
