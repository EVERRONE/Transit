# TransIt - Technische Visie

## 1. PROBLEEMSTELLING

Bestaande vertaaltools vernietigen documentstructuur bij vertaling. Er is behoefte aan een tool die:
- Alle originele elementen behoudt met exacte formatting
- Vertaling toevoegt direct onder elk origineel element
- Alle documenteigenschappen preserveert (kleur, lettertype, uitlijning, tabellen, headers, footers, enz.)

## 2. TECHNISCHE STRATEGIE

### 2.1 DOCX-aanpak (PRIMAIR)

**Kern architectuur:**
- Python-docx voor document manipulatie (niet docx2python - te beperkt voor write-operaties)
- Element-by-element benadering op Run-niveau (niet Paragraph-niveau)
- Deep-copy strategie voor formatting preservation

**Waarom Run-niveau:**
- Een paragraph bevat meerdere runs met verschillende formatting
- Run = kleinste tekstsegment met uniforme formatting eigenschappen
- Alleen op run-niveau kunnen we mixed-formatting binnen één alinea behouden
- Voorbeeld: "Dit is **vet** en dit niet" = 3 runs met verschillende properties

**Element detectie granulariteit:**
```
Document
├── Paragraph (w:p)
│   ├── Run (w:r) - OPERATIONEEL NIVEAU
│   │   ├── Text (w:t)
│   │   └── Properties (bold, italic, font, size, color, etc.)
│   └── Paragraph Format (alignment, spacing, indent)
├── Table
│   └── Cell
│       └── Paragraph → Run → Text
├── Header/Footer
│   └── Paragraph → Run → Text
```

**Vertaalbare eenheid:**
- Per run: extractie van alle zinnen → vertalen → insertie onder origineel
- Behoud run formatting voor zowel origineel als vertaling

### 2.2 PDF-aanpak (SECUNDAIR)

**Beperking erkend:**
- PDF is geen bewerkbaar formaat - geoptimaliseerd voor weergave, niet voor editing
- Structuur preservering bij PDF editing is technisch complex en foutgevoelig
- Text positioning werkt met bbox coordinates - zeer fragiel bij text expansion

**Gekozen strategie:**
```
PDF → DOCX conversie → TransIt DOCX flow → Output DOCX
```

**Rationale:**
- PyMuPDF/pypdf2 text extraction vernietigt semantische structuur
- Text replacement via redaction + insertion vereist exacte coordinate berekeningen
- Text expansion (NL→DE +35%) breekt layout volledig
- DOCX heeft semantische structuur die PDF mist

**Conversie tool:**
- pdf2docx library (behoudt layout redelijk goed)
- Alternatief: Adobe PDF Services API (commercieel, zeer accuraat)
- Gebruiker krijgt DOCX output - kan zelf naar PDF converteren indien nodig

## 3. CORE TECHNOLOGIE STACK

### 3.1 Document Processing

**python-docx v1.2.0+**
- Volledige toegang tot OOXML structuur (w:p, w:r, w:t elements)
- Run-level property manipulation
- Table, header, footer support
- Paragraph formatting preservation

**Kritieke operaties:**
```python
# Deep copy run properties
def clone_run_properties(source_run, target_run):
    target_run.bold = source_run.bold
    target_run.italic = source_run.italic
    target_run.underline = source_run.underline
    target_run.font.size = source_run.font.size
    target_run.font.name = source_run.font.name
    target_run.font.color.rgb = source_run.font.color.rgb
    # ... alle andere properties
```

### 3.2 NLP - Sentence Segmentation

- Dependency parse-based sentence boundary detection
- 88%+ accuracy voor Nederlands
- Superieur aan regex-based splitting voor Nederlandse taal

**Workflow:**
```python

def split_sentences(text):
    doc = nlp(text)
    return [sent.text for sent in doc.sents]
```

### 3.3 Translation API


**Technische voordelen:**
- Beste vertaalkwaliteit voor NL→XX (gevalideerd door benchmarks)
- `preserve_formatting=True` parameter
- `tag_handling='xml'` voor placeholder preservatie
- Glossaries voor terminologie consistency

**Pricing:**
- Free tier: 500k characters/maand
- Pro: €5.49/miljoen characters (50% goedkoper dan Google)

**API implementatie:**
```python

result = translator.translate_text(
    text,
    source_lang="NL",
    target_lang=target_lang,  # instelbaar
    preserve_formatting=True,
    tag_handling='xml'
)
```

**Fallback optie:**
- Google Cloud Translation API (130+ talen, minder kwaliteit voor NL)

### 3.4 Text Expansion Handling

**Probleem:**
- NL→DE: tot +35% text expansion
- NL→FR: +15-25%
- Single words: tot +300%

**Oplossing:**
- DOCX past automatisch aan (reflowable format)
- Geen hardcoded positioning zoals PDF
- Mogelijk probleem: tabellen met vaste kolombreedte
  - Detectie: check cell width properties
  - Waarschuwing aan gebruiker indien overflow risk

## 4. DOCUMENT INTERPRETATIE & ELEMENT DETECTIE

### 4.1 Document Traversal Strategie

**Kern principe:** Document order preservation via `iter_inner_content()`

**Implementatie:**
```python
from docx import Document

doc = Document('input.docx')

# Traverse document in exact order
for block in doc.iter_inner_content():
    if isinstance(block, Paragraph):
        process_paragraph(block)
    elif isinstance(block, Table):
        process_table(block)
```

**Waarom dit cruciaal is:**
- `doc.paragraphs` en `doc.tables` zijn aparte collecties zonder order
- `iter_inner_content()` geeft echte document volgorde
- Essentieel voor structuurbehoud

### 4.2 Element Definitie Hierarchie

**Niveau 1: Block-level elements**
```
Document Body
├── Paragraph (w:p)
├── Table (w:tbl)
└── SectionBreak
```

**Niveau 2: Paragraph-level elements**
```
Paragraph
├── Run (w:r) [meerdere per paragraph]
├── Hyperlink [speciale run container]
└── ParagraphFormat [alignment, spacing, indent]
```

**Niveau 3: Run-level elements** (OPERATIONEEL NIVEAU)
```
Run
├── Text (w:t) [de daadwerkelijke tekst]
├── Font properties
│   ├── name, size, color.rgb
│   └── bold, italic, underline, strike
├── Highlighting
└── Character spacing
```

**Niveau 4: Table-level elements**
```
Table
├── Row (w:tr) [meerdere per table]
│   └── Cell (w:tc) [meerdere per row]
│       ├── Cell properties (borders, shading, width)
│       └── Paragraph(s) [RECURSIEF → Niveau 2]
└── Table properties (borders, alignment)
```

**Niveau 5: Section-level elements**
```
Section
├── Header (3 types: default, first_page, even_page)
│   └── Paragraph(s) [RECURSIEF → Niveau 2]
├── Footer (3 types: default, first_page, even_page)
│   └── Paragraph(s) [RECURSIEF → Niveau 2]
└── Section properties (margins, orientation)
```

### 4.3 WAT IS EEN "ELEMENT" VOOR VERTALING?

**Vertaalbare eenheid = SENTENCE binnen RUN**

**Rationale:**
1. **Run-niveau te grof:** Een run kan meerdere zinnen bevatten
2. **Character-niveau te fijn:** Onpraktisch en breekt context
3. **Sentence-niveau binnen run:** Optimale granulariteit

**Voorbeeld breakdown:**
```
ORIGINEEL PARAGRAPH:
"Dit is een test. Het werkt goed. Nog een zin."

DOCX STRUCTUUR:
Paragraph
└── Run (bold=True)
    └── Text: "Dit is een test. Het werkt goed. Nog een zin."

VERTAALBARE ELEMENTEN:
1. "Dit is een test." → Translate → "This is a test."
2. "Het werkt goed." → Translate → "It works well."
3. "Nog een zin." → Translate → "Another sentence."

OUTPUT STRUCTUUR:
Paragraph (origineel)
└── Run (bold=True)
    └── "Dit is een test. Het werkt goed. Nog een zin."

Paragraph (vertaling - DIRECT ONDER ORIGINEEL)
└── Run (bold=True, italic=True als marker)
    └── "This is a test. It works well. Another sentence."
```

**COMPLEX VOORBEELD (multi-run paragraph):**
```
ORIGINEEL:
"Dit is <bold>belangrijk</bold> en dit niet."

DOCX STRUCTUUR:
Paragraph
├── Run 1 (bold=False): "Dit is "
├── Run 2 (bold=True): "belangrijk"
└── Run 3 (bold=False): " en dit niet."

VERTAALBARE ELEMENTEN:
Run 1: "Dit is " → "This is "
Run 2: "belangrijk" → "important"
Run 3: " en dit niet." → " and this is not."

OUTPUT:
Paragraph (origineel)
├── Run 1 (bold=False): "Dit is "
├── Run 2 (bold=True): "belangrijk"
└── Run 3 (bold=False): " en dit niet."

Paragraph (vertaling)
├── Run 1 (bold=False, italic=True): "This is "
├── Run 2 (bold=True, italic=True): "important"
└── Run 3 (bold=False, italic=True): " and this is not."
```

### 4.4 Sentence Boundary Detection

```python


def split_sentences_preserve_whitespace(text):
    """
    Split text into sentences while preserving exact whitespace.
    Returns list of (sentence, trailing_whitespace) tuples.
    """
    doc = nlp(text)
    sentences = []

    for sent in doc.sents:
        # sent.text_with_ws preserveert trailing whitespace
        sentence_text = sent.text_with_ws
        sentences.append(sentence_text)

    return sentences

# Voorbeeld:
text = "Eerste zin. Tweede zin.  Derde zin."
result = split_sentences_preserve_whitespace(text)
# → ["Eerste zin. ", "Tweede zin.  ", "Derde zin."]
# Let op: dubbele spatie tussen zin 2 en 3 behouden!
```

**Edge cases:**
- **Getallen:** "3.14" → geen sentence boundary
- **Aanhalingstekens:** "Hij zei: 'Stop.'" → 1 zin
- **Lege runs:** Skip, geen vertaling nodig

### 4.5 Formatting Preservation Mechanisme

**Complete Run Property Clone:**
```python
def clone_run_formatting(source_run, target_run):
    """
    Deep copy ALL formatting properties from source to target run.
    Uses tri-state logic (True/False/None for inheritance).
    """
    # Font properties
    target_run.font.name = source_run.font.name
    target_run.font.size = source_run.font.size

    # Color (check if set)
    if source_run.font.color.type is not None:
        target_run.font.color.rgb = source_run.font.color.rgb

    # Tri-state properties (bold, italic, etc.)
    target_run.bold = source_run.bold  # None/True/False
    target_run.italic = source_run.italic
    target_run.underline = source_run.underline

    # Additional tri-state properties
    target_run.font.all_caps = source_run.font.all_caps
    target_run.font.small_caps = source_run.font.small_caps
    target_run.font.strike = source_run.font.strike
    target_run.font.double_strike = source_run.font.double_strike
    target_run.font.outline = source_run.font.outline
    target_run.font.shadow = source_run.font.shadow
    target_run.font.emboss = source_run.font.emboss
    target_run.font.imprint = source_run.font.imprint

    # Superscript/subscript (mutually exclusive)
    target_run.font.superscript = source_run.font.superscript
    target_run.font.subscript = source_run.font.subscript

    # Highlighting
    if source_run.font.highlight_color is not None:
        target_run.font.highlight_color = source_run.font.highlight_color

    # Character spacing
    if source_run.font.spacing is not None:
        target_run.font.spacing = source_run.font.spacing

    # Style (named character style)
    if source_run.style is not None:
        target_run.style = source_run.style
```

**Paragraph Property Clone:**
```python
def clone_paragraph_formatting(source_para, target_para):
    """
    Clone paragraph-level formatting.
    """
    fmt_src = source_para.paragraph_format
    fmt_tgt = target_para.paragraph_format

    # Alignment
    fmt_tgt.alignment = fmt_src.alignment

    # Indentation
    fmt_tgt.left_indent = fmt_src.left_indent
    fmt_tgt.right_indent = fmt_src.right_indent
    fmt_tgt.first_line_indent = fmt_src.first_line_indent

    # Spacing
    fmt_tgt.space_before = fmt_src.space_before
    fmt_tgt.space_after = fmt_src.space_after
    fmt_tgt.line_spacing = fmt_src.line_spacing
    fmt_tgt.line_spacing_rule = fmt_src.line_spacing_rule

    # Pagination control
    fmt_tgt.keep_together = fmt_src.keep_together
    fmt_tgt.keep_with_next = fmt_src.keep_with_next
    fmt_tgt.page_break_before = fmt_src.page_break_before
    fmt_tgt.widow_control = fmt_src.widow_control

    # Style
    if source_para.style is not None:
        target_para.style = source_para.style
```

### 4.6 Translation Insertion Strategie

**Probleem:** python-docx heeft GEEN `insert_paragraph_after()`

**Oplossing:** Gebruik XML-level `addnext()`

**Implementatie:**
```python
def insert_translation_paragraph_after(original_paragraph, translated_runs):
    """
    Insert translation paragraph directly after original.
    Uses low-level XML manipulation.
    """
    # Create new paragraph via XML
    new_para_element = original_paragraph._element._new_p()

    # Insert in document order via XML
    original_paragraph._p.addnext(new_para_element)

    # Wrap in python-docx Paragraph object
    translation_para = Paragraph(new_para_element, original_paragraph._parent)

    # Clone paragraph formatting
    clone_paragraph_formatting(original_paragraph, translation_para)

    # Add translated runs with formatting
    for run_data in translated_runs:
        new_run = translation_para.add_run(run_data['text'])
        clone_run_formatting(run_data['original_run'], new_run)
        new_run.italic = True  # Visual marker voor vertaling

    return translation_para
```

**Alternatieve aanpak (veiliger):**
```python
def insert_via_next_paragraph(original_para, translation_text):
    """
    Find next paragraph and insert before it.
    Falls back to append if last paragraph.
    """
    doc = original_para._parent
    all_paragraphs = list(doc.iter_inner_content())

    # Find index
    orig_index = None
    for i, block in enumerate(all_paragraphs):
        if isinstance(block, Paragraph) and block._p == original_para._p:
            orig_index = i
            break

    if orig_index is None:
        raise ValueError("Original paragraph not found")

    # Insert before next OR append if last
    if orig_index + 1 < len(all_paragraphs):
        next_para = all_paragraphs[orig_index + 1]
        if isinstance(next_para, Paragraph):
            return next_para.insert_paragraph_before(translation_text)

    # Last paragraph - append
    return doc.add_paragraph(translation_text)
```

### 4.7 Table Processing Strategie

**Merged cells detectie:**
```python
def process_table(table):
    """
    Process table cell-by-cell, handling merged cells.
    """
    processed_cells = set()

    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            cell_id = (row_idx, col_idx)

            # Skip if already processed (merged cell)
            if cell_id in processed_cells:
                continue

            # Detect merge
            grid_span = cell._tc.grid_span or 1  # colspan
            v_merge = cell._tc.vMerge  # rowspan indicator

            # Mark all cells in merge range as processed
            for r in range(row_idx, row_idx + get_rowspan(cell)):
                for c in range(col_idx, col_idx + grid_span):
                    processed_cells.add((r, c))

            # Process cell content (recursief → paragraphs)
            for paragraph in cell.paragraphs:
                process_paragraph(paragraph)

def get_rowspan(cell):
    """
    Determine rowspan of merged cell.
    Note: DOCX doesn't store explicit rowspan count.
    """
    v_merge = cell._tc.vMerge
    if v_merge is None:
        return 1
    # vMerge="restart" means start of merge
    # Need to count subsequent cells with vMerge="continue"
    # Complex logic - simplified here
    return 1  # TODO: implement full detection
```

### 4.8 Header/Footer Processing

**Section iteration:**
```python
def process_headers_footers(doc):
    """
    Process all headers and footers across sections.
    """
    for section in doc.sections:
        # Header types
        headers = [
            section.header,              # Default header
            section.first_page_header,   # First page (if different_first_page)
            section.even_page_header     # Even pages (if odd_and_even_pages)
        ]

        for header in headers:
            if not header.is_linked_to_previous:
                # Has own definition
                for paragraph in header.paragraphs:
                    process_paragraph(paragraph)

        # Footer types (same structure)
        footers = [
            section.footer,
            section.first_page_footer,
            section.even_page_footer
        ]

        for footer in footers:
            if not footer.is_linked_to_previous:
                for paragraph in footer.paragraphs:
                    process_paragraph(paragraph)
```

## 5. COMPLETE PROCESSING PIPELINE

### 5.1 Main Processing Flow

```python
from docx import Document


def translate_document(input_path, output_path, target_lang):
    """
    Main translation pipeline.
    """
    doc = Document(input_path)

    # STAGE 1: Process main document body
    for block in doc.iter_inner_content():
        if isinstance(block, Paragraph):
            translate_paragraph(block, target_lang)
        elif isinstance(block, Table):
            translate_table(block, target_lang)

    # STAGE 2: Process headers/footers
    for section in doc.sections:
        translate_section_headers_footers(section, target_lang)

    # STAGE 3: Save output
    doc.save(output_path)

def translate_paragraph(paragraph, target_lang):
    """
    Translate single paragraph at run+sentence level.
    """
    # Skip empty paragraphs
    if not paragraph.text.strip():
        return

    # Collect all run translations
    translated_runs = []

    for run in paragraph.runs:
        if not run.text.strip():
            continue

        # Sentence segmentation
        sentences = split_sentences_preserve_whitespace(run.text)

        # Translate each sentence
        translated_sentences = []
        for sentence in sentences:
            if sentence.strip():  # Non-empty
                result = translator.translate_text(
                    sentence,
                    source_lang="NL",
                    target_lang=target_lang,
                    preserve_formatting=True
                )
                translated_sentences.append(result.text)
            else:
                # Preserve whitespace-only
                translated_sentences.append(sentence)

        # Combine translated sentences
        translated_text = ''.join(translated_sentences)

        translated_runs.append({
            'text': translated_text,
            'original_run': run
        })

    # Insert translation paragraph
    insert_translation_paragraph_after(paragraph, translated_runs)

def translate_table(table, target_lang):
    """
    Translate table cell-by-cell.
    """
    processed_cells = set()

    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            cell_id = id(cell._element)

            if cell_id in processed_cells:
                continue

            processed_cells.add(cell_id)

            # Process each paragraph in cell
            for paragraph in cell.paragraphs:
                translate_paragraph(paragraph, target_lang)

def translate_section_headers_footers(section, target_lang):
    """
    Translate headers and footers in section.
    """
    # Process headers
    for header in [section.header, section.first_page_header, section.even_page_header]:
        if header and not header.is_linked_to_previous:
            for paragraph in header.paragraphs:
                translate_paragraph(paragraph, target_lang)

    # Process footers
    for footer in [section.footer, section.first_page_footer, section.even_page_footer]:
        if footer and not footer.is_linked_to_previous:
            for paragraph in footer.paragraphs:
                translate_paragraph(paragraph, target_lang)
```

### 5.2 Edge Case Handling

**1. Empty runs:**
```python
if not run.text or not run.text.strip():
    continue  # Skip, maar behoud in origineel
```

**2. Whitespace-only sentences:**
```python
if sentence.strip():
    translate(sentence)
else:
    # Preserve whitespace exactly
    translated_sentences.append(sentence)
```

**3. Mixed language detection:**
```python
def detect_language(text):
    """Detecteer taal voordat vertalen"""
    detected = translator.translate_text(
        text[:100],  # First 100 chars
        target_lang="EN-US"
    )
    if detected.detected_source_lang != "NL":
        log_warning(f"Expected NL, got {detected.detected_source_lang}")
```

**4. API rate limiting:**
```python
import time
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(5))
def translate_with_retry(text, target_lang):
    try:
        return translator.translate_text(text, target_lang=target_lang)
        time.sleep(2)
        raise  # Retry
```

**5. Overly long text (API limits):**
```python

def translate_long_text(text, target_lang):
    if len(text) <= MAX_CHARS:
        return translator.translate_text(text, target_lang=target_lang).text

    # Split into chunks at sentence boundaries
    doc = nlp(text)
    chunks = []
    current_chunk = ""

    for sent in doc.sents:
        if len(current_chunk) + len(sent.text_with_ws) > MAX_CHARS:
            chunks.append(current_chunk)
            current_chunk = sent.text_with_ws
        else:
            current_chunk += sent.text_with_ws

    if current_chunk:
        chunks.append(current_chunk)

    # Translate chunks
    translated_chunks = [
        translator.translate_text(chunk, target_lang=target_lang).text
        for chunk in chunks
    ]

    return ''.join(translated_chunks)
```

## 6. ROBUSTNESS & VALIDATIE

### 6.1 Document Structure Validation

**Pre-processing validatie:**
```python
def validate_document(doc):
    """
    Validate document before processing.
    Returns list of warnings/errors.
    """
    issues = []

    # Check for unsupported elements
    if has_textboxes(doc):
        issues.append(("warning", "Document contains text boxes - may not preserve perfectly"))

    if has_embedded_objects(doc):
        issues.append(("warning", "Document contains embedded objects (charts, equations)"))

    # Check language
    sample_text = extract_sample_text(doc, max_chars=500)
    detected_lang = detect_language(sample_text)
    if detected_lang != "NL":
        issues.append(("error", f"Expected Dutch, detected {detected_lang}"))

    # Check table complexity
    for table in doc.tables:
        if has_nested_tables(table):
            issues.append(("warning", "Nested tables detected - may be slow"))

        if has_complex_merges(table):
            issues.append(("info", "Complex merged cells detected"))

    return issues
```

**Post-processing validatie:**
```python
def validate_translation_output(original_doc, translated_doc):
    """
    Verify translation preserved structure.
    """
    checks = []

    # Paragraph count should double (original + translation)
    orig_para_count = len(list(original_doc.paragraphs))
    trans_para_count = len(list(translated_doc.paragraphs))

    if trans_para_count != orig_para_count * 2:
        checks.append(("error", f"Paragraph count mismatch: {orig_para_count} → {trans_para_count}"))

    # Table count should remain same
    orig_table_count = len(original_doc.tables)
    trans_table_count = len(translated_doc.tables)

    if orig_table_count != trans_table_count:
        checks.append(("error", f"Table count changed: {orig_table_count} → {trans_table_count}"))

    # Section count should remain same
    if len(original_doc.sections) != len(translated_doc.sections):
        checks.append(("error", "Section count mismatch"))

    return checks
```

### 6.2 Critical Edge Cases

**1. Text met speciale characters:**
```python
def handle_special_characters(text):
    """
    Preserve special characters that may break translation.
    """
    # Preserve non-breaking spaces
    text = text.replace('\u00A0', '<NBSP>')

    # Preserve tabs
    text = text.replace('\t', '<TAB>')

    # Translate
    translated = translator.translate_text(text, ...)

    # Restore
    translated = translated.replace('<NBSP>', '\u00A0')
    translated = translated.replace('<TAB>', '\t')

    return translated
```

**2. Runs met alleen formatting (geen text):**
```python
def process_run(run):
    """Handle runs that may have no text but have formatting."""
    if run.text == "":
        # Empty run - skip translation maar behoud in structuur
        return None

    if run.text.isspace():
        # Whitespace-only - preserve exactly
        return run.text

    # Normal translation
    return translate(run.text)
```

**3. Paragraphs met alleen images:**
```python
def has_only_images(paragraph):
    """Check if paragraph contains only images, no text."""
    has_text = any(run.text.strip() for run in paragraph.runs)
    return not has_text and len(paragraph.runs) > 0
```

**4. Hyperlinks preservation:**
```python
def process_paragraph_with_hyperlinks(paragraph):
    """
    Process paragraph that may contain hyperlinks.
    Hyperlinks are special run containers.
    """
    for element in paragraph._element.iter():
        if element.tag.endswith('hyperlink'):
            # Hyperlink detected
            link_runs = [Run(r, paragraph) for r in element.findall('.//w:r', namespaces=element.nsmap)]

            for run in link_runs:
                # Translate run text maar behoud hyperlink
                translate_run(run)
```

**5. Lists (bullets/numbering):**
```python
def preserve_list_formatting(paragraph):
    """
    Preserve list numbering and bullet formatting.
    """
    # Check if paragraph is part of list
    if paragraph.style.name.startswith('List'):
        # Get numbering properties
        numPr = paragraph._element.find('.//w:numPr', namespaces=paragraph._element.nsmap)

        if numPr is not None:
            # Paragraph has numbering
            # Must preserve numPr in translation paragraph
            translation_para = create_translation_paragraph(paragraph)

            # Clone numbering properties via XML
            translation_para._element.get_or_add_pPr().append(copy.deepcopy(numPr))
```

### 6.3 Performance Optimizations

**Batch API calls:**
```python
def translate_paragraph_batch(paragraphs, target_lang):
    """
    Batch multiple paragraph translations into single API call.
    Reduces API overhead significantly.
    """
    # Collect all text fragments
    fragments = []
    fragment_map = []  # Track which fragment belongs to which para/run

    for para_idx, para in enumerate(paragraphs):
        for run_idx, run in enumerate(para.runs):
            if run.text.strip():
                fragments.append(run.text)
                fragment_map.append((para_idx, run_idx))

    batch_size = 50
    all_translations = []

    for i in range(0, len(fragments), batch_size):
        batch = fragments[i:i+batch_size]
        results = translator.translate_text(
            batch,
            source_lang="NL",
            target_lang=target_lang
        )
        all_translations.extend([r.text for r in results])

    # Map translations back
    for (para_idx, run_idx), translation in zip(fragment_map, all_translations):
        # Apply translation to correct para/run
        apply_translation(paragraphs[para_idx].runs[run_idx], translation)
```

**Async processing:**
```python
import asyncio

async def translate_document_async(doc, target_lang):
    """
    Async translation for better performance.
    """
    translator = AsyncTranslator(api_key)

    # Collect all translation tasks
    tasks = []

    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            if run.text.strip():
                task = translator.translate_text_async(
                    run.text,
                    target_lang=target_lang
                )
                tasks.append((run, task))

    # Execute all translations concurrently
    results = await asyncio.gather(*[task for _, task in tasks])

    # Apply results
    for (run, _), result in zip(tasks, results):
        apply_translation(run, result.text)
```

**Progress tracking:**
```python
from tqdm import tqdm

def translate_document_with_progress(doc, target_lang):
    """
    Show progress bar during translation.
    """
    # Count total elements
    total_runs = sum(
        len(para.runs)
        for para in doc.paragraphs
    )

    with tqdm(total=total_runs, desc="Translating") as pbar:
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                if run.text.strip():
                    translate_run(run, target_lang)
                pbar.update(1)
```

## 7. IMPLEMENTATIE STRATEGIE

### 7.1 Ontwikkelingsfasen

**Phase 1: DOCX Core (MVP)** - 2 weken
- [x] Document loading & traversal (iter_inner_content)
- [x] Basic paragraph processing
- [x] Run-level text extraction
- [x] Paragraph insertion na origineel (addnext)
- [x] Basic run formatting clone (bold, italic, font)
- [ ] CLI interface: `transit translate input.docx --target EN-US`

**Success criteria Phase 1:**
- Simpel document (10 para's, geen tabellen) correct vertaald
- Alle tekst aanwezig (origineel + vertaling)
- Bold/italic/underline behouden

**Phase 2: Sentence Detection & Complex Formatting** - 2 weken
- [ ] Sentence boundary detection met whitespace preservation
- [ ] Multi-run paragraph handling
- [ ] Complete formatting clone (alle 20+ properties)
- [ ] Paragraph formatting clone
- [ ] List formatting preservation (bullets, numbering)

**Success criteria Phase 2:**
- Multi-sentence paragraphs correct gesplitst
- Complex formatting (highlight, superscript, etc.) behouden
- Genummerde lijsten blijven correct genummerd

**Phase 3: Tables & Sections** - 2 weken
- [ ] Table iteration & cell processing
- [ ] Merged cell detection (colspan, rowspan)
- [ ] Header/footer detection & processing
- [ ] Section iteration (different first page, even/odd)
- [ ] Table structure validation

**Success criteria Phase 3:**
- 3x3 tabel met merged cells correct vertaald
- Headers/footers vertaald zonder structuurverlies
- Multi-section documents werken

**Phase 4: Edge Cases & Robustness** - 1 week
- [ ] Hyperlink preservation
- [ ] Special character handling (tabs, non-breaking spaces)
- [ ] Empty run handling
- [ ] Image-only paragraphs
- [ ] Validation (pre & post processing)
- [ ] Error handling & logging

**Success criteria Phase 4:**
- Edge case test suite (15 scenarios) passes
- Geen crashes bij corrupt input
- Duidelijke error messages

**Phase 5: Performance & UX** - 1 week
- [ ] Batch API calls
- [ ] Async translation
- [ ] Progress indicator
- [ ] Retry logic met exponential backoff
- [ ] API rate limiting handling
- [ ] Memory optimization voor grote docs

**Success criteria Phase 5:**
- 100-page document < 2 minuten
- Progress bar werkt
- Geen API timeouts

**Phase 6: PDF Support** - 2 weken
- [ ] pdf2docx integration
- [ ] Conversion quality validation
- [ ] User preview before translation
- [ ] Fallback strategies voor slechte conversies

**Phase 7: GUI (optioneel)** - 2 weken
- [ ] Tkinter/Qt interface
- [ ] Drag-drop upload
- [ ] Live preview
- [ ] Settings panel

### 7.2 Testing Strategie

**Unit tests:**
```python
# tests/test_formatting.py
def test_clone_run_bold():
    source = create_run(bold=True)
    target = create_run()
    clone_run_formatting(source, target)
    assert target.bold == True

def test_clone_run_all_properties():
    # Test alle 20+ properties
    pass

# tests/test_sentence_detection.py
    text = "Dit is zin 1. Dit is zin 2."
    result = split_sentences_preserve_whitespace(text)
    assert len(result) == 2
    assert result[0] == "Dit is zin 1. "

def test_abbreviation_handling():
    text = "Dr. Smith woont hier."
    result = split_sentences_preserve_whitespace(text)
    assert len(result) == 1  # Geen split bij Dr.

# tests/test_translation_insertion.py
def test_insert_paragraph_after():
    doc = create_test_doc()
    para = doc.paragraphs[0]
    insert_translation_paragraph_after(para, [{"text": "Translated"}])
    assert len(doc.paragraphs) == 2
    assert doc.paragraphs[1].text == "Translated"
```

**Integration tests:**
```python
# tests/integration/test_document_processing.py
def test_simple_document():
    """Test 5-paragraph document met mixed formatting."""
    input_doc = "fixtures/simple.docx"
    output_doc = translate_document(input_doc, "EN-US")

    # Verify structure
    assert paragraph_count(output_doc) == paragraph_count(input_doc) * 2

    # Verify formatting preserved
    orig_para = load_doc(input_doc).paragraphs[0]
    trans_para = output_doc.paragraphs[1]
    assert orig_para.runs[0].bold == trans_para.runs[0].bold

def test_table_document():
    """Test document met 3x3 tabel."""
    input_doc = "fixtures/table.docx"
    output_doc = translate_document(input_doc, "EN-US")

    # Verify table structure intact
    assert table_count(output_doc) == table_count(input_doc)
    assert table_cell_count(output_doc.tables[0]) == 9

def test_header_footer_document():
    """Test document met headers/footers."""
    input_doc = "fixtures/header_footer.docx"
    output_doc = translate_document(input_doc, "EN-US")

    # Verify headers translated
    orig_header = load_doc(input_doc).sections[0].header
    trans_header = output_doc.sections[0].header
    assert paragraph_count(trans_header) == paragraph_count(orig_header) * 2
```

**Edge case tests:**
```python
# tests/edge_cases/test_edge_cases.py
@pytest.mark.parametrize("test_case", [
    "empty_runs.docx",
    "whitespace_only.docx",
    "special_chars.docx",
    "hyperlinks.docx",
    "merged_cells.docx",
    "nested_tables.docx",
    "images_only.docx",
    "mixed_languages.docx",
    "very_long_paragraph.docx",
    "bullets_and_numbering.docx"
])
def test_edge_case(test_case):
    input_path = f"fixtures/edge_cases/{test_case}"
    output_doc = translate_document(input_path, "EN-US")

    # Should not crash
    assert output_doc is not None

    # Should preserve structure
    validate_structure(input_path, output_doc)
```

**Acceptance tests (manueel):**
```
Test Suite:
1. Juridisch contract (10 pagina's, complex formatting)
2. Financieel rapport (tabellen, grafieken)
3. Technische handleiding (afbeeldingen, code samples)
4. Academisch paper (voetnoten, bibliografie)
5. Marketing brochure (multi-column, text boxes)

Voor elk document:
- [ ] Vertaling accuraat (spot check 10 zinnen)
- [ ] Formatting identiek (visual comparison)
- [ ] Geen crashes
- [ ] Redelijke performance (<5 min voor 50 pagina's)
```

### 7.3 Error Handling Strategie

**Critical errors (stop processing):**
```python
class TranslationError(Exception):
    """Base exception for translation errors."""
    pass

class APIAuthenticationError(TranslationError):
    def __init__(self):

class CorruptDocumentError(TranslationError):
    """DOCX structure is corrupt."""
    def __init__(self, details):
        super().__init__(f"Document structure corrupt: {details}")

class FileIOError(TranslationError):
    """Cannot read/write file."""
    def __init__(self, path, operation):
        super().__init__(f"Cannot {operation} file: {path}")
```

**Recoverable errors (log + continue):**
```python
import logging

logger = logging.getLogger('transit')

def translate_run_safe(run, target_lang):
    """Translate run with error recovery."""
    try:
        return translator.translate_text(run.text, target_lang=target_lang)
        logger.warning("Rate limit hit, retrying with backoff...")
        time.sleep(2)
        return translate_run_safe(run, target_lang)  # Retry
        # Fallback: return original text
        logger.info("Returning original text as fallback")
        return run.text
    except Exception as e:
        logger.error(f"Unexpected error translating run: {e}")
        return run.text
```

**Warnings:**
```python
def check_table_overflow_risk(table):
    """Warn if table cells may overflow due to text expansion."""
    for row in table.rows:
        for cell in row.cells:
            cell_width = cell.width
            text_length = sum(len(para.text) for para in cell.paragraphs)

            # Heuristic: if text is >80% of estimated cell capacity
            estimated_capacity = cell_width / 100  # Rough estimate
            if text_length > estimated_capacity * 0.8:
                logger.warning(
                    f"Cell may overflow after translation (current: {text_length} chars, "
                    f"width: {cell_width}). Consider manual review."
                )
```

## 8. SAMENVATTING: VAN UPLOAD TOT OUTPUT

**Complete workflow:**

```
USER UPLOADS DOCX
        ↓
[1] VALIDATIE
    - Check file format (DOCX/PDF)
    - Validate DOCX structure (niet corrupt)
    - Detect language (verwacht NL)
    - Scan voor unsupported elements (textboxes, etc.)
    - Waarschuw gebruiker indien issues
        ↓
[2] DOCUMENT PARSING
    - Load document met python-docx
    - Traverse via iter_inner_content() (document order!)
    - Identify blocks: Paragraph, Table
        ↓
[3] ELEMENT PROCESSING (per block)
    │
    ├── PARAGRAPH:
    │   │
    │   ├─ Iterate over runs in paragraph
    │   │
    │   ├─ Per RUN:
    │   │   ├─ Extract text
    │   │   │   → ["Zin 1. ", "Zin 2."]
    │   │   │   → ["Sentence 1. ", "Sentence 2."]
    │   │   └─ Combine: "Sentence 1. Sentence 2."
    │   │
    │   ├─ Construct translation paragraph
    │   │   ├─ Clone paragraph formatting
    │   │   ├─ Add runs met translated text
    │   │   └─ Clone run formatting (20+ properties)
    │   │
    │   └─ Insert translation paragraph DIRECT ONDER origineel
    │       └─ Via XML: original_para._p.addnext(translation_para._p)
    │
    ├── TABLE:
    │   │
    │   ├─ Iterate over cells (skip merged duplicates)
    │   │
    │   └─ Per CELL:
    │       └─ Process paragraphs in cell (RECURSIEF → PARAGRAPH)
    │
    └── HEADER/FOOTER:
        │
        ├─ Iterate over sections
        │
        └─ Per SECTION:
            ├─ Process header (default, first_page, even_page)
            └─ Process footer (default, first_page, even_page)
                └─ Apply PARAGRAPH processing
        ↓
[4] QUALITY ASSURANCE
    - Validate paragraph count (should be 2x original)
    - Validate table count (should be unchanged)
    - Check for untranslated text
    - Log warnings voor edge cases
        ↓
[5] OUTPUT
    - Save translated DOCX
    - Show statistics (chars translated, API cost, time)
        ↓
USER DOWNLOADS TRANSLATED DOCX
```

**Kritieke beslissingen recap:**
1. **Element = Sentence binnen Run** (niet paragraph, niet character)
2. **Traversal via iter_inner_content()** (niet doc.paragraphs + doc.tables)
3. **Insertion via XML addnext()** (geen native insert_after)
4. **Formatting clone = 20+ properties** (niet alleen bold/italic)
5. **Whitespace preservation** (sent.text_with_ws)
6. **Batch API calls** (50 texts per call)
7. **Error recovery** (fallback naar original bij API fail)

## 9. ALTERNATIEVEN OVERWOGEN & VERWORPEN

**Alternatief 1: Direct XML manipulation (lxml)**
- ❌ Te low-level, error-prone
- ❌ Geen abstractie over OOXML complexiteit
- ✅ python-docx biedt betere API

**Alternatief 2: Paragraph-level processing**
- ❌ Verliest intra-paragraph formatting variaties
- ❌ Kan mixed-style tekst niet correct hanteren
- ✅ Run-level is granulairder en accurater

**Alternatief 3: Google Translate API**
- ❌ Lagere kwaliteit voor NL→XX
- ❌ Dubbele prijs

**Alternatief 4: Native PDF editing (PyMuPDF)**
- ❌ Technisch zeer complex
- ❌ Text expansion breekt layout
- ❌ Geen semantische structuur
- ✅ PDF→DOCX conversie pragmatischer

**Alternatief 5: LibreOffice UNO API**
- ❌ Vereist LibreOffice installatie
- ❌ Overhead en dependencies
- ❌ Platform compatibility issues
- ✅ python-docx is puur Python, portable

## 9. TECHNISCHE RISICO'S & MITIGATIES

| Risico | Impact | Mitigatie |
|--------|--------|-----------|
| Text expansion breekt table layout | Gemiddeld | Pre-flight check + waarschuwing gebruiker |
| Formatting properties niet volledig | Gemiddeld | Exhaustive property list + testing |
| PDF→DOCX conversie verliest data | Hoog | Quality validation + user preview |
| API rate limiting | Gemiddeld | Exponential backoff + batch processing |
| Unsupported DOCX features | Laag | Detectie + warning + skip |

## 10. DELIVERABLES

**Minimaal (MVP):**
- CLI tool: `transit translate document.docx --target EN-US`
- DOCX paragraph + run level translation
- Basic formatting preservation

**Uitgebreid:**
- GUI (tkinter of Qt)
- Batch processing (folder van documenten)
- PDF support via conversie
- Progress tracking
- Translation memory (cache voor repeated phrases)
- Custom glossaries

**Professioneel:**
- Web API (FastAPI)
- Cloud deployment
- Multi-user support
- Translation review interface
- Quality metrics & reporting
