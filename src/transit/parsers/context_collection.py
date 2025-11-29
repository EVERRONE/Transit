"""Utilities for collecting paragraph contexts from DOCX documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParagraphContext:
    """Metadata describing where a paragraph lives within the document."""

    paragraph: Paragraph
    location: str  # body | header | footer
    section_index: Optional[int] = None
    table_path: Tuple[Tuple[int, int], ...] = field(default_factory=tuple)
    depth: int = 0  # nesting depth of tables

    @property
    def cell_coordinates(self) -> Optional[Tuple[int, int]]:
        """Return row/column for the innermost table cell, if any."""
        return self.table_path[-1] if self.table_path else None

    @property
    def key(self) -> int:
        """Unique key for this paragraph (stable for lifetime of paragraph)."""
        return id(self.paragraph._element)


@dataclass
class DocumentTraversalResult:
    """Container for paragraph contexts plus traversal warnings."""

    contexts: List[ParagraphContext] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def collect_document_contexts(doc: DocxDocument) -> DocumentTraversalResult:
    """
    Collect every paragraph in the document (body + headers/footers) with context metadata.
    """

    result = DocumentTraversalResult()

    # Body
    result.contexts.extend(_collect_from_parent(doc, location="body"))

    # Headers/footers per section
    for section_index, section in enumerate(doc.sections):
        result.contexts.extend(
            collect_section_contexts(section.header, location="header", section_index=section_index)
        )
        result.contexts.extend(
            collect_section_contexts(section.first_page_header, location="header_first_page", section_index=section_index)
        )
        result.contexts.extend(
            collect_section_contexts(section.even_page_header, location="header_even_page", section_index=section_index)
        )

        result.contexts.extend(
            collect_section_contexts(section.footer, location="footer", section_index=section_index)
        )
        result.contexts.extend(
            collect_section_contexts(section.first_page_footer, location="footer_first_page", section_index=section_index)
        )
        result.contexts.extend(
            collect_section_contexts(section.even_page_footer, location="footer_even_page", section_index=section_index)
        )

    # Ensure contexts are unique (paragraph may be referenced by multiple header aliases)
    seen = set()
    unique_contexts: List[ParagraphContext] = []
    for context in result.contexts:
        key = context.key
        if key in seen:
            continue
        seen.add(key)
        unique_contexts.append(context)
    result.contexts = unique_contexts

    return result


def collect_section_contexts(header_footer, location: str, section_index: Optional[int] = None) -> List[ParagraphContext]:
    if header_footer is None or getattr(header_footer, "is_linked_to_previous", False):
        return []
    return _collect_from_parent(header_footer, location=location, section_index=section_index)


def _collect_from_parent(parent, location: str, section_index: Optional[int] = None, table_path: Tuple[Tuple[int, int], ...] = ()) -> List[ParagraphContext]:
    contexts: List[ParagraphContext] = []
    for block in _iter_block_items(parent):
        if isinstance(block, Paragraph):
            contexts.append(
                ParagraphContext(
                    paragraph=block,
                    location=location,
                    section_index=section_index,
                    table_path=table_path,
                    depth=len(table_path),
                )
            )
        elif isinstance(block, Table):
            contexts.extend(
                _collect_from_table(
                    block,
                    location=location,
                    section_index=section_index,
                    parent_table_path=table_path,
                )
            )
    return contexts


def _collect_from_table(table: Table, location: str, section_index: Optional[int], parent_table_path: Tuple[Tuple[int, int], ...]) -> List[ParagraphContext]:
    contexts: List[ParagraphContext] = []
    processed_cells = set()

    row_count = len(table.rows)
    col_count = len(table.columns) if row_count else 0

    for row_index in range(row_count):
        for col_index in range(col_count):
            cell = table.cell(row_index, col_index)
            cell_id = id(cell._element)

            if cell_id in processed_cells:
                continue

            processed_cells.add(cell_id)
            current_path = parent_table_path + ((row_index, col_index),)
            contexts.extend(_collect_from_parent(cell, location, section_index, current_path))

    return contexts


def _iter_block_items(parent) -> Iterable:
    """
    Yield paragraphs and tables in document order for the given parent element.
    """
    if isinstance(parent, DocxDocument):
        parent_element = parent.element.body
    else:
        parent_element = getattr(parent, "_element", None)
        if parent_element is None:
            # Some python-docx containers expose .element instead of ._element
            parent_element = getattr(parent, "element", None)

    if parent_element is None or not hasattr(parent_element, "iterchildren"):
        logger.debug("Unsupported parent type encountered during traversal: %r", type(parent))
        return

    try:
        for child in parent_element.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)
    except TypeError:
        logger.debug("Parent element iteration failed for %r", type(parent_element))
        return
