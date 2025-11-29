export default function TermsPage() {
    return (
        <div className="min-h-screen bg-black text-white py-24">
            <div className="container mx-auto px-6 max-w-3xl">
                <h1 className="text-4xl font-bold mb-8">Terms of Service</h1>
                <div className="space-y-6 text-zinc-400">
                    <p>Last updated: November 29, 2025</p>
                    <p>
                        Please read these Terms of Service carefully before using TransIt.
                    </p>
                    <h2 className="text-2xl font-semibold text-white mt-8">1. Acceptance of Terms</h2>
                    <p>
                        By accessing or using our service, you agree to be bound by these Terms. If you disagree with any part of the terms, you may not access the service.
                    </p>
                    <h2 className="text-2xl font-semibold text-white mt-8">2. Use of Service</h2>
                    <p>
                        You agree to use TransIt only for lawful purposes and in accordance with these Terms. You are responsible for all content you upload.
                    </p>
                    <h2 className="text-2xl font-semibold text-white mt-8">3. Termination</h2>
                    <p>
                        We may terminate or suspend access to our service immediately, without prior notice or liability, for any reason whatsoever.
                    </p>
                </div>
            </div>
        </div>
    );
}
