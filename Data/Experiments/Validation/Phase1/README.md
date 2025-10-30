# Phase 1 Validation Data

**Completed**: October 29, 2025
**Purpose**: Address credibility concerns through expanded testing and comparative benchmarks

---

## Directory Structure

### Extended_Moduli_Sweep/
**30 diverse moduli tested** (vs. 4 previously)
- Small primes: 991, 997, 1009, 1013, 1021, 1031, 1033, 1039
- Safe primes (N=2p+1): 10 moduli
- Carmichael numbers: 561, 1105, 1729
- Prime powers (p²): 4 moduli
- Semiprimes (pq): 5 moduli

**Key Results**:
- Small primes: Mean R² = 0.836 (excellent performance)
- TRANSITION regime: Mean R² = 0.631
- HIGH SNR regime: Mean R² = 0.620

**Data File**: `20251029_230252_extended_moduli_sweep.json`

### Regime_Boundary_Validation/
**66 test points** densely sampled around regime boundaries
- Boundary 1 (ρ = 0.146): 45 points tested
- Boundary 2 (ρ = 0.263): 21 points tested
- 6 moduli: 991, 997, 1009, 1021, 1031, 1033

**Key Results**:
- R² = 1.0 across all boundary tests (perfect √M scaling)
- Confirms regime boundaries generalize across moduli
- Estimated transitions validated with statistical analysis

**Data File**: `20251029_231145_boundary_validation.json`

### Baseline_Benchmarks/
**8 test cases** across 3 regimes, comparing 5 methods
- Methods: Brute Force, Baby-Step Giant-Step, Single FFT, Incoherent Averaging, VRA Coherent
- M values: [1, 4, 8, 16, 32]
- Total tests: 40 FFT comparisons + 8 classical tests

**Key Results**:
- VRA Coherent: **2× faster** than Incoherent Averaging
- Speedup increases with M: 1.29× (M=1) → 2.15× (M=32)
- Validates precision/recall design (direct order estimation unreliable)

**Data File**: `20251029_231540_benchmark_results.json`
**Summary**: `BENCHMARK_SUMMARY.md`

---

## Usage

All data files are JSON format with metadata and results. Load with:

```python
import json

with open('Extended_Moduli_Sweep/20251029_230252_extended_moduli_sweep.json') as f:
    data = json.load(f)
```

---

## Corresponding Figures

See `Figures/Experiments/Validation/Cross_Modulus/` and `Figures/Experiments/Benchmarks/Performance/` for visualizations.
