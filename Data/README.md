# VRA Data Directory

Experimental results and validation data for all VRA experiments.

## Directory Structure

### [`Novelty/`](Novelty/)
**VRA vs. RPT Comparison Data** - Statistical validation proving VRA novelty
- `e1_vra_vs_rpt_results.json` - 62 test cases comparing VRA to RPT baseline
- `e1_novelty_report.txt` - Statistical summary with bootstrap CIs
- `novelty_ci_report.txt` - Formal proof report with p-values

**Key Results**: VRA 51.6% vs. RPT 15.6% precision (3.3× advantage, p < 10⁻⁴)

### [`Experiments/`](Experiments/)
**Research Experiments and Validation Studies**

#### `Validation/`
- **phase1/** - Initial core validation (N=1009, multiple orders)
  - Baseline benchmarks
  - Extended moduli sweep
  - Regime boundary validation
- **baseline_reValidation/** - Corrected baseline tests after coherent averaging fix
- **cross_moduli/** - 4 moduli × 7 regimes validation
- **extended_moduli/** - Larger modulus testing
- **regime_boundaries/** - Boundary characterization
- **robustness_sweep/** - FFT length robustness
- **Benchmarks/** - Performance benchmarking data

#### `Robustness/`
- **phase4/** - Phase 4 robustness testing
  - **Adversarial_Tests/** - Attack resistance validation
  - **Noise_Injection/** - Noise immunity testing

#### `reproduced/`
- Independent reproduction attempt results

## Data Format

Most data files are JSON format with structure:
```json
{
  "N": 1009,
  "r": 168,
  "M": 4,
  "precision_vra": 1.0,
  "precision_rpt": 0.333,
  "regime": "TRANSITION"
}
```

## See Also

- **Figures**: See [`../Figures/`](../Figures/) for visualizations of this data
- **Code**: See [`../Code/Experiments/`](../Code/Experiments/) for data generation scripts
- **Documentation**: See [`../Docs/Novelty/`](../Docs/Novelty/) for analysis
