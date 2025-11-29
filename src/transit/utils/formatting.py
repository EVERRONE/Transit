"""Formatting preservation utilities."""

from docx.text.run import Run
from docx.text.paragraph import Paragraph
from typing import Optional
import logging
from transit.utils.special_characters import preserve_special_formatting_in_run

logger = logging.getLogger(__name__)


def clone_run_formatting(source_run: Run, target_run: Run) -> None:
    """
    Deep copy ALL formatting properties from source to target run.
    Uses tri-state logic (True/False/None for inheritance).

    Args:
        source_run: Run to copy formatting from
        target_run: Run to apply formatting to
    """
    try:
        # Font properties
        if source_run.font.name is not None:
            target_run.font.name = source_run.font.name
        if source_run.font.size is not None:
            target_run.font.size = source_run.font.size

        # Color (check if set)
        try:
            if source_run.font.color.type is not None:
                target_run.font.color.rgb = source_run.font.color.rgb
        except Exception:
            pass  # Color not set or accessible

        # Tri-state properties (bold, italic, etc.)
        target_run.bold = source_run.bold  # None/True/False
        target_run.italic = source_run.italic
        target_run.underline = source_run.underline

        # Additional tri-state properties
        try:
            target_run.font.all_caps = source_run.font.all_caps
            target_run.font.small_caps = source_run.font.small_caps
            target_run.font.strike = source_run.font.strike
            target_run.font.double_strike = source_run.font.double_strike
            target_run.font.outline = source_run.font.outline
            target_run.font.shadow = source_run.font.shadow
            target_run.font.emboss = source_run.font.emboss
            target_run.font.imprint = source_run.font.imprint
        except AttributeError:
            pass  # Some properties may not be available

        # Superscript/subscript (mutually exclusive)
        try:
            target_run.font.superscript = source_run.font.superscript
            target_run.font.subscript = source_run.font.subscript
        except AttributeError:
            pass

        # Highlighting
        try:
            if source_run.font.highlight_color is not None:
                target_run.font.highlight_color = source_run.font.highlight_color
        except AttributeError:
            pass

        # Character spacing
        try:
            if source_run.font.spacing is not None:
                target_run.font.spacing = source_run.font.spacing
        except AttributeError:
            pass

        # Style (named character style)
        if source_run.style is not None:
            target_run.style = source_run.style

        # Preserve special formatting (tabs, line breaks)
        preserve_special_formatting_in_run(source_run, target_run)

    except Exception as e:
        logger.warning(f"Error cloning run formatting: {e}")


def clone_paragraph_formatting(source_para: Paragraph, target_para: Paragraph) -> None:
    """
    Clone paragraph-level formatting.

    Args:
        source_para: Paragraph to copy formatting from
        target_para: Paragraph to apply formatting to
    """
    try:
        fmt_src = source_para.paragraph_format
        fmt_tgt = target_para.paragraph_format

        # Alignment
        if fmt_src.alignment is not None:
            fmt_tgt.alignment = fmt_src.alignment

        # Indentation
        if fmt_src.left_indent is not None:
            fmt_tgt.left_indent = fmt_src.left_indent
        if fmt_src.right_indent is not None:
            fmt_tgt.right_indent = fmt_src.right_indent
        if fmt_src.first_line_indent is not None:
            fmt_tgt.first_line_indent = fmt_src.first_line_indent

        # Spacing
        if fmt_src.space_before is not None:
            fmt_tgt.space_before = fmt_src.space_before
        if fmt_src.space_after is not None:
            fmt_tgt.space_after = fmt_src.space_after
        if fmt_src.line_spacing is not None:
            fmt_tgt.line_spacing = fmt_src.line_spacing
        if fmt_src.line_spacing_rule is not None:
            fmt_tgt.line_spacing_rule = fmt_src.line_spacing_rule

        # Pagination control
        if fmt_src.keep_together is not None:
            fmt_tgt.keep_together = fmt_src.keep_together
        if fmt_src.keep_with_next is not None:
            fmt_tgt.keep_with_next = fmt_src.keep_with_next
        if fmt_src.page_break_before is not None:
            fmt_tgt.page_break_before = fmt_src.page_break_before
        if fmt_src.widow_control is not None:
            fmt_tgt.widow_control = fmt_src.widow_control

        # Style
        if source_para.style is not None:
            target_para.style = source_para.style

    except Exception as e:
        logger.warning(f"Error cloning paragraph formatting: {e}")
