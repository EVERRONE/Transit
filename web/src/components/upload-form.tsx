"use client";

import { useState } from "react";
import { Upload, FileText, Check, AlertCircle, Loader2 } from "lucide-react";
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";

export function UploadForm() {
    const supabase = createClientComponentClient();
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
    const [targetLang, setTargetLang] = useState("FR");

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) return;

        setStatus("uploading");

        const formData = new FormData();
        formData.append("file", file);

        try {
            const { data: { session } } = await supabase.auth.getSession();
            const token = session?.access_token;

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${apiUrl}/api/v1/translation/upload?target_lang=${targetLang}`, {
                method: "POST",
                body: formData,
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (!res.ok) throw new Error("Upload failed");

            setStatus("success");
        } catch (error) {
            console.error(error);
            setStatus("error");
        }
    };

    return (
        <form onSubmit={handleSubmit} className="max-w-xl mx-auto space-y-8">
            <div className="space-y-4">
                <label className="block text-sm font-medium text-zinc-400">Select Document</label>
                <div className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center hover:border-blue-500/50 hover:bg-blue-500/5 transition-colors cursor-pointer relative">
                    <input
                        type="file"
                        onChange={handleFileChange}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        accept=".docx,.pdf"
                    />
                    <div className="flex flex-col items-center gap-4">
                        <div className="p-4 bg-white/5 rounded-full">
                            {file ? <FileText className="w-8 h-8 text-blue-400" /> : <Upload className="w-8 h-8 text-zinc-400" />}
                        </div>
                        <div>
                            <p className="font-medium text-white">{file ? file.name : "Click to upload or drag and drop"}</p>
                            <p className="text-sm text-zinc-500 mt-1">DOCX or PDF up to 10MB</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="space-y-4">
                <label className="block text-sm font-medium text-zinc-400">Target Language</label>
                <select
                    value={targetLang}
                    onChange={(e) => setTargetLang(e.target.value)}
                    className="w-full bg-zinc-900 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
                >
                    <option value="FR">French (Français)</option>
                    <option value="ES">Spanish (Español)</option>
                    <option value="DE">German (Deutsch)</option>
                    <option value="IT">Italian (Italiano)</option>
                    <option value="PT">Portuguese (Português)</option>
                    <option value="NL">Dutch (Nederlands)</option>
                </select>
            </div>

            <button
                type="submit"
                disabled={!file || status === "uploading"}
                className={`w-full py-4 rounded-xl font-medium transition-all ${!file ? "bg-zinc-800 text-zinc-500 cursor-not-allowed" :
                        status === "uploading" ? "bg-blue-600/50 text-white cursor-wait" :
                            status === "success" ? "bg-green-600 text-white" :
                                "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20"
                    }`}
            >
                {status === "uploading" ? (
                    <span className="flex items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Uploading...
                    </span>
                ) : status === "success" ? (
                    <span className="flex items-center justify-center gap-2">
                        <Check className="w-5 h-5" />
                        Upload Complete
                    </span>
                ) : (
                    "Start Translation"
                )}
            </button>

            {status === "error" && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-400">
                    <AlertCircle className="w-5 h-5" />
                    Something went wrong. Please try again.
                </div>
            )}
        </form>
    );
}
