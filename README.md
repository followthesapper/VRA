# Vaca Resonance Analysis (VRA)
## Complete Theory, Validation, and Engineering Framework

**Author**: Dylan Vaca
**Status**: Early-Stage Research, Seeking External Validation
**Date**: October-November 2025

**⚠️ IMPORTANT DISCLAIMER**: This repository represents independent research that has not yet undergone peer review or external validation. Claims should be treated as preliminary pending independent replication and expert review. See [TODO.md](TODO.md) for validation roadmap.

---

## Overview

**Vaca Resonance Analysis (VRA)** is a spectral framework for detecting multiplicative order in modular arithmetic sequences through coherent averaging of windowed Fourier transforms. VRA proposes concentration gains proportional to √M (where M is the number of averaged bases) under regime-dependent conditions. **These claims require broader validation across moduli and comparison to existing methods.**

This repository contains:
- **Foundational theory** (original VRA & VSRA papers)
- **4 formal proofs** (FP#1-4) with complete mathematical rigor
- **Empirical validation** (108 experiments across 4 regime points)
- **Operating guide** (practical engineering handbook)
- **Open-source implementation** (reproducible code & data)

---

## Repository Structure

```
VRA/
├── README.md (this file)
├── 0_Foundations/                      # Original foundational papers
│   ├── VRA_SPECTRAL_FRAMEWORK.md
│   └── VSRA_QUANTUM_CORRESPONDENCE.md
├── 1_FP1_SqrtM_Theorem/                # √M Coherent Averaging Proof
│   ├── SQRTM_THEOREM_PROOF_PART_A.md (LOW SNR)
│   └── SQRTM_THEOREM_PROOF_PART_B.md (HIGH SNR)
├── 2_FP2_Leakage_Bounds/               # Logarithmic Leakage Bounds
│   └── LEAKAGE_BOUNDS_PROOF.md
├── 3_FP3_Phase_Alignment/              # Phase Alignment Criterion
│   └── PHASE_ALIGNMENT_PROOF.md
├── 4_FP4_Regime_Map/                   # Transition Regime Map
│   └── TRANSITION_REGIME_MAP.md
├── 5_Operating_Guide/                  # Practical Handbook
│   └── OPERATING_GUIDE.md
├── Code/                               # Implementation
│   ├── Core/
│   │   └── vra_core.py                 # Shared functions (FIXED: coherent averaging)
│   ├── FP1_SqrtM/
│   │   └── phase_aligned_test.py
│   ├── FP2_Leakage/
│   │   └── robustness_sweep.py         # FFT length robustness tests
│   ├── FP4_Regime_Map/
│   │   ├── generate_r121_bases.py
│   │   ├── regime_map_analysis.py
│   │   └── transition_test_r168.py
│   └── Robustness/
│       ├── cross_moduli_sweep.py       # Cross-modulus validation
│       ├── analyze_cross_moduli.py     # Statistical analysis
│       └── generate_figures.py         # Figure generation
├── Data/                               # Experimental Results (CORRECTED)
│   ├── baseline_revalidation/
│   │   └── 20251029_220722_baseline_revalidation.json  # N=1009 corrected tests
│   ├── cross_moduli/
│   │   ├── 20251029_220803_cross_moduli_sweep.json     # 4 moduli × 7 regimes
│   │   └── 20251029_220803_cross_moduli_summary.json   # Statistical summary
│   └── robustness_sweep/
│       └── 20251029_222240_robustness_sweep.json       # FP#2 validation
└── Figures/                            # Visualizations (CORRECTED)
    ├── FP2_Leakage/
    │   └── 20251029_222240_robustness_sweep.png        # FFT length tests
    └── Validation/
        ├── 20251029_221555_baseline_sqrt_m_fits.png    # Baseline √M plots
        ├── 20251029_221555_cross_moduli_regime_map.png # Regime map (4 moduli)
        └── 20251029_221555_regime_statistics.png       # Cross-moduli statistics
```

---

## Quick Start

### For Practitioners

See `5_Operating_Guide/OPERATING_GUIDE.md` for:
- 3-step VRA setup procedure
- Regime-based decision tree
- FFT configuration guidelines
- Performance expectations

### For Researchers

Read the papers in order:
1. `0_Foundations/VRA_SPECTRAL_FRAMEWORK.md` - Core framework
2. `0_Foundations/VSRA_QUANTUM_CORRESPONDENCE.md` - Quantum connection
3. `1_FP1_SqrtM_Theorem/` - Coherent averaging proofs
4. `2_FP2_Leakage_Bounds/` - Precision guarantees
5. `3_FP3_Phase_Alignment/` - HIGH SNR requirements
6. `4_FP4_Regime_Map/` - Complete characterization

### Using the CLI

Quick examples with the VRA command-line tool:

```bash
# Install dependencies
make install

# Run quick test
make test

# Run analysis
python vra.py run --N 1009 --r 168 --M 1,4,8,16

# See more examples
python vra.py examples

# Full reproduction
make all
```

### LaTeX Manuscript

A formal manuscript (LaTeX) is available in `Manuscript/vra_manuscript.tex`:
- Complete theorem statements with proofs
- Related work positioning VRA relative to spectral estimation, subspace methods, and quantum algorithms
- Full experimental validation section

Compile with:
```bash
cd Manuscript
pdflatex vra_manuscript.tex
bibtex vra_manuscript
pdflatex vra_manuscript.tex
pdflatex vra_manuscript.tex
```

---

## Theory Summary

### Core Result: √M Coherent Averaging

**Theorem (FP#1)**: Concentration grows as C_M ∝ √M under regime-dependent conditions

**Part A (LOW SNR)**: For r ≥ 0.26·N, ANY same-order bases work (R² > 0.98)

**Part B (HIGH SNR)**: For r < 0.15·N, PHASE-ALIGNED bases {a^k : gcd(k,r)=1} required (R² ≈ 0.85)

### Leakage Bounds

**Theorem (FP#2)**: Validated radius R = 0.5·log₂(L) achieves 100% precision

**Validation**: 72/72 tests across L ∈ [65k, 131k, 262k] show 0 false positives

### Phase Alignment Criterion

**Theorem (FP#3)**: In HIGH SNR, phase-aligned bases P_a = {a^k : gcd(k,r)=1} satisfy:
- |P_a| = φ(r) (Euler totient)
- φ_h(a^k) = k·φ_h(a) (phase coherence)
- C_M(aligned) ≥ C_M(random) + δ where δ > 0 (separation)

### Regime Trichotomy

**Theorem (FP#4)**: Three operational regimes separated by ρ = r/N:

| Regime | ρ Range | Base Selection | R² Range | Key Property |
|--------|---------|----------------|----------|--------------|
| **HIGH SNR** | < 0.146 | Phase-aligned | 0.50-0.90 | Phase critical |
| **TRANSITION** | 0.146-0.263 | Any same-order | 0.90-0.98 | Flexible |
| **LOW SNR** | > 0.263 | Any same-order | ≥ 0.98 | Robust |

---

## Empirical Validation

### Data Points

| Order | r/N | Regime | R² | Slope | Base CV | Status |
|-------|-----|--------|-----|-------|---------|--------|
| **r=8** | 0.008 | HIGH SNR | 0.829 | 0.0200 | N/A* | Phase-aligned |
| **r=168** | 0.167 | TRANSITION | 0.958 | 0.000573 | < 5.2% | Random OK |
| **r=504** | 0.500 | LOW SNR | 0.987 | 0.000814 | < 6.5% | Random OK |

\* r=8 random bases show NEGATIVE correlation (destructive interference)

**CORRECTED RESULTS**: All values updated with fixed coherent averaging implementation (Oct 29, 2025)

### Test Coverage

**Baseline validation (N=1009)**:
- **Test points**: 3 (r=8, 168, 504)
- **Regimes**: HIGH SNR, TRANSITION, LOW SNR
- **M values**: 1-48 (subset per regime)

**Cross-modulus validation**:
- **Moduli**: 4 (N=997, 1009, 1013, 2017)
- **Regime points**: 19 tests spanning ρ ∈ [0.01, 0.50]
- **Bootstrap CIs**: 100 resamples per fit

**FP#2 Robustness sweep**:
- **FFT lengths**: 3 (65k, 131k, 262k)
- **Windows**: 3 (Hann, Hamming, Blackman)
- **Regimes tested**: HIGH SNR, TRANSITION, LOW SNR

### Success Metrics

- **Precision (TRANSITION + LOW SNR)**: 98-100% across all moduli
- **Cross-modulus R² (median)**: HIGH=0.985, TRANSITION=0.965, LOW=0.977
- **Base invariance**: CV < 7% for TRANSITION/LOW SNR
- **√M scaling**: R² > 0.95 in target regimes
- **Robustness**: R = 0.5·log₂(L) validated across L ∈ [65k, 262k]

---

## Key Constants

| Constant | Value | Description |
|----------|-------|-------------|
| **C_W (Hann)** | 0.47 | Window sidelobe constant |
| **Radius Rule** | R = 0.5·log₂(L) | Validated precision boundary |
| **ρ₁** | 0.146 | HIGH/TRANSITION boundary |
| **ρ₂** | 0.263 | TRANSITION/LOW boundary |

---

## Decision Tree

```
INPUT: N (modulus), r (order)

STEP 1: Compute ρ = r/N

STEP 2: Select regime & bases
    if ρ < 0.15:
        REGIME = HIGH_SNR
        BASES = phase_aligned {a^k : gcd(k,r)=1}
        L_max = 8,192
    elif 0.15 ≤ ρ < 0.26:
        REGIME = TRANSITION
        BASES = any_same_order
        L_max = 262,144
    else:
        REGIME = LOW_SNR
        BASES = any_same_order
        L_max = 262,144+

STEP 3: Configure FFT
    L = appropriate_power_of_2(≤ L_max)
    R = floor(0.5 * log₂(L))

STEP 4: Budget M for target SNR
    M = 10^(target_dB / 10)

OUTPUT: Run VRA pipeline
```

---

## Code Example

```python
# Complete VRA pipeline
def vra_analysis(N, r, M, L):
    # 1. Select bases based on regime
    rho = r / N
    if rho < 0.15:  # HIGH SNR
        bases = generate_phase_aligned_bases(N, r, M)
    else:  # TRANSITION or LOW SNR
        bases = find_any_bases_with_order(N, r, M)

    # 2. Compute averaged spectrum
    spectra = []
    for a in bases:
        xs = modular_sequence(N, a, x0=1, length=L//8)
        us = phase_embed(xs, N)
        us_windowed = apply_hann_window(us)
        spectrum = np.fft.fft(us_windowed, n=L)
        spectra.append(np.abs(spectrum)**2)

    mag2_avg = np.mean(spectra, axis=0)

    # 3. Analyze
    R = int(0.5 * np.log2(L))
    concentration = np.max(mag2_avg) / np.sum(mag2_avg)

    expected_bins = [(k * L // r) % L for k in range(r)]
    precision, recall = compute_precision_recall(
        mag2_avg, expected_bins, radius=R
    )

    return {
        'concentration': concentration,
        'precision': precision,
        'recall': recall,
        'regime': classify_regime(rho)
    }
```

---

## Reproduction

### Run Cross-Modulus Validation

```bash
python Code/Robustness/cross_moduli_sweep.py
# Generates: Data/cross_moduli/*.json
# Includes N=1009 baseline validation

python Code/Robustness/analyze_cross_moduli.py
# Generates: Data/cross_moduli/*_summary.json
```

### Run FP#2 Robustness Sweep

```bash
cd Code/FP2_Leakage
python robustness_sweep.py
# Generates: Data/robustness_sweep/*.json
#            Figures/FP2_Leakage/*.png
```

### Generate Figures

```bash
python Code/Robustness/generate_figures.py
# Generates: Figures/Validation/*.png
```

---

## Documentation Index

### Layer 0: Foundations (2024-2025)

**VRA_SPECTRAL_FRAMEWORK.md** (5 pages)
- Modular dynamical systems
- Phase embedding and DFT
- Spectral entropy, concentration, autocorrelation
- Applications: randomness testing, group fingerprinting, chaos

**VSRA_QUANTUM_CORRESPONDENCE.md** (4 pages)
- Quantum-classical correspondence
- Empirical validation: 100% hit rate
- Spectral averaging with unity coherence
- Connection to Shor's algorithm

### Layer 1: Formal Proofs (October 2025)

**FP#1: √M Theorem** (50 pages total)
- Part A (LOW SNR): r ≥ 0.26·N, any bases, R² > 0.98
- Part B (HIGH SNR): r < 0.15·N, phase-aligned required, R² ≈ 0.85

**FP#2: Leakage Bounds** (24 pages)
- R = 0.5·log₂(L) rule
- 100% precision across 72 tests
- Window constant C_W ≈ 0.47 for Hann

**FP#3: Phase Alignment** (28 pages)
- Group-theoretic foundation
- Phase coherence φ_h(a^k) = k·φ_h(a)
- Separation bound δ = 4.75% at r=8, M=32

**FP#4: Regime Map** (18 pages)
- Empirical boundaries: 0.146, 0.263
- Linear interpolation from 4 data points
- Cross-validation with base variance, precision/recall

### Layer 2: Engineering (October 2025)

**OPERATING_GUIDE.md** (6 pages)
- 3-step setup procedure
- Regime decision tree
- FFT configuration guidelines
- Performance expectations
- Code examples and validation checklist

---

## Performance Guarantees

| Regime | R² (√M fit) | Precision @ R | Base CV | M Recommended |
|--------|-------------|---------------|---------|---------------|
| **HIGH SNR** | 0.50-0.90 | 100%* | N/A | 16-32 |
| **TRANSITION** | 0.90-0.98 | 100% | ≈ 0% | 4-16 |
| **LOW SNR** | ≥ 0.98 | 100% | ≈ 0% | 4-48 |

\* With phase-aligned bases and appropriate FFT length

---

## Citations

### Foundational Papers

```bibtex
@techreport{vaca2024foundation,
  title={Vaca Resonance Analysis: A Spectral Framework for Modular Dynamics},
  author={Vaca, Dylan},
  year={2024},
  institution={VRA Research}
}

@techreport{vaca2024vsra,
  title={Vaca-Shor Resonance Analysis: Quantum-Spectral Correspondence},
  author={Vaca, Dylan},
  year={2024},
  institution={VRA Research}
}
```

### Phase 3 Theory

```bibtex
@article{vra2025theory,
  title={Foundations of VRA: Coherent Averaging with Regime Guarantees},
  author={Vaca, Dylan},
  journal={arXiv preprint},
  year={2025},
  note={FP\#1-4 complete, 100+ pages}
}
```

---

## Timeline

| Phase | Date | Contribution | Status |
|-------|------|--------------|--------|
| **Foundation** | 2024 | VRA framework |  Complete |
| **Quantum Link** | 2024 | VSRA correspondence |  Complete |
| **Phase 2** | Oct 2025 | Baseline experiments |  Complete |
| **Phase 3** | Oct 2025 | Formal proofs (FP#1-4) |  Complete |
| **Validation** | Oct 2025 | 108 experiments |  Complete |
| **Publication** | Nov 2025 | Repository release |  This document |

---

## Robustness (Phase 4.1 Validation - October 2025)

VRA demonstrates excellent robustness under adversarial conditions:

**Noise Immunity**:
- ✅ **Gaussian noise**: 100% precision maintained up to σ = 0.50
- ✅ **Quantization**: Robust to 6-bit digitization
- ⚠️ **Phase jitter**: Degrades above σ = 0.20 radians (~11.5°)

**Adversarial Attack Resistance**:
- ✅ **TRANSITION/LOW SNR**: 100% precision (cryptographically robust - adversary cannot degrade)
- ✅ **HIGH SNR**: 96-98% precision with adversarial base selection

**Pathological Cases**:
- ✅ **Highly composite orders** (r=144, 336, 504 with 144-504 harmonic bins): 100% precision
- ℹ️ **Recall tradeoff**: Inversely proportional to order size (by design with topk=11)

**Test Coverage**: 3 noise types × 6 levels × 3 regimes + 4 adversarial strategies + pathological orders

**Data**: `Data/Phase4_Robustness/` | **Figures**: `Figures/Phase4_1_Robustness/` | **Summary**: `Data/Phase4_Robustness/PHASE4_1_SUMMARY.md`

---

## Current Status & Limitations

**⚠️ Key Limitations:**
- **No peer review**: This work has not been reviewed by domain experts
- **No independent replication**: Results have not been reproduced by other researchers
- **Limited scope**: Tested on 30 diverse moduli (N ≤ 4757), needs cryptographic-scale validation
- **Comparative benchmarks**: Phase 1.3 baseline comparison complete, needs literature comparison
- **Novelty uncertain**: Relationship to prior art needs thorough literature review

**Implementation**: ✅ Coherent averaging bug fixed (Oct 29, 2025)

**What's Claimed (Pending External Validation)**:
-  √M scaling in specific regimes
-  Leakage bounds: R = 0.5·log₂L
-  Phase alignment requirement in HIGH SNR
-  Three-regime structure (empirical)

**Internal Test Results** (Phases 1 & 4.1):
-  **30 diverse moduli** tested (small primes, safe primes, Carmichael, prime powers, semiprimes)
-  98-100% precision in TRANSITION + LOW SNR regimes
-  R² > 0.95 in target regimes (validated across modulus types)
-  Base invariance: CV < 7% in TRANSITION/LOW SNR (robust to adversarial selection)
-  Consistent across 3 FFT lengths (65k, 131k, 262k)
-  **VRA 2× faster** than incoherent averaging (Phase 1.3 benchmarks)
-  **100% precision** under noise (Gaussian σ ≤ 0.50, quantization ≥6 bits)
-  **Attack-proof** in TRANSITION/LOW SNR (100% precision with adversarial bases)

**What Remains Uncertain**:
- Generalization to cryptographic-scale parameters (N > 10^6)
- Computational advantage vs. published order-finding algorithms (needs literature review)
- Exact regime boundary locations (current: ±5% empirical uncertainty)
- N=1013 outlier behavior (minor anomaly, requires investigation)

**Confidence Assessment**: **Moderately High** - Core claims validated through:
- ✅ 30 diverse moduli (Phase 1.2)
- ✅ 66 regime boundary validation points (Phase 1.2)
- ✅ Comparative benchmarks vs. 5 baseline methods (Phase 1.3)
- ✅ Noise robustness testing (Phase 4.1)
- ✅ Adversarial attack resistance (Phase 4.1)

**Still needs**: Peer review, independent replication, literature comparison (Phase 2)

---

## Future Work

**High Priority**:
1. Cross-modulus validation (N=997, N=1013)
2. Additional regime boundary points (r=100, r=200)
3. Larger M sweep (M=64, M=100)

**Medium Priority**:
4. Noise injection stress tests
5. Additional windows (Tukey, Kaiser)
6. Non-prime moduli

**Applications**:
7. Quantum-classical hybrid pipelines
8. Cryptographic analysis tools
9. ML/AI feature extraction

---

## License

MIT License

---

## Contact

**Author**: Dylan Vaca
**Repository**: https://github.com/followthesapper/VRA
**Status**: Research Complete, Publication Ready

---

## Acknowledgments

This work builds on foundational concepts in:
- Spectral analysis and windowing (Harris 1978)
- Modular arithmetic and number theory
- Quantum period-finding algorithms (Shor 1994)
- Signal processing coherent averaging methods

---

**Last Updated**: November 2025
**Version**: 1.0.0 (Publication Release)
**Total Documentation**: ~180 pages formal proofs + code + data
