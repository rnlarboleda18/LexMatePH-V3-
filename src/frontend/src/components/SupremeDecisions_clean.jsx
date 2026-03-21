import React, { useState, useEffect } from 'react';
import { jsPDF } from "jspdf";
import { Search, Calendar, Gavel, FileText } from 'lucide-react';
import { formatDate } from '../utils/dateUtils';
import ReactMarkdown from 'react-markdown';

const SmartLink = ({ text, onCaseClick }) => {
    const [tooltip, setTooltip] = useState({ visible: false, content: '', x: 0, y: 0 });

    const handleHover = async (e, type, match) => {
        // Only fetch tooltip for G.R. numbers or specific case references
        if (type === 'case') {
            // Simplified tooltip logic for now
            // In a real app, this would fetch digest preview
        }
    };

    if (!text) return null;

    // Regex to detect G.R. Nos and Republic Acts
    const regex = /(G\.R\. No\.\s?\d+[\w-]*)|(Republic Act No\.\s?\d+)/gi;
    const parts = text.split(regex);
    const matches = text.match(regex);

    if (!matches) return <span>{text}</span>;

    let matchIndex = 0;
    return (
        <span>
            {parts.map((part, i) => {
                if (matches[matchIndex] === part) {
                    const currentMatch = matches[matchIndex];
                    matchIndex++;
                    return (
                        <span
                            key={i}
                            className="text-blue-600 dark:text-blue-400 cursor-pointer hover:underline font-medium relative group"
                            onClick={(e) => {
                                e.stopPropagation();
                                onCaseClick(currentMatch);
                            }}
                        >
                            {part}
                        </span>
                    );
                }
                return <span key={i}>{part}</span>;
            })}
        </span>
    );
};

const SmartLinkWrapper = ({ children, onCaseClick }) => {
    // If children is string, smart link it. If array/object, just render.
    if (typeof children === 'string') {
        return <SmartLink text={children} onCaseClick={onCaseClick} />;
    }
    if (Array.isArray(children)) {
        return (
            <>
                {children.map((child, idx) => {
                    if (typeof child === 'string') {
                        return <SmartLink key={idx} text={child} onCaseClick={onCaseClick} />;
                    }
                    return <React.Fragment key={idx}>{child}</React.Fragment>;
                })}
            </>
        );
    }
    return <>{children}</>;
};

const SupremeDecisions = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedDecision, setSelectedDecision] = useState(null);
    const [viewMode, setViewMode] = useState('digest'); // 'digest' or 'full'
    const [fullText, setFullText] = useState(null);
    const [loadingFullText, setLoadingFullText] = useState(false);
    const [showMockExam, setShowMockExam] = useState(false);
    const [mockExamQuestions, setMockExamQuestions] = useState(null);
    const [loadingMockExam, setLoadingMockExam] = useState(false);

    // Filter states
    const [selectedYear, setSelectedYear] = useState('');
    const [selectedMonth, setSelectedMonth] = useState('');
    const [selectedPonente, setSelectedPonente] = useState('');
    const [availableYears, setAvailableYears] = useState([]);
    const [availablePonentes, setAvailablePonentes] = useState([]);

    useEffect(() => {
        fetchAvailableFilters();
    }, []);

    const fetchAvailableFilters = async () => {
        try {
            // Mock data or fetch from API
            const currentYear = new Date().getFullYear();
            const years = Array.from({ length: currentYear - 1900 }, (_, i) => currentYear - i);
            setAvailableYears(years);
            // Fetch ponentes would go here
        } catch (error) {
            console.error("Error fetching filters", error);
        }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            let query = `/api/search_decisions?q=${searchTerm}`;
            if (selectedYear) query += `&year=${selectedYear}`;
            if (selectedMonth) query += `&month=${selectedMonth}`;
            if (selectedPonente) query += `&ponente=${selectedPonente}`;

            const response = await fetch(query);
            const data = await response.json();
            setSearchResults(data);
        } catch (error) {
            console.error("Search failed", error);
        } finally {
            setLoading(false);
        }
    };

    const handleCaseClick = async (decision) => {
        setSelectedDecision(decision);
        setViewMode('digest');
        setFullText(null);
        setShowMockExam(false);
        // Pre-fetch check if full text is cached or needs scraping
        // fetchFullText(decision.id); // Lazy load instead
    };

    const handleSmartCaseClick = (caseRef) => {
        // Auto-search for the clicked case reference
        setSearchTerm(caseRef);
        // handleSearch(new Event('submit')); // Trigger search somehow
        // For now just set the search term
    };

    const fetchFullText = async (id) => {
        setLoadingFullText(true);
        try {
            const response = await fetch(`/api/get_decision_full_text?id=${id}`);
            const data = await response.json();
            if (data.full_text) {
                setFullText(data.full_text);
            } else {
                setFullText("Full text not available yet. It may be in the scraping queue.");
            }
        } catch (error) {
            console.error("Failed to fetch full text", error);
            setFullText("Error loading full text.");
        } finally {
            setLoadingFullText(false);
        }
    };

    const handleGenerateMockExam = async (id) => {
        if (showMockExam && mockExamQuestions) {
            setShowMockExam(false);
            return;
        }
        setLoadingMockExam(true);
        try {
            const response = await fetch(`/api/generate_mock_exam?id=${id}`);
            const data = await response.json();
            setMockExamQuestions(data.questions);
            setShowMockExam(true);
        } catch (error) {
            console.error("Mock exam generation failed", error);
            alert("Failed to generate mock exam. Please try again.");
        } finally {
            setLoadingMockExam(false);
        }
    };

    const handleDownloadDigestPDF = () => {
        if (!selectedDecision) return;
        const doc = new jsPDF();

        doc.setFontSize(16);
        doc.text("Supreme Court Decision Digest", 105, 20, null, null, "center");

        doc.setFontSize(12);
        doc.setFont(undefined, 'bold');
        doc.text(selectedDecision.title, 105, 30, null, null, "center");

        doc.setFont(undefined, 'normal');
        doc.setFontSize(10);
        doc.text(`G.R. No. ${selectedDecision.gr_number} | ${formatDate(selectedDecision.date)}`, 105, 40, null, null, "center");

        let y = 50;

        const addSection = (title, content) => {
            if (!content) return;
            if (y > 270) { doc.addPage(); y = 20; }
            doc.setFont(undefined, 'bold');
            doc.text(title, 20, y);
            y += 7;
            doc.setFont(undefined, 'normal');
            const splitText = doc.splitTextToSize(content, 170);
            doc.text(splitText, 20, y);
            y += splitText.length * 5 + 10;
        };

        addSection("FACTS", selectedDecision.digest_facts);
        addSection("ISSUE", selectedDecision.digest_issues);
        addSection("RULING", selectedDecision.digest_ruling);
        addSection("RATIO DECIDENDI", selectedDecision.digest_ratio);

        doc.save(`${selectedDecision.gr_number}_digest.pdf`);
    };

    const handleDownloadFullTextPDF = () => {
        if (!fullText) return;
        const doc = new jsPDF();
        const splitText = doc.splitTextToSize(fullText, 170);

        let y = 20;
        splitText.forEach(line => {
            if (y > 280) {
                doc.addPage();
                y = 20;
            }
            doc.text(line, 20, y);
            y += 5;
        });

        doc.save(`${selectedDecision.gr_number}_full_text.pdf`);
    };


    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 font-sans">
            {/* Header */}
            <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Gavel className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
                            PhilLaw<span className="text-blue-600 dark:text-blue-400">Wise</span>
                        </h1>
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 hidden sm:block">
                        Philippine Supreme Court Decisions AI Assistant
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
                {/* Search Section */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mb-8 transform transition-all hover:shadow-xl">
                    <form onSubmit={handleSearch} className="space-y-4">
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <Search className="h-5 w-5 text-gray-400" />
                            </div>
                            <input
                                type="text"
                                className="block w-full pl-10 pr-3 py-3 border border-gray-300 dark:border-gray-600 rounded-lg leading-5 bg-gray-50 dark:bg-gray-700 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:text-white transition-colors"
                                placeholder="Search by G.R. number, title, topic, or keyword..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="relative">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Year</label>
                                <select
                                    className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md dark:bg-gray-700 dark:text-white"
                                    value={selectedYear}
                                    onChange={(e) => setSelectedYear(e.target.value)}
                                >
                                    <option value="">All Years</option>
                                    {availableYears.map(year => (
                                        <option key={year} value={year}>{year}</option>
                                    ))}
                                </select>
                            </div>
                            {/* More filters can go here */}
                            <div className="relative sm:col-span-2 flex items-end justify-end">
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors shadow-md hover:shadow-lg"
                                >
                                    {loading ? (
                                        <>
                                            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                            Searching...
                                        </>
                                    ) : 'Search Decisions'}
                                </button>
                            </div>
                        </div>
                    </form>
                </div>

                {/* Results Section */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* List */}
                    <div className="lg:col-span-1 space-y-4 max-h-[calc(100vh-300px)] overflow-y-auto pr-2 custom-scrollbar">
                        {searchResults.length === 0 && !loading && (
                            <div className="text-center py-10 text-gray-500">
                                <FileText className="h-12 w-12 mx-auto text-gray-300 mb-2" />
                                <p>No decisions found. Try a search.</p>
                            </div>
                        )}
                        {searchResults.map((decision) => (
                            <div
                                key={decision.id}
                                onClick={() => handleCaseClick(decision)}
                                className={`p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm border cursor-pointer transition-all hover:shadow-md ${selectedDecision?.id === decision.id
                                    ? 'border-blue-500 ring-1 ring-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                    : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700'
                                    }`}
                            >
                                <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 line-clamp-2 mb-2">{decision.title}</h3>
                                <div className="flex items-center text-xs text-gray-500 dark:text-gray-400 gap-2 mb-2">
                                    <span className="font-mono bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">{decision.gr_number}</span>
                                    <span>•</span>
                                    <span>{formatDate(decision.date)}</span>
                                </div>
                                <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-3 leading-relaxed">
                                    {decision.snippet || "No snippet available."}
                                </p>
                            </div>
                        ))}
                    </div>

                    {/* Detail View */}
                    <div className="lg:col-span-2">
                        {selectedDecision ? (
                            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden min-h-[500px] flex flex-col">
                                <div className="p-6 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                                    <h2 className="text-xl font-bold text-gray-900 dark:text-white text-center leading-snug mb-4">
                                        {selectedDecision.title}
                                    </h2>
                                    <div className="flex flex-wrap justify-center items-center gap-4 text-sm text-gray-600 dark:text-gray-300">
                                        <div className="flex items-center gap-1.5 bg-white dark:bg-gray-700 px-3 py-1 rounded-full shadow-sm border border-gray-200 dark:border-gray-600">
                                            {/* <span className="font-bold text-blue-600 dark:text-blue-400">G.R. No.</span> */}
                                            <span className="font-mono">{selectedDecision.gr_number}</span>
                                        </div>
                                        <div className="flex items-center gap-1.5 bg-white dark:bg-gray-700 px-3 py-1 rounded-full shadow-sm border border-gray-200 dark:border-gray-600">
                                            <Calendar className="h-4 w-4 text-blue-500" />
                                            <span>{formatDate(selectedDecision.date)}</span>
                                        </div>
                                        {selectedDecision.vote_nature && (
                                            <div className="flex items-center gap-1.5 bg-purple-50 dark:bg-purple-900/30 px-3 py-1 rounded-full shadow-sm border border-purple-100 dark:border-purple-800">
                                                <span className="font-bold text-xs text-purple-700 dark:text-purple-300 uppercase tracking-wide">
                                                    {selectedDecision.vote_nature}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="p-6 flex-grow">
                                    {/* Tabs / Toggle */}
                                    <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6">
                                        <button
                                            onClick={() => setViewMode('digest')}
                                            className={`pb-3 px-4 text-sm font-medium transition-colors relative ${viewMode === 'digest'
                                                ? 'text-blue-600 dark:text-blue-400'
                                                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                                                }`}
                                        >
                                            Case Digest
                                            {viewMode === 'digest' && (
                                                <span className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-600 dark:bg-blue-400 rounded-t-full"></span>
                                            )}
                                        </button>
                                        <button
                                            onClick={() => {
                                                if (!fullText) fetchFullText(selectedDecision.id);
                                                setViewMode('full');
                                            }}
                                            className={`pb-3 px-4 text-sm font-medium transition-colors relative ${viewMode === 'full'
                                                ? 'text-blue-600 dark:text-blue-400'
                                                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                                                }`}
                                        >
                                            Full Text
                                            {viewMode === 'full' && (
                                                <span className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-600 dark:bg-blue-400 rounded-t-full"></span>
                                            )}
                                        </button>
                                    </div>

                                    {viewMode === 'full' ? (
                                        <div className="animate-fadeIn">
                                            <div className="flex justify-between items-center mb-4">
                                                <h3 className="text-lg font-bold text-gray-900 dark:text-white">Full Text Decision</h3>
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={handleDownloadFullTextPDF}
                                                        className="text-blue-600 dark:text-blue-400 text-sm hover:underline font-medium flex items-center gap-1"
                                                    >
                                                        Download PDF
                                                    </button>
                                                    <button
                                                        onClick={() => setViewMode('digest')}
                                                        className="text-gray-500 dark:text-gray-400 text-sm hover:text-gray-700 dark:hover:text-gray-200"
                                                    >
                                                        Back to Digest
                                                    </button>
                                                </div>
                                            </div>
                                            {loadingFullText ? (
                                                <div className="text-center py-10">
                                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                                                    <p className="mt-2 text-sm text-gray-500">Loading full text...</p>
                                                </div>
                                            ) : (
                                                <div className="text-gray-800 dark:text-gray-200 text-sm leading-relaxed font-sans text-justify markdown-content">
                                                    {fullText ? (
                                                        <div className="prose dark:prose-invert max-w-none">
                                                            <ReactMarkdown
                                                                components={{
                                                                    p: ({ node, children }) => <p className="mb-4 text-justify"><SmartLinkWrapper children={children} onCaseClick={handleSmartCaseClick} /></p>,
                                                                    h1: ({ node, children }) => <h1 className="text-center font-extrabold text-3xl mb-8 mt-10 uppercase tracking-widest text-gray-900 dark:text-gray-100">{children}</h1>,
                                                                    h2: ({ node, children }) => <div className="text-center font-bold text-lg mb-4 px-6 leading-relaxed text-gray-800 dark:text-gray-200">{children}</div>,
                                                                    h3: ({ node, children }) => <div className="text-center font-semibold text-base text-gray-600 dark:text-gray-400 mb-1">{children}</div>,
                                                                    h4: ({ node, children }) => <div className="text-center font-medium italic text-gray-500 my-2">{children}</div>,
                                                                    h5: ({ node, children }) => <h5 className="text-center font-bold text-sm uppercase tracking-wide mb-6 text-gray-500">{children}</h5>,
                                                                    hr: ({ node }) => <hr className="my-8 border-gray-300 dark:border-gray-600" />
                                                                }}
                                                            >
                                                                {(() => {
                                                                    if (!fullText) return "";

                                                                    const lines = fullText.split('\n');
                                                                    const processedLines = [];
                                                                    let bodyStarted = false;
                                                                    let capturedCaseNo = null;

                                                                    // Regex patterns
                                                                    const ponenteRegex = /^[\*_]*[A-ZÑ\s\.-]+,\s*[\*_]*(J\.|C\.J\.|CJ|J)[\*_]*[:\.]?[\*_]*$/i;
                                                                    const perCuriamRegex = /^[\*_]*PER\s+CURIAM[:\.]?[\*_]*$/i;
                                                                    const divisionRegex = /^[\*_]*(EN\s+BANC|((FIRST|SECOND|THIRD|FOURTH|FIFTH)\s+)?DIVISION)[\*_]*$/i;
                                                                    const vsRegex = /^[\*_]*(vs\.?|versus|v\.)[\*_]*$/i;
                                                                    const partyRegex = /(Petitioner|Respondent|Accused|Plaintiff|Defendant)[s]?[\.,]?[\*_]*$/i;

                                                                    for (let i = 0; i < lines.length; i++) {
                                                                        const line = lines[i].trim();
                                                                        if (!line) {
                                                                            processedLines.push('');
                                                                            continue;
                                                                        }

                                                                        if (bodyStarted) {
                                                                            processedLines.push(line);
                                                                            continue;
                                                                        }

                                                                        // 1. Check for Ponente -> Body Start
                                                                        if (ponenteRegex.test(line) || perCuriamRegex.test(line)) {
                                                                            bodyStarted = true;
                                                                            processedLines.push(`\n${line}`);
                                                                            continue;
                                                                        }

                                                                        const cleanUpper = line.replace(/[\*_]/g, '').toUpperCase();
                                                                        const cleanNoSpace = cleanUpper.replace(/\s+/g, '');

                                                                        // 2. Main Headers (DECISION -> D E C I S I O N) -> H1
                                                                        if (/^(DECISION|RESOLUTION|SENTENCE|AUTO)$/.test(cleanNoSpace)) {
                                                                            processedLines.push(`\n# ${cleanUpper.replace(/\s+/g, ' ')}\n`);
                                                                            continue;
                                                                        }

                                                                        // 3. Division/En Banc -> H5
                                                                        if (divisionRegex.test(line)) {
                                                                            processedLines.push(`\n##### ${line}\n`);
                                                                            continue;
                                                                        }

                                                                        // 4. Case Number & Date Merging
                                                                        if (cleanUpper.startsWith("G.R. NO.") || cleanUpper.startsWith("A.M. NO.") || cleanUpper.startsWith("A.C. NO.")) {
                                                                            capturedCaseNo = line;
                                                                            continue;
                                                                        }

                                                                        if (capturedCaseNo) {
                                                                            const isDate = /^(January|February|March|April|May|June|July|August|September|October|November|December)/i.test(line);
                                                                            if (isDate) {
                                                                                processedLines.push(`\n### ${capturedCaseNo} • ${line}\n`);
                                                                                capturedCaseNo = null;
                                                                                continue;
                                                                            } else {
                                                                                processedLines.push(`\n### ${capturedCaseNo}\n`);
                                                                                capturedCaseNo = null;
                                                                            }
                                                                        }

                                                                        // 5. VS -> H4
                                                                        if (vsRegex.test(line)) {
                                                                            processedLines.push(`\n#### ${line.toLowerCase()}\n`);
                                                                            continue;
                                                                        }

                                                                        // 6. Party Names -> H2 (Center)
                                                                        if (partyRegex.test(line) || line.length < 200) {
                                                                            processedLines.push(`\n## ${line}\n`);
                                                                            continue;
                                                                        }

                                                                        // Fallback
                                                                        bodyStarted = true;
                                                                        processedLines.push(line);
                                                                    }

                                                                    if (capturedCaseNo) {
                                                                        processedLines.push(`\n### ${capturedCaseNo}\n`);
                                                                    }

                                                                    return processedLines.join('\n');
                                                                })()}
                                                            </ReactMarkdown>
                                                        </div>
                                                    ) : (
                                                        <p className="italic text-gray-500">Full text content not available.</p>
                                                    )}
                                                </div>
                                            )}
                                            {relatedOpinions && relatedOpinions.length > 0 && (
                                                <div className="mt-8 border-t border-gray-200 dark:border-gray-700 pt-8">
                                                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Separate Opinions</h3>
                                                    <div className="space-y-8">
                                                        {relatedOpinions.map((opinion, idx) => (
                                                            <div key={opinion.id || idx} className="bg-gray-50 dark:bg-gray-700/30 rounded-lg p-6">
                                                                <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4 border-b border-gray-200 dark:border-gray-600 pb-2">
                                                                    {opinion.title || opinion.document_type || "Opinion"}
                                                                </h4>
                                                                <div className="text-gray-800 dark:text-gray-200 text-sm leading-relaxed font-sans text-justify markdown-content">
                                                                    <div className="prose dark:prose-invert max-w-none">
                                                                        <ReactMarkdown
                                                                            components={{
                                                                                p: ({ node, children }) => <p><SmartLinkWrapper children={children} onCaseClick={handleSmartCaseClick} /></p>
                                                                            }}
                                                                        >
                                                                            {opinion.full_text_md || "*Content not available*"}
                                                                        </ReactMarkdown>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <>
                                            <div className="flex items-center justify-between mb-4">
                                                <h3 className="text-lg font-bold text-gray-900 dark:text-white">Case Digest</h3>
                                                <div className="flex items-center gap-2">
                                                    {selectedDecision.spoken_script && (
                                                        <button
                                                            onClick={() => alert('TTS feature requires Azure credentials. See console for endpoint.')}
                                                            className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded-md font-medium flex items-center gap-1 transition-colors"
                                                            title="Listen to Case Digest"
                                                        >
                                                            🎧 Podcast Mode
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => handleGenerateMockExam(selectedDecision.id)}
                                                        disabled={loadingMockExam}
                                                        className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs rounded-md font-medium flex items-center gap-1 transition-colors disabled:opacity-50"
                                                    >
                                                        {loadingMockExam ? '⏳ Generating...' : '📝 Mock Exam'}
                                                    </button>
                                                    <button
                                                        onClick={handleDownloadDigestPDF}
                                                        className="text-red-600 dark:text-red-400 text-sm hover:underline font-medium flex items-center gap-1"
                                                    >
                                                        Download PDF
                                                    </button>
                                                </div>
                                            </div>
                                            {showMockExam && mockExamQuestions && (
                                                <div className="mb-6 bg-teal-50 dark:bg-teal-900/20 p-4 rounded-lg border border-teal-200 dark:border-teal-800">
                                                    <div className="flex justify-between items-center mb-3">
                                                        <h4 className="text-md font-bold text-teal-800 dark:text-teal-300">MOCK BAR EXAM QUESTIONS</h4>
                                                        <button onClick={() => setShowMockExam(false)} className="text-xs text-gray-500 hover:text-gray-700">✕ Close</button>
                                                    </div>
                                                    <div className="space-y-4">
                                                        {mockExamQuestions.map((q, idx) => (
                                                            <div key={idx} className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-teal-100 dark:border-teal-900/30">
                                                                <p className="font-bold text-gray-900 dark:text-gray-100 mb-2">{idx + 1}. {q.q}</p>
                                                                {q.options && (
                                                                    <ul className="ml-4 mb-2 space-y-1">
                                                                        {q.options.map((opt, i) => (
                                                                            <li key={i} className="text-sm text-gray-700 dark:text-gray-300">{opt}</li>
                                                                        ))}
                                                                    </ul>
                                                                )}
                                                                <div className="mt-3 pt-3 border-t border-teal-100 dark:border-teal-900/30">
                                                                    <p className="text-xs font-bold text-teal-700 dark:text-teal-400">Answer: {q.a}</p>
                                                                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{q.explanation}</p>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                            {selectedDecision.main_doctrine && (
                                                <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border-l-4 border-blue-500 mb-6 font-medium">
                                                    <h4 className="text-sm font-bold text-blue-800 dark:text-blue-300 uppercase mb-1">Main Doctrine</h4>
                                                    <div className="text-gray-800 dark:text-gray-200">
                                                        <SmartLink text={selectedDecision.main_doctrine} onCaseClick={handleSmartCaseClick} />
                                                    </div>
                                                </div>
                                            )}
                                            {selectedDecision.spoken_script && (
                                                <div className="mb-6">
                                                    <h4 className="text-md font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-1 mb-2">AUDIO SCRIPT / SUMMARY</h4>
                                                    <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-lg border border-gray-200 dark:border-gray-600">
                                                        <div className="text-gray-700 dark:text-gray-300 text-sm italic leading-relaxed">
                                                            <SmartLink text={selectedDecision.spoken_script} onCaseClick={handleSmartCaseClick} />
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                            {(selectedDecision.statutes_involved || selectedDecision.cited_cases) && (
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                                                    {selectedDecision.statutes_involved && (
                                                        <div className="bg-indigo-50 dark:bg-indigo-900/10 p-4 rounded-lg border border-indigo-100 dark:border-indigo-900/30">
                                                            <h4 className="text-xs font-bold text-indigo-800 dark:text-indigo-300 uppercase mb-2">Statutes Involved</h4>
                                                            <div className="flex flex-wrap gap-2">
                                                                {Array.isArray(selectedDecision.statutes_involved) ? selectedDecision.statutes_involved.map((s, i) => (
                                                                    <span key={i} className="px-2 py-1 bg-white dark:bg-gray-800 text-xs rounded border border-indigo-200 dark:border-indigo-700 text-indigo-700 dark:text-indigo-300">{s}</span>
                                                                )) : <span className="text-sm text-gray-600 dark:text-gray-400">{selectedDecision.statutes_involved}</span>}
                                                            </div>
                                                        </div>
                                                    )}
                                                    {selectedDecision.cited_cases && (
                                                        <div className="bg-teal-50 dark:bg-teal-900/10 p-4 rounded-lg border border-teal-100 dark:border-teal-900/30">
                                                            <h4 className="text-xs font-bold text-teal-800 dark:text-teal-300 uppercase mb-2">Cited Jurisprudence</h4>
                                                            <div className="flex flex-wrap gap-2">
                                                                {Array.isArray(selectedDecision.cited_cases) ? selectedDecision.cited_cases.map((c, i) => (
                                                                    <span key={i} className="px-2 py-1 bg-white dark:bg-gray-800 text-xs rounded border border-teal-200 dark:border-teal-700 text-teal-700 dark:text-teal-300">{c}</span>
                                                                )) : <span className="text-sm text-gray-600 dark:text-gray-400">{selectedDecision.cited_cases}</span>}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                            {selectedDecision.flashcards && selectedDecision.flashcards.length > 0 && (
                                                <div className="mb-6">
                                                    <h4 className="text-md font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-1 mb-3">BAR REVIEW FLASHCARDS</h4>
                                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                                        {selectedDecision.flashcards.map((card, idx) => (
                                                            <div key={idx} className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-blue-100 dark:border-blue-900/30 relative group transition-all hover:shadow-md">
                                                                <div className="absolute top-2 right-2 text-[10px] font-bold text-blue-300 dark:text-blue-700">Q</div>
                                                                <p className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-3 pr-4">{card.front || card.question}</p>
                                                                <div className="border-t border-blue-50 dark:border-blue-900/20 pt-3">
                                                                    <p className="text-xs text-blue-600 dark:text-blue-400 font-medium whitespace-pre-wrap">{card.back || card.answer}</p>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                            {selectedDecision.separate_opinions && selectedDecision.separate_opinions.length > 0 && (
                                                <div className="mb-6 flex flex-wrap gap-2">
                                                    {selectedDecision.separate_opinions.map((op, idx) => (
                                                        <button
                                                            key={idx}
                                                            onClick={() => document.getElementById(`sep-op-${idx}`).scrollIntoView({ behavior: 'smooth' })}
                                                            className="px-3 py-1 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-full text-xs font-medium text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 transition-colors"
                                                        >
                                                            {op.type}: {op.justice}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                            {selectedDecision.digest_facts ? (
                                                <>
                                                    <section>
                                                        <h4 className="text-md font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-1 mb-2">FACTS</h4>
                                                        <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                                                            <SmartLink text={selectedDecision.digest_facts} onCaseClick={handleSmartCaseClick} />
                                                        </div>
                                                    </section>
                                                    <section>
                                                        <h4 className="text-md font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-1 mb-2">ISSUE</h4>
                                                        <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                                                            <SmartLink text={selectedDecision.digest_issues} onCaseClick={handleSmartCaseClick} />
                                                        </div>
                                                    </section>
                                                    <section>
                                                        <h4 className="text-md font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-1 mb-2">RULING</h4>
                                                        <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                                                            <SmartLink text={selectedDecision.digest_ruling} onCaseClick={handleSmartCaseClick} />
                                                        </div>
                                                    </section>
                                                    <section>
                                                        <h4 className="text-md font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-1 mb-2">RATIO DECIDENDI</h4>
                                                        <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                                                            <SmartLink text={selectedDecision.digest_ratio} onCaseClick={handleSmartCaseClick} />
                                                        </div>
                                                    </section>
                                                    <section>
                                                        <h4 className="text-md font-bold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-1 mb-2">SIGNIFICANCE</h4>
                                                        {selectedDecision.digest_significance && selectedDecision.digest_significance.includes('PROCESSING') ? (
                                                            <div className="flex items-center gap-3 text-blue-600 bg-blue-50 dark:bg-blue-900/30 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                                                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 dark:border-blue-400"></div>
                                                                <div>
                                                                    <p className="font-semibold text-sm">AI Digest Generation in Progress</p>
                                                                    <p className="text-xs opacity-80">This section is being updated by the fleet. Check back in a moment.</p>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                                                                <SmartLink text={selectedDecision.digest_significance} onCaseClick={handleSmartCaseClick} />
                                                            </div>
                                                        )}
                                                    </section>
                                                    {selectedDecision.secondary_rulings && selectedDecision.secondary_rulings.length > 0 && (
                                                        <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg border border-yellow-200 dark:border-yellow-800/50 mt-6">
                                                            <h4 className="text-sm font-bold text-yellow-800 dark:text-yellow-200 uppercase mb-3 flex items-center gap-2">
                                                                <span>📌</span> Other Notable Rulings
                                                            </h4>
                                                            <div className="space-y-4">
                                                                {selectedDecision.secondary_rulings.map((ruling, idx) => (
                                                                    <div key={idx} className="bg-white dark:bg-gray-800 p-3 rounded shadow-sm border border-yellow-100 dark:border-gray-700">
                                                                        <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm mb-1">{ruling.topic}</h5>
                                                                        <p className="text-gray-700 dark:text-gray-300 text-sm">{ruling.ruling}</p>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                    {selectedDecision.separate_opinions && selectedDecision.separate_opinions.length > 0 && (
                                                        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
                                                            <h4 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Separate Opinions</h4>
                                                            <div className="space-y-6">
                                                                {selectedDecision.separate_opinions.map((op, idx) => (
                                                                    <SeparateOpinionCard key={idx} op={op} idx={idx} />
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                </>
                                            ) : (
                                                <div className="text-center py-6 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                                    <p className="text-gray-500 dark:text-gray-400 italic">
                                                        No AI digest generated for this case yet.
                                                    </p>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
