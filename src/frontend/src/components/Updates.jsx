import React, { useEffect } from 'react';
import { ExternalLink, Facebook, Globe, Newspaper, Scale } from 'lucide-react';

const Updates = () => {

    useEffect(() => {
        let isMounted = true;
        const container = document.getElementById("twitter-container");
        if (!container) return;

        const createTimeline = () => {
            if (!isMounted) return;
            container.innerHTML = ""; // Clear loading text

            window.twttr.widgets.createTimeline(
                {
                    sourceType: "profile",
                    screenName: "SCPh_PIO"
                },
                container,
                {
                    theme: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
                    height: 600,
                    chrome: "noheader, nofooter",
                    dnt: true // Respect Do Not Track
                }
            ).then(() => {
                console.log("Twitter timeline created successfully.");
            }).catch((err) => {
                console.error("Error creating Twitter timeline:", err);
                if (isMounted) {
                    showFallback();
                }
            });
        };

        const showFallback = () => {
            if (!isMounted) return;
            container.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full text-center p-6 space-y-4">
                    <p class="text-gray-500 dark:text-gray-400">Unable to load Twitter feed.</p>
                    <a href="https://twitter.com/SCPh_PIO" target="_blank" rel="noopener noreferrer" class="px-6 py-2 bg-blue-500 text-white rounded-full font-semibold hover:bg-blue-600 transition-colors">
                        View on X (Twitter)
                    </a>
                    <button onclick="location.reload()" class="text-xs text-blue-500 hover:underline mt-2">
                        Refresh Page
                    </button>
                </div>
            `;
        };

        // Polling mechanism to wait for Twitter widget to be ready
        let attempts = 0;
        const maxAttempts = 50; // 5 seconds (50 * 100ms)

        const checkAndLoad = () => {
            if (!isMounted) return;

            if (window.twttr && window.twttr.widgets) {
                createTimeline();
            } else {
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(checkAndLoad, 100);
                } else {
                    console.error("Twitter widget load timed out.");
                    showFallback();
                }
            }
        };

        // Inject script if not present
        if (!window.twttr) {
            const script = document.createElement("script");
            script.src = "https://platform.twitter.com/widgets.js";
            script.async = true;
            script.charset = "utf-8";
            document.body.appendChild(script);
        }

        // Start polling
        checkAndLoad();

        return () => {
            isMounted = false;
        };
    }, []);

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center gap-3 mb-6">
                <Newspaper className="text-blue-600 dark:text-amber-400" size={32} />
                <h2 className="text-3xl font-bold text-gray-800 dark:text-gray-100">Latest Updates</h2>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Column 1: Social Feeds (Twitter) - Spans 2 columns on large screens */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Twitter Feed */}
                    <div className="bg-white dark:bg-[#1a1a1a] rounded-xl shadow-[0_30px_60px_-10px_rgba(0,0,0,0.3)] border border-stone-400 dark:border-gray-800 overflow-hidden">
                        <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex justify-between items-center bg-gray-50 dark:bg-gray-800/30">
                            <h3 className="font-bold text-lg flex items-center gap-2">
                                <svg viewBox="0 0 24 24" className="h-5 w-5 text-black dark:text-white fill-current" aria-hidden="true">
                                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"></path>
                                </svg>
                                Supreme Court PIO (@SCPh_PIO)
                            </h3>
                            <a
                                href="https://twitter.com/SCPh_PIO?ref_src=twsrc%5Etfw"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-blue-500 dark:text-amber-400 hover:underline flex items-center gap-1"
                            >
                                View on X <ExternalLink size={14} />
                            </a>
                        </div>
                        <div className="p-4 h-[600px] overflow-y-auto custom-scrollbar" id="twitter-container">
                            <div className="flex justify-center items-center h-full text-gray-500">
                                Loading Tweets...
                            </div>
                        </div>
                    </div>
                </div>

                {/* Column 2: Quick Links & Facebook */}
                <div className="space-y-6">
                    {/* Facebook Card */}
                    <div className="bg-white dark:bg-[#1a1a1a] rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.15)] border border-stone-400 dark:border-gray-800 p-6 hover:shadow-[0_8px_30px_rgba(0,0,0,0.2)] transition-all">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-3 bg-blue-100 dark:bg-amber-900/30 rounded-full">
                                <Facebook className="text-blue-600 dark:text-amber-400" size={24} />
                            </div>
                            <div>
                                <h3 className="font-bold text-lg">Facebook Page</h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400">Official SC Philippines Page</p>
                            </div>
                        </div>
                        <p className="text-gray-600 dark:text-gray-300 mb-4 text-sm">
                            Follow the Supreme Court of the Philippines on Facebook for official announcements, live streams, and more.
                        </p>
                        <a
                            href="https://www.facebook.com/SupremeCourtPhilippines"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block w-full py-2.5 text-center bg-[#1877F2] hover:bg-[#166fe5] text-white rounded-lg font-semibold transition-colors"
                        >
                            Visit Facebook Page
                        </a>
                    </div>

                    {/* Official Website News Card */}
                    <div className="bg-white dark:bg-[#1a1a1a] rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.15)] border border-stone-400 dark:border-gray-800 p-6 hover:shadow-[0_8px_30px_rgba(0,0,0,0.2)] transition-all">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-3 bg-purple-100 dark:bg-amber-900/30 rounded-full">
                                <Globe className="text-purple-600 dark:text-amber-400" size={24} />
                            </div>
                            <div>
                                <h3 className="font-bold text-lg">Judiciary News</h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400">sc.judiciary.gov.ph</p>
                            </div>
                        </div>
                        <p className="text-gray-600 dark:text-gray-300 mb-4 text-sm">
                            Read the latest press releases, decisions, and official news directly from the Supreme Court website.
                        </p>
                        <a
                            href="https://sc.judiciary.gov.ph/news/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block w-full py-2.5 text-center border-2 border-purple-600 text-purple-600 dark:text-amber-400 dark:border-amber-400 rounded-lg font-semibold hover:bg-purple-50 dark:hover:bg-amber-900/20 transition-colors"
                        >
                            Read News
                        </a>
                    </div>

                    {/* Bar Bulletins Card */}
                    <div className="bg-white dark:bg-[#1a1a1a] rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.15)] border border-stone-400 dark:border-gray-800 p-6 hover:shadow-[0_8px_30px_rgba(0,0,0,0.2)] transition-all">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-3 bg-yellow-100 dark:bg-amber-900/30 rounded-full">
                                <Scale className="text-yellow-600 dark:text-amber-400" size={24} />
                            </div>
                            <div>
                                <h3 className="font-bold text-lg">Bar Bulletins</h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400">Official Announcements</p>
                            </div>
                        </div>
                        <p className="text-gray-600 dark:text-gray-300 mb-4 text-sm">
                            Stay updated with the latest Bar Bulletins and important announcements for Bar examinees.
                        </p>
                        <a
                            href="https://sc.judiciary.gov.ph/bar-matters/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block w-full py-2.5 text-center border-2 border-yellow-600 text-yellow-600 dark:text-amber-400 dark:border-amber-400 rounded-lg font-semibold hover:bg-yellow-50 dark:hover:bg-amber-900/20 transition-colors"
                        >
                            View Bulletins
                        </a>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Updates;
