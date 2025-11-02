#!/usr/bin/env python3
"""
VRA Mathematical Deep Search
Searches for the MATHEMATICAL CORE of VRA, not implementation details.
Based on actual paper equations and theoretical framework.

Usage:
  python3 vra_math_deep_search.py --out /home/admin/dev/VRA/Novelty/math_search
"""
import argparse
import os
import json
import csv
import time
import re
import pathlib
from datetime import datetime
import requests

# Mathematical queries extracted from VRA paper equations
MATH_CORE_QUERIES = [
    # Phase embedding (Equation 3): u_i = exp(2πj·x_i/N)
    "complex phase embedding modular arithmetic sequences",
    "unit circle representation modular exponentiation",
    "exponential map finite group elements cyclic",

    # Coherent averaging (Equations 6-7): S[f] = (1/M)ΣU_i[f], Power = |S[f]|²
    "coherent averaging complex spectra before magnitude",
    "phase-aligned spectral averaging Fourier transform",
    "amplitude averaging versus power averaging FFT",

    # Multiplicative order + harmonics (Equation 8): B_k = ⌊k·N_zp/r⌋
    "multiplicative order spectral peaks harmonic structure",
    "spectral method order finding cyclic group",
    "harmonic bin spacing subgroup order",

    # Phase coherence across bases
    "phase alignment multiple bases same order modular",
    "coherence multiple sequences cyclic group",
    "constructive interference same subgroup order",

    # √M scaling (Equation 13): C(M) ∝ √M
    "square root M coherent averaging SNR scaling",
    "coherent versus incoherent averaging signal processing",
    "constructive interference scaling law phase randomness",

    # Regime mapping: ρ = r/N
    "order-to-modulus ratio spectral properties",
    "period length modulus ratio detection performance",

    # Quantum correspondence (conceptual, not computational)
    "classical Fourier quantum Fourier correspondence",
    "classical analogue quantum interference pattern",
    "classical period finding spectral method",

    # Group character theory
    "character embedding finite abelian group spectral",
    "group characters Fourier analysis cyclic",
    "harmonic analysis finite group character sums",

    # Spectral-order correspondence
    "Fourier spectrum group structure correspondence",
    "periodicity detection finite group spectral analysis",
    "spectral peaks subgroup order relationship",

    # Ramanujan comparison (known prior art)
    "Ramanujan sums multiplicative order detection",
    "Ramanujan periodicity transform spectral analysis",
    "number-theoretic transform period detection",

    # Phase coherence metrics (R̄ = 0.137)
    "resultant length circular statistics phase",
    "phase locking value mean resultant vector",
    "coherence coefficient complex sequences",

    # Spectral concentration
    "spectral energy concentration ratio top peaks",
    "spectral entropy periodic signals",
    "energy localization frequency domain harmonics",

    # Validated radius (Equation 9): R = ⌊0.5·log₂(N_zp)⌋
    "harmonic bin width window main lobe",
    "frequency resolution zero-padding FFT",
    "spectral peak tolerance window function",

    # Statistical comparison methodology
    "bootstrap confidence intervals spectral method comparison",
    "permutation test signal processing algorithm",

    # Additive vs multiplicative structure
    "additive periodicity versus multiplicative order spectral",
    "integer period multiplicative group period Fourier",
]

HEADERS = {"User-Agent": "VRA-Math-Deep-Search/2.0 (Research; +mailto:research@example.com)"}

def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[^\w\-.]+', '_', name)
    return name[:180]

def arxiv_search(q, max_results=50):
    """Search arXiv with category filters for math/CS theory"""
    base = "https://export.arxiv.org/api/query"

    # Search in relevant categories
    categories = ["math.NT", "math.GR", "cs.IT", "cs.DS", "math.SP", "quant-ph"]
    category_str = " OR ".join([f"cat:{c}" for c in categories])

    params = {
        "search_query": f"all:{q} AND ({category_str})",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance"
    }

    try:
        r = requests.get(base, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()

        entries = []
        for entry in r.text.split("<entry>")[1:]:
            title = re.search(r"<title>(.*?)</title>", entry, re.S)
            title = title.group(1).strip() if title else ""

            link = re.search(r'<link href="(.*?)"', entry)
            link = link.group(1) if link else ""

            pdf = re.search(r'<link title="pdf" href="(.*?)"', entry)
            pdf = pdf.group(1) if pdf else ""

            summary = re.search(r"<summary>(.*?)</summary>", entry, re.S)
            summary = summary.group(1).strip() if summary else ""

            doi = re.search(r"<arxiv:doi>(.*?)</arxiv:doi>", entry)
            doi = doi.group(1).strip() if doi else ""

            primary_cat = re.search(r'<arxiv:primary_category[^>]*term="(.*?)"', entry)
            primary_cat = primary_cat.group(1) if primary_cat else ""

            entries.append({
                "source": "arxiv",
                "title": title,
                "url": link,
                "pdf_url": pdf,
                "abstract": summary,
                "doi": doi,
                "primary_category": primary_cat
            })
        return entries
    except Exception as e:
        print(f"    arXiv error: {e}")
        return []

def crossref_search(q, rows=50):
    """Search Crossref with subject filter"""
    url = "https://api.crossref.org/works"
    params = {
        "query": q,
        "rows": rows,
        "select": "DOI,title,URL,author,container-title,issued,type,link,abstract"
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json().get("message", {}).get("items", [])
    except Exception as e:
        print(f"    Crossref error: {e}")
        return []

def google_scholar_search(q, num_results=20):
    """
    Placeholder for Google Scholar search
    Note: Google Scholar doesn't have official API, would need:
    - serpapi.com (paid)
    - scholarly Python library (unofficial)
    - Manual search
    """
    print(f"    Note: Google Scholar search would require paid API or manual review")
    print(f"    Suggested manual search: https://scholar.google.com/scholar?q={requests.utils.quote(q)}")
    return []

def mathscinet_search_suggestion(q):
    """Suggest MathSciNet search (requires subscription)"""
    print(f"    MathSciNet search suggested: https://mathscinet.ams.org/mathscinet/search/publications.html?query={requests.utils.quote(q)}")
    return []

def collect_one_query(q, years, out_rows, seen):
    """Collect results from arXiv and Crossref for one query"""
    print(f"  Searching: {q[:80]}...")

    # arXiv (with category filters)
    count_before = len(out_rows)
    for a in arxiv_search(q):
        key = (a.get("doi", "") or a.get("url", "")).lower()
        if key in seen:
            continue
        seen.add(key)
        out_rows.append({**a, "year": "", "venue": "", "query": q})
    print(f"    arXiv: +{len(out_rows) - count_before} papers")

    # Crossref
    count_before = len(out_rows)
    for c in crossref_search(q):
        doi = (c.get("DOI", "") or "").lower()
        url = c.get("URL", "")
        key = doi or url
        if key in seen:
            continue
        seen.add(key)

        link_pdf = ""
        for lnk in c.get("link", []) or []:
            if lnk.get("content-type", "").lower() == "application/pdf":
                link_pdf = lnk.get("URL", "")
                break

        title = " ".join(c.get("title") or [])
        issued = c.get("issued", {}).get("date-parts", [[None]])[0][0]
        venue = " ".join(c.get("container-title") or [])
        abstract = c.get("abstract", "")

        out_rows.append({
            "source": "crossref",
            "title": title,
            "doi": doi,
            "url": url,
            "pdf_url": link_pdf,
            "abstract": abstract,
            "year": issued,
            "venue": venue,
            "query": q
        })
    print(f"    Crossref: +{len(out_rows) - count_before} papers")

    time.sleep(1.0)  # Be polite to APIs

def try_download_pdf(pdf_url, dest_path):
    """Attempt to download PDF"""
    if not pdf_url:
        return False
    try:
        with requests.get(pdf_url, headers=HEADERS, timeout=60, stream=True) as r:
            if r.status_code != 200:
                return False
            size = 0
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        size += len(chunk)
        return dest_path.exists() and dest_path.stat().st_size > 1024
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser(description="VRA Mathematical Deep Search")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--query", action="append", default=[], help="Add custom query")
    ap.add_argument("--years", default="1990-2026", help="Year range")
    ap.add_argument("--max", type=int, default=400, help="Max total records")
    args = ap.parse_args()

    outdir = pathlib.Path(args.out)
    papers_dir = outdir / "papers"
    ensure_dir(outdir)
    ensure_dir(papers_dir)

    queries = args.query or MATH_CORE_QUERIES

    print(f"\n{'='*80}")
    print(f"VRA MATHEMATICAL DEEP SEARCH")
    print(f"{'='*80}")
    print(f"Output directory: {outdir}")
    print(f"Number of queries: {len(queries)}")
    print(f"Focus: MATHEMATICAL CORE, not implementation")
    print(f"{'='*80}\n")

    rows, seen = [], set()

    for i, q in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Query: {q}")
        collect_one_query(q, args.years, rows, seen)
        print(f"  Total collected: {len(rows)}")

    # Trim to max
    rows = rows[:args.max]
    ts = datetime.utcnow().isoformat() + "Z"

    print(f"\n{'='*80}")
    print(f"DOWNLOADING PDFs")
    print(f"{'='*80}\n")

    download_success = 0
    for i, r in enumerate(rows, 1):
        pdf = r.get("pdf_url", "")
        if not pdf:
            continue

        safe = sanitize_filename((r.get("title") or r.get("doi") or f"paper_{i}") + ".pdf")
        dest = papers_dir / safe

        if dest.exists():
            r["local_pdf"] = str(dest)
            download_success += 1
            continue

        if i % 20 == 0:
            print(f"  [{i}/{len(rows)}] Downloading...")

        ok = try_download_pdf(pdf, dest)
        if ok:
            r["local_pdf"] = str(dest)
            download_success += 1

    # Write results
    print(f"\n{'='*80}")
    print(f"SAVING RESULTS")
    print(f"{'='*80}\n")

    (outdir / "index.json").write_text(
        json.dumps({"generated_at": ts, "count": len(rows), "focus": "mathematical_core", "items": rows}, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ Saved index.json")

    with open(outdir / "index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "title", "doi", "url", "pdf_url", "local_pdf", "year", "venue", "query", "abstract"])
        for r in rows:
            w.writerow([r.get(k, "") for k in ["source", "title", "doi", "url", "pdf_url", "local_pdf", "year", "venue", "query", "abstract"]])
    print(f"  ✓ Saved index.csv")

    readme = f"""# VRA Mathematical Core - Deep Search Results

Generated: {ts}
Total Records: {len(rows)}
PDFs Downloaded: {download_success}
Focus: **Mathematical foundations**, not implementation

## Search Strategy

This search focused on VRA's **mathematical core**:

1. **Phase Embedding** (Eq. 3): u_i = exp(2πj·x_i/N) where x_i = a^k mod N
2. **Coherent Averaging** (Eq. 6-7): S[f] = (1/M)ΣU_i[f], Power = |S[f]|²
3. **Harmonic Structure** (Eq. 8): B_k = ⌊k·N_zp/r⌋
4. **√M Scaling Law** (Eq. 13): C(M) ∝ √M under phase alignment
5. **Regime Mapping**: ρ = r/N with validated boundaries
6. **Phase Coherence**: R̄ = 0.137 limitation
7. **Group Character Embeddings**: Extension to ECC
8. **Classical-Quantum Correspondence**: Pattern similarity (not computational equivalence)

## Key Mathematical Features to Check

For each paper, verify if it contains:

- [ ] **Phase embedding of modular sequences** u = exp(2πi·(a^k mod N)/N)
- [ ] **Coherent averaging before power**: |Σ FFT_i / M|² not Σ|FFT_i|²/M
- [ ] **Multiplicative order detection** via spectral harmonic peaks
- [ ] **Harmonic bins at k·L/r** where r is multiplicative order
- [ ] **√M scaling from phase coherence** (not just standard averaging)
- [ ] **Regime boundaries** ρ = r/N with HIGH/TRANSITION/LOW SNR
- [ ] **Phase coherence limitation** preventing M² scaling
- [ ] **Statistical validation** against spectral baseline (RPT)

## Queries Used

{chr(10).join(f"{i}. {q}" for i, q in enumerate(queries, 1))}

## Files

- **index.json** — Full metadata with abstracts
- **index.csv** — Spreadsheet view
- **papers/** — Downloaded PDFs ({download_success} files)

## Next Steps

1. **Review abstracts** in index.csv for mathematical overlap
2. **Read PDFs** for papers with potential mathematical similarity
3. **Compare equations** against VRA's core equations (listed above)
4. **Manual searches** (APIs limited):
   - MathSciNet: https://mathscinet.ams.org/
   - Google Scholar: https://scholar.google.com/
   - zbMATH: https://zbmath.org/

## VRA's Unique Mathematical Combination

Even if individual components exist in literature:
- Phase embedding (standard Fourier)
- Coherent averaging (standard signal processing)
- Group characters (standard algebra)

**VRA's novelty is the COMBINATION**:
1. Phase embedding of **modular exponentiation** (not generic sequences)
2. Coherent averaging across **same-order bases** (not random signals)
3. Detection at **harmonic bins k·L/r** (order-aware, not blind scanning)
4. **Regime mapping** via ρ = r/N (empirically validated)
5. **Statistical proof** of superiority over RPT (3.3× precision, p < 10⁻⁴)
"""

    (outdir / "README.md").write_text(readme, encoding="utf-8")
    print(f"  ✓ Saved README.md")

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Papers collected: {len(rows)}")
    print(f"PDFs downloaded: {download_success}")
    print(f"Output: {outdir}")
    print(f"\nFocus: Mathematical core (equations, not code)")
    print(f"{'='*80}\n")

    # Print manual search suggestions
    print(f"\n{'='*80}")
    print(f"MANUAL SEARCH SUGGESTIONS")
    print(f"{'='*80}")
    print(f"\nFor comprehensive coverage, also search manually:")
    print(f"1. Google Scholar: https://scholar.google.com/")
    print(f"   - Try: 'phase embedding modular exponentiation spectral'")
    print(f"   - Try: 'coherent averaging multiplicative order FFT'")
    print(f"2. MathSciNet (requires subscription):")
    print(f"   - https://mathscinet.ams.org/")
    print(f"3. zbMATH:")
    print(f"   - https://zbmath.org/")
    print(f"4. IEEE Xplore:")
    print(f"   - https://ieeexplore.ieee.org/")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
