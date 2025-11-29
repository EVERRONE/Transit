# TransIt Gebruikershandleiding

## Quick Start

```bash
transit translate document.docx --target EN-US
```

**Nieuw in v0.2:** TransIt gebruikt nu standaard **OpenAI GPT-4o** voor intelligente, context-aware vertalingen die afkortingen, idiomen en technische termen perfect vertalen!

## Command Syntax

```bash
transit translate INPUT_FILE --target LANGUAGE [OPTIONS]
```

### Argumenten

- `INPUT_FILE`: Pad naar DOCX bestand (verplicht)
- `--target, -t`: Doeltaal code (verplicht)

### Opties

- `--output, -o PATH`: Output bestand (default: `<input>_translated.docx`)
- `--openai-key KEY`: OpenAI API key (of gebruik OPENAI_API_KEY env var)
- `--model MODEL`: OpenAI model (default: `gpt-4o`, of kies `gpt-4o-mini` voor snelheid)
- `--verbose, -v`: Toon progress bar
- `--max-concurrent N`: Stel max gelijktijdige async-requests in (default: 10)
- `--sync-mode`: Gebruik synchrone verwerking (default: async)
- `--help`: Toon help

## Ondersteunde Talen

OpenAI GPT-4o ondersteunt o.a. de volgende taalcodes:


| Taal | Code | Taal | Code |
|------|------|------|------|
| Engels (US) | EN-US | Duits | DE |
| Engels (UK) | EN-GB | Frans | FR |
| Spaans | ES | Italiaans | IT |
| Portugees | PT | Pools | PL |
| Russisch | RU | Japans | JA |
| Chinees | ZH | Koreaans | KO |


## Voorbeelden

### Basis vertaling (met OpenAI GPT-4o)

```bash
transit translate rapport.docx --target EN-US
```

Output: `rapport_translated.docx` - Afkortingen zoals "m.b.t." worden intelligent vertaald!

### Custom output pad

```bash
transit translate rapport.docx --target FR --output french_report.docx
```

### Met sneller model (GPT-4o-mini)

```bash
transit translate groot_document.docx --target DE --model gpt-4o-mini --verbose
```



### Async instellingen

```bash
# Stel max gelijktijdige requests in (async is standaard)
transit translate document.docx --target EN-US --max-concurrent 20

# Schakel over naar synchron processing (debug/doel)
transit translate document.docx --target EN-US --sync-mode
```

### Meerdere documenten

```bash
for file in *.docx; do
    transit translate "$file" --target EN-US
done
```

## Waarom OpenAI GPT-4o?

TransIt gebruikt standaard OpenAI GPT-4o voor **intelligente, context-aware vertalingen**:

### ✅ Voordelen OpenAI
- **Afkortingen**: "m.b.t." → "regarding", "b.v." → "for example" (niet letterlijk!)
- **Idiomen**: Vertaalt naar equivalente uitdrukking in doeltaal
- **Technische termen**: Begrijpt context en kiest juiste vertaling
- **Ambiguïteit**: Gebruikt document context voor disambiguatie
- **Consistentie**: Onthoudt eerder gebruikte termen in document
- **Formeel/informeel**: Matcht tone van origineel


| Afkortingen | ✅ Excellent | ⚠️ Letterlijk |
| Context begrip | ✅ Document-level | ❌ Sentence-level |
| Idiomen | ✅ Equivalent | ⚠️ Letterlijk |
| Technische termen | ✅ Smart | ✅ Good |
| Kosten (10 pagina's) | $0.09 | €0.03 |
| Snelheid | ~30 sec | ~15 sec |


## Wat wordt vertaald?

TransIt vertaalt:
- ✅ Alle paragrafen in document body
- ✅ Tabellen (cel-voor-cel)
- ✅ Headers en footers
- ✅ Multiple sections (different first page, even/odd pages)

TransIt preserveert:
- ✅ Bold, italic, underline, strikethrough
- ✅ Font type, size, color
- ✅ Paragraph alignment, spacing, indentation
- ✅ Table borders, cell shading, merged cells
- ✅ List numbering and bullets
- ✅ Hyperlinks
- ✅ Exact whitespace (spaties, tabs, line breaks)

**Niet ondersteund (nog):**
- ❌ Text boxes
- ❌ SmartArt / grafieken
- ❌ Embedded objects
- ❌ Voetnoten/eindnoten (Phase 3)

## Output Formaat

Elk origineel element blijft behouden, met vertaling direct eronder:

**Origineel:**
```
Dit is vet en dit is normaal.
```

**Output:**
```
Dit is vet en dit is normaal.
This is bold and this is normal.  [italic, als visuele marker]
```

## Performance

Verwachte processing tijd:

| Document grootte | Tijd |
| 5 pagina's | ~15 sec |
| 20 pagina's | ~1 min |
| 50 pagina's | ~3 min |
| 100 pagina's | ~6 min |

Factoren die snelheid beïnvloeden:
- Aantal tabellen (cel-voor-cel processing)
- Complexe formatting (veel runs per paragraph)
- API rate limiting (50 req/sec gratis tier)

## API Kosten

### OpenAI Pricing (GPT-4o - default)
- **Input**: $2.50 per 1M tokens
- **Output**: $10.00 per 1M tokens

Voorbeeld (10 pagina's ≈ 5,000 woorden ≈ 7,500 tokens):
- Input: 7,500 tokens × $2.50/1M = **$0.019**
- Output: 7,500 tokens × $10/1M = **$0.075**
- **Totaal**: ~$0.09 per 10 pagina's

### GPT-4o-mini (goedkoper alternatief)
- **Input**: $0.15 per 1M tokens
- **Output**: $0.60 per 1M tokens
- **Totaal**: ~$0.006 per 10 pagina's (15x goedkoper!)

Check usage:
- OpenAI: https://platform.openai.com/usage

## Troubleshooting

### Vertaling stopt halverwege

**Oorzaak**: API rate limiting

**Oplossing**: Wacht 1 minuut en probeer opnieuw. TransIt heeft automatisch retry logic.

### Output formatting niet perfect

**Check**:
1. Open output in Microsoft Word (niet LibreOffice)
2. Vergelijk origineel run-voor-run
3. Check console output voor warnings

**Report**: Als formatting echt fout is, maak issue aan met:
- Input document (of vergelijkbaar voorbeeld)
- Screenshot van origineel vs output
- Console output met `--verbose`

### "Expected Dutch, detected XX"

**Oorzaak**: Document bevat niet-Nederlandse tekst

**Oplossingen**:
1. Accepteer warning, TransIt probeert toch te vertalen
2. Verwijder niet-NL tekst voor vertaling
3. Gebruik andere tool voor multi-language documenten

### Table layout verstoord

**Oorzaak**: Text expansion (NL→DE +35%) in vaste-breedte kolommen

**Oplossing**:
1. Check origineel tabel - zijn kolommen te smal?
2. Verbreed kolommen in origineel
3. Of accepteer dat vertaling overflow heeft

## Tips & Tricks

### Grote documenten

Voor documenten >100 pagina's:
1. Split in kleinere files
2. Vertaal apart
3. Merge in Word

### Batch processing

```bash
# Vertaal alle DOCX in folder
for file in *.docx; do
    echo "Processing $file..."
    transit translate "$file" --target EN-US
done
```

### Quality check

1. Open origineel en translated naast elkaar
2. Scroll synchroon
3. Spot-check 10 random zinnen
4. Check tabellen visueel
5. Check headers/footers

### Formatting issues

Als italic marker voor vertaling storend is:
1. Open output in Word
2. Find & Replace: Italic → Remove italic
3. Let op: ook originele italic verdwijnt

## Support

- Documentatie: `Visie.md`
- Issues: GitHub repository
- Email: [your-email]
