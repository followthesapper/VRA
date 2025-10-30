# VRA Theory Documentation

Complete formal proofs and theoretical framework for Vaca Resonance Analysis.

## Directory Structure

### [`Foundations/`](Foundations/)
Foundational VRA papers (formerly 0_Foundations):
- **VRA_SPECTRAL_FRAMEWORK.md** - Core spectral framework for modular dynamics
- **VSRA_QUANTUM_CORRESPONDENCE.md** - Quantum-classical correspondence

### [`Sqrt_M_Theorem/`](Sqrt_M_Theorem/)
√M Coherent Averaging Theorem (formerly 1_FP1_SqrtM_Theorem):
- **SQRTM_THEOREM_PROOF_PART_A.md** - LOW SNR regime proof
- **SQRTM_THEOREM_PROOF_PART_B.md** - HIGH SNR regime proof

### [`Leakage_Bounds/`](Leakage_Bounds/)
Logarithmic Leakage Bounds (formerly 2_FP2_Leakage_Bounds):
- **LEAKAGE_BOUNDS_PROOF.md** - Validated radius rule R = 0.5·log₂(L)

### [`Phase_Alignment/`](Phase_Alignment/)
Phase Alignment Criterion (formerly 3_FP3_Phase_Alignment):
- **PHASE_ALIGNMENT_PROOF.md** - Phase coherence and separation bounds

### [`Regime_Map/`](Regime_Map/)
Transition Regime Map (formerly 4_FP4_Regime_Map):
- **TRANSITION_REGIME_MAP.md** - Three-regime characterization

### [`Operating_Guide/`](Operating_Guide/)
Practical Operating Guide (formerly 5_Operating_Guide):
- **OPERATING_GUIDE.md** - Hands-on engineering handbook

## Reading Order

For researchers new to VRA, recommended reading order:

1. **Start**: `Foundations/VRA_SPECTRAL_FRAMEWORK.md` - Core concepts
2. `Sqrt_M_Theorem/` - Part A (LOW SNR), then Part B (HIGH SNR)
3. `Leakage_Bounds/LEAKAGE_BOUNDS_PROOF.md` - Precision guarantees
4. `Phase_Alignment/PHASE_ALIGNMENT_PROOF.md` - HIGH SNR requirements
5. `Regime_Map/TRANSITION_REGIME_MAP.md` - Complete characterization
6. **Practical**: `Operating_Guide/OPERATING_GUIDE.md` - How to use VRA

## Key Results Summary

- **√M Scaling**: C_M ∝ √M in target regimes (R² > 0.95)
- **Leakage Bounds**: R = 0.5·log₂(L) achieves 100% precision
- **Phase Alignment**: Required in HIGH-SNR (ρ < 0.146)
- **Regime Boundaries**: 0.146 and 0.263 (empirically validated)

## See Also

- **Novelty Validation**: See [`../Novelty/`](../Novelty/) for statistical proof
- **Paper**: See [`../../Manuscript/vra_complete_paper.pdf`](../../Manuscript/vra_complete_paper.pdf)
- **Code**: See [`../../Code/`](../../Code/) for implementation
