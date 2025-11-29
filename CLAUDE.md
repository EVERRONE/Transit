# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TransIt is a DOCX document translation tool that translates Dutch documents to other languages while preserving **ultra-precise formatting**. Each original element remains in place with the translation inserted directly underneath. The tool uses OpenAI GPT-4o by default for context-aware translation (handles abbreviations, idioms, technical terms).

## Development Commands

### Installation
```bash
# Install in editable mode
pip install -e .

# Install dependencies
pip install -r requirements.txt

```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=transit

# Run specific test file
pytest tests/unit/test_formatting.py

# Run single test
pytest tests/unit/test_edge_cases.py::TestEmptyContent::test_empty_paragraph -v

# Run integration tests only
pytest tests/integration/

# Create test fixtures (generates 12 DOCX files)
python tests/fixtures/create_fixtures.py

# Run performance benchmarks
python tests/performance/benchmark.py

# Type checking
mypy src/
```

### Usage
```bash
# Basic translation (uses OpenAI GPT-4o by default)
transit translate document.docx --target EN-US


# Use cheaper/faster OpenAI model
transit translate document.docx --target EN-US --model gpt-4o-mini

# Show progress
transit translate document.docx --target EN-US --verbose
```

### Environment Setup
API keys must be set as environment variables:
```bash
# PowerShell (Windows)
$env:OPENAI_API_KEY="your_key_here"

# Bash (Linux/Mac)
export OPENAI_API_KEY="your_key_here"
```


## Architecture Overview

### Core Translation Flow

```
Document → iter_inner_content() → [Paragraph | Table] → Translation → XML Insertion
```

**Critical architectural decisions:**

1. **Run-level processing**: A paragraph contains multiple runs (text segments with uniform formatting). Translation operates at run level to preserve mixed formatting within paragraphs.

2. **Context-aware vertaling**:
   OpenAI GPT-4o vertaalt paragrafen met documentcontext. Afkortingen (m.b.t. ??' regarding), idiomen en technische termen worden intelligent afgehandeld.

3. **Document traversal via `iter_inner_content()`**: Must use this method (not `doc.paragraphs` + `doc.tables` separately) to maintain proper document order.

4. **Translation insertion via XML `addnext()`**: python-docx has no native `insert_paragraph_after()`, so we use low-level XML manipulation: `original_paragraph._p.addnext(new_para_element)`.

### Key Components

**`src/transit/parsers/document_processor.py`** - Main processing engine
- `translate_document()`: 3-stage pipeline:
  1. Main body (paragraphs + tables)
  2. Headers/footers across all sections
  3. Save output
- `_translate_paragraph_openai()`: Paragraph-level translation with context extraction
- `_insert_translation_paragraph_after()`: XML manipulation to insert translation immediately after original
- `_extract_document_context()`: Analyzes document to provide context (headers, sample content, detected type) to OpenAI

**`src/transit/translators/openai_translator.py`** - AI-powered translator
- Uses GPT-4o (default) or GPT-4o-mini
- `set_document_context()`: Receives document context for intelligent translation
- `_build_system_prompt()`: Constructs detailed prompt with instructions for:
  - Abbreviations (b.v., m.b.t., etc.)
  - Idioms and formality matching
  - Technical terms and proper nouns
  - Document context integration
- `translate_batch()`: Combines up to 5 texts with `---TEXT_SEPARATOR---` for context-aware batch translation

- Sentence-by-sentence translation
- Retry logic with tenacity
- Batch support (50 texts per API call)

**`src/transit/utils/formatting.py`** - Formatting preservation
- `clone_run_formatting()`: Deep-copies 20+ run properties (bold, italic, font, color, etc.)
- `clone_paragraph_formatting()`: Copies paragraph-level formatting (alignment, spacing, indentation)
- Uses tri-state logic (True/False/None) for inherited properties

- Uses `nl_core_news_lg` model
- Preserves whitespace via `sent.text_with_ws`

**`src/transit/utils/list_formatting.py`** - List preservation (NEW)
- `has_list_formatting()`: Detects bullet/numbered lists via `numPr` XML element
- `clone_list_formatting()`: Deep-copies numbering properties to translation paragraphs
- `get_list_level()`: Extracts indentation level (ilvl 0-8)
- Critical for maintaining list structure in translated documents

**`src/transit/utils/hyperlink_formatting.py`** - Hyperlink handling (NEW)
- `get_paragraph_hyperlinks()`: Extracts hyperlinks with text and URL
- `preserve_hyperlinks_in_translation()`: Logs hyperlinks for awareness
- Note: Full hyperlink re-insertion is complex due to position mapping after translation

**`src/transit/utils/special_characters.py`** - Special character preservation (NEW)
- `protect_special_characters()`: Replaces special chars with placeholders before translation
- `restore_special_characters()`: Restores after translation
- `preserve_tabs_in_run()`: Copies tab XML elements to translation runs
- `preserve_line_breaks_in_run()`: Copies line break XML elements
- Handles: non-breaking space, tab, line break, em/en space, zero-width space

**`src/transit/cli.py`** - Command-line interface
- Passes `sentence_splitter=None` for OpenAI translator

### Critical Implementation Details

**Formatting Preservation**:
- Must clone ALL 20+ run properties, not just bold/italic
- Tri-state properties (bold, italic, underline) can be `True`, `False`, or `None` (inherited)
- Translation paragraphs get `italic=True` as visual marker

**Table Processing**:
- Detect merged cells via `cell_id = id(cell._element)` to avoid duplicate processing
- Process recursively: Table → Cell → Paragraph → Run
- **Nested tables**: Check `cell.tables` before processing paragraphs; recursively call `_translate_table()` for nested tables

**List Formatting**:
- Bullets and numbered lists preserved via XML `numPr` element cloning
- Indentation levels (ilvl) maintained in translation paragraphs
- Integration: Called in `_insert_translation_paragraph_after()` after paragraph formatting clone

**Special Characters**:
- Tabs and line breaks preserved via XML element copying (not text replacement)
- Non-breaking spaces handled via protect/restore mechanism
- Integration: Called in `clone_run_formatting()` via `preserve_special_formatting_in_run()`

**Headers/Footers**:
- Each section has 3 types: default, first_page, even_page
- Check `not header.is_linked_to_previous` to avoid processing inherited headers

**Whitespace Preservation**:
- Critical for maintaining exact spacing between sentences

## Important Constraints


2. **XML manipulation required**: Translation insertion uses `original_paragraph._p.addnext(new_p)` because python-docx lacks native paragraph insertion methods.

3. **Run-level granularity is mandatory**: Cannot process at paragraph level without losing mixed formatting (e.g., "This is **bold** and this is not" has 3 runs).

4. **Document context is OpenAI-only**: The `_extract_document_context()` method only runs for OpenAI translator and provides sample content for intelligent abbreviation/idiom handling.

5. **Translation doubles paragraph count**: Output validation should verify `translated_para_count == original_para_count * 2`.

## Testing Infrastructure

**Test structure** (`tests/`):
```
tests/
├── unit/                          # Component-level tests
│   ├── test_edge_cases.py         # 100+ edge case scenarios
│   ├── test_openai_translator.py  # OpenAI translator with mocking
│   ├── test_document_processor.py # Document processor unit tests
│   ├── test_list_formatting.py    # List preservation tests
│   ├── test_hyperlink_formatting.py # Hyperlink detection tests
│   └── test_special_characters.py # Special char handling tests
├── integration/                   # End-to-end tests
│   └── test_full_translation.py   # Full pipeline tests with MockTranslator
├── fixtures/                      # Test DOCX files
│   └── create_fixtures.py         # Generates 12 test documents
└── performance/
    └── benchmark.py               # Performance benchmarks with statistics
```

**Available test fixtures** (created via `python tests/fixtures/create_fixtures.py`):
- `simple.docx` - 3 plain paragraphs
- `formatted.docx` - Mixed formatting (bold, italic, underline, colors, alignment)
- `table.docx` - 3x3 table with data
- `merged_cells.docx` - Table with merged cells (horizontal and vertical)
- `header_footer.docx` - Document with headers and footers
- `complex.docx` - Multi-element document (headings, tables, formatted text)
- `special_chars.docx` - Non-breaking spaces, tabs, line breaks
- `empty_elements.docx` - Empty paragraphs, whitespace-only paragraphs
- `abbreviations.docx` - Dutch abbreviations (b.v., m.b.t., o.a., etc.)
- `lists.docx` - Bullet lists, numbered lists, nested lists
- `hyperlinks.docx` - URLs and text hyperlinks
- `nested_tables.docx` - Tables within table cells

**Mock translator for testing**:
```python
class MockOpenAITranslator:
    def translate_text(self, text, ...):
        if not text or not text.strip():
            return text
        return text.upper()  # Simple uppercase transformation
```

**Performance benchmarks**:
- Benchmarks for different document sizes (10, 50, 200 paragraphs)
- Table benchmarks (10 tables with 3x3 cells)
- Mixed document benchmarks (paragraphs + tables + formatting)
- API delay impact tests (10ms, 50ms, 100ms, 200ms)
- Statistical analysis (mean, min, max, standard deviation)

## Technical Documentation

See `Visie.md` for comprehensive technical architecture including:
- Complete OOXML structure breakdown
- Element detection strategy (why sentence-within-run is optimal)
- Edge case handling (merged cells, hyperlinks, special characters)
- Performance optimization strategies
- 7-phase implementation roadmap

See `USAGE.md` for:
- API cost calculations
- Supported language codes
- Troubleshooting guide
