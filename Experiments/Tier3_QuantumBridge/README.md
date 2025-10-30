# Tier 3 — Quantum Bridge Experiments

This tier explores whether VRA can *reduce quantum resource needs* by supplying classical structure (priors/shortlists) to quantum post-processing.

## E7 — Shot Reduction Study (Pre-solver)

**Question.** If a lightweight VRA step proposes a shortlist of candidate periods, can a QPE-like decoder reach high confidence with fewer shots?

**Method.**
- Simulate shots: phases `θ ≈ k/r (mod 1)` with wrapped-Gaussian noise `σ`.
- Decode period via Bayesian inference over `r' ∈ [r_min, r_max]`.
- Compare:
  1) **Baseline** — uniform prior over `r'`.
  2) **VRA prior** — sparse shortlist prior (size `K`) that *includes the true `r` with probability `p_hit`* (parameters calibrated to your measured VRA precision / shortlist).

**Pass criterion.**
- Median required shots with VRA prior ≤ **0.7×** baseline, and the 95% paired-bootstrap CI for the ratio excludes `1.0`.

**Run.**
```bash
python Experiments/Tier3_QuantumBridge/E7_shot_reduction_qpe_prior.py \
  --r 168 --r-min 32 --r-max 1024 --sigma 0.02 \
  --trials 500 --target 0.90 --prior-hit 0.55 --prior-k 12 --save-csv
