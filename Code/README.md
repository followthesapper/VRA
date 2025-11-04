# VRA Code Directory

Complete implementation of Vaca Resonance Analysis with core algorithms, applications, baselines, and utilities.

---

## Directory Structure

### [`VRA/`](VRA/)
**Core VRA Package** - Main phase-coherent spectral order detection implementation
- `core.py` - Core VRA algorithms and functions
- `uncertainty.py` - Uncertainty quantification and error analysis

### [`Applications/`](Applications/)
**User-Facing Tools** - Practical applications of VRA
- `vra_cli.py` - Interactive VRA command-line interface
- `rsa_quality_checker.py` - RSA parameter validation tool

### [`Baselines/`](Baselines/)
**Novelty Validation** - Comparison with state-of-the-art methods
- `rpt.py` - Ramanujan Periodicity Transform (RPT) implementation
- `comparison.py` - Head-to-head VRA vs. RPT comparison framework
- `statistical_tests.py` - Statistical analysis (bootstrap, permutation tests)
- `prove_novelty.py` - Formal novelty proof script (exit code 0 = NOVEL)
- `Figures/` - Novelty and proof figure generation

### [`Utils/`](Utils/)
**Shared Utilities** - Statistical and analysis utilities
- `bootstrap_utils.py` - Bootstrap confidence interval utilities
- `add_bootstrap_cis.py` - Add bootstrap CIs to existing results

### [`Scripts/`](Scripts/)
**Utility Scripts** - Convenience tools for reproducibility and experimentation
- `REPRODUCE.py` - Run any or all experiments (E1-E27) with verification
- `vra.py` - Simple command-line VRA analysis tool
- `run_novelty_tests.py` - Novelty validation test runner
- `setup.py` - Setup and configuration utilities

---

## Quick Start

### Run VRA Analysis
```bash
python Code/Scripts/vra.py --N 1009 --r 168 --M 4
```

### Run Experiments
```bash
# List all available experiments
python Code/Scripts/REPRODUCE.py --list

# Run specific experiment
python Code/Scripts/REPRODUCE.py --experiment E1

# Run all math experiments
python Code/Scripts/REPRODUCE.py --category math

# Run all experiments
python Code/Scripts/REPRODUCE.py --all
```

### Verify Novelty
```bash
python Code/Baselines/prove_novelty.py
# Exit code 0 = NOVEL, 2 = PARTIAL, 3 = NOT NOVEL
```

---

## Main Experiments Location

**Note**: Experimental code has been reorganized for better structure.

- **Main Experiments**: See [`../Experiments/`](../Experiments/) for E1-E27 systematic validation
- **Theoretical Suite**: See [`../Experiments/Theoretical_Suite/`](../Experiments/Theoretical_Suite/) for A1-L1 theoretical foundations

### Experiment Categories

| Category | Experiments | Location |
|----------|-------------|----------|
| **Mathematical Validation** | E1-E3 | `/Experiments/E{1-3}_*/` |
| **Elliptic Curve Extension** | E4-E5 | `/Experiments/E{4-5}_*/` |
| **Quantum Bridge** | E6-E7 | `/Experiments/E{6-7}_*/` |
| **Hybrid & Applied** | E8-E10 | `/Experiments/E{8-10}_*/` |
| **AI/ML Integration** | E11-E16 | `/Experiments/E{11-16}_*/` |
| **Theory-First Validation** | E17-E27 | `/Experiments/E{17-27}_*/` |
| **Theoretical Foundations** | A1-L1 | `/Experiments/Theoretical_Suite/` |

---

## Import Structure

```python
# Core VRA
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "Code" / "VRA"))
from core import (
    modular_sequence,
    phase_embed,
    compute_averaged_spectrum,
    validated_radius,
    multiplicative_order
)

# Baselines
from Code.Baselines.rpt import ramanujan_sum, detect_period_rpt
from Code.Baselines.comparison import evaluate_vra_vs_rpt_single
from Code.Baselines.statistical_tests import check_novelty_criteria

# Utilities
from Code.Utils.bootstrap_utils import bootstrap_confidence_interval
```

---

## REPRODUCE.py - Experiment Runner

The new `REPRODUCE.py` script (v2.0) provides easy experiment reproduction:

### Features
- ✅ Run any E1-E27 experiment by ID
- ✅ Run experiments by category (math, ecc, quantum, ai, theory)
- ✅ Run all experiments at once
- ✅ Quick validation mode
- ✅ Automatic result logging
- ✅ Experiment status tracking
- ✅ Timeout protection (10 minutes per experiment)

### Usage Examples

```bash
# List all experiments
python Code/Scripts/REPRODUCE.py --list

# Run single experiment
python Code/Scripts/REPRODUCE.py --experiment E1

# Run multiple experiments
python Code/Scripts/REPRODUCE.py --experiment E1 E3 E5

# Run all math experiments (E1-E3)
python Code/Scripts/REPRODUCE.py --category math

# Run all AI experiments (E11-E16)
python Code/Scripts/REPRODUCE.py --category ai

# Run all experiments
python Code/Scripts/REPRODUCE.py --all

# Quick validation (where supported)
python Code/Scripts/REPRODUCE.py --quick --category math
```

### Output
Results are saved to `Data/Reproducibility/reproduction_<timestamp>.json` with:
- Experiment ID and name
- Success/failure status
- Duration in seconds
- Error messages if failed
- Summary statistics

---

## Historical Code

Old experimental code has been archived to `/Archive/Code_Experiments_Historical/`:
- `Benchmarks/` - Early baseline comparisons (superseded by E11)
- `Leakage/` - Leakage bounds testing (superseded by E2, E9)
- `Regime_Map/` - Regime analysis (superseded by E17)
- `Robustness/` - Noise/adversarial tests (superseded by E9)
- `Sqrt_M/` - √M scaling tests (superseded by E3, E14)
- `Statistics/` - Statistical utilities (moved to Utils/)

---

## Development

### Adding New Experiments

To add a new experiment to REPRODUCE.py:

1. Create experiment folder: `/Experiments/E{N}_{Name}/`
2. Add script to `/Experiments/E{N}_{Name}/Code/`
3. Update `REPRODUCE.py` experiment catalog:
   ```python
   'E{N}': {
       'name': 'Experiment Name',
       'category': 'category',
       'script': 'script_name.py'
   }
   ```

### Running Tests

```bash
# Test REPRODUCE.py
python Code/Scripts/REPRODUCE.py --list  # Should list all experiments

# Verify VRA implementation (Replication Challenge)
cd Test_Vectors
python3 verify_test_vectors.py  # Should pass all 10 test vectors

# Test core VRA (unit tests)
cd Tests
python3 -m pytest test_vra_core.py -v  # Requires: pip install pytest

# Test novelty validation
python Code/Baselines/prove_novelty.py  # Exit code 0 = NOVEL
```

---

## Dependencies

### Core
```bash
pip install numpy scipy matplotlib
```

### GPU Acceleration (for E17-E27)
```bash
pip install cupy-cuda11x  # or cupy-cuda12x depending on CUDA version
```

### Quantum Experiments (E6-E7)
```bash
pip install qiskit
```

### ECC Experiments (E4-E5)
```bash
pip install ecdsa
```

---

## See Also

- **Experiments**: See [`../Experiments/`](../Experiments/) for all experimental code
- **Documentation**: See [`../Docs/`](../Docs/) for comprehensive documentation
- **Tests**: See [`../Tests/`](../Tests/) for unit tests
- **Test Vectors**: See [`../Test_Vectors/`](../Test_Vectors/) for replication challenge
- **Data**: See [`../Data/`](../Data/) for experimental results
- **Archive**: See [`../Archive/`](../Archive/) for historical code

---

## Citation

If you use the VRA code, please cite:

```bibtex
@software{vaca2025vra_code,
  author = {Vaca, Dylan},
  title = {VRA: Vaca Resonance Analysis Implementation},
  year = {2025},
  url = {https://github.com/followthesapper/VRA}
}
```

---

**Last Updated**: November 3, 2025
**Version**: 2.0 (Reorganized structure)
**Status**: Production-ready code with comprehensive experiment framework
