import React from 'react';

const ControlBar = ({
    searchTerm,
    onSearchChange,
    selectedYear,
    onYearChange
}) => {
    const years = Array.from({ length: 25 }, (_, i) => 2024 - i); // 2024 to 2000

    return (
        <div className="relative z-10 mb-6 flex flex-col md:flex-row gap-4 items-center justify-between bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border-2 border-gray-300 dark:border-gray-700">

            {/* Year Dropdown */}
            <div className="w-full md:w-64">
                <select
                    value={selectedYear || ''}
                    onChange={(e) => onYearChange(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border-2 border-blue-500 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer shadow-sm appearance-none"
                >
                    <option value="">All Years</option>
                    {years.map(year => (
                        <option key={year} value={year}>{year}</option>
                    ))}
                </select>
            </div>

            {/* Search Box */}
            <div className="relative w-full flex-1">
                <input
                    type="text"
                    placeholder="Type to search questions..."
                    value={searchTerm}
                    onChange={(e) => onSearchChange(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border-2 border-blue-500 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all shadow-sm placeholder-gray-400"
                />
            </div>
        </div>
    );
};

export default ControlBar;
