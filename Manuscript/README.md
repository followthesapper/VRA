# VRA Manuscript

This directory contains the complete manuscript for the paper:

**"Vaca Resonance Analysis (VRA): A Phase-Coherent Framework for Multiplicative Order Detection with Fundamental Coherence Limits---Verified on IBM Quantum Hardware (Brisbane, 127q)"**

## Files

### Main Manuscript
- **`vra_paper.pdf`** - Final publication-ready PDF (arXiv submission version)
- **`vra_paper.tex`** - LaTeX source with all mathematical corrections and clarifications

### Supporting Files
- **`references.bib`** - Bibliography database
- **`figures/`** - Directory containing all manuscript figures
- **`generate_figures.py`** - Python script to regenerate figures from experimental data
- **`Sections/`** - Legacy modular section files (archived structure)

### Archived Versions
All previous manuscript versions (v2, v3, v4, arxiv) are archived in `/Archive/Manuscript_Drafts/`

## Compilation

To compile the manuscript to PDF:

```bash
cd Manuscript
pdflatex vra_paper.tex
bibtex vra_paper
pdflatex vra_paper.tex
pdflatex vra_paper.tex
```

Or use the provided Makefile:
```bash
make manuscript
```

## Version History

- **Version 1.0** (November 3, 2025) - ArXiv submission version with:
  - Complete hardware validation (IBM Brisbane, 127-qubit Eagle r3)
  - √M scaling clarified as +3 dB/doubling in power SNR units
  - Fixed radius-law formula (R ≈ 2.0 bins at α=1.0, σ_bins=1.0)
  - Explicit V_φ = -2·ln(R̄) definition (von Mises circular statistics)
  - Ensemble size requirement: M ≥ 64 for <5% deviation from e⁻² law
  - Bootstrap 95% confidence intervals on all key measurements
  - Test matrix table (13 experiments, 16/17 passed)
  - Appendix C: Derivation of E{|S|²} coherence equation
  - Updated GitHub file paths for repository structure
  - Hardware-agnostic validation statement in Discussion

Previous versions archived in `/Archive/Manuscript_Drafts/`

## Citation

If you use this work, please cite:

```bibtex
@article{vaca2025vra,
  title={Vaca Resonance Analysis (VRA): A Phase-Coherent Framework for Multiplicative Order Detection with Fundamental Coherence Limits---Verified on IBM Quantum Hardware (Brisbane, 127q)},
  author={Vaca, Dylan},
  year={2025},
  note={arXiv preprint. Version 1.0},
  url={https://github.com/followthesapper/VRA}
}
```

## Key Clarifications and Corrections

This final version addresses all identified issues and potential replication pitfalls:

1. **√M Scaling Terminology**: Clarified as "+3 dB/doubling" in power SNR (not amplitude), with explicit note that amplitude SNR follows √M
2. **Radius-Law Formula**: Fixed to R ≈ 2.0 bins (was 1.8) with explicit derivation showing R = α/σ_bins = 1.0/0.5 = 2.0
3. **V_φ Definition**: Added explicit operational definition V_φ = -2·ln(R̄) following von Mises circular statistics to prevent implementation errors
4. **Ensemble Size Requirement**: Specified M ≥ 64 needed for convergence to e⁻² law (smaller M shows systematic upward bias from phase undersampling)
5. **von Mises vs Gaussian**: Added quantitative comparison showing <2% error for circular-to-linear variance conversion
6. **Confidence Intervals**: Added ±95% CI notation to all experimental results and figure captions
7. **Test Matrix**: Added comprehensive table showing 16/17 tests passed (94.1% validation rate)
8. **Appendix Derivation**: Added 3-line derivation of E{|S|²} = |A|²·[1 + (M-1)·R̄²]/M
9. **Numerical Precision**: Updated R² ≈ 1.000, slope ≈ 3.01 dB, V_φ = 4.02 ± 0.28 rad²
10. **Repository File Paths**: Updated all GitHub file references to match current repository structure

See commit `e^-2 Coherence Law Breakthrough` and subsequent commits for detailed change log.
