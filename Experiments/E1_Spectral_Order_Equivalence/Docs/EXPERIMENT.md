# E1: Spectral-Order Equivalence Validation

**Experiment ID**: E1
**Category**: Mathematical Validation (Tier 1)
**Status**: Completed
**Date**: October 30, 2025

---

## 1. Observation

VRA (Vaca Resonance Analysis) uses FFT to detect multiplicative order r in finite groups by phase embedding modular exponentiation sequences. The method produces spectral peaks, but it is unclear whether these peaks correspond exactly to the theoretical harmonic bins predicted by the order r.

**Key Question**: Do VRA's spectral peaks align with the expected harmonic locations derived from multiplicative order?

---

## 2. Question

**Primary Research Question**: Does VRA exhibit spectral-order equivalence, meaning do detected peaks correspond to harmonic bins k·L/r within a validated radius R?

**Sub-Questions**:
- What is the precision (fraction of detected peaks that are true harmonics)?
- What is the recall (fraction of true harmonics that are detected)?
- How does performance vary across different SNR regimes?

---

## 3. Background Research

**Prior Knowledge**:
- Fourier analysis theory predicts that periodic sequences with period r produce spectral peaks at frequencies f = k/r for integer k
- With zero-padding factor zp, expected bins are B_k = ⌊k·L·zp/r⌋
- VRA uses validated radius R = ⌊0.5·log₂(L)⌋ to define peak detection tolerance
- Different regimes classified by ρ = r/N parameter

**Related Experiments**:
- E2 validates the radius rule itself
- E1B-E1D variants explore M-scaling behavior

---

## 4. Hypothesis

**Hypothesis**: VRA detected peaks will correspond to theoretical harmonic bins k·N_zp/r with:
- **High precision** (≥98%) in TRANSITION and LOW_SNR regimes
- **High precision** (≥85%) in HIGH_SNR regime
- **High recall** (≥85-98%) across all regimes when using appropriate detection thresholds

**Null Hypothesis**: VRA peaks are randomly distributed and do not align with theoretical harmonic locations.

**Rationale**: VRA's phase embedding should preserve the cyclic group structure, causing FFT peaks to appear at predictable harmonic frequencies.

---

## 5. Experiment Design

### Variables

**Independent Variables**:
- Modulus N ∈ {997, 1009, 1013, 2017, 3001}
- Multiplicative order r (varies per modulus)
- Sequence length L = 131,072
- Number of bases M = 16
- Detection threshold (99.9th percentile)

**Dependent Variables**:
- Precision: TP / (TP + FP)
- Recall: TP / (TP + FN)
- F1 score: 2·Precision·Recall / (Precision + Recall)

**Controlled Variables**:
- Window function: Hann
- Zero-padding factor: zp = 4
- Validated radius: R = ⌊0.5·log₂(L_zp)⌋

### Procedure

1. **Setup**: For each (N, r) test case:
   - Select M=16 bases with ord_N(a_i) = r
   - Generate modular exponentiation sequences x_i[k] = a_i^k mod N

2. **Phase Embedding**: Convert to complex phases
   ```
   u_i[k] = exp(2πi · x_i[k] / N)
   ```

3. **FFT + Coherent Averaging**:
   ```
   U_i[f] = FFT(u_i, length=L·zp)
   S[f] = (1/M) · Σ U_i[f]
   Power[f] = |S[f]|²
   ```

4. **Peak Detection**: Find peaks above 99.9th percentile threshold

5. **Validation**: Compare detected peaks to expected harmonics B_k = ⌊k·N_zp/r⌋ within radius R

6. **Metrics**: Compute precision, recall, F1 per test case

### Data Collection

- 81 test cases total
- Regime distribution:
  - HIGH_SNR (ρ < 0.146): 57 cases
  - TRANSITION (0.146 ≤ ρ < 0.263): 10 cases
  - LOW_SNR (ρ ≥ 0.263): 14 cases
- Data saved to: `Data/E1_results_*.json`

---

## 6. Results

### Summary Statistics

| Regime | Cases | Precision | Recall | F1 Score | Status |
|--------|-------|-----------|--------|----------|--------|
| HIGH_SNR | 57 | 0.859 | 0.781 | 0.777 | Near target |
| TRANSITION | 10 | 0.986 | 0.373 | 0.517 | Prec: PASS, Recall: FAIL |
| LOW_SNR | 14 | 0.990 | 0.171 | 0.281 | Prec: PASS, Recall: FAIL |

**Key Findings**:
- Precision exceeds targets (85-98%) across all regimes
- Recall insufficient in TRANSITION/LOW_SNR (17-37% vs 98% target)
- HIGH_SNR recall at 78.1% (near 85% target)

### Data Analysis

**Precision Analysis**:
- TRANSITION/LOW_SNR: ~99% precision confirms spectral-order equivalence
- HIGH_SNR: 85.9% precision acceptable given regime complexity
- Very few false positives (high specificity)

**Recall Analysis**:
- LOW_SNR: Only 17% of true harmonics detected
- TRANSITION: Only 37% of true harmonics detected
- Issue: Large r values have many weak harmonics below detection threshold

**Figures**:
- See `Figures/` directory for precision/recall plots by regime
- SNR distributions
- Harmonic peak detection examples

---

## 7. Conclusion

### Hypothesis Evaluation

**Hypothesis Status**: PARTIALLY CONFIRMED
- **Precision hypothesis**: ✓ CONFIRMED (86-99% across regimes)
- **Recall hypothesis**: ✗ REJECTED (17-78% vs 85-98% target)

### Interpretation

**Scientific Findings**:
1. VRA **correctly identifies harmonic peaks** (high precision validates spectral-order equivalence)
2. VRA **misses weak harmonics** in large-r regimes (sensitivity limitation, not theoretical flaw)
3. The 99.9th percentile threshold is too conservative for LOW_SNR detection

**Practical Implications**:
- VRA works as designed for HIGH_SNR regime (ρ < 0.146)
- TRANSITION/LOW_SNR regimes require:
  - More permissive thresholds (see E1C/E1D variants)
  - Larger M for √M SNR boost
  - Alternative detection strategies (CFAR in E1C)

### Limitations

1. **Fixed detection threshold**: 99.9th percentile not optimal across all regimes
2. **Single M value**: M=16 may be insufficient for LOW_SNR cases
3. **Limited moduli**: Only 5 moduli tested

### Future Directions

1. **Adaptive thresholding**: Regime-specific detection parameters (see E1C/E1D)
2. **M-scaling study**: Test M ∈ {8, 16, 32, 64, 128} for recall improvement
3. **Alternative detectors**: CFAR, MAD, or machine learning approaches

---

## 8. Communication

### Publications
- Results incorporated into VRA validation paper (Section 4.1)
- E1B-E1D variants provide extended analysis

### Code Repository
- Main code: `Code/e1_spectral_order_equivalence.py`
- Utilities: `Code/vra_test_utils.py`
- See README in Code/ for usage instructions

### Data Availability
- Raw results: `Data/E1_results_*.json`
- Processed metrics: `Data/E1_metrics_summary.csv`
- All data uses relative paths for reproducibility

---

## Experiment Variants

This experiment has three important variants that explore related hypotheses:

- **E1B**: Tests M-scaling with percentile threshold (discovered threshold artifact)
- **E1C**: Tests M-scaling with fixed CFAR threshold (100% recall achieved)
- **E1D**: Alpha sweep to find optimal precision/recall tradeoff

See `Variants/` directory for complete documentation.

---

**Document Version**: 1.0
**Last Updated**: November 3, 2025
**Author**: VRA Research Team
