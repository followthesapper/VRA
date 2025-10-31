# Tier 5: AI/ML Experiments - GPU Required

**STATUS**: ⚠️ GPU ENVIRONMENT SETUP REQUIRED

All Tier 5 experiments **REQUIRE GPU** and will **FAIL FAST** if GPU is not available.
No silent CPU fallback - this prevents accidental multi-day CPU runs.

---

## Current GPU Environment Status

```bash
$ python3 Experiments/Tier5_AI_ML/gpu_utils.py
```

**Hardware**: ✅ NVIDIA GB10 detected (CUDA 13.0)
**CuPy**: ❌ NumPy 2.x vs 1.x incompatibility
**PyTorch**: ❌ CPU-only version installed

---

## Setup Instructions

### Option 1: Fix Current Environment (Recommended)

The issue is NumPy 2.3.4 is incompatible with system SciPy compiled for NumPy 1.x.

**Fix**:
```bash
# In project root
pip install 'numpy<2' --upgrade

# Verify fix
python3 Experiments/Tier5_AI_ML/gpu_utils.py
```

### Option 2: Clean Virtual Environment

```bash
# Create fresh venv
python3 -m venv venv_gpu
source venv_gpu/bin/activate

# Install compatible NumPy first
pip install 'numpy<2'

# Install GPU libraries
pip install cupy-cuda12x  # Adjust for your CUDA version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install project dependencies
pip install -r requirements.txt

# Test
python3 Experiments/Tier5_AI_ML/gpu_utils.py
```

### Option 3: Docker (Isolation)

```bash
# TODO: Create Dockerfile with proper CUDA/CuPy/PyTorch stack
```

---

## GPU Environment Requirements

**Minimum**:
- NVIDIA GPU with Compute Capability ≥ 7.0
- CUDA 12.x or 13.x
- 8 GB GPU RAM (16 GB recommended)

**Software**:
- CuPy (for NumPy-like GPU arrays + FFT)
- OR PyTorch with CUDA support
- NumPy < 2.0 (for compatibility)

---

## Experiment Overview

### E11: VRA Features for Periodicity Detection
**Goal**: Benchmark VRA-derived features vs MUSIC/Goertzel on real datasets
**Datasets**: Audio (pitch), ECG/PPG, industrial vibration, grid frequency
**Success**: +3–5 dB effective SNR or +5–10% F1 at same latency
**GPU speedup**: 10–50× for large (M, L)

### E12: VRA Tokens for Transformers
**Goal**: Convert harmonic structure to compact tokens for neural networks
**Benchmarks**: Speech commands, machinery fault detection, ECG arrhythmia
**Success**: +1–2% accuracy or 30–50% fewer labeled samples
**GPU speedup**: Batch token generation 20–100× faster

### E13: Learned Phase Alignment
**Goal**: Recover √M scaling via lightweight parametric phase corrector
**Constraint**: Unsupervised (no labels for r)
**Success**: >50% of theoretical √M gain on ℤ*_N
**GPU speedup**: Gradient descent on GPU 50–200× faster

### E14: Phase-Aligned Stacking (Deterministic)
**Goal**: Validate phase alignment with L=Q·r, window=none
**Success**: +1–2 dB per doubling with proper alignment
**GPU speedup**: Batch FFT 10–30× faster

### E15: Base Selection Policy
**Goal**: Predict coherence R from cheap proxies, choose optimal bases
**Success**: +2–4 dB SNR over random base choice at fixed M
**GPU speedup**: Policy search/optimization 20–100× faster

### E16: L-Scaling Curve (Publication-Grade)
**Goal**: Replicate +18 dB per 4× with bootstrap CIs
**Success**: Clean figure with theory overlay (1/L²)
**GPU speedup**: Bootstrap resampling 50–200× faster

---

## Usage Pattern

All experiments follow this pattern:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from gpu_utils import check_gpu_available, GPURequiredError

def main():
    # FAIL FAST if no GPU
    try:
        cp = check_gpu_available('cupy')  # or 'torch'
    except GPURequiredError as e:
        print(e)
        sys.exit(1)

    # GPU-accelerated experiment code here
    ...

if __name__ == "__main__":
    main()
```

**Expected output when GPU not ready**:
```
❌ GPU not available or not working with CuPy: numpy.dtype size changed...
   Check: nvidia-smi
   Check: echo $CUDA_VISIBLE_DEVICES
```

Experiment **EXITS** immediately - no wasted CPU time.

---

## Performance Expectations

### CPU Baseline (what we want to avoid)
- M=64, L=131,072: ~5–10 minutes per trial
- 500 trials: **42–83 hours** (unacceptable)

### GPU Target
- Same workload: ~30–60 seconds per trial
- 500 trials: **4–8 hours** (acceptable)

**Speedup**: 10–100× depending on experiment

---

## Troubleshooting

### "NumPy dtype size changed"
**Cause**: NumPy 2.x incompatibility
**Fix**: `pip install 'numpy<2' --upgrade`

### "torch.cuda.is_available() = False"
**Cause**: CPU-only PyTorch installed
**Fix**: Reinstall with CUDA:
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### "CUDA out of memory"
**Cause**: GPU RAM exhausted
**Fix**: Reduce batch size M or sequence length L

### "GPURequiredError"
**Cause**: This is **intentional** - experiments need GPU
**Fix**: Follow setup instructions above

---

## Testing GPU Setup

```bash
# Test GPU utilities
python3 Experiments/Tier5_AI_ML/gpu_utils.py

# Expected output when working:
# ✅ GPU available: CuPy X.X.X, Compute Capability 12.1
# ✅ GPU available: PyTorch X.X.X, Device: NVIDIA GB10
# CuPy GPU test passed ✅
# PyTorch GPU test passed ✅
```

---

## File Structure

```
Tier5_AI_ML/
├── README.md              (this file)
├── gpu_utils.py           (GPU check + batch FFT utilities)
├── E11_vra_features.py    (VRA vs MUSIC/Goertzel)
├── E12_vra_tokens.py      (Transformer integration)
├── E13_learned_alignment.py (Phase alignment learning)
├── E14_phase_stacking.py  (Deterministic validation)
├── E15_base_selection.py  (Coherence-aware base choice)
└── E16_l_scaling.py       (Publication figure)

Data/Experiments/Tier5/
├── E11/  (benchmark results)
├── E12/  (token experiments)
├── E13/  (learned alignment)
├── E14/  (phase stacking)
├── E15/  (base selection)
└── E16/  (L-scaling curves)

Figures/Experiments/Tier5/
├── E11/  (SNR comparison plots)
├── E12/  (accuracy curves)
├── E13/  (alignment quality)
├── E14/  (SNR vs M)
├── E15/  (policy performance)
└── E16/  (L-scaling with CIs)
```

---

## Next Steps

1. **Fix GPU environment** (see Setup Instructions above)
2. **Verify with**: `python3 Experiments/Tier5_AI_ML/gpu_utils.py`
3. **Run experiments**: Each has `--help` with parameter grids
4. **Check results** in `Data/Experiments/Tier5/E*/`

---

**Last Updated**: 2025-10-30
**Status**: Infrastructure ready, awaiting GPU environment fix
