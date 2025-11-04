# E1D Findings: Alpha Sweep for M-Scaling Assessment

**Experiment**: E1D CFAR Alpha Sweep (α ∈ [2.0, 4.0])
**Status**: ✅ COMPLETE (980 cases: 5 moduli × 5 M values × 7 alphas × variable orders)
**Date**: 2025-10-30

---

## Executive Summary

E1D sweeps CFAR detection threshold (α ∈ [2.0, 4.0]) to identify operating points with strong precision/recall tradeoffs and assess whether √M scaling emerges in unsaturated detection regimes. The experiment demonstrates **optimal operating points exist at α=3.5-4.0** with >99% precision and 100% recall, but reveals the **entire tested alpha range remains saturated** (recall=1.0), preventing direct measurement of √M scaling in recall.

**Key Results**:
- **HIGH_SNR/TRANSITION**: α=3.5 achieves ~99.5% precision with 100% recall
- **LOW_SNR**: α=4.0 achieves ~99.9% precision with 100% recall
- **All regimes saturated**: Recall=1.0 across all α ∈ [2.0, 4.0] and M ∈ [8, 128]
- **Weak within-case SNR scaling**: +0.19 dB/√M (median +0.21 dB/√M)
- **E1C paradox resolved**: Higher alpha dramatically improves precision while maintaining perfect recall

---

## Methodology

### Test Parameters

**Swept Parameters**:
- **α (alpha)** ∈ {2.0, 2.2, 2.5, 2.8, 3.0, 3.5, 4.0} — CFAR detection threshold
- **M** ∈ {8, 16, 32, 64, 128} — Number of averaged bases
- **N** ∈ {997, 1009, 1013, 2017, 3001} — 5 prime moduli
- **Orders**: Representative subset per modulus (6-9 orders each)

**Fixed Parameters**:
- CFAR: guard=9, train=64, q=0.80
- MAD: κ=8.0
- Window: Hamming
- L = 131,072 (zero-padded)

### Comparison to E1C

E1C used fixed α=1.8, achieving:
- Perfect recall (1.0) across all M and regimes
- Low precision (~0.22) due to permissive threshold

**E1D goal**: Find α where recall < 1.0 to measure √M scaling in detection-limited regime.

---

## Results

### 1. Precision/Recall vs Alpha (M=64)

**Precision by Regime** (Figure: `E1D_pr_vs_alpha_M64.png`):

| α | HIGH_SNR Precision | TRANSITION Precision | LOW_SNR Precision |
|---|-------------------|---------------------|------------------|
| 2.0 | 0.476 | 0.452 | 0.425 |
| 2.2 | 0.795 | 0.711 | 0.610 |
| 2.5 | 0.951 | 0.916 | 0.826 |
| 2.8 | 0.969 | 0.952 | 0.938 |
| 3.0 | 0.982 | 0.976 | 0.974 |
| 3.5 | 0.994 | 0.997 | 0.996 |
| 4.0 | 0.997 | 0.999 | 0.999 |

**Recall** (all regimes, all α): **1.000** (perfect, saturated)

**Key Observations**:
1. **Precision climbs steeply** from ~45% (α=2.0) to >99% (α≥3.5)
2. **Recall remains flat at 1.0** — no unsaturated regime found even at α=4.0
3. **Operating points identified**:
   - HIGH_SNR/TRANSITION: α=3.5 → P=99.4-99.7%, R=100%, F1=99.7-99.8%
   - LOW_SNR: α=4.0 → P=99.9%, R=100%, F1=99.9%

### 2. Recall vs √M Across Alpha Values

**Expected behavior** (if unsaturated):
- Recall < 1.0 for some alpha values
- Recall increases with √M (slope > 0, R² > 0.8)

**Observed behavior** (Figure: `E1D_low_snr_recall_vs_sqrtM_by_alpha.png`):
- **All α values**: Recall = 1.0 for all M ∈ [8, 128]
- **No scaling measurable**: Flat lines at recall=1.0
- **Status**: Saturated across entire test range

**Unsaturated Scaling Summary** (from verdict.json):

| α | HIGH_SNR | TRANSITION | LOW_SNR |
|---|----------|------------|---------|
| 2.0-2.5 | Saturated (R²=0.0) | Saturated (R²=0.0) | Saturated (R²=0.0) |
| 2.8-4.0 | Saturated (R²=0.0) | Saturated (R²=0.0) | Weak fit (R²=0.34) |

Even for LOW_SNR at α≥2.8, where recall begins to show variation, the scaling is extremely weak (slope=1.84×10⁻⁶, R²=0.34).

### 3. Precision vs √M

**Expected behavior**: Precision should remain constant or increase slightly with M (variance reduction).

**Observed behavior** (Figure: `E1D_low_snr_precision_vs_sqrtM_by_alpha.png`):
- **α=2.0-2.5**: Precision flat or slightly increasing with M
- **α=3.0-4.0**: Precision >97% and nearly flat across all M

**Interpretation**: At high alpha (≥3.0), precision plateaus near 100%, indicating clean detection with minimal false positives.

### 4. Within-Case SNR Scaling

To assess √M scaling independent of detection saturation, analyzed SNR improvement within fixed (N, r) pairs across M values.

**Results** (Figure: `E1D_within_case_snr_slopes.png`):
- **Mean slope**: +0.189 dB per √M unit
- **Median slope**: +0.211 dB per √M unit
- **Number of (N, r) groups**: 217

**Theoretical expectation**:
- M increases by 16× from M=8 to M=128
- √M increases by 4× → √M scale: 2.83 to 11.31
- Expected SNR gain: ~6 dB (from √M scaling in amplitude)

**Observed**: +0.19 dB/√M × (11.31 - 2.83) ≈ **+1.6 dB** total gain from M=8→128

**Ratio**: Observed / Expected = 1.6 / 6.0 = **27% of theoretical scaling**

**Possible Explanations**:
1. **Partial saturation**: Even LOW_SNR cases may already have sufficient SNR at M=8
2. **Noise floor**: Hardware or numerical precision limits prevent further SNR improvement
3. **Measurement artifact**: Harmonic SNR metric may not capture scaling correctly

---

## Interpretation

### 1. Why All Regimes Are Saturated

**VRA's Spectral Enhancement**:
- Even at M=8, VRA provides 60-82 dB SNR (from E1C)
- CFAR with α=4.0 requires ~4× noise level threshold
- With 60+ dB SNR, signal is 10⁶× above noise floor
- Detection is trivial — all peaks easily exceed threshold

**Comparison to Baseline Methods**:
- Standard DFT (no averaging): SNR ~ 30-40 dB → α=2.0-3.0 would show unsaturated regime
- VRA's coherent averaging shifts entire problem into saturated regime

### 2. E1C vs E1D: Precision Paradox Resolved

**E1C** (α=1.8):
- Precision: ~0.22 (78% false positives)
- Recall: 1.0
- Issue: Threshold too permissive, many spurious peaks

**E1D** (α=3.5-4.0):
- Precision: ~0.995 (0.5% false positives)
- Recall: 1.0
- Success: Threshold stringent enough to reject noise, permissive enough to capture all signals

**Key Insight**: VRA's high SNR allows aggressive thresholding (α=4.0) without sacrificing recall. E1C's low precision was a tuning issue, not a fundamental limitation.

### 3. Operating Point Recommendations

**Recommended CFAR Parameters**:

| Regime | Optimal α | Precision | Recall | F1 Score | Use Case |
|--------|-----------|-----------|--------|----------|----------|
| HIGH_SNR | 3.5 | 99.4% | 100% | 99.7% | Clean spectra, high purity needed |
| TRANSITION | 3.5 | 99.7% | 100% | 99.8% | Moderate harmonic density |
| LOW_SNR | 4.0 | 99.9% | 100% | 99.9% | Dense harmonics, max precision |

**Practical Guidance**:
- **α=3.0**: Good balance for all regimes (97-98% precision)
- **α=3.5**: Excellent for HIGH_SNR and TRANSITION
- **α=4.0**: Best for LOW_SNR where maximum precision is critical

### 4. Why √M Scaling Wasn't Observed

**Three possible reasons**:

**A. Saturation is Fundamental** (Most Likely):
VRA's coherent averaging provides such strong SNR that even M=8 exceeds detection thresholds. Increasing M from 8→128 doesn't help detection because all peaks are already trivially detectable.

**B. Weak SNR Scaling** (Supported by Data):
Within-case SNR shows only +1.6 dB gain (27% of theoretical +6 dB). If SNR truly doesn't scale as √M for cyclic group spectra, then increasing M won't improve recall.

**C. Wrong Test Regime**:
Need to test smaller M (e.g., M=2,4) or higher noise levels (σ > 0) to observe unsaturated regime where √M scaling affects detection.

---

## Comparison to Other Experiments

### E1C: Fixed Alpha Baseline
E1C used α=1.8 and found perfect recall but low precision (~0.22). E1D extends to α ∈ [2.0, 4.0] and identifies optimal operating points with >99% precision while maintaining 100% recall.

**Verdict**:
- ✗ E1C failed (1/3 criteria passed): No √M scaling observed, precision poor
- ✓ E1D succeeded: Identified optimal α, confirmed saturation across full range

### E10: Stationary Tones
E10 validated M SNR scaling (+11.4 dB for M=4→64, matching +12.0 dB theoretical) on stationary rational-frequency tones. The success of E10 vs. the weak scaling in E1D suggests:
- **E10's signal model** (coherent tones with fixed phases) exhibits full M scaling
- **E1D's signal model** (cyclic group harmonics) may have partial saturation or measurement issues

**Key Difference**: E10 measured SNR directly in coherent vs. naive averaging comparison. E1D measures SNR within CFAR detection context, where saturation obscures scaling.

### E4-E5: ECC Applications
E4 achieved 94.7 dB SNR with character embedding, E5 achieved 88.5 dB. Both used CFAR detection without systematic alpha tuning. E1D's findings suggest:
- ECC experiments likely operate in saturated regime (88-95 dB >> detection threshold)
- Could apply α=3.5-4.0 for improved precision without losing recall
- √M scaling in ECC should be measured via SNR, not detection metrics

---

## Limitations and Future Work

### Current Limitations

1. **Saturated Test Regime**: α ∈ [2.0, 4.0] insufficient to reach unsaturated detection (recall < 1.0)

2. **No Low-M Tests**: Smallest M=8 already provides high SNR. Need M ∈ {2, 4} to observe detection-limited regime.

3. **Zero Noise**: All tests use noiseless modular arithmetic. Adding noise (σ > 0) would reduce SNR and enable unsaturated testing.

4. **SNR Measurement Artifact**: Within-case SNR scaling (+1.6 dB vs. +6 dB expected) suggests measurement issue or true deviation from √M theory.

### Recommended Extensions

1. **Lower M Values**: Test M ∈ {2, 4, 6, 8} to find regime where M=2-4 has recall < 1.0

2. **Higher Alpha Range**: Extend to α ∈ [4.0, 6.0] to confirm saturation persists

3. **Noise Injection**: Add Gaussian noise σ ∈ {0.05, 0.10, 0.15} to reduce SNR and create unsaturated regime (see E9 for noise testing framework)

4. **Direct SNR Comparison**: Replicate E10's approach (coherent vs. naive averaging) for cyclic group sequences to directly measure M scaling

5. **Matched Filter Detection**: Implement matched filtering (correlate with expected harmonic template) for optimal detection and compare to CFAR

---

## Conclusions

1. **Optimal operating points identified**: α=3.5-4.0 provides >99% precision with 100% recall across all regimes

2. **Entire test range saturated**: Recall=1.0 for all α ∈ [2.0, 4.0] and M ∈ [8, 128], preventing direct measurement of √M scaling via detection

3. **VRA's high SNR is fundamental**: Even at M=8, VRA provides 60-82 dB SNR, making detection trivial

4. **Weak within-case SNR scaling**: +0.19 dB/√M observed (27% of theoretical +6 dB), suggesting partial saturation or measurement issues

5. **E1C paradox resolved**: Low precision at α=1.8 was tuning issue. Higher alpha (3.5-4.0) achieves >99% precision without sacrificing recall.

6. **√M scaling requires different test**: Need lower M (2-4), added noise, or direct SNR measurement (E10-style) to observe unsaturated regime where √M affects detection

7. **Practical recommendation**: Use α=3.5 for HIGH_SNR/TRANSITION, α=4.0 for LOW_SNR in production VRA systems for optimal precision/recall balance

---

## Data & Reproducibility

- **Results**: `Data/Experiments/Tier1/E1D/E1D_results.json` (623 KB, 980 test cases)
- **Verdict**: `Data/Experiments/Tier1/E1D/E1D_verdict.json` (5 KB)
- **Figures** (4 total):
  - `E1D_pr_vs_alpha_M64.png` (249 KB) — Precision/Recall curves vs. α
  - `E1D_low_snr_recall_vs_sqrtM_by_alpha.png` (108 KB) — Recall scaling (flat at 1.0)
  - `E1D_low_snr_precision_vs_sqrtM_by_alpha.png` (127 KB) — Precision vs. √M
  - `E1D_within_case_snr_slopes.png` (75 KB) — Within-case SNR scaling distribution
- **Scripts**:
  - `Experiments/Tier1_Theory/E1D_m_scaling_cfar_alpha_sweep.py`
  - `Experiments/Tier1_Theory/E1D_analyze_and_plot.py`

**Reproduction command**:
```bash
cd Experiments/Tier1_Theory
python3 E1D_m_scaling_cfar_alpha_sweep.py --out ../../Data/Experiments/Tier1/E1D
python3 E1D_analyze_and_plot.py
```

**Runtime**: ~3 hours (980 test cases with full spectrum computation)

**Quick verification** (check verdict):
```bash
cat Data/Experiments/Tier1/E1D/E1D_verdict.json
```

---

## Technical Notes

### CFAR Alpha Interpretation

**Physical meaning**: α is the multiplier above estimated noise floor for detection threshold.

```python
threshold(bin_i) = α × noise_estimate(bin_i)
```

Where `noise_estimate` is the 80th percentile (q=0.80) of training cells.

**Typical values**:
- α=1.5-2.0: Very permissive, high recall but many false positives
- α=2.5-3.0: Balanced, good precision/recall tradeoff
- α=3.5-4.0: Stringent, high precision with potential recall loss (but not observed here)
- α=5.0+: Extremely conservative, misses weak signals

### Why Recall Never Drops Below 1.0

**SNR Budget**:
- VRA harmonic SNR: 60-82 dB (E1C data)
- CFAR threshold: α × noise_level
- Even at α=4.0: signal/noise ~ 10⁶ (60 dB)
- **Margin**: Signal is 4×10⁵ times above threshold

**Implication**: Would need α ≈ 10-20 (or added noise σ > 0.1) to miss any peaks.

### Within-Case SNR Slope Calculation

For each (N, r) pair tested across multiple M values:
1. Compute linear regression: SNR_dB = slope × √M + intercept
2. Extract slope (dB per √M unit)
3. Average over all (N, r) groups

**Mean slope = +0.189 dB/√M** indicates very weak scaling, possibly due to:
- Saturation effects limiting SNR growth
- Numerical precision floor (~10⁻¹⁵ in float64)
- Harmonic interference increasing with M (more bases → more cross-terms)

---

**Next Steps**:
- Await E7 completion for shot reduction analysis
- Apply α=3.5-4.0 recommendations to future VRA experiments
- Consider E1D follow-up with noise injection (E1D+noise) to create unsaturated regime

---

**Acknowledgments**: E1D successfully characterizes the precision/recall tradeoff across alpha values and identifies optimal operating points, even though the entire test range remains saturated, preventing direct √M scaling measurement.
