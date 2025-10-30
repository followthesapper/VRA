# Tier 1 — Foundational Theory and Validation

This tier establishes the **mathematical and empirical foundations** of VRA — the theoretical core that underpins all higher tiers. It focuses on verifying the structure, leakage control, and phase coherence mechanisms that distinguish VRA from prior methods like the Ramanujan Periodicity Transform (RPT).

---

## E1 — Baseline Equivalence (VRA vs Classical Periodicity)

**Goal:** Verify that VRA spectra align with theoretical periodicities from classical modular arithmetic. Confirm that DFT peak alignments correspond to the true multiplicative order `r`.

**Pass Criterion:**

* Peak localization within ±1 bin of `L / r` for all tested bases (95% of trials).
* Leakage < 1% for non-harmonic bins.

**Usage:**

```bash
python Experiments/Tier1_Theory/E1_baseline_equivalence.py
```

**Outputs:**

* JSON with peak-bin deviations and harmonic map.
* Figures showing amplitude vs harmonic structure.

---

## E2 — Leakage Bound Regression (Radius Rule)

**Goal:** Fit/log-sweep across sequence lengths `L` to confirm the empirical bound:

[
R \approx 0.5 \log_2 L
]

This minimizes false positives (FP) without harming recall, validating the logarithmic leakage radius predicted in the formal theorem.

**Pass Criterion:**

* Zero (or near-zero) FP within that radius across windows and regimes.
* Consistent scaling law across 2–3 orders of magnitude of `L`.

**Usage:**

```bash
python Experiments/Tier1_Theory/E2_leakage_bounds_regression.py
```

**Outputs:**

* `E2_leakage_regression.json`: fitted curves, CI, and FP counts.
* Figures showing log-scale leakage falloff and best-fit slope.

---

## E3 — Phase Alignment Ablation (HIGH-SNR)

**Goal:** In HIGH-SNR regime (ρ < 0.146), demonstrate that **phase-aligned bases** outperform random or adversarial configurations by ≥8–12% precision.

This tests the coherence principle — whether VRA’s averaged spectra truly amplify aligned structure rather than random noise.

**Pass Criterion:**
[
\Delta_{precision}(aligned - random) \ge 0.08 \quad \text{and 95% CI > 0.}
]

**Usage:**

```bash
python Experiments/Tier1_Theory/E3_phase_alignment_ablation.py
```

**Outputs:**

* `E3_phase_alignment_results.json`: raw precision values.
* `E3_phase_alignment_summary.json`: CI, Δprecision, and pass/fail verdict.
* Optional figures showing precision distributions per configuration.

---

## Tier 1 Outcome

When all Tier 1 tests pass, we achieve:

* ✅ **Empirical equivalence** between spectral and modular periodicity.
* ✅ **Controlled leakage radius** following logarithmic scaling.
* ✅ **Proof of phase alignment advantage** under high-SNR conditions.

These establish the theoretical legitimacy of VRA’s spectral mechanics — forming the foundation for scaling, elliptic-curve extensions, and quantum-bridge experiments in Tiers 2–3.

---

**Next:** Proceed to [Tier 2 — Scaling and Generality](../Tier2_Scaling/README.md) to extend VRA into elliptic curve groups and multi-base √M scaling regimes.
