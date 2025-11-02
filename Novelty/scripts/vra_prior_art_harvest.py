#!/usr/bin/env python3
"""
VRA Prior-Art Harvester
Searches OpenAlex, arXiv, Crossref, and optionally Semantic Scholar for
terms related to VRA's niche, saves metadata and PDFs for review.

Usage:
  python3 vra_prior_art_harvest.py --out /home/admin/dev/VRA/Novelty
  python3 vra_prior_art_harvest.py --out /home/admin/dev/VRA/Novelty --query "custom query" --years 2000-2026
"""
import argparse
import os
import json
import csv
import time
import re
import pathlib
import urllib.parse
from datetime import datetime
import requests

# VRA-specific queries targeting potential overlaps
VRA_QUERIES = [
    # Core VRA concepts
    "multiplicative order detection spectrum modular exponentiation",
    "spectral analysis multiplicative group finite field",
    "phase coherent averaging FFT detection",
    "modular arithmetic frequency domain analysis",

    # Ramanujan-related (known prior art for comparison)
    "Ramanujan Periodicity Transform signal processing",
    "Ramanujan sums spectral decomposition",
    "Ramanujan filter bank periodicity detection",

    # Phase coherence and averaging
    "coherent averaging SNR improvement signal processing",
    "phase alignment spectral detection",
    "resultant length phase coherence circular statistics",

    # Order finding and detection
    "order finding classical algorithm modular arithmetic",
    "period detection finite group spectral method",
    "multiplicative order modulo composite number",

    # Structured resonance and related frameworks
    "structured resonance coherence field detection",
    "phase coherence optical decoding emission",
    "resonance analysis harmonic detection",

    # Group theory and spectral methods
    "cyclic group character Fourier transform",
    "group character embedding spectral analysis",
    "finite group harmonic analysis",

    # Signal processing + number theory
    "CFAR detection periodic signals",
    "spectral peak detection harmonic structure",
    "discrete Fourier transform modular sequences",

    # Quantum-classical connections
    "quantum period finding classical approximation",
    "Shor algorithm classical variant",
    "quantum phase estimation classical simulation",
]

HEADERS = {"User-Agent": "VRA-Prior-Art-Harvester/1.0 (Research; +mailto:research@example.com)"}

def ensure_dir(p: pathlib.Path):
    """Create directory if it doesn't exist"""
    p.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name: str) -> str:
    """Convert string to safe filename"""
    name = re.sub(r'[^\w\-.]+', '_', name)
    return name[:180]

def get_semantic_scholar_key():
    """Get Semantic Scholar API key from environment"""
    return os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

def openalex_search(q, years=None, per_page=50, max_pages=3):
    """Search OpenAlex API for scholarly works"""
    url = "https://api.openalex.org/works"
    params = {
        "search": q,
        "per_page": per_page,
        "sort": "relevance_score:desc"
    }
    if years and "-" in years:
        start, end = years.split("-")
        params["from_publication_date"] = f"{start}-01-01"
        params["to_publication_date"] = f"{end}-12-31"

    out = []
    cursor = "*"
    for _ in range(max_pages):
        params["cursor"] = cursor
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            out.extend(data.get("results", []))
            cursor = data.get("meta", {}).get("next_cursor")
            if not cursor:
                break
        except Exception as e:
            print(f"OpenAlex error: {e}")
            break
    return out

def arxiv_search(q, max_results=50):
    """Search arXiv export API"""
    base = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{q}",
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
        print(f"arXiv error: {e}")
        return []

def crossref_search(q, rows=50):
    """Search Crossref API"""
    url = "https://api.crossref.org/works"
    params = {
        "query": q,
        "rows": rows,
        "select": "DOI,title,URL,author,container-title,issued,type,link"
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json().get("message", {}).get("items", [])
    except Exception as e:
        print(f"Crossref error: {e}")
        return []

def s2_search(q, limit=30):
    """Search Semantic Scholar (optional, requires API key)"""
    key = get_semantic_scholar_key()
    if not key:
        return []

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": q,
        "limit": limit,
        "fields": "title,abstract,year,venue,url,openAccessPdf,externalIds,authors"
    }

    try:
        r = requests.get(url, params=params, headers={"x-api-key": key, **HEADERS}, timeout=30)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        print(f"Semantic Scholar error: {e}")
        return []

def best_pdf_from_openalex(item):
    """Extract best PDF URL from OpenAlex result"""
    oa = item.get("open_access")
    if oa and oa.get("is_oa"):
        loc = oa.get("oa_url") or ""
        if loc.endswith(".pdf"):
            return loc

    host = item.get("primary_location") or {}
    if host.get("pdf_url"):
        return host["pdf_url"]
    return ""

def collect_one_query(q, years, out_rows, seen):
    """Collect results from all sources for one query"""
    print(f"  Searching: {q}")

    # OpenAlex
    for w in openalex_search(q, years=years):
        doi = (w.get("doi") or "").lower()
        url = w.get("id") or ""
        key = doi or url
        if key in seen:
            continue
        seen.add(key)

        abstract_text = ""
        inv_idx = w.get("abstract_inverted_index")
        if inv_idx:
            # Reconstruct abstract from inverted index
            words = []
            for word, positions in inv_idx.items():
                for pos in positions:
                    words.append((pos, word))
            words.sort()
            abstract_text = " ".join(word for _, word in words)

        out_rows.append({
            "source": "openalex",
            "title": w.get("title", ""),
            "doi": doi,
            "url": url,
            "pdf_url": best_pdf_from_openalex(w),
            "abstract": abstract_text,
            "year": w.get("publication_year"),
            "venue": (w.get("host_venue") or {}).get("display_name", ""),
            "query": q
        })

    # arXiv
    for a in arxiv_search(q):
        key = (a.get("doi", "") or a.get("url", "")).lower()
        if key in seen:
            continue
        seen.add(key)
        out_rows.append({
            **a,
            "year": "",
            "venue": "",
            "query": q
        })

    # Crossref
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

        out_rows.append({
            "source": "crossref",
            "title": title,
            "doi": doi,
            "url": url,
            "pdf_url": link_pdf,
            "abstract": "",
            "year": issued,
            "venue": venue,
            "query": q
        })

    # Semantic Scholar (optional)
    for s in s2_search(q):
        ids = s.get("externalIds", {}) or {}
        doi = (ids.get("DOI", "") or "").lower()
        url = s.get("url", "")
        key = doi or url
        if key in seen:
            continue
        seen.add(key)

        pdf_url = ((s.get("openAccessPdf") or {}).get("url") or "")

        out_rows.append({
            "source": "semanticscholar",
            "title": s.get("title", ""),
            "doi": doi,
            "url": url,
            "pdf_url": pdf_url,
            "abstract": s.get("abstract", ""),
            "year": s.get("year"),
            "venue": s.get("venue", ""),
            "query": q
        })

    time.sleep(0.8)  # Be polite to APIs

def try_download_pdf(pdf_url, dest_path):
    """Attempt to download PDF from URL"""
    if not pdf_url:
        return False

    try:
        with requests.get(pdf_url, headers=HEADERS, timeout=45, stream=True) as r:
            if r.status_code != 200:
                return False

            size = 0
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        size += len(chunk)

        return dest_path.exists() and dest_path.stat().st_size > 1024
    except Exception as e:
        print(f"    Download failed: {e}")
        return False

def main():
    ap = argparse.ArgumentParser(description="VRA Prior Art Harvester")
    ap.add_argument("--out", required=True, help="Output directory (created if missing)")
    ap.add_argument("--query", action="append", default=[], help="Add search query (can repeat)")
    ap.add_argument("--years", default="", help="Year range e.g. 1995-2026")
    ap.add_argument("--max", type=int, default=500, help="Max total records to keep")
    args = ap.parse_args()

    outdir = pathlib.Path(args.out)
    papers_dir = outdir / "papers"
    ensure_dir(outdir)
    ensure_dir(papers_dir)

    queries = args.query or VRA_QUERIES
    print(f"\n{'='*80}")
    print(f"VRA PRIOR ART HARVESTER")
    print(f"{'='*80}")
    print(f"Output directory: {outdir}")
    print(f"Number of queries: {len(queries)}")
    print(f"Year range: {args.years or 'all years'}")
    print(f"{'='*80}\n")

    rows, seen = [], set()

    for i, q in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] Query: {q[:70]}...")
        collect_one_query(q, args.years.strip() or None, rows, seen)
        print(f"    Total papers collected: {len(rows)}\n")

    # Trim to max
    rows = rows[:args.max]
    ts = datetime.utcnow().isoformat() + "Z"

    print(f"\n{'='*80}")
    print(f"DOWNLOADING PDFs")
    print(f"{'='*80}\n")

    # Attempt PDF downloads
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

        print(f"  [{i}/{len(rows)}] Downloading: {r.get('title', 'Unknown')[:60]}...")
        ok = try_download_pdf(pdf, dest)
        if ok:
            r["local_pdf"] = str(dest)
            download_success += 1
            print(f"    ✓ Success")
        else:
            print(f"    ✗ Failed")

    # Write JSON/CSV + README
    print(f"\n{'='*80}")
    print(f"SAVING RESULTS")
    print(f"{'='*80}\n")

    (outdir / "index.json").write_text(
        json.dumps({"generated_at": ts, "count": len(rows), "items": rows}, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ Saved index.json")

    csv_path = outdir / "index.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "title", "doi", "url", "pdf_url", "local_pdf", "year", "venue", "query"])
        for r in rows:
            w.writerow([
                r.get(k, "") for k in
                ["source", "title", "doi", "url", "pdf_url", "local_pdf", "year", "venue", "query"]
            ])
    print(f"  ✓ Saved index.csv")

    readme = f"""# VRA Prior Art Relations (auto-collected)

Generated: {ts}
Total Records: {len(rows)}
PDFs Downloaded: {download_success}

## Search Queries

{chr(10).join(f"{i}. {q}" for i, q in enumerate(queries, 1))}

## Files

- **index.json** — Full metadata with abstracts
- **index.csv** — Spreadsheet view for easy browsing
- **papers/** — Downloaded open-access PDFs ({download_success} files)

## Sources

- OpenAlex (open scholarly graph)
- arXiv (preprint server)
- Crossref (DOI registry)
{"- Semantic Scholar (AI-powered search)" if get_semantic_scholar_key() else ""}

## Next Steps

1. Review index.csv to identify relevant papers
2. Read abstracts in index.json
3. Review downloaded PDFs in papers/
4. Compare each paper's methodology to VRA's unique features:
   - Multiplicative order detection in ℤ*_N
   - Phase coherent averaging across multiple bases
   - CFAR detection with guard cells
   - √M and √L scaling laws
   - Group character embeddings
   - Regime mapping via ρ = r/N

## VRA Novelty Checklist

For each paper, check if it contains:
- [ ] Multiplicative order detection via spectral methods
- [ ] Multi-base coherent FFT averaging
- [ ] CFAR peak detection in modular sequences
- [ ] Phase embedding of modular arithmetic
- [ ] Validated √M and √L scaling
- [ ] Application to ECC/quantum bridging
- [ ] GPU-accelerated implementation

If ANY paper contains ALL these features, it may overlap with VRA.
"""

    (outdir / "README.md").write_text(readme, encoding="utf-8")
    print(f"  ✓ Saved README.md")

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total papers collected: {len(rows)}")
    print(f"PDFs downloaded: {download_success}")
    print(f"Output directory: {outdir}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
