"use client";

import { useState } from "react";
import { Play, Square, Loader2, Save } from "lucide-react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/GlassCard";

interface PipelineControlProps {
    isRunning: boolean;
    onStart: (targets: string[], mode: "auto" | "manual") => void;
    onStop: () => void;
}

const DEFAULT_TARGETS = [
    "Jaka Food v. Pacot (G.R. No. 151358, Mar 28, 2005)",
    "People v. Orit (G.R. No. 120967, July 5, 1997)",
    "Geminis v. People (G.R. No. 118431, Oct 23, 1996)",
    "Intod v. CA (G.R. No. 103119, Oct 21, 1992)",
    "Leria v. People (G.R. No. 256828, Oct 11, 2023)",
    "Togado v. People (G.R. No. 260973, Aug 6, 2024)",
    "CPRA (A.M. No. 22-09-01-SC, Apr 11, 2023)",
    "People v. Webb (G.R. No. 176864, Dec 14, 2010)",
    "Burbe v. Magulta (A.C. No. 99-634, June 10, 2002)",
    "Biaquillo v. CA (G.R. No. 129277, Sep 30, 1999)"
];

export default function PipelineControl({ isRunning, onStart, onStop }: PipelineControlProps) {
    const [targetText, setTargetText] = useState(DEFAULT_TARGETS.join("\n"));
    const [mode, setMode] = useState<"auto" | "manual">("manual"); // Default to manual now for safety

    const handleStart = () => {
        const targets = targetText.split("\n").filter(line => line.trim().length > 0);
        onStart(targets, mode);
    };

    return (
        <GlassCard className="h-full flex flex-col" gradient>
            <div className="mb-6 flex justify-between items-start">
                <div>
                    <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
                        Pipeline Controller
                    </h2>
                    <p className="text-zinc-400 text-sm mt-1">Manage scraping, conversion, and ingestion tasks.</p>
                </div>
            </div>

            <div className="flex-1 flex flex-col gap-4">
                {/* Mode Toggle */}
                <div className="flex bg-black/40 p-1 rounded-lg border border-white/10">
                    <button
                        onClick={() => setMode("auto")}
                        className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === "auto"
                                ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
                                : "text-zinc-400 hover:text-white"
                            }`}
                    >
                        Auto Pilot
                    </button>
                    <button
                        onClick={() => setMode("manual")}
                        className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === "manual"
                                ? "bg-purple-600 text-white shadow-lg shadow-purple-500/20"
                                : "text-zinc-400 hover:text-white"
                            }`}
                    >
                        Manual Review
                    </button>
                </div>

                <label className="text-sm font-medium text-zinc-300">Target Cases (Line Separated)</label>
                <textarea
                    className="flex-1 bg-black/30 border border-white/10 rounded-lg p-4 text-sm font-mono text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
                    value={targetText}
                    onChange={(e) => setTargetText(e.target.value)}
                    disabled={isRunning}
                />

                <div className="flex gap-4 mt-2">
                    {!isRunning ? (
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={handleStart}
                            className={`flex-1 text-white font-semibold py-4 rounded-xl flex items-center justify-center gap-2 shadow-lg ${mode === 'auto'
                                    ? "bg-blue-600 hover:bg-blue-500 shadow-blue-500/20"
                                    : "bg-purple-600 hover:bg-purple-500 shadow-purple-500/20"
                                }`}
                        >
                            <Play size={20} fill="currentColor" />
                            START PIPELINE ({mode.toUpperCase()})
                        </motion.button>
                    ) : (
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={onStop}
                            className="flex-1 bg-red-600 hover:bg-red-500 text-white font-semibold py-4 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-red-500/20 animate-pulse"
                        >
                            <Square size={20} fill="currentColor" />
                            STOP PIPELINE
                        </motion.button>
                    )}
                </div>
            </div>
        </GlassCard>
    );
}
