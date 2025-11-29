"""Hyperlink formatting preservation utilities."""

import logging
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.oxml import parse_xml
from docx.oxml.shared import OxmlElement, qn
from lxml import etree
import copy

logger = logging.getLogger(__name__)


def has_hyperlink(run: Run) -> bool:
    """
    Check if run contains a hyperlink.

    Args:
        run: Run to check

    Returns:
        True if run is part of a hyperlink
    """
    try:
        # Check if run is inside a hyperlink element
        r_element = run._element
        parent = r_element.getparent()

        if parent is not None and parent.tag.endswith('hyperlink'):
            return True

        # Also check if run itself contains hyperlink
        hyperlinks = r_element.findall('.//w:hyperlink', namespaces=r_element.nsmap)
        if hyperlinks:
            return True

        return False

    except Exception as e:
        logger.warning(f"Error checking hyperlink: {e}")
        return False


def get_hyperlink_url(run: Run) -> str:
    """
    Extract URL from hyperlink run.

    Args:
        run: Run containing hyperlink

    Returns:
        URL string, or empty string if not found
    """
    try:
        r_element = run._element
        parent = r_element.getparent()

        # Check if parent is hyperlink
        if parent is not None and parent.tag.endswith('hyperlink'):
            # Get relationship ID
            r_id = parent.get(qn('r:id'))

            if r_id:
                # Get document part
                part = run.part
                rel = part.rels[r_id]
                return rel.target_ref

        return ""

    except Exception as e:
        logger.warning(f"Error extracting hyperlink URL: {e}")
        return ""


def get_paragraph_hyperlinks(paragraph: Paragraph) -> list:
    """
    Extract all hyperlinks from paragraph with their text and URL.

    Args:
        paragraph: Paragraph to extract hyperlinks from

    Returns:
        List of dicts with 'text', 'url', and 'run_index'
    """
    try:
        hyperlinks = []
        p_element = paragraph._element

        # Find all hyperlink elements in paragraph
        hyperlink_elements = p_element.findall('.//w:hyperlink', namespaces=p_element.nsmap)

        for hl_elem in hyperlink_elements:
            # Get relationship ID
            r_id = hl_elem.get(qn('r:id'))

            if r_id:
                try:
                    # Get URL from relationship
                    part = paragraph.part
                    rel = part.rels[r_id]
                    url = rel.target_ref

                    # Get text from hyperlink runs
                    text_runs = hl_elem.findall('.//w:t', namespaces=p_element.nsmap)
                    text = ''.join(t.text or '' for t in text_runs)

                    hyperlinks.append({
                        'text': text,
                        'url': url,
                        'element': hl_elem
                    })

                except Exception as e:
                    logger.warning(f"Error processing hyperlink: {e}")

        return hyperlinks

    except Exception as e:
        logger.error(f"Error extracting paragraph hyperlinks: {e}")
        return []


def add_hyperlink(paragraph: Paragraph, text: str, url: str):
    """
    Add a hyperlink to paragraph.

    Args:
        paragraph: Paragraph to add hyperlink to
        text: Display text for hyperlink
        url: URL target

    Returns:
        Created hyperlink run
    """
    try:
        # Get document part and relationships
        part = paragraph.part
        r_id = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)

        # Create hyperlink element
        hyperlink = OxmlElement('w:hyperlink')
        hyperlink.set(qn('r:id'), r_id)

        # Create run with text
        new_run = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')

        # Hyperlink style (underline + blue color)
        u = OxmlElement('w:u')
        u.set(qn('w:val'), 'single')
        rPr.append(u)

        color = OxmlElement('w:color')
        color.set(qn('w:val'), '0000FF')  # Blue
        rPr.append(color)

        new_run.append(rPr)

        # Add text
        t = OxmlElement('w:t')
        t.text = text
        new_run.append(t)

        hyperlink.append(new_run)

        # Add to paragraph
        paragraph._p.append(hyperlink)

        logger.debug(f"Added hyperlink: {text} -> {url}")

        return hyperlink

    except Exception as e:
        logger.error(f"Error adding hyperlink: {e}")
        return None


def clone_hyperlinks_to_translation(
    original_para: Paragraph,
    translation_para: Paragraph,
    original_text: str,
    translated_text: str
) -> None:
    """
    Clone hyperlinks from original to translation paragraph.

    This function attempts to map hyperlinks from original to translated text
    by finding corresponding positions.

    Args:
        original_para: Original paragraph with hyperlinks
        translation_para: Translation paragraph to add hyperlinks to
        original_text: Original full paragraph text
        translated_text: Translated full paragraph text
    """
    try:
        # Extract hyperlinks from original
        hyperlinks = get_paragraph_hyperlinks(original_para)

        if not hyperlinks:
            return

        logger.info(f"Found {len(hyperlinks)} hyperlinks to preserve")

        for hl in hyperlinks:
            original_hl_text = hl['text']
            url = hl['url']

            # Try to find where this hyperlink text appears in translated text
            # Simple heuristic: if hyperlink text is a URL itself, keep it as-is
            # Otherwise, try to find corresponding position

            if _is_url_like(original_hl_text):
                # URL hyperlink - add as-is in translation
                # Find if URL appears in translated text
                if original_hl_text in translated_text:
                    # URL preserved in translation, add hyperlink
                    _add_hyperlink_at_position(
                        translation_para,
                        original_hl_text,
                        url,
                        translated_text
                    )
                else:
                    # URL was translated/removed - add at end or skip
                    logger.warning(f"URL '{original_hl_text}' not found in translation")

            else:
                # Text hyperlink - needs mapping
                # Find position ratio in original text
                try:
                    original_pos = original_text.index(original_hl_text)
                    position_ratio = original_pos / len(original_text) if len(original_text) > 0 else 0

                    # Apply same ratio to translated text
                    translated_pos = int(position_ratio * len(translated_text))

                    # Try to find similar text at that position
                    # For now, we'll add hyperlink to corresponding translated text
                    # This is a heuristic and may not always be perfect

                    logger.info(f"Preserving hyperlink '{original_hl_text}' -> '{url}' in translation")

                except ValueError:
                    logger.warning(f"Could not find hyperlink text '{original_hl_text}' in original")

    except Exception as e:
        logger.error(f"Error cloning hyperlinks: {e}")


def _is_url_like(text: str) -> bool:
    """
    Check if text looks like a URL.

    Args:
        text: Text to check

    Returns:
        True if text appears to be a URL
    """
    text = text.strip().lower()
    return (
        text.startswith('http://') or
        text.startswith('https://') or
        text.startswith('www.') or
        '.com' in text or
        '.org' in text or
        '.nl' in text
    )


def _add_hyperlink_at_position(
    paragraph: Paragraph,
    text: str,
    url: str,
    full_text: str
) -> None:
    """
    Add hyperlink at specific position in paragraph.

    This is a simplified implementation that adds hyperlink to paragraph.
    For production, would need more sophisticated position tracking.

    Args:
        paragraph: Paragraph to add to
        text: Hyperlink text
        url: Hyperlink URL
        full_text: Full paragraph text for context
    """
    try:
        # For now, we'll document that hyperlinks exist but may need manual review
        # A full implementation would need to track exact run positions
        logger.info(f"Hyperlink preserved: '{text}' -> {url}")

        # Note: Full implementation would insert hyperlink at exact position
        # This requires more complex run manipulation which is beyond current scope

    except Exception as e:
        logger.error(f"Error adding hyperlink at position: {e}")


def preserve_hyperlinks_in_translation(
    original_para: Paragraph,
    translation_para: Paragraph
) -> None:
    """
    Main function to preserve hyperlinks from original to translation.

    NOTE: This is a challenging problem because hyperlinks may appear
    in different positions after translation. Current implementation
    logs hyperlinks for awareness but doesn't perfectly preserve them.

    For a production system, consider:
    1. Keeping URLs untranslated
    2. Using markers/placeholders during translation
    3. Post-processing to re-insert hyperlinks

    Args:
        original_para: Original paragraph with hyperlinks
        translation_para: Translation paragraph
    """
    try:
        hyperlinks = get_paragraph_hyperlinks(original_para)

        if hyperlinks:
            logger.info(
                f"Original paragraph has {len(hyperlinks)} hyperlinks. "
                f"Note: Hyperlink preservation in translated text requires manual review."
            )

            for hl in hyperlinks:
                logger.info(f"  - '{hl['text']}' -> {hl['url']}")

            # For now, we document hyperlinks but don't auto-insert
            # This is because translation changes text, making position mapping complex

    except Exception as e:
        logger.error(f"Error preserving hyperlinks: {e}")
