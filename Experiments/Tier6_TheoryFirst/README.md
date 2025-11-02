# Tier 6: Theory-First Validation Experiments

**Purpose**: Validate VRA's fundamental scaling laws and theoretical predictions with GPU-accelerated implementations.

---

## CRITICAL: Correct VRA Scaling Laws

### 1. M-Scaling (Base Averaging)

**Concentration**: C ∝ √M
**SNR (Signal-to-Noise Ratio)**: SNR ∝ C² ∝ M

**Implication**: SNR gains **+3.01 dB per doubling of M**

**Why this matters**:
- "√M scaling" in VRA literature refers to **concentration** metric
- SNR (which we measure) is proportional to concentration *squared*
- Therefore: SNR ∝ (√M)² = M (linear in M)

**Source**: VRA Operating Guide (Docs/Theory/Operating_Guide/OPERATING_GUIDE.md, line 92)

**Experimental Validation**:
- E1D: R² = 0.987 fit to √M concentration model
- E5: Flat SNR across M values (saturated regime - no noise headroom)

---

### 2. L-Scaling (Sequence Length)

**Noise Floor**: ∝ 1/L (spectral resolution)
**Noise Power Density**: ∝ 1/L²
**SNR Improvement**: SNR ∝ L²

**Implication**: SNR gains **+6.02 dB per doubling of L**

**Why this matters**:
- L-scaling is the *primary* performance lever in VRA
- More reliable and predictable than M-scaling
- Doubling L gives 2× the frequency resolution → 4× SNR improvement

**Source**: E16 experimental validation

**Experimental Validation**:
- E16: Measured +6.06, +5.53, +6.36, +5.51 dB per doubling
- Theory: +6.02 dB per doubling (20×log₁₀(2))
- R² > 0.99 fit to L² model

---

## Experiment Design Notes

### T6-B1: M-Scaling Law Verification

**Correct Hypothesis**: SNR ∝ M (expecting +3 dB per doubling)

**Common Pitfall**: **Saturation**
- If baseline SNR is too high (low noise), no room for M-scaling improvement
- Must use sufficient noise (σ ≥ 0.2) to see M-scaling effect
- E5 showed flat SNR (82 dB across all M) due to saturation

**Parameters**:
- Noise σ: 0.2-0.3 (to avoid saturation)
- M values: [4, 8, 16, 32, 64, 128]
- L: Fixed at 8192-16384
- Fit model: SNR = a + 10×log₁₀(M)

---

### T6-B2: L-Scaling Law Verification

**Correct Hypothesis**: SNR ∝ L² (expecting +6 dB per doubling)

**Common Pitfalls**:
1. **Wrong Hypothesis**: Testing √L instead of L²
2. **Under-Resolution**: L=1024 with r=182 gives only 5.6 bins/period
   - Causes severe spectral leakage
   - SNR measurement unreliable at low L/r ratios
   - Recommend L ≥ 4×r as minimum

**Parameters**:
- L values: [2048, 4096, 8192, 16384, 32768] (start at 2048 minimum)
- M: Fixed at 16
- Noise σ: 0.03 (moderate, allows high SNR to demonstrate L² scaling)
- Fit model: SNR = a + 20×log₁₀(L/L₀)  [Note: 20× coefficient, not 10×]

---

## Mathematical Relationships

| Quantity | Scaling | dB per Doubling | Mathematical Form |
|----------|---------|-----------------|-------------------|
| **Concentration (C)** | √M | +1.5 dB | 10×log₁₀(√M) |
| **SNR vs M** | M | **+3.0 dB** | 10×log₁₀(M) |
| **SNR vs L** | L² | **+6.0 dB** | 20×log₁₀(L) |

**Key Insight**: When measuring SNR (power-based metric), always use 10×log₁₀ of the *squared* quantity.

---

## Experiments

| ID | Name | Status | Key Finding |
|----|------|--------|-------------|
| **T6-A1** | Coherence-Incoherence Transition | ✅ Running | R̄ ≈ 0.137 universal constant |
| **T6-A2** | Shot Reduction Bound | ⚠️ CPU-only | Bayesian inference (no GPU) |
| **T6-B1** | M-Scaling Law (M → SNR) | 🔧 Refining | Test SNR ∝ M hypothesis |
| **T6-B2** | L-Scaling Law (L² → SNR) | 🔧 Refining | Test SNR ∝ L² hypothesis |
| **T6-C1** | Multimodal Period Search | ⏸️ Planned | TBD |
| **T6-D1** | Exoplanet Biosignature | ✅ Complete | Bound too loose (FAIL) |

---

## Lessons Learned

1. **SNR ≠ Concentration**: VRA literature often discusses √M scaling of *concentration*, but SNR (measured quantity) scales as M
2. **Saturation Masks M-Scaling**: Need sufficient noise to observe M-scaling improvement
3. **L/r Resolution Minimum**: Require L ≥ 4r for reliable SNR measurement
4. **L-Scaling Primary**: L² scaling is more reliable than M scaling for performance optimization
5. **Terminology Clarity**: Always specify whether discussing concentration C or SNR when citing scaling laws

---

## References

- VRA Operating Guide: `/Docs/Theory/Operating_Guide/OPERATING_GUIDE.md`
- √M Theorem Proof: `/Docs/Theory/Sqrt_M_Theorem/SQRTM_THEOREM_PROOF_PART_A.md`
- E16 L-Scaling: `/Experiments/Tier5_AI_ML/E16_l_scaling.py`
- E1D M-Scaling: `/Docs/Experiments/Tier1/E1D_FINDINGS.md`
