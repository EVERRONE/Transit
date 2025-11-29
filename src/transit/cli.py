"""Command-line interface for TransIt."""

import click
import logging
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from transit.parsers.document_processor import DocumentProcessor
from transit.translators.openai_translator import OpenAITranslator
from transit.core.validator import DocumentValidator
from transit.core.exceptions import TranslationError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """TransIt - Document translation with ultra-precise structure preservation."""
    pass


@main.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--target', '-t', required=True, help='Target language code (e.g., EN-US, FR, DE)')
@click.option('--output', '-o', type=click.Path(), help='Output file path (default: input_translated.docx)')
@click.option('--openai-key', envvar='OPENAI_API_KEY', help='OpenAI API key (or set OPENAI_API_KEY env var)')
@click.option('--model', default='gpt-4o', help='OpenAI model (default: gpt-4o)')
@click.option('--verbose', '-v', is_flag=True, help='Show progress bar')
@click.option('--sync-mode', is_flag=True, default=False, help='Use synchronous processing instead of async (default: async).')
@click.option('--enable-cache', is_flag=True, default=True, help='Enable translation caching (default: enabled)')
@click.option('--max-concurrent', type=int, default=None, show_default=False, help='Max concurrent requests in async mode (default: auto)')
def translate(input_file: str, target: str, output: str, openai_key: str,
              model: str, verbose: bool, sync_mode: bool, enable_cache: bool,
              max_concurrent: Optional[int]):
    """
    Translate a DOCX document with AI-powered context awareness.

    Supports both DOCX and PDF files (PDF will be auto-converted).

    Examples:
        transit translate document.docx --target EN-US
        transit translate document.pdf --target EN-US
        transit translate document.docx --target DE --model gpt-4o-mini
        transit translate document.docx --target EN-US --sync-mode
    """
    # Check if input is PDF - auto-convert if needed
    input_path = Path(input_file)
    intermediate_docx = None

    if input_path.suffix.lower() == '.pdf':
        click.echo("PDF file detected - converting to DOCX first...")

        from transit.converters.pdf_converter import PDFConverter
        from transit.converters.pdf_quality_validator import PDFConversionQualityValidator

        # Convert PDF to DOCX
        converter = PDFConverter()

        if not converter.is_available():
            click.echo(
                "Error: pdf2docx not installed. Install with: pip install pdf2docx",
                err=True
            )
            sys.exit(1)

        # Convert with validation
        success, docx_path, stats = converter.convert_and_validate(str(input_path))

        if not success:
            click.echo(f"Error: PDF conversion failed: {stats.get('error')}", err=True)
            sys.exit(1)

        click.echo(f"✓ PDF converted to DOCX: {docx_path}")

        # Show validation results
        if "validation" in stats:
            validation = stats["validation"]
            click.echo(
                f"  Converted: {validation['paragraph_count']} paragraphs, "
                f"{validation['table_count']} tables"
            )

            if validation["issues"]:
                click.echo("  Conversion issues:")
                for severity, message in validation["issues"]:
                    click.echo(f"    [{severity.upper()}] {message}")

        # Use converted DOCX as input
        input_file = docx_path
        intermediate_docx = docx_path

        # Adjust output path for PDF
        if not output:
            output = str(input_path.parent / f"{input_path.stem}_translated.pdf")
        click.echo()

    # Validate required OpenAI API key
    if not openai_key:
        click.echo("Error: OpenAI API key required. Set OPENAI_API_KEY environment variable or use --openai-key", err=True)
        sys.exit(1)

    # Set output path
    if not output:
        input_path = Path(input_file)
        output = str(input_path.parent / f"{input_path.stem}_translated{input_path.suffix}")

    click.echo(f"Input: {input_file}")
    click.echo(f"Output: {output}")
    click.echo(f"Target language: {target}")
    click.echo("Translation engine: OpenAI")
    click.echo(f"Model: {model}")
    click.echo()

    try:
        # Initialize translator
        click.echo("Initializing OpenAI translator...")
        translator_instance = OpenAITranslator(openai_key, model=model)

        # Wrap translator with performance features
        if enable_cache:
            from transit.utils.translation_cache import CachedTranslator
            click.echo("Enabling translation cache...")
            translator_instance = CachedTranslator(translator_instance)

        # Choose processing mode
        use_async = not sync_mode
        if use_async:
            from transit.parsers.async_document_processor import AsyncDocumentProcessor
            auto_concurrency = max_concurrent or getattr(translator_instance, "recommended_concurrency", 10)
            if max_concurrent is None:
                click.echo(f"Using async processing (auto max_concurrent={auto_concurrency})...")
            else:
                click.echo(f"Using async processing (max_concurrent={auto_concurrency})...")
            processor = AsyncDocumentProcessor(
                translator_instance,
                max_concurrent=auto_concurrency
            )
        else:
            click.echo("Using synchronous processing...")
            processor = DocumentProcessor(translator_instance)

        # Validate input
        from docx import Document
        doc = Document(input_file)
        validator = DocumentValidator()
        issues = validator.validate_document(doc)

        for severity, message in issues:
            if severity == "error":
                click.echo(f"ERROR: {message}", err=True)
            elif severity == "warning":
                click.echo(f"WARNING: {message}")
            else:
                click.echo(f"INFO: {message}")

        # Process document
        click.echo("\nTranslating document...")
        processor.translate_document(
            input_file,
            output,
            target,
            show_progress=verbose
        )

        # Validate output
        translated_doc = Document(output)
        validation_checks = validator.validate_translation_output(input_file, translated_doc)

        if validation_checks:
            click.echo("\nValidation results:")
            for severity, message in validation_checks:
                click.echo(f"  {severity.upper()}: {message}")

        click.echo(f"\n✓ Translation complete: {output}")

        # Show cache stats if enabled
        if enable_cache and hasattr(translator_instance, 'log_cache_stats'):
            click.echo("\nCache statistics:")
            translator_instance.log_cache_stats()
            stats = translator_instance.get_cache_stats()
            click.echo(f"  Cache hit rate: {stats.get('hit_rate', 0):.1f}%")
            click.echo(f"  Cached translations: {stats.get('size', 0)}")

        if hasattr(processor, 'close'):
            try:
                processor.close()
            except Exception as close_error:
                logger.debug("Processor cleanup raised: %s", close_error)

        # Clean up intermediate DOCX if it was converted from PDF
        if intermediate_docx and Path(intermediate_docx).exists():
            try:
                Path(intermediate_docx).unlink()
                click.echo(f"\n✓ Cleaned up intermediate file: {intermediate_docx}")
            except Exception as e:
                logger.warning(f"Could not remove intermediate file: {e}")

    except TranslationError as e:
        click.echo(f"Translation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('pdf_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output DOCX file path (default: same name with .docx)')
@click.option('--validate/--no-validate', default=True, help='Validate conversion quality (default: enabled)')
@click.option('--show-report', is_flag=True, help='Show detailed quality report')
def convert_pdf(pdf_file: str, output: str, validate: bool, show_report: bool):
    """
    Convert PDF file to DOCX format.

    This command converts a PDF to DOCX and validates the conversion quality.
    Use this to preview the conversion before translating.

    Examples:
        transit convert-pdf document.pdf
        transit convert-pdf document.pdf --output converted.docx --show-report
    """
    from transit.converters.pdf_converter import PDFConverter
    from transit.converters.pdf_quality_validator import PDFConversionQualityValidator

    # Check file extension
    pdf_path = Path(pdf_file)
    if pdf_path.suffix.lower() != '.pdf':
        click.echo(f"Error: Not a PDF file: {pdf_file}", err=True)
        sys.exit(1)

    # Set output path
    if not output:
        output = str(pdf_path.with_suffix('.docx'))

    click.echo(f"Converting PDF to DOCX...")
    click.echo(f"Input: {pdf_file}")
    click.echo(f"Output: {output}")
    click.echo()

    try:
        # Initialize converter
        converter = PDFConverter()

        if not converter.is_available():
            click.echo(
                "Error: pdf2docx not installed. Install with: pip install pdf2docx",
                err=True
            )
            sys.exit(1)

        # Get PDF info
        pdf_info = converter.get_pdf_info(pdf_file)

        if "error" not in pdf_info:
            click.echo(f"PDF Info:")
            click.echo(f"  Pages: {pdf_info.get('page_count', 'unknown')}")
            click.echo(f"  Size: {pdf_info.get('file_size_mb', 0):.2f} MB")
            click.echo()

        # Convert
        click.echo("Converting...")

        if validate:
            success, docx_path, stats = converter.convert_and_validate(pdf_file, output)
        else:
            success, docx_path, stats = converter.convert_pdf_to_docx(pdf_file, output)

        if not success:
            click.echo(f"✗ Conversion failed: {stats.get('error')}", err=True)
            sys.exit(1)

        click.echo(f"✓ Conversion successful: {docx_path}")
        click.echo()

        # Show basic stats
        click.echo("Conversion Statistics:")
        click.echo(f"  Input size: {stats.get('input_size_mb', 0):.2f} MB")
        click.echo(f"  Output size: {stats.get('output_size_mb', 0):.2f} MB")

        # Show validation results
        if validate and "validation" in stats:
            validation = stats["validation"]

            click.echo()
            click.echo("Document Content:")
            click.echo(f"  Paragraphs: {validation['paragraph_count']}")
            click.echo(f"  Tables: {validation['table_count']}")

            if validation["issues"]:
                click.echo()
                click.echo("Validation Issues:")
                for severity, message in validation["issues"]:
                    icon = "✗" if severity == "error" else "⚠" if severity == "warning" else "ℹ"
                    click.echo(f"  {icon} [{severity.upper()}] {message}")

            # Show detailed report if requested
            if show_report:
                validator = PDFConversionQualityValidator()
                is_valid, issues, report_stats = validator.validate_conversion(
                    docx_path,
                    pdf_info.get('page_count')
                )
                report = validator.generate_report((is_valid, issues, report_stats))
                click.echo()
                click.echo(report)

        click.echo()
        click.echo("✓ Conversion complete!")
        click.echo(f"  You can now translate this file with:")
        click.echo(f"  transit translate {output} --target <LANG>")

    except Exception as e:
        logger.exception("Conversion error")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@main.command()
def gui():
    """
    Launch the TransIt GUI application.

    Opens a graphical interface for document translation with:
    - Drag-and-drop file upload
    - Visual settings configuration
    - Progress tracking
    - Document preview

    Example:
        transit gui
    """
    try:
        from transit.gui.main_window import launch_gui

        click.echo("Launching TransIt GUI...")
        launch_gui()

    except ImportError as e:
        click.echo(
            f"Error: GUI dependencies not available.\n"
            f"Install with: pip install tkinterdnd2\n\n"
            f"Details: {e}",
            err=True
        )
        sys.exit(1)
    except Exception as e:
        logger.exception("GUI error")
        click.echo(f"Error launching GUI: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
