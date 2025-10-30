# Contributing to VRA

Thank you for your interest in contributing to Vaca Resonance Analysis (VRA)! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Issues

If you find a bug, have a question, or want to suggest an enhancement:

1. Check if the issue already exists in the [GitHub Issues](https://github.com/followthesapper/VRA/issues)
2. If not, open a new issue with a clear title and description
3. Include:
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
   - Your environment (Python version, OS, etc.)
   - Relevant code snippets or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:

1. Open an issue with the "enhancement" label
2. Describe the proposed feature and its use case
3. Explain why this enhancement would be useful
4. Include examples if possible

### Pull Requests

We welcome pull requests! Here's the process:

1. **Fork the repository** and create a new branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the existing code style
   - Add tests if applicable
   - Update documentation as needed

3. **Test your changes**
   ```bash
   make test
   ```

4. **Commit your changes** with clear, descriptive messages
   ```bash
   git commit -m "Add feature: brief description"
   ```

5. **Push to your fork** and submit a pull request
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Describe your PR** clearly
   - What problem does it solve?
   - What changes were made?
   - How was it tested?

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/followthesapper/VRA.git
   cd VRA
   ```

2. Install dependencies:
   ```bash
   make install
   ```

3. Run tests:
   ```bash
   make test
   ```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and modular
- Comment complex algorithms

Example function format:
```python
def compute_concentration(mag2):
    """Compute concentration ratio.

    Parameters:
        mag2 (numpy.ndarray): Power spectrum

    Returns:
        float: C = max(|S|^2) / sum(|S|^2)
    """
    return np.max(mag2) / np.sum(mag2)
```

## Testing

- Add tests for new features
- Ensure existing tests pass
- Include edge cases and error conditions
- Use descriptive test names

## Documentation

When contributing, please update:

- Code docstrings
- README.md (if adding major features)
- Operating Guide (if changing user-facing behavior)
- Examples in `vra.py examples` (if relevant)

## Areas for Contribution

### High Priority

1. **Cross-modulus validation**
   - Test with N=997, N=1013, N=2017
   - Validate regime boundaries hold across moduli

2. **Uncertainty quantification**
   - Bootstrap confidence intervals for √M fits
   - Sensitivity analysis for regime boundaries

3. **Additional windows**
   - Implement Tukey, Kaiser, and other window functions
   - Compare performance across window types

4. **Performance optimization**
   - Profile and optimize hot paths
   - Parallelize base iterations
   - Implement caching for repeated computations

### Medium Priority

5. **Visualization improvements**
   - Interactive plots
   - Better figure generation pipeline
   - Publication-quality figure templates

6. **CLI enhancements**
   - Progress bars for long computations
   - Verbose/debug modes
   - Configuration file support

7. **Documentation**
   - More examples
   - Tutorial notebooks
   - Video walkthroughs

### Research Extensions

8. **Noise robustness**
   - Test under additive/multiplicative noise
   - Characterize SNR degradation

9. **Composite moduli**
   - Extend theory to non-prime N
   - Test on RSA-like moduli

10. **Quantum correspondence**
    - Implement quantum circuit simulator
    - Direct VSRA comparisons

## Questions?

- Open a [GitHub Issue](https://github.com/followthesapper/VRA/issues)
- Check the [Operating Guide](5_Operating_Guide/OPERATING_GUIDE.md)
- Review existing documentation in the formal proofs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be acknowledged in:
- The repository contributors list
- Future publications (for significant contributions)
- Release notes

Thank you for helping improve VRA!
