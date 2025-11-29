"""Main GUI window for TransIt."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import logging
import threading
from pathlib import Path
from typing import Optional, Callable
import queue

from transit.gui.drag_drop import DragDropFrame
from transit.gui.settings_panel import SettingsPanel
from transit.gui.preview_panel import PreviewPanel

logger = logging.getLogger(__name__)


class TransItGUI:
    """
    Main GUI application for TransIt.

    Provides a user-friendly interface for document translation with:
    - Drag-and-drop file upload
    - Live preview of conversion
    - Settings configuration
    - Progress tracking
    """

    def __init__(self, root: tk.Tk):
        """
        Initialize GUI.

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("TransIt - Document Translation")
        self.root.geometry("1200x800")

        # State
        self.input_file: Optional[str] = None
        self.output_file: Optional[str] = None
        self.translation_thread: Optional[threading.Thread] = None
        self.is_translating = False

        # Queue for thread-safe GUI updates
        self.gui_queue = queue.Queue()

        # Setup GUI
        self._setup_styles()
        self._setup_menu()
        self._create_widgets()
        self._setup_layout()

        # Start queue processor
        self._process_queue()

        logger.info("TransIt GUI initialized")

    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()

        # Use a modern theme
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')

        # Configure colors
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Helvetica', 10))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Primary.TButton', font=('Helvetica', 10, 'bold'))

    def _setup_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File...", command=self._browse_input_file)
        file_menu.add_command(label="Save As...", command=self._browse_output_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Convert PDF to DOCX", command=self._show_pdf_converter)
        tools_menu.add_command(label="Clear Cache", command=self._clear_cache)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="10")

        # Title
        self.title_label = ttk.Label(
            self.main_frame,
            text="TransIt - Document Translation",
            style='Title.TLabel'
        )

        self.subtitle_label = ttk.Label(
            self.main_frame,
            text="Translate DOCX and PDF documents with AI-powered precision",
            style='Subtitle.TLabel'
        )

        # Drag-drop area
        self.drag_drop = DragDropFrame(
            self.main_frame,
            on_file_drop=self._on_file_selected
        )

        # File info panel
        self.file_info_frame = ttk.LabelFrame(self.main_frame, text="Selected File", padding="10")

        self.input_label = ttk.Label(self.file_info_frame, text="No file selected")
        self.output_label = ttk.Label(self.file_info_frame, text="")

        self.browse_button = ttk.Button(
            self.file_info_frame,
            text="Browse...",
            command=self._browse_input_file
        )

        # Settings panel
        self.settings_panel = SettingsPanel(self.main_frame)

        # Action buttons
        self.button_frame = ttk.Frame(self.main_frame)

        self.translate_button = ttk.Button(
            self.button_frame,
            text="Translate Document",
            command=self._start_translation,
            style='Primary.TButton',
            state='disabled'
        )

        self.cancel_button = ttk.Button(
            self.button_frame,
            text="Cancel",
            command=self._cancel_translation,
            state='disabled'
        )

        # Progress panel
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="Progress", padding="10")

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='indeterminate',
            length=400
        )

        self.status_label = ttk.Label(self.progress_frame, text="Ready")

        # Log panel
        self.log_frame = ttk.LabelFrame(self.main_frame, text="Log", padding="10")

        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            height=10,
            width=80,
            state='disabled',
            wrap='word'
        )

        # Preview panel
        self.preview_panel = PreviewPanel(self.main_frame)

    def _setup_layout(self):
        """Layout all widgets."""
        self.main_frame.grid(row=0, column=0, sticky='nsew')

        # Configure grid weights
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(6, weight=1)  # Log frame expands
        self.main_frame.columnconfigure(0, weight=1)

        # Title
        self.title_label.grid(row=0, column=0, pady=(0, 5), sticky='w')
        self.subtitle_label.grid(row=1, column=0, pady=(0, 20), sticky='w')

        # Drag-drop
        self.drag_drop.grid(row=2, column=0, pady=10, sticky='ew')

        # File info
        self.file_info_frame.grid(row=3, column=0, pady=10, sticky='ew')
        self.input_label.grid(row=0, column=0, sticky='w', padx=5)
        self.browse_button.grid(row=0, column=1, padx=5)
        self.output_label.grid(row=1, column=0, columnspan=2, sticky='w', padx=5, pady=(5, 0))

        # Settings
        self.settings_panel.grid(row=4, column=0, pady=10, sticky='ew')

        # Buttons
        self.button_frame.grid(row=5, column=0, pady=10)
        self.translate_button.grid(row=0, column=0, padx=5)
        self.cancel_button.grid(row=0, column=1, padx=5)

        # Progress
        self.progress_frame.grid(row=6, column=0, pady=10, sticky='ew')
        self.status_label.grid(row=0, column=0, pady=(0, 5), sticky='w')
        self.progress_bar.grid(row=1, column=0, sticky='ew')

        # Log
        self.log_frame.grid(row=7, column=0, pady=10, sticky='nsew')
        self.log_text.grid(row=0, column=0, sticky='nsew')

        # Preview (hidden by default)
        # self.preview_panel.grid(row=8, column=0, pady=10, sticky='ew')

    def _on_file_selected(self, file_path: str):
        """
        Handle file selection.

        Args:
            file_path: Path to selected file
        """
        self.input_file = file_path
        file_path_obj = Path(file_path)

        # Update labels
        self.input_label.config(text=f"Input: {file_path_obj.name}")

        # Generate output path
        if file_path_obj.suffix.lower() == '.pdf':
            self.output_file = str(file_path_obj.parent / f"{file_path_obj.stem}_translated.docx")
        else:
            self.output_file = str(file_path_obj.parent / f"{file_path_obj.stem}_translated{file_path_obj.suffix}")

        self.output_label.config(text=f"Output: {Path(self.output_file).name}")

        # Enable translate button
        self.translate_button.config(state='normal')

        # Log
        self._log(f"File selected: {file_path}")

        # Show preview if available
        self._show_file_preview(file_path)

    def _browse_input_file(self):
        """Browse for input file."""
        file_path = filedialog.askopenfilename(
            title="Select Document",
            filetypes=[
                ("Supported Files", "*.docx *.pdf"),
                ("Word Documents", "*.docx"),
                ("PDF Files", "*.pdf"),
                ("All Files", "*.*")
            ]
        )

        if file_path:
            self._on_file_selected(file_path)

    def _browse_output_file(self):
        """Browse for output file location."""
        if not self.input_file:
            messagebox.showwarning("No Input", "Please select an input file first.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Translation As",
            defaultextension=".docx",
            filetypes=[
                ("Word Documents", "*.docx"),
                ("All Files", "*.*")
            ],
            initialfile=Path(self.output_file).name if self.output_file else "translated.docx"
        )

        if file_path:
            self.output_file = file_path
            self.output_label.config(text=f"Output: {Path(file_path).name}")
            self._log(f"Output file set to: {file_path}")

    def _start_translation(self):
        """Start translation in background thread."""
        if self.is_translating:
            return

        # Validate settings
        settings = self.settings_panel.get_settings()

        if not settings.get('api_key'):
            messagebox.showerror(
                "Missing API Key",
                "Please enter your OpenAI API key in the settings."
            )
            return

        if not settings.get('target_language'):
            messagebox.showerror("Missing Target Language", "Please select a target language.")
            return

        # Update UI
        self.is_translating = True
        self.translate_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.progress_bar.start()
        self.status_label.config(text="Translating...")

        self._log("Starting translation...")
        self._log(f"Settings: {settings}")

        # Start translation thread
        self.translation_thread = threading.Thread(
            target=self._run_translation,
            args=(self.input_file, self.output_file, settings),
            daemon=True
        )
        self.translation_thread.start()

    def _run_translation(self, input_file: str, output_file: str, settings: dict):
        """
        Run translation in background thread.

        Args:
            input_file: Input file path
            output_file: Output file path
            settings: Translation settings
        """
        try:
            from transit.translators.openai_translator import OpenAITranslator
            from transit.parsers.document_processor import DocumentProcessor

            # Check if PDF conversion needed
            if Path(input_file).suffix.lower() == '.pdf':
                self.gui_queue.put(('log', "Converting PDF to DOCX..."))

                from transit.converters.pdf_converter import PDFConverter

                converter = PDFConverter()
                success, docx_path, stats = converter.convert_and_validate(input_file)

                if not success:
                    raise Exception(f"PDF conversion failed: {stats.get('error')}")

                self.gui_queue.put(('log', f"✓ PDF converted: {docx_path}"))
                input_file = docx_path

            # Initialize translator
            self.gui_queue.put(('log', "Initializing OpenAI translator..."))
            translator = OpenAITranslator(
                settings['api_key'],
                model=settings.get('model', 'gpt-4o')
            )

            if settings.get('enable_cache', True):
                from transit.utils.translation_cache import CachedTranslator
                self.gui_queue.put(('log', "Enabling translation cache..."))
                translator = CachedTranslator(translator)

            # Create processor
            async_enabled = settings.get('async_mode', True)
            if async_enabled:
                from transit.parsers.async_document_processor import AsyncDocumentProcessor
                max_concurrent = settings.get('max_concurrent', 10)
                self.gui_queue.put(('log', f"Using async processing (max_concurrent={max_concurrent})..."))
                processor = AsyncDocumentProcessor(
                    translator,
                    max_concurrent=max_concurrent
                )
            else:
                self.gui_queue.put(('log', "Using synchronous processing..."))
                processor = DocumentProcessor(translator)

            # Translate
            self.gui_queue.put(('log', "Translating document..."))

            processor.translate_document(
                input_file,
                output_file,
                settings['target_language'],
                show_progress=False
            )

            # Success
            self.gui_queue.put(('log', f"✓ Translation complete: {output_file}"))
            self.gui_queue.put(('status', 'Translation complete!'))
            self.gui_queue.put(('complete', output_file))

            # Cache stats
            if settings.get('enable_cache') and hasattr(translator, 'get_cache_stats'):
                stats = translator.get_cache_stats()
                self.gui_queue.put(('log', f"Cache hit rate: {stats.get('hit_rate', 0):.1f}%"))

            if hasattr(processor, 'close'):
                try:
                    processor.close()
                except Exception as close_error:
                    logger.debug("Processor cleanup raised: %s", close_error)

        except Exception as e:
            logger.exception("Translation error")
            self.gui_queue.put(('error', str(e)))

        finally:
            self.gui_queue.put(('done', None))

    def _cancel_translation(self):
        """Cancel ongoing translation."""
        if not self.is_translating:
            return

        # Note: Thread cancellation is not trivial in Python
        # This will only update UI state
        self.is_translating = False
        self.progress_bar.stop()
        self.status_label.config(text="Translation cancelled")
        self._log("Translation cancelled by user")

        self.translate_button.config(state='normal')
        self.cancel_button.config(state='disabled')

    def _process_queue(self):
        """Process GUI update queue."""
        try:
            while True:
                msg_type, msg_data = self.gui_queue.get_nowait()

                if msg_type == 'log':
                    self._log(msg_data)
                elif msg_type == 'status':
                    self.status_label.config(text=msg_data)
                elif msg_type == 'error':
                    self._on_translation_error(msg_data)
                elif msg_type == 'complete':
                    self._on_translation_complete(msg_data)
                elif msg_type == 'done':
                    self._on_translation_done()

        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self._process_queue)

    def _on_translation_complete(self, output_file: str):
        """Handle translation completion."""
        messagebox.showinfo(
            "Translation Complete",
            f"Document translated successfully!\n\nSaved to:\n{output_file}"
        )

    def _on_translation_error(self, error_msg: str):
        """Handle translation error."""
        messagebox.showerror("Translation Error", f"Translation failed:\n\n{error_msg}")
        self._log(f"ERROR: {error_msg}")

    def _on_translation_done(self):
        """Handle translation thread completion."""
        self.is_translating = False
        self.progress_bar.stop()
        self.translate_button.config(state='normal')
        self.cancel_button.config(state='disabled')

    def _log(self, message: str):
        """
        Add message to log.

        Args:
            message: Log message
        """
        self.log_text.config(state='normal')
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def _show_file_preview(self, file_path: str):
        """
        Show preview of file.

        Args:
            file_path: Path to file
        """
        # For now, just log
        # TODO: Implement preview panel
        self._log(f"Preview: {Path(file_path).name}")

    def _show_pdf_converter(self):
        """Show PDF converter dialog."""
        messagebox.showinfo(
            "PDF Converter",
            "Use the command line for PDF conversion:\n\n"
            "transit convert-pdf document.pdf"
        )

    def _clear_cache(self):
        """Clear translation cache."""
        try:
            from transit.utils.translation_cache import TranslationCache

            cache = TranslationCache()
            cache.clear()

            self._log("Translation cache cleared")
            messagebox.showinfo("Cache Cleared", "Translation cache has been cleared.")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            messagebox.showerror("Error", f"Failed to clear cache:\n{e}")

    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About TransIt",
            "TransIt v0.1.0\n\n"
            "Document translation with ultra-precise structure preservation.\n\n"
            "Powered by OpenAI GPT-4o."
        )

    def run(self):
        """Start GUI main loop."""
        self.root.mainloop()


def launch_gui():
    """Launch TransIt GUI application."""
    root = tk.Tk()
    app = TransItGUI(root)
    app.run()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    launch_gui()
