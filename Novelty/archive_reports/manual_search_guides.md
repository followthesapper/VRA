# Manual Search Guides for Missing Databases

These are step-by-step instructions for manual searches in databases without good API access.

---

## 1. Google Scholar (Most Important!)

**Why**: Most comprehensive (400M+ articles), no API, must search manually

**URL**: https://scholar.google.com/

### Search Strategy

#### Phase 1: Core Concepts (10 searches)

1. **Search 1**: `"multiplicative order" spectral Fourier detection`
   - Look for: Papers combining order detection + spectral methods
   - Red flag: Any paper describing FFT-based order finding

2. **Search 2**: `"phase embedding" modular exponentiation`
   - Look for: Complex phase representation of modular sequences
   - Red flag: Phase embedding specifically for order detection

3. **Search 3**: `"coherent averaging" multiplicative order bases`
   - Look for: Averaging across same-order elements
   - Red flag: Multi-base spectral averaging for order finding

4. **Search 4**: `classical period finding spectral method`
   - Look for: Classical (not quantum) spectral period detection
   - Red flag: Any classical spectral alternative to Shor

5. **Search 5**: `Ramanujan multiplicative order spectral`
   - Look for: Extensions of Ramanujan methods to multiplicative structure
   - Red flag: Ramanujan + multiplicative order (not just additive)

6. **Search 6**: `harmonic peaks subgroup order finite field`
   - Look for: Spectral harmonics from group structure
   - Red flag: Detection via harmonic bin analysis

7. **Search 7**: `"same order bases" Fourier modular`
   - Look for: Using multiple bases with identical order
   - Red flag: Exact phrase "same order bases"

8. **Search 8**: `√M scaling coherent averaging modular`
   - Look for: SNR scaling in modular/number-theoretic context
   - Red flag: √M scaling for multiplicative sequences

9. **Search 9**: `regime mapping order-to-modulus ratio`
   - Look for: Performance analysis vs ρ = r/N
   - Red flag: Regime boundaries in order detection

10. **Search 10**: `"phase coherent" FFT "multiplicative group"`
    - Look for: Coherent spectral methods on multiplicative groups
    - Red flag: Phase-coherent analysis of Z*_N

#### Phase 2: Author-Specific (Check Key Authors)

Search for recent work by:
- `P.P. Vaidyanathan Ramanujan` (RPT inventor, recent work?)
- `Peter Shor period finding classical` (Any classical variants?)
- `Cooley Tukey multiplicative order` (FFT pioneers, extensions?)

#### Phase 3: Recent Work (2023-2025)

Add year filters:
- `multiplicative order detection since:2023`
- `spectral period finding since:2024`
- `coherent averaging modular since:2024`

### What to Record

For each search, note:
- **Total results**: How many papers found?
- **Top 10 titles**: Do any sound relevant?
- **Download any**: PDFs that mention VRA's combination
- **Flag for review**: Any papers scoring >3 on overlap

### Time Estimate
- ~20 minutes per search
- ~3-4 hours total for all 10 searches + author checks

---

## 2. IEEE Xplore (Signal Processing Focus)

**Why**: 4M+ papers, excellent for signal processing, API has limits

**URL**: https://ieeexplore.ieee.org/

### Advanced Search

**Click**: "Advanced Search" button

#### Search 1: Multiplicative Order + Spectral
```
Field 1 (All Metadata): "multiplicative order"
AND
Field 2 (All Metadata): "spectral" OR "Fourier" OR "FFT"
```

#### Search 2: Coherent Averaging + Modular
```
Field 1 (All Metadata): "coherent averaging"
AND
Field 2 (All Metadata): "modular" OR "multiplicative" OR "finite field"
```

#### Search 3: Period Finding + Classical
```
Field 1 (All Metadata): "period finding" OR "order finding"
AND
Field 2 (All Metadata): "classical" NOT "quantum"
AND
Field 3 (All Metadata): "spectral" OR "Fourier"
```

#### Search 4: Phase Embedding + Group
```
Field 1 (All Metadata): "phase embedding" OR "phase representation"
AND
Field 2 (All Metadata): "group" OR "modular" OR "cyclic"
```

#### Search 5: Ramanujan + Order
```
Field 1 (All Metadata): "Ramanujan"
AND
Field 2 (All Metadata): "multiplicative order" OR "order detection"
```

### Filters to Apply

- **Publication Years**: 1990-2025
- **Content Type**: Journals + Conference Papers
- **Topics**: Signal Processing, Algorithms, Number Theory

### What to Check

For each result:
1. Read abstract carefully
2. Check if it mentions VRA's specific combination
3. Download PDF if potentially relevant
4. Score using checklist (0-5)

### Time Estimate
- ~30 minutes per search
- ~3 hours total for 5 searches + filtering

---

## 3. zbMATH (Pure Math Focus)

**Why**: 4M+ math papers, excellent for number theory, FREE!

**URL**: https://zbmath.org/

### Simple Search (Try First)

**Query box searches**:

1. `multiplicative order spectral`
2. `phase embedding finite group`
3. `coherent averaging Fourier modular`
4. `Ramanujan periodicity transform`
5. `classical period finding spectral`
6. `harmonic analysis multiplicative group`

### Advanced Search (If Needed)

**Click**: "Advanced Search"

#### Search Template:
```
Title/Abstract: multiplicative order
AND
Title/Abstract: spectral OR Fourier
AND
MSC (Math Subject Class): 11Y16 (Number-theoretic algorithms)
```

#### Alternative MSC Codes:
- **11Y16**: Number-theoretic algorithms
- **42A38**: Fourier analysis
- **20K01**: Finite abelian groups
- **68W40**: Analysis of algorithms

### Browsing Strategy

1. **Start broad**: "multiplicative order"
2. **Refine**: Add "spectral" or "Fourier"
3. **Check MSC**: Look at classifications of relevant papers
4. **Follow citations**: Check "Cites" and "Cited by"

### Time Estimate
- ~20 minutes per search
- ~2 hours total

---

## 4. MathSciNet (If Accessible)

**Why**: Gold standard for math, curated reviews, BUT requires $$$

**URL**: https://mathscinet.ams.org/

### If You Have Access

#### Publications Search

**Primary Classification**: 11Y16 (Number-theoretic algorithms)

**Keywords (use AND/OR)**:
```
multiplicative order AND (spectral OR Fourier OR harmonic)
```

```
period finding AND classical AND spectral
```

```
coherent averaging AND modular arithmetic
```

#### Search by Review Text

MathSciNet has expert reviews - search review text:
```
Reviews containing: "multiplicative order" AND "spectral"
```

### If You DON'T Have Access

**Options**:
1. **University library**: Many universities subscribe
2. **Collaborator**: Ask someone with access to search for you
3. **AMS membership**: $$$, but includes MathSciNet
4. **Skip it**: Not essential if you've done Google Scholar + zbMATH

### Time Estimate
- ~1 hour if you have access
- N/A if you don't

---

## 5. Patent Databases

### Google Patents (Free, Easy)

**URL**: https://patents.google.com/

**Searches**:
1. `multiplicative order detection method`
2. `spectral order finding algorithm`
3. `phase coherent averaging modular`
4. `Fourier transform cryptographic order`
5. `classical period finding system`

**Look for**:
- **Title** mentions order detection or spectral methods
- **Abstract** describes VRA-like approach
- **Claims** (most important) - do they cover VRA's combination?

**Classification codes** to browse:
- `G06F 17/14`: Fourier transformation
- `G06F 7/72`: Modular arithmetic
- `H04L 9/30`: Cryptographic algorithms

### USPTO (Official US Database)

**URL**: https://www.uspto.gov/patents/search

**Advanced Search**:
```
SPEC/"multiplicative order" AND SPEC/"spectral"
```

```
SPEC/"coherent averaging" AND SPEC/"modular"
```

```
SPEC/"phase embedding" AND SPEC/"Fourier"
```

### Espacenet (European)

**URL**: https://worldwide.espacenet.com/

Use similar queries, check International Patent Classification (IPC):
- **G06F 17/14**: Fourier transforms
- **H04L 9/30**: Cryptographic techniques

### Time Estimate
- ~1 hour for Google Patents
- ~1 hour for USPTO/Espacenet
- ~2 hours total

---

## Summary Checklist

### Must Do (High Priority)

- [ ] **Google Scholar**: 10 core searches + author checks (~4 hours)
- [ ] **IEEE Xplore**: 5 advanced searches (~3 hours)
- [ ] **zbMATH**: 6 simple searches (~2 hours)
- [ ] **Total**: ~9 hours for high-priority manual searches

**Confidence gain**: +7% (87% → 94%)

### Should Do (Medium Priority)

- [ ] **Google Patents**: 5 searches (~1 hour)
- [ ] **Recent year filters**: Google Scholar since:2024 (~1 hour)
- [ ] **Citation following**: Track 5-10 key papers (~2 hours)
- [ ] **Total**: +4 hours

**Confidence gain**: +3% (94% → 97%)

### Optional (Low Priority)

- [ ] **MathSciNet**: If accessible (~1 hour)
- [ ] **USPTO/Espacenet**: Deep patent search (~2 hours)
- [ ] **Author contact**: Email key researchers (~1 hour)
- [ ] **Total**: +4 hours

**Confidence gain**: +1% (97% → 98%)

---

## Recording Template

Use this template to track your searches:

```markdown
## Search: [Database Name] - [Query]

**Date**: YYYY-MM-DD
**Query**: "exact query used"
**Results**: X papers found
**Time**: XX minutes

### Top 5 Results:
1. [Title] - [Author] - [Year]
   - Relevance: Low/Medium/High
   - Overlap score: 0-5
   - Notes: ...

2. [Title] - [Author] - [Year]
   - Relevance: Low/Medium/High
   - Overlap score: 0-5
   - Notes: ...

... (continue for top 5)

### Papers Downloaded:
- [Filename.pdf] - Overlap score X

### Red Flags:
- None found / [List any concerning papers]

### Conclusion:
No exact match found / Found similar work [cite] / etc.
```

---

## Final Notes

### What Constitutes a "Match"?

**Full match** (would invalidate novelty):
- Paper has 5+ VRA features
- Explicitly describes coherent averaging across same-order bases
- Applied to multiplicative order detection
- Uses spectral/Fourier methods

**Partial match** (cite and compare):
- Paper has 3-4 VRA features
- Similar concept in different domain
- Would need detailed comparison in "Related Work"

**No match** (safe):
- Paper has 0-2 VRA features
- Superficial keyword similarity only
- Clearly different approach

### When to Stop Searching

**Stop when**:
1. You've completed Must Do searches (9 hours)
2. No papers score >3 on overlap
3. You've reviewed top 50 results per major search
4. Diminishing returns (finding same papers repeatedly)

**You have enough evidence** if:
- 10+ searches with no exact matches
- 50+ relevant papers reviewed
- No paper combines 5+ VRA features

---

**Good luck with manual searches!**

**Remember**: Even 95% confidence is excellent. The final 5% comes from peer review and community scrutiny AFTER publication. No one can guarantee 100% novelty beforehand.
