"""List formatting preservation utilities."""

import copy
import logging
import re
from typing import Dict

from docx.oxml import parse_xml
from docx.text.paragraph import Paragraph

logger = logging.getLogger(__name__)


def _style_suggests_list(paragraph: Paragraph) -> bool:
    style = getattr(paragraph, "style", None)
    if not style or not style.name:
        return False
    style_name = style.name.lower()
    return any(keyword in style_name for keyword in ("list", "bullet", "number"))


def _infer_level_from_style(style_name: str) -> int:
    match = re.search(r'(\d+)$', style_name)
    if not match:
        return 0
    return max(int(match.group(1)) - 1, 0)


def has_list_formatting(paragraph: Paragraph) -> bool:
    """
    Check if paragraph has list formatting (bullets or numbering).

    Args:
        paragraph: Paragraph to check

    Returns:
        True if paragraph is part of a list
    """
    try:
        # Check for numbering properties in paragraph XML
        p_element = paragraph._element
        pPr = p_element.find('.//w:pPr', namespaces=p_element.nsmap)

        if pPr is not None:
            numPr = pPr.find('.//w:numPr', namespaces=p_element.nsmap)
            if numPr is not None:
                return True

        if _style_suggests_list(paragraph):
            return True

        return False

    except Exception as e:
        logger.warning(f"Error checking list formatting: {e}")
        return False


def get_list_properties(paragraph: Paragraph) -> Dict[str, str]:
    """
    Extract list properties from paragraph.

    Args:
        paragraph: Paragraph with list formatting

    Returns:
        Dictionary with list properties (numId, ilvl, etc.)
    """
    try:
        p_element = paragraph._element
        pPr = p_element.find('.//w:pPr', namespaces=p_element.nsmap)

        if pPr is not None:
            numPr = pPr.find('.//w:numPr', namespaces=p_element.nsmap)
            if numPr is not None:
                properties: Dict[str, str] = {}

                numId = numPr.find('.//w:numId', namespaces=p_element.nsmap)
                if numId is not None:
                    properties['numId'] = numId.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')

                ilvl = numPr.find('.//w:ilvl', namespaces=p_element.nsmap)
                if ilvl is not None:
                    properties['ilvl'] = ilvl.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')

                if properties:
                    return properties

        if _style_suggests_list(paragraph):
            style = paragraph.style
            style_name = style.name if style else "List"
            return {
                'numId': getattr(style, 'style_id', style_name),
                'ilvl': str(_infer_level_from_style(style_name)),
                'styleName': style_name,
            }

        return {}

    except Exception as e:
        logger.error(f"Error extracting list properties: {e}")
        return {}


def clone_list_formatting(source_para: Paragraph, target_para: Paragraph) -> None:
    """
    Clone list formatting from source to target paragraph.

    Args:
        source_para: Source paragraph with list formatting
        target_para: Target paragraph to apply formatting to
    """
    try:
        if not has_list_formatting(source_para):
            return

        source_element = source_para._element
        target_element = target_para._element

        # Get source paragraph properties
        source_pPr = source_element.find('.//w:pPr', namespaces=source_element.nsmap)

        if source_pPr is None:
            return

        # Get or create target paragraph properties
        target_pPr = target_element.find('.//w:pPr', namespaces=target_element.nsmap)

        if target_pPr is None:
            # Create pPr element
            target_pPr = parse_xml(
                r'<w:pPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
            )
            # Insert at beginning of paragraph
            target_element.insert(0, target_pPr)

        # Get numbering properties from source
        source_numPr = source_pPr.find('.//w:numPr', namespaces=source_element.nsmap)

        if source_numPr is not None:
            # Deep copy the numPr element
            cloned_numPr = copy.deepcopy(source_numPr)

            # Remove existing numPr if any
            existing_numPr = target_pPr.find('.//w:numPr', namespaces=target_element.nsmap)
            if existing_numPr is not None:
                target_pPr.remove(existing_numPr)

            # Add cloned numPr to target
            target_pPr.append(cloned_numPr)

            logger.debug("Cloned list formatting from source to target paragraph")
        else:
            # Fallback to style-based cloning
            if _style_suggests_list(source_para):
                target_para.style = source_para.style
                logger.debug("Applied list style fallback during cloning")

        if _style_suggests_list(source_para):
            target_para.style = source_para.style

    except Exception as e:
        logger.error(f"Error cloning list formatting: {e}")


def is_bullet_list(paragraph: Paragraph) -> bool:
    """
    Check if paragraph is part of a bullet list (vs numbered list).

    Args:
        paragraph: Paragraph to check

    Returns:
        True if bullet list, False if numbered or not a list
    """
    try:
        # This is a heuristic - check the style name
        if paragraph.style and paragraph.style.name:
            style_name = paragraph.style.name.lower()
            if 'bullet' in style_name:
                return True

        # More sophisticated: would need to look up the numId in
        # the numbering.xml part and check the number format
        # For now, return False (assume numbered)
        return False

    except Exception as e:
        logger.warning(f"Error checking bullet list: {e}")
        return False


def get_list_level(paragraph: Paragraph) -> int:
    """
    Get the indentation level of a list item (0-8).

    Args:
        paragraph: Paragraph in list

    Returns:
        Indentation level (0 = top level)
    """
    try:
        properties = get_list_properties(paragraph)
        ilvl_str = properties.get('ilvl', '0')
        return int(ilvl_str)
    except Exception as e:
        logger.warning(f"Error getting list level: {e}")
        return 0


def preserve_list_structure_in_translation(original_para: Paragraph, translation_para: Paragraph) -> None:
    """
    Ensure translation paragraph preserves list structure from original.

    This is the main function to call when creating translation paragraphs
    that are part of lists.

    Args:
        original_para: Original paragraph (may be in a list)
        translation_para: Translation paragraph to apply list formatting to
    """
    if has_list_formatting(original_para):
        clone_list_formatting(original_para, translation_para)

        properties = get_list_properties(original_para)
        level = get_list_level(original_para)

        logger.info(
            "Preserved list formatting - Level: %s, NumId: %s",
            level,
            properties.get('numId', 'N/A'),
        )
