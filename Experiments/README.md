# VRA Experimental Program

This directory contains all experiments for validating and extending the Vaca Resonance Analysis framework across four research tiers.

## Quick Start

```bash
# Run all experiments
make all

# Run specific tier
make tier1    # Mathematical validation
make tier2    # Elliptic curve extension
make tier3    # Quantum bridge validation
make tier4    # Hybrid/applied studies
```

## Structure

```
Experiments/
├── Tier1_Theory/          # Mathematical foundations
│   ├── E1: Spectral-Order Equivalence
│   ├── E2: Leakage Bounds Regression
│   └── E3: Phase Alignment Ablation
├── Tier2_ECC/             # Elliptic curve groups
│   ├── E4: ECC Order Detection
│   └── E5: ECC Scaling Grid
├── Tier3_QuantumBridge/   # Classical-quantum correspondence
│   ├── E6: VRA vs QPE Patterns
│   └── E7: Shot Reduction Study
└── Tier4_HybridApplied/   # Real-world applications
    ├── E8: Semiprime Groundwork
    ├── E9: Noise & Jitter Map
    └── E10: Physics Signal Pilot
```

## Experiment Overview

### Tier 1: Mathematical Validation

**Goal**: Prove spectral-order equivalence theorem with explicit leakage bounds

- **E1**: Tests that VRA peaks correspond to subgroup orders k·L/r with validated radius
- **E2**: Validates radius rule R ≈ 0.5·log₂(L) minimizes false positives
- **E3**: Proves phase-aligned bases outperform random in HIGH-SNR regime

### Tier 2: Elliptic Curve Extension

**Goal**: Demonstrate VRA works on elliptic curve groups E(𝔽ₚ)

- **E4**: Detects subgroup order r using point-to-phase embedding
- **E5**: Tests √M concentration scaling across different curves and regimes

### Tier 3: Quantum Bridge

**Goal**: Show VRA mirrors quantum period-finding interference patterns

- **E6**: Compares VRA spectral peaks to simulated QPE distributions
- **E7**: Proves VRA priors reduce quantum shot requirements by 5-10×

### Tier 4: Hybrid & Applied

**Goal**: Explore computational and physical applications

- **E8**: Profiles semiprime structure without factor leakage
- **E9**: Maps precision across noise/jitter parameter space
- **E10**: Tests VRA on physics-inspired oscillatory signals

## Output Structure

Each experiment produces:
- `Data/Experiments/tierN/eN/*.json` - Numerical results
- `Figures/Experiments/tierN/*.png` - Visualizations
- Console summary with pass/fail criteria

## Success Criteria

| Tier | Experiment | Passing Threshold |
|------|-----------|-------------------|
| 1    | E1        | Precision ≥ 0.98 (TRANS/LOW), ≥ 0.85 (HIGH) |
| 1    | E2        | FP ≈ 0 at validated radius |
| 1    | E3        | Δprecision ≥ 0.08 (95% CI > 0) |
| 2    | E4        | Precision ≥ 0.95 (TRANS/LOW), ≥ 0.80 (HIGH) |
| 2    | E5        | R² ≥ 0.90 for √M fit (TRANS/LOW) |
| 3    | E6        | Spearman ρ ≥ 0.8 |
| 3    | E7        | Shot ratio ≤ 0.7 (CI upper bound < 1) |
| 4    | E8        | No factor leakage |
| 4    | E9        | 100% precision in safe regions |
| 4    | E10       | Better precision vs periodograms |

## Requirements

```bash
pip install numpy matplotlib scipy
```

## Citation

If you use these experiments, please cite:

```bibtex
@software{vaca2025vra_experiments,
  author = {Vaca, Dylan},
  title = {VRA Experimental Validation Suite},
  year = {2025},
  url = {https://github.com/followthesapper/VRA}
}
```

## Troubleshooting

**Import errors**: Ensure you're running from VRA root or Experiments/ directory

**Long runtimes**: E1, E2, E9 test many cases; use `--quick` flag where available

**Missing dependencies**: Check `requirements.txt` in repo root

## Contact

Issues/questions: Open a GitHub issue at https://github.com/followthesapper/VRA
