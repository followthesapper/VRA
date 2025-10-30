# VRA Code Directory

Complete implementation of Vaca Resonance Analysis with baselines, applications, and experiments.

## Directory Structure

### [`VRA/`](VRA/)
**Core VRA Package** - Main phase-coherent spectral order detection implementation
- `core.py` - Core VRA algorithms and functions
- `uncertainty.py` - Uncertainty quantification and error analysis

### [`Baselines/`](Baselines/)
**Novelty Validation** - Comparison with state-of-the-art methods
- `rpt.py` - Ramanujan Periodicity Transform (RPT) implementation
- `comparison.py` - Head-to-head VRA vs. RPT comparison framework
- `statistical_tests.py` - Statistical analysis (bootstrap, permutation tests)
- `prove_novelty.py` - Formal novelty proof script (exit code 0 = NOVEL)
- `Figures/` - Novelty and proof figure generation

### [`Applications/`](Applications/)
**User-Facing Tools** - Practical applications of VRA
- `vra_cli.py` - Interactive VRA command-line interface
- `rsa_quality_checker.py` - RSA parameter validation tool

### [`Experiments/`](Experiments/)
**Experimental Code** - Research experiments and validation studies
- `Sqrt_M/` - √M theorem validation experiments
- `Leakage/` - Leakage bounds robustness testing
- `Regime_Map/` - Regime boundary characterization
- `Robustness/` - Noise injection and adversarial tests
- `Benchmarks/` - Performance benchmarking vs. baseline methods
- `Statistics/` - Statistical analysis and bootstrapping utilities

## Quick Start

### Run VRA Analysis
```bash
python Applications/vra_cli.py --N 1009 --r 168 --M 4
```

### Verify Novelty
```bash
python Baselines/prove_novelty.py
# Exit code 0 = NOVEL, 2 = PARTIAL, 3 = NOT NOVEL
```

### Generate Figures
```bash
python Baselines/Figures/novelty.py
python Baselines/Figures/proof.py
```

## Import Structure

```python
# Core VRA
from Code.VRA.core import ...

# Baselines
from Code.Baselines.rpt import ramanujan_sum, detect_period_rpt
from Code.Baselines.comparison import evaluate_vra_vs_rpt_single
from Code.Baselines.statistical_tests import check_novelty_criteria
```

## See Also

- **Documentation**: See [`../Docs/`](../Docs/) for all documentation
- **Tests**: See [`../Tests/`](../Tests/) for unit tests
- **Scripts**: See [`../Scripts/`](../Scripts/) for utility scripts
- **Data**: See [`../Data/`](../Data/) for experimental results
