"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal, SquareTerminal } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";

interface LogViewerProps {
    logs: string[];
}

export default function LogViewer({ logs }: LogViewerProps) {
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    return (
        <GlassCard className="h-[500px] flex flex-col font-mono text-sm border-t-4 border-blue-500">
            <div className="flex items-center gap-2 mb-4 text-blue-400 border-b border-white/10 pb-2">
                <SquareTerminal size={18} />
                <span className="uppercase tracking-widest text-xs font-bold">Pipeline Console</span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-1 p-2 bg-black/40 rounded-lg custom-scrollbar">
                {logs.length === 0 && (
                    <div className="text-zinc-500 italic text-center mt-20">Waiting for pipeline logs...</div>
                )}

                {logs.map((log, i) => (
                    <div key={i} className="break-all whitespace-pre-wrap text-zinc-300">
                        <span className="text-zinc-600 select-none mr-2">$</span>
                        {log}
                    </div>
                ))}
                <div ref={endRef} />
            </div>
        </GlassCard>
    );
}
