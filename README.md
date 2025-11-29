# TransIt

**Ultra-precise document translation with AI-powered context awareness**

TransIt vertaalt DOCX en PDF documenten van Nederlands naar elke doeltaal met **intelligente context-aware vertaling via OpenAI GPT-4o**. Elk origineel element blijft behouden met de vertaling er direct onder. Afkortingen, idiomen en technische termen worden perfect vertaald dankzij document-level context begrip.

## ✨ Features

### Core Translation

- **🤖 AI-Powered**: OpenAI GPT-4o voor context-aware vertalingen (afkortingen, idiomen, technische termen)
- **Run-level vertaling**: Elke paragraaf wordt intelligent vertaald met behoud van context
- **Complete formatting preservation**: 20+ run properties, paragraph formatting, table structures

### Advanced Features
- **📄 PDF Support**: Automatische conversie van PDF naar DOCX met quality validation
- **🔗 Hyperlink preservation**: Links blijven behouden tijdens vertaling
- **📋 List formatting**: Genummerde en bullet lists met correcte formatting
- **🔤 Special characters**: Tabs, non-breaking spaces, protected characters
- **📊 Nested tables**: Volledige ondersteuning voor complexe tabel structuren

### Performance Optimization
- **⚡ Async processing**: Tot 10x sneller voor grote documenten
- **🎯 Smart batching**: Intelligente batch optimalisatie voor API calls
- **💾 Translation caching**: Vermijd dubbele vertalingen met persistent cache
- **📈 Memory optimization**: Efficiënte verwerking van grote documenten

### User Interface
- **🖥️ GUI Application**: Moderne Tkinter interface met drag-and-drop
- **📋 Preview panel**: Bekijk document inhoud voor en na vertaling
- **⚙️ Settings panel**: Visuele configuratie van alle opties
- **📊 Progress tracking**: Real-time voortgang en logging

### Structure & Quality
- **Structure integrity**: Document volgorde via `iter_inner_content()`, XML-level insertion
- **Robust**: Comprehensive error handling, validation, edge case support
- **Quality validation**: Automatische validatie van conversie en vertaling kwaliteit

## Installation

```bash
# Clone repository
git clone <repo-url>
cd TransIt

# Install dependencies
pip install -r requirements.txt


# Install package
pip install -e .
```

## Configuration

Create `.env` file:

```
OPENAI_API_KEY=your_openai_api_key_here

```

Get your OpenAI API key: https://platform.openai.com/api-keys

## Usage

### GUI Mode (Recommended)

```bash
# Launch graphical interface
transit gui
```

The GUI provides:
- Drag-and-drop file upload
- Visual settings configuration
- Real-time progress tracking
- Document preview
- Easy API key management

### Command Line Mode

#### Basic Translation

```bash
# Translate DOCX (uses OpenAI GPT-4o by default)
transit translate document.docx --target EN-US

# Translate PDF (auto-converts to DOCX)
transit translate document.pdf --target EN-US

# With output path
transit translate document.docx --target EN-US --output translated.docx

# Use faster/cheaper model
transit translate document.docx --target EN-US --model gpt-4o-mini


# Show progress
transit translate document.docx --target EN-US --verbose
```

#### Performance Options

```bash
# Tune async concurrency (async is default)
transit translate document.docx --target EN-US --max-concurrent 20

# Disable caching (if needed)
transit translate document.docx --target EN-US --no-enable-cache
```

#### PDF Conversion

```bash
# Convert PDF to DOCX with quality validation
transit convert-pdf document.pdf

# Show detailed quality report
transit convert-pdf document.pdf --show-report

# Custom output path
transit convert-pdf document.pdf --output converted.docx
```

### Supported Languages

- **EN-US** / **EN-GB**: English (US/UK)
- **FR**: French
- **DE**: German
- **ES**: Spanish
- **IT**: Italian
- **NL**: Dutch
- **PT** / **PT-BR**: Portuguese (Portugal/Brazil)
- **RU**: Russian
- **JA**: Japanese
- **ZH**: Chinese
- **KO**: Korean


### Waarom OpenAI?

- ✅ **Afkortingen**: "m.b.t." → "regarding" (niet "m.b.t.")
- ✅ **Idiomen**: Vertaalt naar equivalent in doeltaal
- ✅ **Context**: Begrijpt document als geheel
- ✅ **Technische termen**: Intelligente keuzes o.b.v. domein

Zie `USAGE.md` voor volledige handleiding en voorbeelden.

## Architecture

```
Document → Paragraph → Run (OPERATIONEEL NIVEAU) → Sentence
```

Zie `Visie.md` voor volledige technische documentatie.

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=transit

# Type checking
mypy src/
```

## Project Status

### Completed ✅

- **Option A: Testing & QA**
  - ✅ Unit tests voor edge cases
  - ✅ Integration tests voor complexe documenten
  - ✅ Test fixtures (tabellen, headers, merged cells)
  - ✅ Performance benchmarks

- **Option B: Advanced Features**
  - ✅ List formatting preservation
  - ✅ Hyperlink preservation tijdens vertaling
  - ✅ Special character handling (tabs, non-breaking spaces)
  - ✅ Nested table support

- **Option C: Performance Optimization**
  - ✅ Async translation voor grote documenten
  - ✅ Smart batch processing optimalisatie
  - ✅ Memory optimization voor grote documenten
  - ✅ Translation caching met persistent storage

- **Option D: PDF Support**
  - ✅ pdf2docx integration
  - ✅ Conversion quality validation
  - ✅ User preview workflow

- **Option E: GUI**
  - ✅ Tkinter interface met modern design
  - ✅ Drag-drop upload functionaliteit
  - ✅ Live preview van documenten
  - ✅ Settings panel voor configuratie

### Architecture

```
TransIt/
├── src/transit/
│   ├── core/              # Core translation logic
│   ├── parsers/           # Document parsing (sync + async)
?"   ?"o?"?"? translators/       # OpenAI translator
│   ├── converters/        # PDF to DOCX conversion
│   ├── utils/             # Caching, batching, memory optimization
│   ├── gui/               # Tkinter GUI application
│   └── cli.py             # Command-line interface
├── tests/                 # Comprehensive test suite
└── docs/                  # Documentation
```

## License

MIT
