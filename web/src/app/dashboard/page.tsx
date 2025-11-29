"use client";

import { useEffect, useState } from "react";
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { FileText, Download, Clock, CheckCircle, XCircle, Search, Trash2, Filter } from "lucide-react";
import Link from "next/link";

interface Job {
    job_id: string;
    filename: string;
    status: "queued" | "processing" | "completed" | "failed";
    target_lang: string;
    created_at?: string; // Mocked for now
}

export default function Dashboard() {
    const supabase = createClientComponentClient();
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [filterStatus, setFilterStatus] = useState<"all" | "completed" | "processing" | "failed">("all");

    // Mock fetching jobs - in a real app this would fetch from an API that lists user's jobs
    // Since our current backend is in-memory and doesn't persist user association easily without a DB,
    // we will simulate this or just fetch what we can if we had a list endpoint.
    // For this MVP, let's assume we store job IDs in local storage or just show a mocked list + whatever is in the backend if we could list it.
    // actually, let's just mock the list for the UI demonstration as the backend `jobs` dict is global and not user-scoped yet.

    useEffect(() => {
        // In a real implementation: fetch(`/api/v1/translation/jobs`)
        // For now, we'll use a mix of local state or just mock data for the "Enhanced" look
        const mockJobs: Job[] = [
            { job_id: "1", filename: "contract_v1.docx", status: "completed", target_lang: "FR" },
            { job_id: "2", filename: "manual.pdf", status: "processing", target_lang: "DE" },
            { job_id: "3", filename: "notes.txt", status: "failed", target_lang: "ES" },
        ];
        setJobs(mockJobs);
        setLoading(false);
    }, []);

    const handleDelete = async (jobId: string) => {
        if (!confirm("Are you sure you want to delete this translation?")) return;

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            await fetch(`${apiUrl}/api/v1/translation/jobs/${jobId}`, {
                method: 'DELETE'
            });
            setJobs(jobs.filter(j => j.job_id !== jobId));
        } catch (e) {
            console.error("Failed to delete", e);
        }
    };

    const filteredJobs = jobs.filter(job => {
        const matchesSearch = job.filename.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesFilter = filterStatus === "all" || job.status === filterStatus;
        return matchesSearch && matchesFilter;
    });

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
                    <p className="text-zinc-400">Manage your translations.</p>
                </div>
                <Link
                    href="/dashboard/new"
                    className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium transition-colors"
                >
                    New Translation
                </Link>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-zinc-900/50 border border-white/10 p-6 rounded-2xl">
                    <div className="text-zinc-400 text-sm mb-1">Total Translations</div>
                    <div className="text-3xl font-bold text-white">{jobs.length}</div>
                </div>
                <div className="bg-zinc-900/50 border border-white/10 p-6 rounded-2xl">
                    <div className="text-zinc-400 text-sm mb-1">Active Jobs</div>
                    <div className="text-3xl font-bold text-blue-400">
                        {jobs.filter(j => j.status === 'processing' || j.status === 'queued').length}
                    </div>
                </div>
                <div className="bg-zinc-900/50 border border-white/10 p-6 rounded-2xl">
                    <div className="text-zinc-400 text-sm mb-1">Words Translated</div>
                    <div className="text-3xl font-bold text-emerald-400">12.5k</div>
                </div>
            </div>

            {/* Controls */}
            <div className="flex gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                        type="text"
                        placeholder="Search files..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-zinc-900 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <div className="relative">
                    <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value as any)}
                        className="bg-zinc-900 border border-white/10 rounded-lg pl-10 pr-8 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
                    >
                        <option value="all">All Status</option>
                        <option value="completed">Completed</option>
                        <option value="processing">Processing</option>
                        <option value="failed">Failed</option>
                    </select>
                </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-zinc-900/50 border border-white/10 rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-white/10">
                    <h2 className="text-lg font-semibold text-white">Recent Activity</h2>
                </div>

                <div className="divide-y divide-white/5">
                    {filteredJobs.length === 0 ? (
                        <div className="p-8 text-center text-zinc-500">
                            No translations found.
                        </div>
                    ) : (
                        filteredJobs.map((job) => (
                            <div key={job.job_id} className="p-4 flex items-center justify-between hover:bg-white/5 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 bg-blue-500/10 rounded-lg">
                                        <FileText className="w-5 h-5 text-blue-400" />
                                    </div>
                                    <div>
                                        <div className="font-medium text-white">{job.filename}</div>
                                        <div className="text-sm text-zinc-500">Target: {job.target_lang}</div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-6">
                                    <div className={`flex items-center gap-2 text-sm px-3 py-1 rounded-full ${job.status === 'completed' ? 'bg-green-500/10 text-green-400' :
                                        job.status === 'failed' ? 'bg-red-500/10 text-red-400' :
                                            'bg-blue-500/10 text-blue-400'
                                        }`}>
                                        {job.status === 'completed' && <CheckCircle className="w-4 h-4" />}
                                        {job.status === 'failed' && <XCircle className="w-4 h-4" />}
                                        <button
                                            onClick={() => handleDelete(job.job_id)}
                                            className="p-2 hover:bg-red-500/10 rounded-lg text-zinc-400 hover:text-red-400 transition-colors"
                                            title="Delete"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
