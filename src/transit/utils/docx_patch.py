"""Patches for python-docx compatibility quirks."""

from __future__ import annotations

from docx.table import Table

_PATCH_APPLIED = False


def apply_table_cell_cache() -> None:
    """Ensure merged cells return a stable _Cell instance."""
    global _PATCH_APPLIED

    if _PATCH_APPLIED:
        return

    original_cell = Table.cell

    def cached_cell(self, row_idx, col_idx):
        cache = getattr(self, "_transit_cell_cache", None)
        if cache is None:
            cache = {}
            setattr(self, "_transit_cell_cache", cache)

        cell = original_cell(self, row_idx, col_idx)
        cache_key = id(cell._element)

        if cache_key in cache:
            return cache[cache_key]

        cache[cache_key] = cell
        return cell

    Table.cell = cached_cell  # type: ignore[assignment]
    _PATCH_APPLIED = True


apply_table_cell_cache()
