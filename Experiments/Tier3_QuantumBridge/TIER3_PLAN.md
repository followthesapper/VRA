# Tier 3: Quantum Bridge — Scientific Method Experimental Suite

**Goal**: Rigorously test whether VRA has genuine value for quantum computing through falsifiable experiments.

**Status**: E7A complete (negative result), E7B-E7G planned

---

## Overview

E7A showed that a one-shot VRA prior doesn't accelerate Bayesian QPE decoding in large noisy regimes (993 candidates, σ=0.02). This raised the question: **Is this a fundamental limitation or a narrow failure mode?**

The E7B-E7G suite systematically tests:
1. **Information feasibility** (E7B): Can shot reduction even exist theoretically?
2. **Realistic priors** (E7C): Does measured VRA data help vs. synthetic priors?
3. **Evidence accumulation** (E7D): Does VRA improve inference under fixed budget?
4. **Adaptive methods** (E7E): Can hierarchical decoding leverage VRA?
5. **Resource reduction** (E7F): Does VRA reduce qubits/depth/gates?
6. **Regime mapping** (E7G): Where does VRA help?

---

## E7A — Baseline: Shot Reduction Study ✅ COMPLETE

### Question
Can a VRA-derived sparse prior reduce quantum measurement shots needed for period recovery?

### Hypothesis
VRA prior (hit-rate 55%, shortlist 12/993) should reduce shots by ≥30% vs. uniform prior.

### Experiment
- **Parameters**: r=168, r∈[32,1024], σ=0.02, target=0.9, trials=200
- **Method**: Bayesian decoder with wrapped-Gaussian likelihood
- **Comparison**: Uniform prior vs. VRA sparse prior

### Results
- **Median shots (Baseline)**: 10,000 (max cap)
- **Median shots (VRA)**: 10,000 (max cap)
- **Ratio**: 1.000 (0% reduction)
- **95% CI**: [1.000, 1.000]
- **Verdict**: ❌ **FAILED**

### Conclusion
One-shot VRA prior provides ZERO benefit in this regime. Both methods saturated at max_shots, indicating problem is information-infeasible.

### Scientific Value
Honest negative result. Shows VRA isn't universally applicable to quantum. Opens questions: Is this fundamental or regime-specific?

---

## E7B — Information Feasibility Test 🔄 PLANNED

### Question
Is shot reduction **theoretically possible** under E7A's conditions, or is the task information-infeasible?

### Hypothesis
**Null hypothesis**: If mutual information per shot I(Θ;R) × 10,000 < H(R), then NO prior (including VRA) can reach 90% confidence → E7A's failure is fundamental, not VRA-specific.

**Alternative**: VRA prior increases I(Θ;R) enough to theoretically enable shot reduction.

### Experiment

**Method:**
1. Compute mutual information I(Θ;R) for both priors via Monte Carlo:
   - Sample (r, k, θ) tuples
   - Estimate p(θ|r) and p(θ)
   - I(Θ;R) = E[log(p(θ|r)/p(θ))]

2. Apply Fano's inequality to bound minimal shots:
   - H(R|Θ₁...Θₙ) ≤ H(P_error) + P_error·log(|R|-1)
   - Solve for n given P_error ≤ 0.10

3. Compare bounds for uniform vs. VRA priors

**Parameters:**
- r=168, r∈[32,1024], σ=0.02
- Monte Carlo samples: 100,000 per prior
- GPU-accelerated likelihood computation

**Pass Criteria:**
- **PASS**: VRA's Fano bound < 0.7 × Uniform's bound → theoretical potential exists
- **FAIL**: Both bounds ≫ 10,000 OR similar → E7A negative is fundamental

### Expected Outcomes

**If E7B PASSES:**
- VRA prior theoretically can help
- E7A failed due to parameter choices (noise too high, candidates too many)
- E7C-E7G should explore easier regimes

**If E7B FAILS:**
- Information-theoretic impossibility confirmed
- No prior can help in this regime
- VRA not at fault — task itself is infeasible
- E7C-E7G should test different regimes or abandon quantum claim

### Implementation
- **Code**: `E7B_information_feasibility.py`
- **Runtime**: ~5-10 minutes (GPU Monte Carlo)
- **Output**: Fano bounds, I(Θ;R) estimates, feasibility verdict

---

## E7C — Realistic VRA Prior Injection 🔄 PLANNED

### Question
Does using **measured VRA spectra** from E1-E6 (instead of synthetic prior_hit/prior_k) provide genuine Bayesian advantage?

### Hypothesis
Measured VRA spectral posteriors carry structure (near-multiples, harmonic peaks) that synthetic priors miss. Using real p(r) from VRA should reduce shots by ≥20% in tractable regimes.

### Experiment

**Method:**
1. Load actual VRA spectral data from E1-E6 for r=168:
   - Use peak heights, CFAR detections, spectral envelope
   - Normalize to valid prior p(r)

2. Re-run Bayesian decoder with:
   - **Exact wrapped likelihood**: ∑ₘ exp(-0.5·((θ - m/r')/σ)²) over all harmonics
   - NOT nearest-multiple approximation

3. Test multiple regimes:
   - **Easy**: r∈[32,256], σ=0.01
   - **Medium**: r∈[32,512], σ=0.015
   - **Hard**: r∈[32,1024], σ=0.02 (E7A baseline)

**Pass Criteria:**
- **PASS**: Median shot ratio < 0.8 with 95% CI < 1.0 in ≥1 regime
- **FAIL**: All ratios ≈ 1.0 → VRA structure doesn't correlate with QPE phases

### Implementation
- **Code**: `E7C_realistic_vra_prior.py`
- **Runtime**: ~30-45 minutes (3 regimes × 200 trials each)
- **Dependencies**: E1-E6 spectral JSON files

---

## E7D — Evidence Gain at Fixed Budget 🔄 PLANNED

### Question
Even if 90% confidence isn't reached, does VRA prior increase **posterior evidence** within the same shot budget?

### Hypothesis
After S=1000 shots, Bayes factor BF = p(r_true|θ₁...θₛ)/p(r_true) should be ≥2× higher under VRA prior.

### Experiment

**Method:**
1. Run decoder for exactly S shots (no early stopping)
2. Measure at S:
   - Posterior mass p(r_true|data)
   - Bayes factor BF
   - KL divergence from uniform: D_KL(p_S || p_uniform)

3. Compare distributions: VRA vs. Uniform

**Test regimes:**
- S ∈ {500, 1000, 2000, 5000}
- Same σ, r-range from E7C

**Pass Criteria:**
- **PASS**: Median BF ≥ 2× (+3 dB evidence) AND posterior mass ≥ 10× in ≥1 regime
- **FAIL**: Negligible lift → VRA doesn't help even pre-threshold

### Implementation
- **Code**: `E7D_evidence_gain_fixed_budget.py`
- **Runtime**: ~20 minutes (4 budgets × 100 trials)
- **Key metric**: Bayes factor distributions

---

## E7E — Hierarchical Coarse-to-Fine Decoding 🔄 PLANNED

### Question
Can VRA accelerate inference when used **adaptively** (coarse → fine) rather than as one-shot prior?

### Hypothesis
Two-stage decoder reduces total shots by ≥20%:
- Stage 1: VRA on coarse grid (steps of 4) → identify top 10%
- Stage 2: Refine only those candidates to full resolution

### Experiment

**Method:**
1. **Coarse stage** (S_c shots):
   - Test r' ∈ {32, 36, 40, ..., 1024} (249 candidates)
   - Accumulate posterior, keep top 10% mass

2. **Fine stage** (S_f shots):
   - Test full resolution within top-10% bins
   - Reach 90% confidence

3. Compare total shots (S_c + S_f) vs. baseline uniform on full grid

**Pass Criteria:**
- **PASS**: Total shots ≥ 20% fewer at equal confidence
- **FAIL**: No improvement or worse

### Implementation
- **Code**: `E7E_hierarchical_decoding.py`
- **Runtime**: ~40 minutes (200 trials)
- **Novel aspect**: Adaptive, not one-shot

---

## E7F — Quantum Resource Model Test 🔄 PLANNED

### Question
Even if shot counts don't drop, does VRA reduce **quantum resources** that matter (precision bits, gate depth, qubit count)?

### Hypothesis
VRA prior concentration allows ≥20% reduction in:
- Precision bits t (QPE register size)
- Max exponent range (controlled-U^(2^j) complexity)
- T-gate depth

### Experiment

**Method:**
1. Map prior entropy to required precision:
   - H(p_VRA) vs. H(p_uniform)
   - t ~ log₂(1/ε) where ε ~ confidence width

2. Estimate controlled-power range:
   - j_max needed to resolve within VRA's concentrated region
   - T-depth ~ ∑ 2^j for j ≤ j_max

3. Compare: Uniform vs. VRA resource requirements

**Pass Criteria:**
- **PASS**: ≥20% reduction in t OR T-depth OR qubit-time product
- **FAIL**: No resource advantage

### Implementation
- **Code**: `E7F_quantum_resource_model.py`
- **Runtime**: ~10 minutes (analytical + Monte Carlo)
- **Output**: Resource comparison table

---

## E7G — Regime Map (Phase Diagram) 🔄 PLANNED

### Question
Across what parameter ranges does VRA actually help?

### Hypothesis
There exists a "useful wedge" in (σ, r-range, hit-rate) space where E7C-E7F criteria hold.

### Experiment

**Method:**
1. Sweep parameter grid:
   - σ ∈ {0.005, 0.01, 0.015, 0.02, 0.03}
   - r-range ∈ {[32,128], [32,256], [32,512], [32,1024], [32,2048]}
   - VRA hit-rate ∈ {0.5, 0.7, 0.9} (from E1-E6 measured values)

2. For each cell, evaluate:
   - Shot ratio (E7C metric)
   - Evidence gain (E7D metric)
   - Resource reduction (E7F metric)
   - Information bound (E7B metric)

3. Produce color-coded heatmap: PASS / MARGINAL / FAIL

**Pass Criteria:**
- **PASS**: ≥1 cell shows shot ratio < 0.8 with resource advantage
- **FAIL**: Entire map is red (no useful regime)

### Implementation
- **Code**: `E7G_regime_map.py`
- **Runtime**: ~2-3 hours (75 cells × ~2 min each, GPU-parallelized)
- **Output**: Publication-ready phase diagram

---

## Meta-Analysis: What Do These Results Mean?

| Outcome                          | Interpretation                                                       |
|----------------------------------|----------------------------------------------------------------------|
| **E7B FAIL**                     | E7A negative is fundamental — info-theoretically impossible          |
| **E7B PASS + E7C FAIL**          | Theoretical potential exists, but VRA structure doesn't align        |
| **E7C PASS + E7D FAIL**          | VRA helps reach threshold but doesn't improve evidence efficiently   |
| **E7D PASS + E7E/F FAIL**        | Evidence improves but not enough for practical advantage             |
| **E7E or E7F PASS**              | VRA provides adaptive or resource-based quantum advantage            |
| **E7G shows nonempty wedge**     | VRA has limited but real applicability — map the frontier            |
| **E7G entirely red**             | VRA-quantum connection doesn't exist in any practical regime         |

---

## Success Metrics for Publication

### Strong Positive (VRA Enables Quantum Advantage)
- E7B PASS (theoretical feasibility confirmed)
- E7C PASS in ≥2 regimes (shot reduction demonstrated)
- E7D PASS (evidence accumulation superior)
- E7E or E7F PASS (adaptive/resource advantage)
- E7G shows clear regime boundaries

**Claim**: "VRA enables 20-40% shot reduction in low-noise, moderate-candidate-set regimes via adaptive hierarchical decoding."

### Honest Negative (VRA Doesn't Help Quantum)
- E7B FAIL in target regimes (info-infeasible)
- E7C FAIL across all tested regimes
- E7D shows no evidence advantage
- E7E/F show no adaptive/resource benefit
- E7G is entirely red

**Claim**: "VRA-derived priors do not provide measurable quantum advantage in QPE-like decoding across tested noise and candidate-set regimes. Negative result establishes boundary of classical preprocessing utility."

### Mixed (Regime-Dependent)
- E7B PASS in some regimes
- E7C PASS in narrow wedge (e.g., σ<0.01, r-range<256)
- E7E shows adaptive benefit in easy cases
- E7G shows small useful wedge

**Claim**: "VRA provides quantum advantage in limited regimes (low noise, small candidate sets). Establishes applicability frontier for hybrid quantum-classical algorithms."

---

## Implementation Timeline

| Experiment | Estimated Runtime | Dependencies | GPU Critical? |
|------------|-------------------|--------------|---------------|
| E7B        | 5-10 min          | None         | Yes           |
| E7C        | 30-45 min         | E1-E6 data   | Yes           |
| E7D        | 20 min            | E7C setup    | Yes           |
| E7E        | 40 min            | E7C setup    | Yes           |
| E7F        | 10 min            | None         | No            |
| E7G        | 2-3 hours         | E7B-E7F      | Yes (parallel)|

**Total**: ~4-5 hours GPU time for complete suite

---

## Files to Generate

### Code
- `E7B_information_feasibility.py`
- `E7C_realistic_vra_prior.py`
- `E7D_evidence_gain_fixed_budget.py`
- `E7E_hierarchical_decoding.py`
- `E7F_quantum_resource_model.py`
- `E7G_regime_map.py`

### Data
- `Data/Experiments/Tier3/E7B/` — Fano bounds, mutual information
- `Data/Experiments/Tier3/E7C/` — Shot ratios per regime
- `Data/Experiments/Tier3/E7D/` — Bayes factors, posterior mass
- `Data/Experiments/Tier3/E7E/` — Adaptive decoding results
- `Data/Experiments/Tier3/E7F/` — Resource comparison tables
- `Data/Experiments/Tier3/E7G/` — Phase diagram data

### Figures
- `Figures/experiments/Tier3/E7B/` — Information feasibility plots
- `Figures/experiments/Tier3/E7C/` — Shot ratio CDFs and histograms
- `Figures/experiments/Tier3/E7D/` — Bayes factor distributions
- `Figures/experiments/Tier3/E7E/` — Adaptive vs. one-shot comparison
- `Figures/experiments/Tier3/E7F/` — Resource reduction bar charts
- `Figures/experiments/Tier3/E7G/` — **PHASE DIAGRAM (publication centerpiece)**

### Documentation
- `E7B_FINDINGS.md` — Information-theoretic analysis
- `E7C_FINDINGS.md` — Realistic prior evaluation
- `E7D_FINDINGS.md` — Evidence accumulation results
- `E7E_FINDINGS.md` — Adaptive decoding assessment
- `E7F_FINDINGS.md` — Quantum resource analysis
- `E7G_FINDINGS.md` — Regime map interpretation
- `TIER3_SUMMARY.md` — Complete quantum bridge assessment

---

## Next Steps

1. **Run E7B first** (most fundamental — establishes if anything is possible)
2. If E7B passes, proceed with E7C-E7F
3. If E7B fails in all regimes, skip to E7G (broader sweep) or accept negative
4. Complete E7G regardless (maps the frontier)
5. Write comprehensive TIER3_SUMMARY.md with honest assessment

---

## Publication Strategy

### If Positive/Mixed
- Lead with E7G phase diagram showing useful wedge
- Detail E7C shot reduction in favorable regimes
- Discuss E7E adaptive methods as practical hybrid approach
- Position E7A negative as "boundary condition" (shows where it doesn't work)

### If Negative
- Lead with E7A + E7B demonstrating information-theoretic barrier
- Show E7C-E7F attempted multiple angles (thoroughness)
- E7G shows complete landscape (no useful wedge)
- Frame as "rigorous nullnegative establishes limits of classical preprocessing"

Either way: **Honest, rigorous, falsifiable science.**

---

## Key Insight

**This suite answers the question definitively**:
- Not "can we make E7 pass?"
- But "**where** (if anywhere) does VRA enable quantum advantage?"

The phase diagram (E7G) is the publication centerpiece — shows the complete landscape, whether it's empty or has useful regions.
