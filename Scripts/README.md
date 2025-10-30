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
Automated reproduction script for all VRA experiments.

**Usage:**
```bash
# Quick reproduction
python Scripts/REPRODUCE.py --quick

# Full reproduction
python Scripts/REPRODUCE.py
```

## See Also

- **Documentation**: See [`../Docs/`](../Docs/) for all documentation
- **Code**: See [`../Code/`](../Code/) for VRA implementation
- **Tests**: See [`../Tests/`](../Tests/) for unit tests
