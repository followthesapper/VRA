# VRA Scripts Directory

This directory contains utility scripts for running VRA analyses and experiments.

## Scripts

### `vra.py`
Main VRA command-line interface for interactive analysis.

**Usage:**
```bash
python Scripts/vra.py run --N 1009 --r 168 --M 1,4,8,16
python Scripts/vra.py examples
```

### `run_novelty_tests.py`
Master test runner for novelty validation experiments.

**Usage:**
```bash
# Quick test (uses cached results)
python Scripts/run_novelty_tests.py --quick --experiment E1

# Full test (runs complete comparison)
python Scripts/run_novelty_tests.py --experiment E1
```

### `REPRODUCE.py`
Automated reproduction script for all VRA experiments (E1-E27).

**Usage:**
```bash
# Run single experiment
python Scripts/REPRODUCE.py --experiment E1

# Run by category
python Scripts/REPRODUCE.py --category math    # E1-E3
python Scripts/REPRODUCE.py --category ai      # E11-E16
python Scripts/REPRODUCE.py --category theory  # E17-E27

# Run all experiments
python Scripts/REPRODUCE.py --all
```

## See Also

- **Documentation**: See [`../Docs/`](../Docs/) for all documentation
- **Code**: See [`../Code/`](../Code/) for VRA implementation
- **Tests**: See [`../Tests/`](../Tests/) for unit tests
