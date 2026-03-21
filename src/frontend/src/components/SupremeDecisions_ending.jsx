                                </div >
    <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
        <button
            type="button"
            className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
            onClick={() => setSelectedDecision(null)}
        >
            Close
        </button>
        <button
            type="button"
            onClick={() => {
                if (viewMode === 'full') {
                    setViewMode('digest');
                } else {
                    if (!fullText) fetchFullText(selectedDecision.id);
                    else setViewMode('full');
                }
            }}
            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
        >
            {viewMode === 'full' ? 'View Digest' : 'View Full Text'}
        </button>
        <a
            href="https://sc.judiciary.gov.ph/decisions/"
            target="_blank"
            rel="noreferrer"
            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
        >
            View Original Decision
        </a>
    </div>
                            </div >
                        ) : (
    <div className="text-center py-10 text-gray-500">
        <FileText className="h-12 w-12 mx-auto text-gray-300 mb-2" />
        <p>Select a decision to view details</p>
    </div>
)}
                    </div >
                </div >
            </main >
        </div >
    );
};

const SeparateOpinionCard = ({ op, idx }) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <div id={`sep-op-${idx}`} className="bg-gray-50 dark:bg-gray-700/30 p-4 rounded-lg border border-gray-100 dark:border-gray-700/50">
            <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    {op.type ? op.type.toUpperCase() : "OPINION"}
                </span>
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400">{op.justice}</span>
            </div>

            <p className="text-gray-700 dark:text-gray-300 text-sm italic border-l-2 border-gray-300 dark:border-gray-600 pl-3 mb-3">
                "{op.summary}"
            </p>

            {op.text && (
                <div>
                    {!expanded ? (
                        <button
                            onClick={() => setExpanded(true)}
                            className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                        >
                            Read Full Opinion <span className="text-xs">▼</span>
                        </button>
                    ) : (
                        <div className="mt-3 animate-fadeIn">
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-md border border-gray-200 dark:border-gray-600 text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto">
                                {op.text}
                            </div>
                            <button
                                onClick={() => setExpanded(false)}
                                className="mt-2 text-xs font-semibold text-gray-500 dark:text-gray-400 hover:underline"
                            >
                                Collapse Opinion ▲
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default SupremeDecisions;
