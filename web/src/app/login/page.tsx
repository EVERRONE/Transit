"use client";

import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LoginPage() {
    const supabase = createClientComponentClient();
    const router = useRouter();

    useEffect(() => {
        const checkUser = async () => {
            const { data: { session } } = await supabase.auth.getSession();
            if (session) {
                router.push("/dashboard");
            }
        };
        checkUser();

        const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
            if (session) {
                router.push("/dashboard");
            }
        });

        return () => subscription.unsubscribe();
    }, [router, supabase]);

    return (
        <div className="min-h-screen bg-black flex items-center justify-center p-4">
            <div className="w-full max-w-md bg-zinc-900 p-8 rounded-2xl border border-white/10">
                <div className="text-center mb-8">
                    <h1 className="text-2xl font-bold text-white mb-2">Welcome Back</h1>
                    <p className="text-zinc-400">Sign in to continue to TransIt</p>
                </div>

                <Auth
                    supabaseClient={supabase}
                    appearance={{
                        theme: ThemeSupa,
                        variables: {
                            default: {
                                colors: {
                                    brand: '#2563eb',
                                    brandAccent: '#1d4ed8',
                                    inputText: 'white',
                                    inputBackground: '#18181b',
                                    inputBorder: '#27272a',
                                    inputLabelText: '#a1a1aa',
                                }
                            }
                        },
                        className: {
                            container: 'w-full',
                            button: 'w-full px-4 py-2 rounded-lg font-medium transition-colors',
                            input: 'w-full px-4 py-2 rounded-lg border bg-zinc-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                        }
                    }}
                    providers={['google', 'github']}
                    theme="dark"
                    redirectTo={`${typeof window !== 'undefined' ? window.location.origin : ''}/auth/callback`}
                />
            </div>
        </div>
    );
}
