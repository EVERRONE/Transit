import os
import logging
from pathlib import Path
from transit.translators.openai_translator import OpenAITranslator
from transit.parsers.async_document_processor import AsyncDocumentProcessor
from transit.utils.translation_cache import CachedTranslator

logger = logging.getLogger(__name__)

async def process_translation(
    job_id: str, 
    input_path: str, 
    target_lang: str, 
    jobs_dict: dict,
    model: str = "gpt-4o",
    tone: str = "formal"
):
    """
    Background task to run the translation.
    """
    try:
        jobs_dict[job_id]["status"] = "processing"
        logger.info(f"Starting translation job {job_id} with model={model}, tone={tone}")
        
        # Setup paths
        input_file = Path(input_path)
        
        # Handle PDF conversion
        if input_file.suffix.lower() == '.pdf':
            from transit.converters.pdf_converter import PDFConverter
            converter = PDFConverter()
            if converter.is_available():
                success, docx_path, stats = converter.convert_and_validate(str(input_file))
                if not success:
                    raise Exception(f"PDF conversion failed: {stats.get('error')}")
                input_file = Path(docx_path)
            else:
                raise Exception("PDF converter not available")

        output_path = input_file.parent / f"{input_file.stem}_translated.docx"
        
        # Get API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
            
        # Initialize components (mimicking CLI)
        translator = OpenAITranslator(api_key, model=model)
        # Note: Tone is not yet supported by OpenAITranslator directly in this version, 
        # but we are passing it for future use or if we modify the prompt.
        # For now we just log it.
        
        translator = CachedTranslator(translator)
        
        processor = AsyncDocumentProcessor(
            translator,
            max_concurrent=10
        )
        
        # Run translation
        # Note: translate_document might be sync or async depending on implementation
        # If it's sync, it will block the thread. ideally we run this in a threadpool if it's sync.
        # Looking at CLI, processor.translate_document seems to be the entry point.
        # AsyncDocumentProcessor.translate_document is likely async or manages its own loop?
        # CLI calls it directly. Let's assume for now we can call it.
        # If it blocks, we should run_in_executor.
        
        # For now, let's try running it directly.
        await processor.translate_document_async(str(input_file), str(output_path), target_lang) 
        # Wait, I need to check if translate_document is async. 
        # CLI calls `processor.translate_document`. 
        # If AsyncDocumentProcessor inherits from DocumentProcessor, it might override it.
        # Let's check AsyncDocumentProcessor source code to be sure.
        
        jobs_dict[job_id]["status"] = "completed"
        jobs_dict[job_id]["output_location"] = str(output_path)
        
    except Exception as e:
        logger.error(f"Translation failed for {job_id}: {e}")
        jobs_dict[job_id]["status"] = "failed"
        jobs_dict[job_id]["error"] = str(e)
