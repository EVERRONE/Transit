"""Special character handling utilities."""

import logging
import re
from docx.text.run import Run
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

logger = logging.getLogger(__name__)

# Special character mappings
SPECIAL_CHARS = {
    '\u00A0': '<NBSP>',  # Non-breaking space
    '\t': '<TAB>',        # Tab
    '\u2003': '<EMSP>',  # Em space
    '\u2002': '<ENSP>',  # En space
    '\u200B': '<ZWSP>',  # Zero-width space
    '\u00AD': '<SHY>',   # Soft hyphen
}

# Reverse mapping for restoration
SPECIAL_CHARS_REVERSE = {v: k for k, v in SPECIAL_CHARS.items()}


def protect_special_characters(text: str) -> str:
    """
    Replace special characters with placeholders before translation.

    This prevents translation APIs from normalizing or removing special
    whitespace characters.

    Args:
        text: Text with special characters

    Returns:
        Text with placeholders
    """
    if not text:
        return text

    protected_text = text

    for char, placeholder in SPECIAL_CHARS.items():
        protected_text = protected_text.replace(char, placeholder)

    return protected_text


def restore_special_characters(text: str) -> str:
    """
    Restore special characters from placeholders after translation.

    Args:
        text: Text with placeholders

    Returns:
        Text with restored special characters
    """
    if not text:
        return text

    restored_text = text

    for placeholder, char in SPECIAL_CHARS_REVERSE.items():
        restored_text = restored_text.replace(placeholder, char)

    return restored_text


def has_tabs(run: Run) -> bool:
    """
    Check if run contains tab characters (as XML elements).

    Args:
        run: Run to check

    Returns:
        True if run contains tabs
    """
    try:
        r_element = run._element
        tabs = r_element.findall('.//w:tab', namespaces=r_element.nsmap)
        return len(tabs) > 0
    except Exception as e:
        logger.warning(f"Error checking for tabs: {e}")
        return False


def get_tab_count(run: Run) -> int:
    """
    Count number of tab elements in run.

    Args:
        run: Run to check

    Returns:
        Number of tabs
    """
    try:
        r_element = run._element
        tabs = r_element.findall('.//w:tab', namespaces=r_element.nsmap)
        return len(tabs)
    except Exception as e:
        logger.warning(f"Error counting tabs: {e}")
        return 0


def add_tab(run: Run) -> None:
    """
    Add a tab character to run.

    Args:
        run: Run to add tab to
    """
    try:
        tab_element = OxmlElement('w:tab')
        run._element.append(tab_element)
        logger.debug("Added tab to run")
    except Exception as e:
        logger.error(f"Error adding tab: {e}")


def preserve_tabs_in_run(original_run: Run, translation_run: Run) -> None:
    """
    Preserve tab characters from original run to translation run.

    Args:
        original_run: Original run with tabs
        translation_run: Translation run to add tabs to
    """
    try:
        tab_count = get_tab_count(original_run)

        if tab_count > 0:
            logger.info(f"Preserving {tab_count} tab(s) in translation")

            # Add same number of tabs to translation
            for _ in range(tab_count):
                add_tab(translation_run)

    except Exception as e:
        logger.error(f"Error preserving tabs: {e}")


def has_line_break(run: Run) -> bool:
    """
    Check if run contains line break (br element).

    Args:
        run: Run to check

    Returns:
        True if run contains line breaks
    """
    try:
        r_element = run._element
        breaks = r_element.findall('.//w:br', namespaces=r_element.nsmap)
        return len(breaks) > 0
    except Exception as e:
        logger.warning(f"Error checking for line breaks: {e}")
        return False


def get_line_break_count(run: Run) -> int:
    """
    Count number of line break elements in run.

    Args:
        run: Run to check

    Returns:
        Number of line breaks
    """
    try:
        r_element = run._element
        breaks = r_element.findall('.//w:br', namespaces=r_element.nsmap)
        return len(breaks)
    except Exception as e:
        logger.warning(f"Error counting line breaks: {e}")
        return 0


def add_line_break(run: Run) -> None:
    """
    Add a line break to run.

    Args:
        run: Run to add line break to
    """
    try:
        br_element = OxmlElement('w:br')
        run._element.append(br_element)
        logger.debug("Added line break to run")
    except Exception as e:
        logger.error(f"Error adding line break: {e}")


def preserve_line_breaks_in_run(original_run: Run, translation_run: Run) -> None:
    """
    Preserve line breaks from original run to translation run.

    Args:
        original_run: Original run with line breaks
        translation_run: Translation run to add line breaks to
    """
    try:
        break_count = get_line_break_count(original_run)

        if break_count > 0:
            logger.info(f"Preserving {break_count} line break(s) in translation")

            for _ in range(break_count):
                add_line_break(translation_run)

    except Exception as e:
        logger.error(f"Error preserving line breaks: {e}")


def detect_special_whitespace(text: str) -> dict:
    """
    Detect various special whitespace characters in text.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with counts of each special character type
    """
    if not text:
        return {}

    counts = {}

    for char, name in SPECIAL_CHARS.items():
        count = text.count(char)
        if count > 0:
            counts[name] = count

    # Also check for regular tabs (not XML elements)
    regular_tabs = text.count('\t')
    if regular_tabs > 0:
        counts['REGULAR_TAB'] = regular_tabs

    return counts


def normalize_whitespace(text: str, preserve_special: bool = True) -> str:
    """
    Normalize whitespace in text.

    Args:
        text: Text to normalize
        preserve_special: If True, preserve special whitespace characters

    Returns:
        Normalized text
    """
    if not text:
        return text

    if preserve_special:
        # Protect special characters first
        protected = protect_special_characters(text)

        # Normalize only regular spaces
        normalized = re.sub(r' +', ' ', protected)

        # Restore special characters
        return restore_special_characters(normalized)
    else:
        # Normalize all whitespace
        return re.sub(r'\s+', ' ', text)


def preserve_special_formatting_in_run(original_run: Run, translation_run: Run) -> None:
    """
    Preserve all special formatting from original to translation run.

    This includes:
    - Tabs
    - Line breaks
    - Other special XML elements

    Args:
        original_run: Original run
        translation_run: Translation run
    """
    try:
        # Preserve tabs
        preserve_tabs_in_run(original_run, translation_run)

        # Preserve line breaks
        preserve_line_breaks_in_run(original_run, translation_run)

        logger.debug("Preserved special formatting in translation run")

    except Exception as e:
        logger.error(f"Error preserving special formatting: {e}")
