"use client";

import { User, CreditCard, BarChart3, Shield, Mail } from "lucide-react";
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { useEffect, useState } from "react";

export default function SettingsPage() {
    const supabase = createClientComponentClient();
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const getUser = async () => {
            const { data: { user } } = await supabase.auth.getUser();
            setUser(user);
            setLoading(false);
        };
        getUser();
    }, [supabase]);

    if (loading) {
        return <div className="text-white">Loading...</div>;
    }

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
                <p className="text-zinc-400">Manage your account and subscription.</p>
            </div>

            <div className="grid gap-8">
                {/* Profile Section */}
                <div className="bg-zinc-900/50 border border-white/10 rounded-2xl p-8">
                    <div className="flex items-center gap-4 mb-6">
                        <div className="p-3 bg-blue-500/10 rounded-lg">
                            <User className="w-6 h-6 text-blue-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold text-white">Profile</h2>
                            <p className="text-sm text-zinc-400">Your personal information</p>
                        </div>
                    </div>

                    <div className="space-y-4 max-w-xl">
                        <div>
                            <label className="block text-sm font-medium text-zinc-400 mb-1">Email Address</label>
                            <div className="flex items-center gap-3 px-4 py-3 bg-black/50 border border-white/10 rounded-lg text-white">
                                <Mail className="w-4 h-4 text-zinc-500" />
                                {user?.email}
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-zinc-400 mb-1">User ID</label>
                            <div className="flex items-center gap-3 px-4 py-3 bg-black/50 border border-white/10 rounded-lg text-zinc-500 font-mono text-sm">
                                <Shield className="w-4 h-4" />
                                {user?.id}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Subscription Section */}
                <div className="bg-zinc-900/50 border border-white/10 rounded-2xl p-8">
                    <div className="flex items-center gap-4 mb-6">
                        <div className="p-3 bg-purple-500/10 rounded-lg">
                            <CreditCard className="w-6 h-6 text-purple-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold text-white">Subscription</h2>
                            <p className="text-sm text-zinc-400">Manage your plan and billing</p>
                        </div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                        <div className="p-6 bg-black/50 border border-white/10 rounded-xl">
                            <div className="text-sm text-zinc-400 mb-1">Current Plan</div>
                            <div className="text-2xl font-bold text-white mb-4">Free Tier</div>
                            <div className="flex items-center gap-2 text-sm text-green-400">
                                <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                                Active
                            </div>
                        </div>

                        <div className="p-6 bg-black/50 border border-white/10 rounded-xl flex flex-col justify-center items-start">
                            <div className="text-sm text-zinc-400 mb-2">Want more features?</div>
                            <a href="/pricing" className="text-blue-400 hover:text-blue-300 font-medium text-sm flex items-center gap-1 transition-colors">
                                Upgrade to Pro &rarr;
                            </a>
                        </div>
                    </div>
                </div>

                {/* Usage Section */}
                <div className="bg-zinc-900/50 border border-white/10 rounded-2xl p-8">
                    <div className="flex items-center gap-4 mb-6">
                        <div className="p-3 bg-emerald-500/10 rounded-lg">
                            <BarChart3 className="w-6 h-6 text-emerald-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold text-white">Usage</h2>
                            <p className="text-sm text-zinc-400">Your translation statistics</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                        <div className="p-4 bg-black/50 border border-white/10 rounded-xl text-center">
                            <div className="text-2xl font-bold text-white mb-1">0</div>
                            <div className="text-xs text-zinc-500 uppercase tracking-wider">Documents</div>
                        </div>
                        <div className="p-4 bg-black/50 border border-white/10 rounded-xl text-center">
                            <div className="text-2xl font-bold text-white mb-1">0</div>
                            <div className="text-xs text-zinc-500 uppercase tracking-wider">Words</div>
                        </div>
                        <div className="p-4 bg-black/50 border border-white/10 rounded-xl text-center">
                            <div className="text-2xl font-bold text-white mb-1">$0.00</div>
                            <div className="text-xs text-zinc-500 uppercase tracking-wider">Cost Saved</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
