"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/ui/GlassCard";
import { FileText, Eye, CheckCircle, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import EditorModal from "./EditorModal";

interface CaseFile {
    filename: string;
    year: string;
    path: string;
}

interface ReviewQueueProps {
    refreshTrigger: number;
}

export default function ReviewQueue({ refreshTrigger }: ReviewQueueProps) {
    const [cases, setCases] = useState<CaseFile[]>([]);
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [isResuming, setIsResuming] = useState(false);

    const fetchCases = async () => {
        try {
            const res = await fetch("http://localhost:8000/api/cases/preview");
            const data = await res.json();
            setCases(data.cases);
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        fetchCases();
    }, [refreshTrigger]);

    const handleResumePipeline = async () => {
        setIsResuming(true);
        try {
            await fetch("http://localhost:8000/api/pipeline/resume", {
                method: "POST"
            });
        } catch (e) {
            console.error(e);
        } finally {
            setTimeout(() => setIsResuming(false), 2000); // Cooldown
        }
    };

    return (
        <>
            <GlassCard className="h-full flex flex-col" gradient>
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h2 className="text-xl font-bold text-zinc-100">Review Queue</h2>
                        <p className="text-zinc-400 text-xs">Review converted markdown files before ingestion.</p>
                    </div>
                    <button
                        onClick={handleResumePipeline}
                        disabled={isResuming}
                        className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-xs font-bold rounded-lg flex items-center gap-2 transition-all shadow-lg shadow-green-500/20"
                    >
                        {isResuming ? <RefreshCw className="animate-spin" size={14} /> : <CheckCircle size={14} />}
                        RESUME INGESTION
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                    {cases.length === 0 ? (
                        <div className="text-center text-zinc-500 py-10">
                            No converted files found yet. Run the pipeline!
                        </div>
                    ) : (
                        cases.map((file, idx) => (
                            <motion.div
                                key={file.path}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.05 }}
                                className="group flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 hover:border-blue-500/30 transition-all"
                            >
                                <div className="flex items-center gap-3 overflow-hidden">
                                    <div className="p-2 rounded bg-blue-500/10 text-blue-400 group-hover:bg-blue-500 group-hover:text-white transition-colors">
                                        <FileText size={16} />
                                    </div>
                                    <div className="flex flex-col overflow-hidden">
                                        <span className="text-sm text-zinc-200 font-medium truncate w-64">{file.filename}</span>
                                        <span className="text-xs text-zinc-500">{file.year}</span>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setSelectedFile(file.path)}
                                    className="p-2 rounded-full hover:bg-white/20 text-zinc-400 hover:text-white transition-colors"
                                >
                                    <Eye size={16} />
                                </button>
                            </motion.div>
                        ))
                    )}
                </div>
            </GlassCard>

            <EditorModal
                isOpen={!!selectedFile}
                filePath={selectedFile}
                onClose={() => setSelectedFile(null)}
            />
        </>
    );
}
