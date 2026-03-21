"use client";

import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import { GlassCard } from "@/components/ui/GlassCard";
import { X, Save, FileText, CheckCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface EditorModalProps {
    isOpen: boolean;
    filePath: string | null;
    onClose: () => void;
}

export default function EditorModal({ isOpen, filePath, onClose }: EditorModalProps) {
    const [content, setContent] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        if (isOpen && filePath) {
            loadFile(filePath);
        }
    }, [isOpen, filePath]);

    const loadFile = async (path: string) => {
        setIsLoading(true);
        try {
            const res = await fetch("http://localhost:8000/api/cases/content", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path })
            });
            const data = await res.json();
            setContent(data.content);
        } catch (err) {
            console.error("Failed to load file", err);
            setContent("Error loading file content.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async () => {
        if (!filePath) return;
        setIsSaving(true);
        try {
            await fetch("http://localhost:8000/api/cases/save", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: filePath, content })
            });
            // Show toast or success
            setTimeout(() => setIsSaving(false), 500); // Fake delay for UX
        } catch (err) {
            console.error("Failed to save", err);
            setIsSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-8 bg-black/80 backdrop-blur-sm">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="w-full h-full max-w-6xl"
                >
                    <GlassCard className="h-full flex flex-col overflow-hidden" gradient>
                        {/* Header */}
                        <div className="flex justify-between items-center p-4 border-b border-white/10 bg-black/20">
                            <div className="flex items-center gap-3">
                                <FileText className="text-blue-400" />
                                <span className="text-zinc-200 font-mono text-sm">{filePath}</span>
                            </div>
                            <div className="flex gap-4">
                                <button
                                    onClick={handleSave}
                                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm font-medium transition-colors"
                                    disabled={isSaving}
                                >
                                    {isSaving ? (
                                        <>
                                            <CheckCircle size={16} />
                                            Saving...
                                        </>
                                    ) : (
                                        <>
                                            <Save size={16} />
                                            Save Changes
                                        </>
                                    )}
                                </button>
                                <button
                                    onClick={onClose}
                                    className="p-2 hover:bg-white/10 rounded-lg transition-colors text-zinc-400 hover:text-white"
                                >
                                    <X size={20} />
                                </button>
                            </div>
                        </div>

                        {/* Editor Area */}
                        <div className="flex-1 relative">
                            {isLoading ? (
                                <div className="absolute inset-0 flex items-center justify-center text-zinc-500">
                                    Loading content...
                                </div>
                            ) : (
                                <Editor
                                    height="100%"
                                    defaultLanguage="markdown"
                                    value={content}
                                    onChange={(val) => setContent(val || "")}
                                    theme="vs-dark"
                                    options={{
                                        minimap: { enabled: false },
                                        fontSize: 14,
                                        wordWrap: "on",
                                        padding: { top: 20 }
                                    }}
                                />
                            )}
                        </div>
                    </GlassCard>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}
