"use client";

import { loadStripe } from "@stripe/stripe-js";
import { CreditCard } from "lucide-react";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "pk_test_placeholder");

export function CheckoutButton({ priceId }: { priceId: string }) {
    const handleCheckout = async () => {
        const stripe = await stripePromise;
        if (!stripe) return;

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${apiUrl}/api/v1/payment/create-checkout-session`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ price_id: priceId }),
        });

        const session = await response.json();

        const result = await stripe.redirectToCheckout({
            sessionId: session.url.split("/").pop(), // Extract session ID from URL if needed, or just use URL
        });

        // Actually the backend returns {url: ...}, so we can just redirect to that URL
        if (session.url) {
            window.location.href = session.url;
        }

        if (result.error) {
            console.error(result.error.message);
        }
    };

    return (
        <button
            onClick={handleCheckout}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
        >
            <CreditCard className="w-4 h-4" />
            Subscribe Now
        </button>
    );
}
