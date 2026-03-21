"use client";

import { useEffect, useState, useRef } from "react";
import PipelineControl from "@/components/dashboard/PipelineControl";
import LogViewer from "@/components/dashboard/LogViewer";
import ReviewQueue from "@/components/dashboard/ReviewQueue";
import { Loader2 } from "lucide-react";

export default function Dashboard() {
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [refreshQueue, setRefreshQueue] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);

  // Status Polling
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/status");
        if (res.ok) {
          const data = await res.json();
          // If state changed from running to not running, refresh queue
          if (isRunning && !data.is_running) {
            setRefreshQueue(prev => prev + 1);
          }
          setIsRunning(data.is_running);
        }
      } catch (e) {
        console.error("Backend offline", e);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 2000);
    return () => clearInterval(interval);
  }, [isRunning]);

  // WebSocket Connection
  useEffect(() => {
    const connectWS = () => {
      const ws = new WebSocket("ws://localhost:8000/api/logs");

      ws.onopen = () => {
        setLogs(prev => [...prev, ">> Connected to Pipeline Stream..."]);
      };

      ws.onmessage = (event) => {
        setLogs(prev => [...prev, event.data]);
      };

      ws.onclose = () => {
        // Reconnect logic could go here
      };

      socketRef.current = ws;
    };

    connectWS();
    return () => socketRef.current?.close();
  }, []);

  const handleStart = async (targets: string[], mode: "auto" | "manual") => {
    try {
      setLogs([]); // Clear previous logs
      await fetch("http://localhost:8000/api/pipeline/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ targets, mode })
      });
      setIsRunning(true);
    } catch (e) {
      alert("Failed to start pipeline");
    }
  };

  const handleStop = async () => {
    try {
      await fetch("http://localhost:8000/api/pipeline/stop", { method: "POST" });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <main className="min-h-screen p-8 bg-zinc-950 text-white selection:bg-blue-500/30">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 neon-text">
              BarAdmin OS
            </h1>
            <p className="text-zinc-400 mt-1">Automated Case Processing Pipeline</p>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-zinc-900 rounded-full border border-white/10">
            <div className={`w-2 h-2 rounded-full ${isRunning ? "bg-green-500 animate-pulse" : "bg-zinc-600"}`} />
            <span className="text-xs font-mono text-zinc-400">
              {isRunning ? "SYSTEM ACTIVE" : "SYSTEM IDLE"}
            </span>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[800px]">

          {/* Left: Controls & Queue */}
          <div className="lg:col-span-1 flex flex-col gap-6 h-full">
            <div className="h-1/2">
              <PipelineControl
                isRunning={isRunning}
                onStart={handleStart}
                onStop={handleStop}
              />
            </div>
            <div className="h-1/2">
              <ReviewQueue refreshTrigger={refreshQueue} />
            </div>
          </div>

          {/* Right: Logs */}
          <div className="lg:col-span-2 h-full">
            <LogViewer logs={logs} />
          </div>
        </div>

      </div>
    </main>
  );
}
