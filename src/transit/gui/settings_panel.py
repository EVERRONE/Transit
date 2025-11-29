"""Settings panel for translation configuration."""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class SettingsPanel(ttk.LabelFrame):
    """
    Panel for configuring translation settings.

    Allows user to set:
    - Target language
    - OpenAI credentials and model
    - Advanced performance options
    """

    def __init__(self, parent, **kwargs):
        """
        Initialize settings panel.

        Args:
            parent: Parent widget
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, text="Translation Settings", padding="10", **kwargs)

        # State
        self.target_lang_var = tk.StringVar(value='EN-US')
        self.model_var = tk.StringVar(value='gpt-4o')
        self.async_mode_var = tk.BooleanVar(value=True)
        self.enable_cache_var = tk.BooleanVar(value=True)
        self.max_concurrent_var = tk.IntVar(value=10)

        # API key
        self.openai_key_var = tk.StringVar(value=os.getenv('OPENAI_API_KEY', ''))

        # Create UI
        self._create_widgets()
        self._setup_layout()

    def _create_widgets(self) -> None:
        """Create all settings widgets."""
        # Target language
        self.target_label = ttk.Label(self, text="Target Language:")
        self.target_combo = ttk.Combobox(
            self,
            textvariable=self.target_lang_var,
            values=[
                'EN-US', 'EN-GB', 'FR', 'DE', 'ES', 'IT', 'NL',
                'PT', 'PT-BR', 'RU', 'JA', 'ZH', 'KO'
            ],
            state='readonly',
            width=15
        )

        # OpenAI settings
        self.openai_frame = ttk.LabelFrame(self, text="OpenAI Settings", padding="5")
        self.openai_key_label = ttk.Label(self.openai_frame, text="API Key:")
        self.openai_key_entry = ttk.Entry(
            self.openai_frame,
            textvariable=self.openai_key_var,
            show='*',
            width=40
        )

        self.model_label = ttk.Label(self.openai_frame, text="Model:")
        self.model_combo = ttk.Combobox(
            self.openai_frame,
            textvariable=self.model_var,
            values=['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
            state='readonly',
            width=20
        )

        # Advanced options
        self.advanced_frame = ttk.LabelFrame(self, text="Advanced Options", padding="5")
        self.async_check = ttk.Checkbutton(
            self.advanced_frame,
            text="Use async processing (recommended)",
            variable=self.async_mode_var
        )
        self.cache_check = ttk.Checkbutton(
            self.advanced_frame,
            text="Enable translation caching",
            variable=self.enable_cache_var
        )
        self.concurrent_label = ttk.Label(self.advanced_frame, text="Max concurrent requests:")
        self.concurrent_spin = ttk.Spinbox(
            self.advanced_frame,
            textvariable=self.max_concurrent_var,
            from_=1,
            to=50,
            width=10
        )

    def _setup_layout(self) -> None:
        """Layout widgets using grid geometry manager."""
        self.target_label.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.target_combo.grid(row=0, column=1, sticky='w', padx=5, pady=5)

        self.openai_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        self.openai_key_label.grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.openai_key_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        self.model_label.grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.model_combo.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        self.openai_frame.columnconfigure(1, weight=1)

        self.advanced_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        self.async_check.grid(row=0, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        self.cache_check.grid(row=1, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        self.concurrent_label.grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.concurrent_spin.grid(row=2, column=1, sticky='w', padx=5, pady=2)

        self.columnconfigure(1, weight=1)

    def get_settings(self) -> Dict[str, Any]:
        """
        Get current settings.

        Returns:
            Dictionary with all settings relevant for translation.
        """
        return {
            'target_language': self.target_lang_var.get(),
            'api_key': self.openai_key_var.get(),
            'model': self.model_var.get(),
            'async_mode': self.async_mode_var.get(),
            'enable_cache': self.enable_cache_var.get(),
            'max_concurrent': self.max_concurrent_var.get(),
        }

    def validate_settings(self) -> tuple[bool, str]:
        """
        Validate current settings.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.openai_key_var.get():
            return (False, "OpenAI API key is required")

        if not self.target_lang_var.get():
            return (False, "Target language is required")

        return (True, "")

    def save_to_env(self) -> None:
        """Save API key to environment variables (for current session)."""
        if self.openai_key_var.get():
            os.environ['OPENAI_API_KEY'] = self.openai_key_var.get()
            logger.info("OpenAI API key saved to environment")
