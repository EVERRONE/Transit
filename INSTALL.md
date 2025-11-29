# Installatie Instructies

## Vereisten

- Python 3.10 of hoger
- pip (Python package manager)
- OpenAI API key voor intelligente context-aware vertalingen  
  Verkrijg op: https://platform.openai.com/api-keys

## Stap 1: Clone repository

```bash
cd "C:\Users\Emilien.VEROLIFT\Documents\1_eigen projecten"
cd TransIt
```

## Stap 2: Virtuele omgeving (aanbevolen)

```bash
# Maak virtuele omgeving
python -m venv venv

# Activeer (Windows)
venv\Scripts\activate

# Activeer (Linux/Mac)
source venv/bin/activate
```

## Stap 3: Installeer dependencies

```bash
pip install -r requirements.txt
```

## Stap 4: Installeer TransIt

```bash
pip install -e .
```

De `-e` flag installeert in "editable" mode, handig voor development.

## Stap 5: Configureer API key

Maak `.env` bestand aan:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Voeg je OpenAI API key toe:

```bash
OPENAI_API_KEY=jouw_openai_api_key_hier
```

## Verificatie

Controleer de installatie:

```bash
transit --version
```

Output: `transit, version 0.1.0`

## Test met voorbeeld document

```bash
# Maak test document
python -c "from docx import Document; d = Document(); d.add_paragraph('Dit is een test.'); d.save('test.docx')"

# Vertaal
transit translate test.docx --target EN-US --verbose
```

De vertaling verschijnt in `test_translated.docx`:

```
Dit is een test.
This is a test.
```

## Troubleshooting

### Error: "OpenAI API authentication failed"

- Controleer of `.env` bestaat
- Controleer of `OPENAI_API_KEY` juist is ingevuld (geen spaties)
- Verifieer de sleutel op https://platform.openai.com/api-keys
- Controleer of je account voldoende credits heeft

### Error: "Cannot load document"

- Controleer of het bestand een geldig DOCX-bestand is
- Converteer oude `.doc` bestanden naar `.docx`
- Open het document in Word en kies **Save As** ��' `.docx`

## Development Setup

Voor development met tests:

```bash
# Installeer dev dependencies
pip install pytest pytest-cov mypy black

# Run tests
pytest

# Run met coverage
pytest --cov=transit

# Code formatting
black src/ tests/

# Type checking
mypy src/
```
