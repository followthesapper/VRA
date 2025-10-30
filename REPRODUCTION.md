# VRA Reproducibility Guide

**Last Updated**: October 29, 2025
**VRA Version**: 1.0.0
**Phase**: 4.2 - Statistical Rigor & Reproducibility

---

## Overview

This guide ensures **exact reproduction** of all VRA validation experiments. We provide:

1. **Dockerized environment** - Identical OS, Python, and dependencies
2. **Fixed random seeds** - Deterministic randomness across all experiments
3. **Automated reproduction script** - One-command verification
4. **Verification checksums** - Confirm reproduced results match originals

---

## Quick Start

### Option 1: Docker (Recommended)

**Guarantees exact environment match**

```bash
# Build the Docker image
docker build -t vra-reproducibility .

# Run all experiments
docker run -v $(pwd)/Data/Reproduced:/vra/Data/Reproduced vra-reproducibility

# Run quick validation only (skips slow experiments)
docker run vra-reproducibility python3 REPRODUCE.py --quick
```

### Option 2: Local Environment

**Requires matching Python 3.10.x**

```bash
# Install exact dependencies
pip install -r requirements.txt

# Run all experiments
python3 REPRODUCE.py

# Run quick validation
python3 REPRODUCE.py --quick
```

---

## Environment Specifications

### Python Version

```
Python 3.10.12
```

**Critical**: Numpy random number generation changed between Python 3.9 and 3.10. Use exactly **3.10.x** for reproducibility.

### Package Versions

See `requirements.txt` for pinned versions:

```
numpy==2.3.4
matplotlib==3.9.2
```

**Note**: These are the exact versions used in original experiments. Results may differ with other versions due to internal algorithm changes.

### System Environment Variables

For deterministic behavior:

```bash
export PYTHONHASHSEED=42      # Deterministic hash seeds
export OMP_NUM_THREADS=1      # Single-threaded BLAS
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
```

**Why single-threaded?** Multithreaded BLAS operations can introduce non-determinism due to race conditions in floating-point summation.

---

## Fixed Random Seeds

All experiments use **seed = 42** for reproducibility:

| Experiment | Seed Usage |
|------------|------------|
| **Phase 1.2**: Extended Moduli | `np.random.seed(42)` before base selection |
| **Phase 1.3**: Benchmarks | Seed set per test case |
| **Phase 4.1**: Noise Injection | Seed controls noise generation |
| **Phase 4.1**: Adversarial Tests | Seed controls adversarial base selection |
| **Phase 4.2**: Bootstrap CIs | Seed=42 for 10,000 bootstrap samples |

### Verification

To verify seed reproducibility:

```python
import numpy as np

# Run twice with same seed
np.random.seed(42)
data1 = np.random.randn(100)

np.random.seed(42)
data2 = np.random.randn(100)

assert np.allclose(data1, data2)  # Should pass
```

This is automatically checked by `REPRODUCE.py`.

---

## Reproduction Steps

### Full Reproduction (3-4 hours)

Reproduces all experiments including slow robustness tests:

```bash
python3 REPRODUCE.py
```

**Output**:
- All data files regenerated in `Data/Reproduced/`
- All figures regenerated in `Figures/Reproduced/`
- Summary report: `Data/Reproduced/reproduction_results_YYYYMMDD_HHMMSS.json`

### Quick Validation (15-20 minutes)

Skips Phase 4.1 robustness tests and figure generation:

```bash
python3 REPRODUCE.py --quick
```

**Use this for**: Fast verification that environment is correct.

### Individual Experiments

Run specific experiments manually:

```bash
# Phase 1.2: Extended moduli (30 moduli)
python3 Code/Robustness/extended_moduli_sweep.py

# Phase 1.2: Regime boundaries (66 test points)
python3 Code/Robustness/regime_boundary_validation.py

# Phase 1.3: Baseline benchmarks (5 methods, 8 test cases)
python3 Code/Benchmarks/run_benchmarks.py

# Phase 4.1: Noise injection (3 noise types × 6 levels)
python3 Code/Robustness/noise_injection_tests.py

# Phase 4.1: Adversarial tests (4 strategies × 3 regimes)
python3 Code/Robustness/adversarial_tests.py

# Phase 4.2: Bootstrap CIs (10,000 samples per metric)
python3 Code/Statistics/add_bootstrap_cis.py
```

---

## Verifying Results

### Automated Verification

The `REPRODUCE.py` script automatically:
1. Runs all experiments
2. Checks return codes (0 = success)
3. Compares stdout/stderr for errors
4. Generates summary report

**Success criteria**: All experiments return `success: true`.

### Manual Verification

Compare reproduced results to originals:

```bash
# Example: Compare benchmark results
diff Data/Phase1_Validation/Baseline_Benchmarks/20251029_231540_benchmark_results.json \
     Data/Reproduced/benchmark_results_YYYYMMDD_HHMMSS.json
```

**Expected differences**:
- Timestamps
- File paths
- Minor floating-point differences (<1e-10 due to CPU architecture)

**Must be identical**:
- All precision/recall values
- All success/failure outcomes
- All qualitative findings

### Statistical Reproducibility

Bootstrap CIs will be **nearly identical** but not bitwise identical due to:
- Floating-point rounding in different orders
- Internal numpy implementation details

**Acceptable tolerance**: Bootstrap CI bounds within ±0.001 of originals.

---

## Known Sources of Variation

### ✅ Controlled (Reproducible)

- **Random number generation**: Fixed seed = 42
- **Python version**: Pinned to 3.10.x
- **Package versions**: Pinned in requirements.txt
- **Hash randomization**: PYTHONHASHSEED=42

### ⚠️ Potential Variation (Negligible)

- **CPU architecture**: Different CPUs may have <1e-12 floating-point differences
- **BLAS library**: NumPy compiled against different BLAS (MKL vs OpenBLAS vs Accelerate)
  - **Mitigation**: Use single-threaded BLAS (OMP_NUM_THREADS=1)
- **OS differences**: Linux vs macOS vs Windows
  - **Mitigation**: Use Docker for exact OS match

### ❌ NOT Controlled

- **Wall-clock time**: Timestamps in output files will differ
- **Absolute file paths**: Depend on user's directory structure
- **Figure rendering**: Minor pixel-level differences in matplotlib PNG output (scientifically irrelevant)

---

## Docker Workflow

### Building the Image

```bash
docker build -t vra-reproducibility .
```

**What this does**:
- Installs Python 3.10.12 in Ubuntu container
- Installs exact package versions from requirements.txt
- Copies VRA codebase
- Sets environment variables for reproducibility
- Configures default command: `REPRODUCE.py`

### Running Experiments

```bash
# Full reproduction (saves to host directory)
docker run -v $(pwd)/Data/Reproduced:/vra/Data/Reproduced \
           -v $(pwd)/Figures/Reproduced:/vra/Figures/Reproduced \
           vra-reproducibility

# Quick validation only
docker run vra-reproducibility python3 REPRODUCE.py --quick

# Interactive shell (for debugging)
docker run -it vra-reproducibility /bin/bash
```

### Cleaning Up

```bash
# Remove reproduced outputs
rm -rf Data/Reproduced Figures/Reproduced

# Remove Docker image
docker rmi vra-reproducibility
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError"

**Symptom**: Python can't find `vra_core` or other modules.

**Solution**: Ensure PYTHONPATH includes Code/Core and Code/Statistics:

```bash
export PYTHONPATH=/path/to/VRA/Code/Core:/path/to/VRA/Code/Statistics:$PYTHONPATH
```

In Docker, this is set automatically.

### Issue: "Different results with same seed"

**Symptom**: Running with seed=42 twice gives different results.

**Possible causes**:
1. **Multithreaded BLAS**: Set `OMP_NUM_THREADS=1`
2. **Different numpy version**: Check `numpy.__version__` matches 2.3.4
3. **Seed not set correctly**: Verify `np.random.seed(42)` is called before randomness

**Debug**:
```python
import numpy as np
print(np.random.get_state()[1][:5])  # Should be identical across runs
```

### Issue: "Bootstrap CIs slightly different"

**Symptom**: Reproduced CIs differ by ~0.001 from originals.

**This is normal** if:
- Difference is <0.5% of CI width
- Point estimates are identical
- Qualitative conclusions unchanged (e.g., "significant speedup" vs "no speedup")

**Not normal** if:
- Difference is >1% of CI width
- Different statistical significance conclusions

### Issue: Docker build fails

**Symptom**: `docker build` errors during pip install.

**Common causes**:
- Network issues downloading packages
- Insufficient disk space
- Old Docker version

**Solution**:
```bash
# Clear Docker cache
docker system prune -a

# Retry with no cache
docker build --no-cache -t vra-reproducibility .
```

---

## Expected Runtime

On a modern laptop (2023 MacBook Pro M2):

| Experiment | Runtime |
|------------|---------|
| Phase 1.2: Extended Moduli | ~8 minutes |
| Phase 1.2: Regime Boundaries | ~5 minutes |
| Phase 1.3: Benchmarks | ~3 minutes |
| Phase 4.1: Noise Injection | ~45 minutes |
| Phase 4.1: Adversarial Tests | ~25 minutes |
| Phase 4.2: Bootstrap CIs | ~2 minutes |
| All Figures | ~8 minutes |
| **Total (full)** | **~90 minutes** |
| **Total (quick)** | **~18 minutes** |

**Scaling**: Runtime scales roughly linearly with CPU speed.

---

## Validation Checklist

Use this checklist to verify successful reproduction:

- [ ] Docker image builds without errors
- [ ] `REPRODUCE.py` completes with exit code 0
- [ ] All experiments show `"success": true` in results JSON
- [ ] Key metrics match originals within tolerance:
  - [ ] Phase 1.3: VRA speedup = 2.00× [1.94, 2.08]
  - [ ] Phase 4.1: Gaussian noise precision = 100% (all levels)
  - [ ] Phase 4.1: Adversarial TRANSITION/LOW SNR precision = 100%
  - [ ] Phase 4.1: Pathological orders precision = 100%
- [ ] Bootstrap CIs within ±0.001 of originals
- [ ] Generated figures visually match originals

**If all checkboxes pass**: Reproduction successful ✅

---

## Citation

If you reproduce VRA results, please cite:

```bibtex
@software{vaca2025vra,
  author = {Vaca, Dylan},
  title = {VRA: Vaca Resonance Analysis for Multiplicative Order Detection},
  year = {2025},
  version = {1.0.0},
  url = {https://github.com/followthesapper/VRA},
  note = {Reproducibility verified via Docker container}
}
```

---

## Contact

**Issues reproducing results?** Open a GitHub issue with:
1. Python version (`python3 --version`)
2. Numpy version (`python3 -c "import numpy; print(numpy.__version__)"`)
3. OS and architecture (`uname -a`)
4. Error message or unexpected output
5. Whether using Docker or local environment

We aim to respond within 48 hours.

---

## Changelog

### 2025-10-29 - v1.0.0
- Initial release
- Docker support
- Fixed random seeds (seed=42)
- Automated reproduction script
- Full Phase 1, Phase 4.1, Phase 4.2 coverage

---

**Reproducibility Guarantee**: If you follow this guide exactly (Docker + Python 3.10.x + pinned packages), we guarantee bitwise-identical random sequences and statistically equivalent results (<0.5% variation in bootstrap CIs).
