# VRA Figures Directory

Publication-quality visualizations of all VRA experimental results.

## Directory Structure

### [`Novelty/`](Novelty/)
**Novelty Validation Figures** (7 publication-quality figures, 300 DPI)

Figures proving VRA novelty vs. RPT baseline:
- `fig1_precision_by_regime.png` - Bar chart: VRA vs. RPT by regime
- `fig2_runtime_speedup.png` - Speedup histogram & boxplots
- `fig3_precision_vs_m.png` - Precision vs. M scaling curves
- `fig4_novelty_summary.png` - Overall summary card
- `fig_proof_summary.png` - Comprehensive statistical proof (CIs + p-values)
- `fig_permutation_tests.png` - Permutation test null distribution
- `fig_bootstrap_ci.png` - Bootstrap confidence intervals by regime

**Used in**: Paper (`Manuscript/vra_complete_paper.pdf`), novelty documentation

### [`Publication/`](Publication/)
**Publication-Ready Figures** - Formatted for journal/conference submission

### [`Experiments/`](Experiments/)
**Experimental Results Visualizations**

#### `Validation/`
- **Cross_Modulus/** - Extended moduli and boundary validation plots
  - Extended moduli overview
  - Regime boundary validation
  - Modulus type comparisons
- **Cross_Moduli/** - Cross-modulus regime maps and statistics
  - Baseline √M fits
  - Regime map (4 moduli)
  - Statistical comparisons

#### `Benchmarks/`
- **Performance/** - Runtime and performance benchmarks
  - Runtime comparisons across methods
  - Scaling with M
  - Success rate analysis

#### `Robustness/`
- **Noise_And_Adversarial/** - Robustness testing plots
  - Noise degradation curves
  - Adversarial base selection
  - Pathological orders
- **Statistical_Analysis/** - Bootstrap confidence intervals
  - Runtime comparison with CIs
  - VRA speedup analysis
  - Bootstrap methodology
  - CI width vs sample size

#### `Leakage/`
- **FP2_Leakage/** - FFT length robustness tests

## Figure Standards

All publication figures are:
- **Resolution**: 300 DPI minimum
- **Format**: PNG (with optional PDF/SVG)
- **Dimensions**: Optimized for IEEE two-column format
- **Fonts**: Consistent sizing, readable at 100% scale
- **Colors**: Colorblind-friendly palette

## Regeneration

To regenerate figures:
```bash
# Novelty figures
python Code/Baselines/Figures/novelty.py
python Code/Baselines/Figures/proof.py

# Experiment figures
python Code/Experiments/Robustness/generate_figures.py
python Code/Experiments/Robustness/generate_phase1_2_figures.py  # Cross_Modulus
python Code/Experiments/Benchmarks/generate_benchmark_figures.py  # Performance
python Code/Experiments/Robustness/generate_phase4_1_figures.py  # Noise_And_Adversarial
python Code/Experiments/Statistics/generate_phase4_2_figures.py  # Statistical_Analysis
```

## See Also

- **Data**: See [`../Data/`](../Data/) for underlying experimental data
- **Paper**: See [`../Manuscript/vra_complete_paper.pdf`](../Manuscript/vra_complete_paper.pdf)
- **Documentation**: See [`../Docs/Novelty/`](../Docs/Novelty/) for interpretation
