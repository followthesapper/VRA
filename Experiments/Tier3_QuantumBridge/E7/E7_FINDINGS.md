# E7: Shot Reduction Study (QPE-like Bayesian Decoding) - Findings

**Experiment**: VRA-informed prior for Bayesian period decoding
**Date**: 2025-10-31
**Status**: ❌ **FAILED** - No shot reduction observed
**Runtime**: 62.2 minutes (200 trials, GPU-accelerated)

---

## Objective

Test whether a VRA-derived sparse prior over candidate periods can reduce the number of quantum measurement "shots" needed for confident period recovery in a QPE-like Bayesian decoding scenario.

**Goal**: Achieve **30-50% shot reduction** compared to uniform prior baseline.

**Pass Criterion**: Median ratio (VRA/Baseline) ≤ 0.70 AND 95% CI upper bound < 1.0

---

## Methodology

### Simulation Setup:
- **True period**: r = 168
- **Search space**: r' ∈ [32, 1024] (993 candidates)
- **Phase noise**: σ = 0.02 (wrapped Gaussian)
- **Confidence threshold**: 90% posterior probability
- **Max shots**: 10,000 per trial
- **Trials**: 200 Monte Carlo runs
- **Bootstrap**: 10,000 resamples for 95% CI

### Two Priors Compared:

**Baseline (Uniform)**:
- Flat prior over all 993 candidates
- No classical preprocessing

**VRA Prior (Sparse)**:
- Shortlist of 12 candidates (1.2% of search space)
- 55% hit rate (true r included 55% of time)
- Concentrated mass via softmax kernel
- Emulates VRA spectral peak detection

### Bayesian Decoder:
Each shot yields phase θ ≈ k/r (mod 1) with noise. Decoder updates posterior over candidates using wrapped-Gaussian likelihood until:
1. MAP estimate equals true r, AND
2. Posterior confidence ≥ 90%

**Stopping metric**: Number of shots to reach confidence threshold (or max_shots if not achieved).

---

## Results

### Quantitative Summary:

| Metric                     | Value        |
|----------------------------|--------------|
| **Median shots (Baseline)**| 10,000       |
| **Median shots (VRA)**     | 10,000       |
| **Shot reduction ratio**   | 1.000        |
| **95% CI (ratio)**         | [1.000, 1.000] |
| **Pass threshold**         | ≤ 0.70       |
| **Verdict**                | **❌ FAIL**  |

### Interpretation:

**ZERO SHOT REDUCTION** - Both approaches hit the max_shots cap (10,000) in all 200 trials.

**What this means**:
1. Neither baseline nor VRA prior could reach 90% confidence within 10,000 shots
2. VRA prior provided **no benefit** over uniform guessing
3. The problem was too hard for this regime's parameters

---

## Why E7 Failed

### 1. **Search Space Too Large**
- 993 candidates is enormous for Bayesian decoding
- Each shot provides only log₂(993) ≈ 10 bits of information
- 10,000 shots insufficient to disambiguate at 90% confidence

### 2. **VRA Hit Rate Too Low**
- 55% hit rate means **45% of trials had wrong shortlist**
- When true r absent, VRA prior actively misleads decoder
- Misled trials: worse than uniform (concentrated mass on wrong candidates)

### 3. **Shortlist Too Small**
- 12 candidates out of 993 (1.2% coverage)
- If true r missed, decoder has no fallback
- Uniform prior at least keeps all options open

### 4. **Phase Noise Too High**
- σ = 0.02 wraps significantly on unit circle
- Likelihood peaks spread out, reducing discrimination
- Need lower noise OR more shots for this search space

### 5. **Strict Confidence Threshold**
- 90% posterior confidence is ambitious
- With sparse prior + noise, achieving MAP=true_r is already hard
- Getting 90% concentrated mass requires many confirming shots

---

## Comparison to Goal

**Original Goal** (from project notes):
> "If E7 confirms 30–50% shot reduction in QPE... that's a practical quantum-classical hybrid breakthrough."

**Reality**:
- **Observed**: 0% reduction (ratio = 1.000)
- **Required**: 30% reduction (ratio = 0.70)
- **Shortfall**: Failed by 30 percentage points

**Conclusion**: **VRA did NOT demonstrate quantum shot reduction in this regime.**

---

## Scientific Implications

### For Quantum Computing Hybrid Algorithms:

**Negative Result - But Scientifically Valuable**:

1. **VRA isn't a universal shot-saver**
   - Shows limitations of classical preprocessing
   - Identifies boundary conditions where it fails

2. **Regime-dependent effectiveness**
   - Small search spaces: VRA might help
   - Large + noisy: VRA prior insufficient
   - Need tighter integration, not just "bolt-on" prior

3. **Hit rate is critical**
   - 55% hit rate too low for this application
   - Would need 80-90% to see benefits
   - Requires better VRA precision or different regimes

4. **Alternative approaches needed**
   - Adaptive priors (update shortlist after some shots)
   - Hierarchical search (coarse-to-fine)
   - Direct VRA-QPE circuit integration

### Does This Invalidate VRA for Quantum?

**NO** - but it narrows the applicability:

**What E7 shows**:
- VRA as a simple prior (one-time preprocessing) doesn't work for large noisy problems
- Current VRA precision (~55%) insufficient for blind QPE acceleration

**What E7 doesn't rule out**:
- VRA in smaller search spaces (r < 100)
- VRA with lower noise (σ < 0.01)
- Iterative VRA-QPE feedback loops
- VRA for coarse filtering + QPE for fine-tuning
- Hardware validation (real quantum noise different from Gaussian)

---

## Comparison to Literature

**Classical Order-Finding**:
- Pollard rho: O(√r) time, deterministic
- VRA: O(r log r) preprocessing, 55% success
- **E7 shows**: Even with VRA, Bayesian QPE doesn't beat classical in this regime

**Quantum Order-Finding (Shor)**:
- Polynomial shots with exponentially large search space
- VRA can't compete with quantum advantage
- **E7 confirms**: Classical preprocessing can't replace quantum parallelism

**Hybrid Quantum-Classical**:
- QAOA, VQE use classical optimization loops
- **E7 lesson**: Need tight integration, not loose coupling
- One-shot priors insufficient

---

## Recommendations

### For Future Quantum Work (E7 Follow-up):

**Option 1: Easier Regime**
- Reduce search space: r_max = 256 (225 candidates)
- Lower noise: σ = 0.01
- Expected: Might see 10-20% reduction

**Option 2: Better VRA Prior**
- Increase hit rate: Use higher-precision VRA (longer L, more M)
- Larger shortlist: K = 50 instead of 12
- Adaptive shortlist: Update after N shots

**Option 3: Iterative Hybrid**
- Phase 1: VRA narrows to top 100 candidates
- Phase 2: QPE on shortlist (not Bayesian sim)
- Phase 3: Refine with more VRA if needed

**Option 4: Accept Negative Result**
- Document as boundary condition
- Focus VRA on classical applications (E11-E16 showed promise there)
- Leave quantum to actual quantum advantage algorithms

### For Publication:

**Honest Reporting**:
- E7 is a **valuable negative result**
- Shows where VRA doesn't help (critical for credibility)
- Prevents over-claiming quantum applicability

**Framing**:
- "VRA as simple prior insufficient for large-scale QPE simulation"
- "Identifies regime boundaries for hybrid quantum-classical"
- "Motivates tighter VRA-QPE circuit integration"

**Don't hide this**:
- Negative results increase trust in positive results (E1-E6, E11-E16)
- Shows scientific rigor
- Opens research questions for future work

---

## Technical Deep Dive

### Why Median = 10000 for Both?

**In all 200 trials**:
- Decoder ran until max_shots = 10,000
- Never reached 90% confidence on true r
- This is a "saturation" failure mode

**Why saturation?**:
1. Likelihood spreads broadly due to noise
2. Posterior never concentrates enough
3. 10,000 shots insufficient for this SNR regime

### What Would Success Look Like?

**Baseline**: 7,000 shots median (some trials hit 10k cap)
**VRA**: 4,500 shots median (70% fewer saturations)
**Ratio**: 0.64 → PASS

**We saw**:
**Baseline**: 10,000 (100% saturation)
**VRA**: 10,000 (100% saturation)
**Ratio**: 1.00 → FAIL

### Can We Fix This?

**Short answer**: Yes, but not easily.

**Paths to success**:
1. **Reduce difficulty**: Smaller search space, less noise
2. **More shots**: Increase cap to 50,000 (expensive)
3. **Better prior**: 90% hit rate + larger shortlist
4. **Different stopping**: Accept 80% confidence instead of 90%
5. **Adaptive method**: Use early shots to refine shortlist

None of these are "free" - all have trade-offs.

---

## Figures

Generated figures show:

1. **CDF of shots**: Both curves saturate at 10,000 (vertical line at cap)
2. **Ratio histogram**: Single spike at 1.0 (all trials equal)

These visualizations confirm complete failure to reduce shots.

---

## Conclusion

**E7 Status**: ❌ **FAILED**

**Key Findings**:
1. VRA-derived sparse prior provided **zero shot reduction** (ratio = 1.000)
2. Both baseline and VRA saturated at max_shots = 10,000 in all trials
3. Problem regime too hard: 993 candidates, σ=0.02 noise, 90% confidence
4. VRA hit rate (55%) and shortlist size (12) insufficient for this scale

**Scientific Value**:
- **Important negative result** - shows VRA limitations
- Identifies boundary conditions for VRA-quantum hybrid
- Motivates tighter integration beyond simple priors

**Implications for Quantum Computing Goal**:
- **Did NOT achieve 30-50% shot reduction target**
- VRA as one-shot prior doesn't enable practical QPE acceleration in this regime
- Would need: smaller search spaces, higher VRA precision, or adaptive methods

**For Publication**:
- Report honestly as negative result
- Strengthens credibility of positive results elsewhere
- Opens future work: tighter VRA-QPE integration, easier regimes, adaptive hybrids

**Recommendation**:
- **Accept negative result** - focus VRA on classical ML/signal processing (E11-E16 successful)
- **Don't over-claim quantum**: VRA's strength is classical spectral analysis, not QPE replacement
- **Future work**: Investigate easier regimes (r < 100, σ < 0.01) or iterative hybrids

---

## Files Generated

- **Code**: `Experiments/Tier3_QuantumBridge/E7_shot_reduction_study.py`
- **Data**: `Data/Experiments/Tier3/E7/20251031_053104_E7_results_r168_sig0.02_T0.9_n200.json`
- **Figures**:
  - `Figures/experiments/Tier3/E7/20251031_053104_E7_shots_cdf_r168_sig0.02_T0.9.png`
  - `Figures/experiments/Tier3/E7/20251031_053104_E7_ratio_hist_r168_sig0.02.png`
- **Progress Log**: `/tmp/e7_progress.log` (200 trial records)

---

## Appendix: Parameter Justification

**Why these parameters?**

- **r=168**: From E1D validation (realistic VRA test case)
- **r_min=32, r_max=1024**: Realistic QPE search range (5-10 bits)
- **σ=0.02**: Moderate phase noise (2% of 2π ≈ 7.2°)
- **target=0.9**: Standard confidence threshold
- **prior_hit=0.55**: Based on VRA measured precision (~0.5)
- **prior_k=12**: Reasonable shortlist size (log₂(993) ≈ 10, k > log)
- **max_shots=10000**: Computational limit (each trial ~18s on GPU)

**Alternative parameters for future work**:
- **Easier**: r_max=256, σ=0.01, target=0.8, prior_hit=0.8, k=25
- **Harder**: r_max=2048, σ=0.03, target=0.95
- **Adaptive**: Start with k=5, expand to k=50 if needed

