"""Drag-and-drop file upload widget."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


class DragDropFrame(ttk.Frame):
    """
    Frame that accepts drag-and-drop file uploads.

    Provides visual feedback when dragging over and calls callback on drop.
    """

    def __init__(
        self,
        parent,
        on_file_drop: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """
        Initialize drag-drop frame.

        Args:
            parent: Parent widget
            on_file_drop: Callback function(file_path) when file is dropped
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)

        self.on_file_drop = on_file_drop

        # State
        self.is_dragging = False

        # Create UI
        self._create_widgets()
        self._setup_drag_drop()

    def _create_widgets(self):
        """Create frame contents."""
        # Configure frame style
        self.config(relief='ridge', borderwidth=2, padding=20)

        # Icon/text
        self.label = ttk.Label(
            self,
            text="Drag & Drop Document Here\n\nor click to browse",
            justify='center',
            font=('Helvetica', 12)
        )
        self.label.pack(expand=True, fill='both')

        # Supported formats label
        self.formats_label = ttk.Label(
            self,
            text="Supported formats: DOCX, PDF",
            justify='center',
            font=('Helvetica', 9),
            foreground='gray'
        )
        self.formats_label.pack(pady=(10, 0))

        # Click to browse
        self.label.bind('<Button-1>', self._on_click)
        self.bind('<Button-1>', self._on_click)

    def _setup_drag_drop(self):
        """Setup drag-and-drop event handlers."""
        try:
            # Try to use tkinterdnd2 if available
            from tkinterdnd2 import DND_FILES

            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_drop)
            self.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.dnd_bind('<<DragLeave>>', self._on_drag_leave)

            logger.info("Drag-and-drop enabled with tkinterdnd2")

        except ImportError:
            logger.warning(
                "tkinterdnd2 not available - drag-and-drop disabled. "
                "Install with: pip install tkinterdnd2"
            )

            # Update label to indicate click only
            self.label.config(text="Click to browse for document")

    def _on_drag_enter(self, event):
        """Handle drag enter event."""
        self.is_dragging = True
        self.config(relief='solid', borderwidth=3)
        self.label.config(
            text="Drop file here",
            font=('Helvetica', 14, 'bold'),
            foreground='blue'
        )

    def _on_drag_leave(self, event):
        """Handle drag leave event."""
        self.is_dragging = False
        self.config(relief='ridge', borderwidth=2)
        self.label.config(
            text="Drag & Drop Document Here\n\nor click to browse",
            font=('Helvetica', 12),
            foreground='black'
        )

    def _on_drop(self, event):
        """
        Handle file drop event.

        Args:
            event: Drop event with file data
        """
        self.is_dragging = False
        self.config(relief='ridge', borderwidth=2)
        self.label.config(
            text="Drag & Drop Document Here\n\nor click to browse",
            font=('Helvetica', 12),
            foreground='black'
        )

        # Parse file path from event data
        file_path = event.data

        # Handle wrapped paths (with curly braces)
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]

        # Remove quotes if present
        file_path = file_path.strip('"\'')

        logger.info(f"File dropped: {file_path}")

        # Validate file extension
        if not self._is_valid_file(file_path):
            logger.warning(f"Invalid file type: {file_path}")
            self.label.config(
                text="Invalid file type!\nSupported: DOCX, PDF",
                foreground='red'
            )
            # Reset after 2 seconds
            self.after(2000, self._reset_label)
            return

        # Call callback
        if self.on_file_drop:
            self.on_file_drop(file_path)

    def _on_click(self, event):
        """Handle click event - browse for file."""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select Document",
            filetypes=[
                ("Supported Files", "*.docx *.pdf"),
                ("Word Documents", "*.docx"),
                ("PDF Files", "*.pdf"),
                ("All Files", "*.*")
            ]
        )

        if file_path and self.on_file_drop:
            self.on_file_drop(file_path)

    def _is_valid_file(self, file_path: str) -> bool:
        """
        Check if file has valid extension.

        Args:
            file_path: Path to file

        Returns:
            True if valid
        """
        valid_extensions = {'.docx', '.pdf'}
        extension = file_path.lower().split('.')[-1]
        return f'.{extension}' in valid_extensions

    def _reset_label(self):
        """Reset label to default state."""
        self.label.config(
            text="Drag & Drop Document Here\n\nor click to browse",
            foreground='black'
        )


class SimpleDragDropFrame(ttk.Frame):
    """
    Simplified drag-drop frame that works without tkinterdnd2.

    Only supports click-to-browse functionality.
    """

    def __init__(
        self,
        parent,
        on_file_select: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """
        Initialize simple drag-drop frame.

        Args:
            parent: Parent widget
            on_file_select: Callback when file is selected
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)

        self.on_file_select = on_file_select

        self._create_widgets()

    def _create_widgets(self):
        """Create frame contents."""
        self.config(relief='ridge', borderwidth=2, padding=20)

        # Icon
        self.icon_label = ttk.Label(
            self,
            text="📄",
            font=('Helvetica', 48)
        )
        self.icon_label.pack()

        # Text
        self.label = ttk.Label(
            self,
            text="Click to select document",
            justify='center',
            font=('Helvetica', 12)
        )
        self.label.pack(pady=10)

        # Browse button
        self.browse_button = ttk.Button(
            self,
            text="Browse Files",
            command=self._browse_file
        )
        self.browse_button.pack(pady=10)

        # Formats
        self.formats_label = ttk.Label(
            self,
            text="Supported: DOCX, PDF",
            font=('Helvetica', 9),
            foreground='gray'
        )
        self.formats_label.pack()

    def _browse_file(self):
        """Browse for file."""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select Document",
            filetypes=[
                ("Supported Files", "*.docx *.pdf"),
                ("Word Documents", "*.docx"),
                ("PDF Files", "*.pdf"),
                ("All Files", "*.*")
            ]
        )

        if file_path and self.on_file_select:
            self.on_file_select(file_path)
