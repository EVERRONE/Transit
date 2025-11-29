import { FileText, Settings, CreditCard, LogOut, LayoutDashboard } from "lucide-react";
import Link from "next/link";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-black text-white flex">
            {/* Sidebar */}
            <aside className="w-64 border-r border-white/10 bg-zinc-950 flex flex-col">
                <div className="p-6 border-b border-white/10">
                    <Link href="/" className="flex items-center gap-2 font-bold text-xl tracking-tighter">
                        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                            <span className="text-white">T</span>
                        </div>
                        TransIt
                    </Link>
                </div>

                <nav className="flex-1 p-4 space-y-1">
                    {[
                        { icon: LayoutDashboard, label: "Overview", href: "/dashboard", active: true },
                        { icon: FileText, label: "Translations", href: "/dashboard/translations" },
                        { icon: CreditCard, label: "Billing", href: "/dashboard/billing" },
                        { icon: Settings, label: "Settings", href: "/dashboard/settings" },
                    ].map((item, i) => (
                        <Link
                            key={i}
                            href={item.href}
                            className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${item.active
                                    ? "bg-blue-600/10 text-blue-400"
                                    : "text-zinc-400 hover:bg-white/5 hover:text-white"
                                }`}
                        >
                            <item.icon className="w-5 h-5" />
                            {item.label}
                        </Link>
                    ))}
                </nav>

                <div className="p-4 border-t border-white/10">
                    <button className="flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-zinc-400 hover:bg-white/5 hover:text-white w-full transition-colors">
                        <LogOut className="w-5 h-5" />
                        Sign Out
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto">
                {children}
            </main>
        </div>
    );
}
