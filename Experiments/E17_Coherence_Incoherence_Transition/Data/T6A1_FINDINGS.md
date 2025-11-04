# T6-A1 Findings: Coherence-Incoherence Transition

**Experiment**: T6-A1 — Coherence-Incoherence Transition
**Date**: 2025-10-31
**Status**: PARTIAL — Phenomenon observed but deviates from target
**Runtime**: ~7 seconds

---

## Executive Summary

We tested whether cross-base phase coherence in multiplicative sequences follows a von Mises distribution with mean resultant length R̄ ≈ 0.137. The standalone implementation successfully computed coherence metrics across moduli and base counts, revealing:

- **Observed R̄**: 0.278 ± 0.102 (overall)
- **Target R̄**: 0.137
- **Deviation**: +0.141 (102% higher than target)

**Verdict: PARTIAL** — The experiment demonstrates:
- ✓ Correct M-scaling: Higher M → Lower R̄ (0.34 → 0.22)
- ✓ Consistent measurement across moduli
- ✗ Absolute values significantly higher than theoretical target

---

## Scientific Method

### 1. Question

Can the phase statistics across multiplicative bases be modeled as a well-defined modular random process with coherence order parameter R̄ ≈ 0.137?

### 2. Hypothesis

For cyclic subgroup order r, normalized phasors at harmonic ℓ behave as i.i.d. draws from a von Mises distribution vM(κ_ℓ), with predicted mean resultant length:

```
R̄(ℓ) = I₁(κ_ℓ) / I₀(κ_ℓ)
⟨R̄⟩ ≈ 0.137  (empirical target from E1D)
```

### 3. Prediction

1. R̄ should be ~0.137 across different (N, r, M) configurations
2. Variance scales as O(1/M): Var(R̄) ∝ 1/M
3. R̄ decreases smoothly with density ρ = r/N

### 4. Experiment Design

**Implementation**: Standalone Python (no VRA dependencies due to import issues)

**Parameters**:
- Moduli: N ∈ {997, 2003} (2 primes)
- Target densities: ρ ∈ {0.10, 0.20, 0.30}
- Base counts: M ∈ {8, 16}
- Sequence length: L = 2048
- Samples per config: 5

**Method**:
1. For each (N, ρ), find multiplicative order r ≈ ρ·N
2. Find M random bases with order exactly r
3. Generate modular sequences: x_t = a^t mod N
4. Convert to phasors: exp(2πi·x_t/N)
5. Compute FFT spectra
6. Calculate mean resultant length:
   - For each harmonic ℓ, normalize phasors to unit length
   - Compute R̄(ℓ) = |mean(unit_phasors)|
   - Average over harmonics 1-50

### 5. Results

**Successful Configurations**:
| N    | ρ     | r   | M  | R̄      | σ(R̄)  |
|------|-------|-----|----|--------|--------|
| 997  | 0.083 | 83  | 8  | 0.3472 | 0.0974 |
| 997  | 0.083 | 83  | 16 | 0.2033 | 0.0520 |
| 2003 | 0.091 | 182 | 8  | 0.3320 | 0.0990 |
| 2003 | 0.091 | 182 | 16 | 0.2303 | 0.0661 |

**Failed Searches**:
- Could not find suitable orders for ρ ∈ {0.20, 0.30} (search exhausted)

**Aggregated Statistics**:
- Mean R̄: 0.2782
- Std Dev: 0.1024
- Range: [0.2033, 0.3472]
- Total samples: 20

**M-Scaling Analysis**:
- M=8:  R̄ = 0.340 ± 0.098
- M=16: R̄ = 0.217 ± 0.059
- Ratio: R̄(M=8) / R̄(M=16) ≈ 1.57

### 6. Analysis

**What Worked**:
1. **M-scaling verified**: Doubling M from 8→16 reduced R̄ by ~37%, consistent with averaging over more bases
2. **Consistency across moduli**: N=997 and N=2003 show similar R̄ values at comparable densities
3. **Low variance within configs**: σ(R̄) = 0.05-0.10, showing measurement stability

**What Didn't Work**:
1. **Absolute values too high**: Observed R̄ ≈ 0.28 vs target 0.137 (2× discrepancy)
2. **Limited density coverage**: Only tested ρ ≈ 0.08-0.09 (failed to find higher densities)
3. **Order-finding challenges**: Stochastic search couldn't locate bases for ρ > 0.10

**Possible Explanations for Discrepancy**:

1. **Parameter regime mismatch**: The empirical R̄ ≈ 0.137 from E1D may require:
   - Larger M (more bases for better averaging)
   - Longer L (better spectral resolution)
   - Different density regime (ρ ≈ 0.2-0.3 instead of 0.08-0.09)

2. **Metric implementation**: While we correctly compute mean resultant length for unit phasors, there may be subtleties in:
   - Which harmonics to average over
   - How to weight harmonics
   - Normalization conventions

3. **Finite-size effects**: With L=2048 and small orders (r=83, 182), we may not be in the asymptotic regime where the von Mises model applies

4. **Statistical mechanics interpretation**: The transition to R̄ ≈ 0.137 may be a critical phenomenon that only emerges at larger system sizes

### 7. Conclusion

**Primary Finding**: Cross-base coherence exhibits M-scaling consistent with statistical averaging, but absolute values deviate significantly from the E1D-reported R̄ ≈ 0.137.

**Verdict: PARTIAL**
- ✓ Successfully implemented standalone coherence measurement
- ✓ Demonstrated systematic M-scaling
- ✗ Did not reproduce target R̄ value
- ✗ Limited density coverage due to order-finding difficulties

**Implications**:
- The R̄ ≈ 0.137 phenomenon likely requires specific parameter regimes not captured in this simplified experiment
- Further investigation needed with full VRA implementation (once import issues resolved)
- Theory-first approach successfully identified measurement challenges

---

## Recommendations

### Immediate Next Steps

1. **Fix VRA imports**: Resolve syntax error in `VRA/__init__.py` to enable full implementation
2. **Expand parameter space**:
   - Increase M to 32-64 bases
   - Use L = 8192 or 16384
   - Test wider density range ρ ∈ [0.05, 0.50]
3. **Improve order-finding**: Implement deterministic search or use known factorizations

### Theoretical Follow-up

1. **Derive R̄(ρ) from first principles**: Use exponential sum techniques to predict density dependence
2. **Asymptotic analysis**: Determine scaling of R̄ with (M, L, r) analytically
3. **Literature review**: Check if similar "order parameters" exist in modular arithmetic or number theory

### Experimental Follow-up

1. **E1D comparison**: Re-run original E1D experiment to verify R̄ ≈ 0.137 claim
2. **Parameter sweep**: Systematic grid search over (M, L, ρ) to locate R̄ minimum
3. **Alternative metrics**: Test other coherence measures (circular variance, entropy)

---

## Data & Outputs

**Generated Files**:
- Raw data: `/home/admin/dev/VRA/Data/Experiments/Tier6/T6A1/T6A1_standalone_results.json`
- Figure: `/home/admin/dev/VRA/Figures/experiments/Tier6/T6A1/T6A1_standalone_summary.png`
- Log: `/home/admin/dev/VRA/Data/Experiments/Tier6/T6A1/T6A1_standalone_20251031_122400.log`
- Findings: This document

**Reproducibility**:
- Code: `/home/admin/dev/VRA/Experiments/Tier6_TheoryFirst/T6A1_coherence_standalone.py`
- Runtime: ~7 seconds
- No VRA dependencies (standalone implementation)

---

## Scientific Method Completion

- [x] Question formulated
- [x] Hypothesis stated with mathematical precision
- [x] Falsifiable predictions made
- [x] Experiment designed and implemented
- [x] Data collected and analyzed
- [x] Results documented with figures
- [x] Conclusion drawn with clear verdict
- [x] Recommendations for follow-up provided

**Status**: PARTIAL — Experiment yields meaningful data but does not validate R̄ ≈ 0.137 hypothesis. Further investigation required with expanded parameter space and full VRA implementation.
