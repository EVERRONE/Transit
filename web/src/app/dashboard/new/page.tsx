import { UploadForm } from "@/components/upload-form";

export default function NewTranslation() {
    return (
        <div className="p-8 max-w-4xl mx-auto">
            <div className="mb-8 text-center">
                <h1 className="text-3xl font-bold text-white mb-2">New Translation</h1>
                <p className="text-zinc-400">Upload your document and choose your target language.</p>
            </div>

            <UploadForm />
        </div>
    );
}
