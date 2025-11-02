# Novelty Analysis Scripts

This folder contains reusable analysis scripts for VRA novelty verification.

## Scripts

### `analyze_pdfs.py`
**Main PDF analysis script** - Analyzes all downloaded PDFs for VRA mathematical concepts.

**Usage:**
```bash
python3 analyze_pdfs.py
```

**Output:**
- `../pdf_analysis_data.json` - Raw analysis data
- `../PDF_GRAPH_ANALYSIS_REPORT.md` - Comprehensive report

**What it does:**
- Extracts text from all PDFs in `../papers/` and `../math_search/papers/`
- Scores each paper for 8 VRA mathematical concepts
- Identifies papers with VRA's critical combination
- Generates detailed novelty report

---

### `vra_prior_art_harvest.py`
**General literature search script** - Downloads papers from arXiv, Crossref, OpenAlex.

**Usage:**
```bash
python3 vra_prior_art_harvest.py
```

**Output:**
- Downloads PDFs to `../papers/`
- Creates `../index.json` and `../index.csv` with metadata

**Searches:**
- 25 general queries across spectral analysis, coherent averaging, etc.
- ~300 papers downloaded

---

### `vra_math_deep_search.py`
**Mathematical literature search** - Focuses on VRA's mathematical core.

**Usage:**
```bash
python3 vra_math_deep_search.py
```

**Output:**
- Downloads PDFs to `../math_search/papers/`
- Creates search metadata

**Searches:**
- 42 equation-based queries
- Targets multiplicative order, phase embedding, coherent averaging
- ~250 papers downloaded

---

## Notes

- All scripts require `pdftotext` (from poppler-utils) installed
- See `../requirements.txt` for Python dependencies
- Scripts are idempotent - safe to run multiple times
