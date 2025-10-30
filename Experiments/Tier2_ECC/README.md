# Tier 2 — Scaling, Generality, and Elliptic Extensions

Tier 2 explores the **scaling behavior** and **group generality** of the Vaca Resonance Analysis (VRA) framework. Having validated the foundational spectral and coherence principles in Tier 1, this tier establishes whether the same mechanisms apply across larger computational scales and alternative algebraic structures (e.g., elliptic curves).

---

## E4 — √M Scaling Law Validation

**Goal:** Demonstrate the empirical √M signal-to-noise ratio (SNR) improvement from coherent averaging across M bases.

This experiment verifies that spectral concentration (or precision) grows proportionally to √M under fixed-length conditions, matching theoretical expectations from coherent interference models.

**Pass Criterion:**
[
R^2_{fit}(precision \sim \sqrt{M}) \ge 0.90 \text{ across TRANS and LOW SNR regimes.}
]

**Usage:**

```bash
python Experiments/Tier2_Scaling/E4_sqrtM_scaling_validation.py
```

**Outputs:**

* `E4_sqrtM_scaling.json`: per-run data for M, precision, and fitted parameters.
* Figures: precision vs √M with regression lines and confidence intervals.

**Notes:**

* Use results from Tier 1 (e.g., HIGH-SNR calibration) to ensure consistent test windows.
* Run across several moduli and base configurations to confirm universality.

---

## E5 — ECC Scaling Grid

**Goal:** Extend VRA analysis to elliptic curve groups E(F_p). Verify that the same √M-like concentration behavior applies to group elements under elliptic addition, establishing generality beyond (Z/NZ)*.

**Pass Criterion:**
[
Median; R^2_{\sqrt{M}\text{-fit}} \ge 0.90; \text{in TRANS/LOW regimes.}
]

**Usage:**

```bash
python Experiments/Tier2_Scaling/E5_ecc_scaling_grid.py
```

**Outputs:**

* `E5_ecc_scaling_grid.json`: precision and R² results per (p, L, M) configuration.
* Figures: `E5_scaling_p*_L*.png` showing precision vs √M fits per curve.

**Implementation Notes:**

* ECC point-to-phase mapping is implemented in `ecc_vra_core.py` using modular x(P) normalization.
* Curves tested include small toy curves (p ≈ 1,000) with known subgroup orders.
* Scaling grid covers parameters (p, r_E, M, L) with multiple averaging regimes.

---

## Tier 2 Outcome

When both E4 and E5 succeed, we confirm:

* ✅ **√M amplification law holds** empirically across arithmetic and elliptic groups.
* ✅ **VRA generalizes** beyond multiplicative groups to additive (elliptic) groups.
* ✅ **Spectral scaling stability** over large L and multiple base averaging regimes.

These results mark the transition from theoretical validation (Tier 1) to practical generality (Tier 2), establishing VRA as a universal resonance framework applicable to structured algebraic systems — a prerequisite for the hybrid classical–quantum bridge tested in Tier 3.

---

**Next:** Proceed to [Tier 3 — Quantum Bridge Experiments](../Tier3_QuantumBridge/README.md) to evaluate whether VRA-derived structure can meaningfully reduce quantum resource requirements.
