import { Check } from "lucide-react";
import { CheckoutButton } from "@/components/checkout-button";

export default function PricingPage() {
    return (
        <div className="min-h-screen bg-black text-white py-24">
            <div className="container mx-auto px-6">
                <div className="text-center mb-16">
                    <h1 className="text-4xl font-bold mb-4">Simple, Transparent Pricing</h1>
                    <p className="text-zinc-400">Choose the plan that fits your needs.</p>
                </div>

                <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                    {/* Free Plan */}
                    <div className="p-8 rounded-2xl border border-white/10 bg-zinc-900/50">
                        <h3 className="text-xl font-semibold mb-2">Starter</h3>
                        <div className="text-3xl font-bold mb-6">$0<span className="text-sm text-zinc-500 font-normal">/mo</span></div>
                        <ul className="space-y-4 mb-8 text-zinc-400">
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> 5 Documents / month</li>
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> Basic Formatting</li>
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> Standard Support</li>
                        </ul>
                        <button className="w-full border border-white/10 hover:bg-white/5 text-white font-medium py-3 rounded-lg transition-colors">
                            Get Started
                        </button>
                    </div>

                    {/* Pro Plan */}
                    <div className="p-8 rounded-2xl border border-blue-500/50 bg-blue-500/5 relative">
                        <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                            MOST POPULAR
                        </div>
                        <h3 className="text-xl font-semibold mb-2">Pro</h3>
                        <div className="text-3xl font-bold mb-6">$29<span className="text-sm text-zinc-500 font-normal">/mo</span></div>
                        <ul className="space-y-4 mb-8 text-zinc-300">
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> Unlimited Documents</li>
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> Advanced Formatting</li>
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> Priority Support</li>
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> PDF Conversion</li>
                        </ul>
                        <CheckoutButton priceId="price_placeholder_pro" />
                    </div>

                    {/* Enterprise Plan */}
                    <div className="p-8 rounded-2xl border border-white/10 bg-zinc-900/50">
                        <h3 className="text-xl font-semibold mb-2">Enterprise</h3>
                        <div className="text-3xl font-bold mb-6">Custom</div>
                        <ul className="space-y-4 mb-8 text-zinc-400">
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> Custom Integration</li>
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> SLA Guarantee</li>
                            <li className="flex items-center gap-2"><Check className="w-4 h-4 text-blue-400" /> Dedicated Account Manager</li>
                        </ul>
                        <button className="w-full border border-white/10 hover:bg-white/5 text-white font-medium py-3 rounded-lg transition-colors">
                            Contact Sales
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
