# Tier 6 Quick Start Guide

**For researchers who want to run Tier 6 experiments immediately**

---

## TL;DR - Run Everything

```bash
cd /home/admin/dev/VRA/Experiments/Tier6_TheoryFirst

# Quick wins only (~30 minutes)
bash run_all_tier6.sh quick

# All implemented experiments (~3-4 hours)
bash run_all_tier6.sh full
```

Results will be saved to:
- **Data**: `/home/admin/dev/VRA/Data/Experiments/Tier6/`
- **Figures**: `/home/admin/dev/VRA/Figures/experiments/Tier6/`

---

## Individual Experiments

### T6-A2: Shot Reduction Bound (⭐⭐⭐ Quick Win)

**What it does**: Proves VRA priors reduce quantum measurement complexity

```bash
python T6A2_shot_reduction_bound.py
```

**Runtime**: ~10-15 minutes
**Output**: Shot ratio bound, statistical validation
**Impact**: Immediate quantum algorithm value

---

### T6-C1: VQE Term Grouping (⭐⭐ Quick Win)

**What it does**: Shows VRA coherence minimizes measurement variance

```bash
python T6C1_vqe_term_grouping.py
```

**Runtime**: ~10 minutes
**Output**: Variance reduction proof
**Impact**: VQE shots-efficiency

---

### T6-D1: Exoplanet Biosignature (⭐⭐ Quick Win)

**What it does**: Detection guarantees for multi-periodic signals

```bash
python T6D1_exoplanet_biosignature.py
```

**Runtime**: ~15-20 minutes
**Output**: Detection probability curves
**Impact**: Astrobiology applications

---

### T6-A1: Coherence Transition (⭐⭐⭐ High Impact, Intensive)

**What it does**: Models R̄ ≈ 0.137 as von Mises modular random process

```bash
python T6A1_coherence_transition.py
```

**Runtime**: ~2-4 hours (Monte Carlo intensive)
**Output**: von Mises model fit, R̄(ρ) curves
**Impact**: NEW SUBFIELD (modular random processes)

---

## Dependencies

```bash
pip install numpy scipy matplotlib sympy statsmodels scikit-learn

# Optional GPU acceleration
pip install cupy-cuda12x  # Adjust for your CUDA version
```

---

## File Structure

```
Tier6_TheoryFirst/
├── README.md                    # Overview & philosophy
├── TIER6_PLAN.md               # Detailed specs
├── TIER6_SUMMARY.md            # Results & status
├── QUICK_START.md              # This file
│
├── T6A1_coherence_transition.py          # ✅ Implemented
├── T6A2_shot_reduction_bound.py          # ✅ Implemented
├── T6C1_vqe_term_grouping.py             # ✅ Implemented
├── T6D1_exoplanet_biosignature.py        # ✅ Implemented
│
├── T6A2_FINDINGS.md            # Results template
├── T6B1-T6D4_*.py              # ⏳ Pending (7 more experiments)
│
└── run_all_tier6.sh            # Master execution script
```

---

## Interpreting Results

### PASS Criteria

Each experiment outputs:
- **JSON data**: Raw results
- **Figures**: 4-panel plots (theory vs empirical)
- **Verdict**: PASS/FAIL based on hypothesis test

**Example PASS**:
```
✓ PASS: Empirical shot ratio (0.42) ≤ 1.2 × bound (0.45)
```

### FAIL Criteria

**Example FAIL**:
```
✗ FAIL: Empirical ratio (0.95) > 1.2 × bound (0.45)
```

**Failures are valuable!** They identify boundaries and prevent overstated claims.

---

## Typical Workflow

1. **Run experiment**:
   ```bash
   python T6A2_shot_reduction_bound.py
   ```

2. **Check console output** for verdict (PASS/FAIL)

3. **Examine figures**:
   ```bash
   open ../../Figures/experiments/Tier6/T6A2/T6A2_shot_reduction_summary.png
   ```

4. **Read data**:
   ```python
   import json
   with open('../../Data/Experiments/Tier6/T6A2/T6A2_results.json') as f:
       results = json.load(f)
   print(results['verdict'])
   ```

5. **Document in findings**:
   - Open `T6A2_FINDINGS.md`
   - Fill in "Results" section with numbers
   - Update "Verdict" section
   - Add interpretation

---

## Troubleshooting

### Import Errors

```bash
# Missing VRA core
export PYTHONPATH=/home/admin/dev/VRA/Code:$PYTHONPATH

# Or add to ~/.bashrc
echo 'export PYTHONPATH=/home/admin/dev/VRA/Code:$PYTHONPATH' >> ~/.bashrc
```

### Long Runtimes

For T6-A1 (intensive):
- Reduce `n_samples_per_config` from 50 to 20
- Use fewer `N_primes` (test with just `[997, 2003]`)
- Consider GPU acceleration (if available)

### Out of Memory

- Reduce `L_values` (use max L=2^14 instead of 2^17)
- Process fewer trials (reduce `n_trials`)

---

## Expected Runtimes (Approximate)

| Experiment | Runtime | Intensity |
|------------|---------|-----------|
| T6-A2 | 10-15 min | Light |
| T6-C1 | 10 min | Light |
| T6-D1 | 15-20 min | Light |
| T6-A1 | 2-4 hours | **Heavy** |

**Total (all implemented)**: ~3-5 hours

---

## Next Steps After Running

### If All PASS

1. **Write papers**: Start with T6-A2 (quantum algorithms)
2. **Submit to arXiv**: Open-access preprints
3. **Target journals**: IEEE Quantum, PRX, Nature Quantum Info

### If Some FAIL

4. **Analyze failures**: Why did hypothesis break down?
5. **Refine models**: Adjust bounds, add corrections
6. **Document honestly**: Negative results are publishable

### If Many FAIL

7. **Pivot**: Focus on validated Tiers 1-5
8. **Boundaries**: Document limits of VRA applicability
9. **Lessons**: "We tested X rigorously, here's what doesn't work"

---

## Support

**Questions?**
- Read `TIER6_PLAN.md` for detailed specs
- Check `TIER6_SUMMARY.md` for status
- Consult main `README.md` for VRA overview

**Found a bug?**
- Check experiment code (Python files)
- Verify dependencies installed
- Review log files in `Data/Experiments/Tier6/`

---

**Last Updated**: October 31, 2025
**Status**: 4/11 experiments ready to run
**Estimated Total Time**: 3-5 hours for all implemented experiments
