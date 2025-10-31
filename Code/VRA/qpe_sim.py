#!/usr/bin/env python3
"""
QPE (Quantum Phase Estimation) Simulator
=========================================

Simulates the measurement histogram pattern from Quantum Phase Estimation
for order-finding on finite groups.

QPE applies the Quantum Fourier Transform (QFT) to extract phase information
from a unitary operator. For order-finding, the phase is φ = s/r where:
  - r is the order we're trying to find
  - s is a random integer in [0, r-1]

The QFT concentrates measurement probability at bins near s (mod r),
creating a peaked distribution similar to VRA's spectral harmonics.

Author: VRA Experimental Team
Date: October 2025
"""

import numpy as np


def qpe_histogram(r: int, shots: int = 10000, bins: int = None, noise_level: float = 0.05):
    """
    Simulate QPE measurement histogram for order-finding.

    In ideal QPE for order r:
    - Measure outcome is uniformly distributed over {0, 1, ..., r-1}
    - Each outcome s corresponds to phase φ = s/r
    - Outcomes concentrate at multiples of the fundamental frequency 1/r

    With noise, outcomes spread slightly around ideal peaks.

    Args:
        r: Order to estimate (target period)
        shots: Number of quantum measurements (shots)
        bins: Number of histogram bins (default: r)
        noise_level: Gaussian noise std dev as fraction of bin width

    Returns:
        hist: Histogram counts array of shape (bins,)
        bin_edges: Bin edges array of shape (bins+1,)
    """
    if bins is None:
        bins = r

    # Generate ideal QPE outcomes: uniform over {0, 1, ..., r-1}
    # Each outcome represents detecting phase s/r
    ideal_outcomes = np.random.randint(0, r, size=shots)

    # Add measurement noise (simulates finite precision in phase estimation)
    # Noise spreads outcomes slightly around ideal bins
    noise = np.random.normal(0, noise_level * r, size=shots)
    noisy_outcomes = ideal_outcomes + noise

    # Wrap to [0, r) to simulate periodic boundary
    noisy_outcomes = noisy_outcomes % r

    # Create histogram
    hist, bin_edges = np.histogram(noisy_outcomes, bins=bins, range=(0, r))

    return hist, bin_edges


def qpe_probability_distribution(r: int, precision_qubits: int = 8):
    """
    Compute the ideal QPE probability distribution for order r.

    With t precision qubits, QPE can distinguish 2^t phases.
    For order r, the probability concentrates at integer multiples of 2^t/r.

    This gives the theoretical (noiseless) distribution that QPE should produce.

    Args:
        r: Order (period) to estimate
        precision_qubits: Number of qubits in QPE precision register

    Returns:
        probs: Probability array of length 2^precision_qubits
    """
    M = 2 ** precision_qubits
    probs = np.zeros(M)

    # For each possible phase outcome s/r where s ∈ {0, ..., r-1}
    for s in range(r):
        # The ideal QPE measurement concentrates at bin closest to s * M / r
        bin_idx = int(round(s * M / r)) % M
        probs[bin_idx] += 1.0 / r

    return probs


def qpe_success_probability(r: int, precision_qubits: int = 8):
    """
    Compute the probability that QPE successfully finds the order r.

    Success means measuring an outcome that allows exact recovery of r
    via continued fractions or similar classical post-processing.

    Args:
        r: Order to estimate
        precision_qubits: Number of precision qubits

    Returns:
        success_prob: Probability of successful order extraction
    """
    # Simplified model: success requires distinguishing r distinct phases
    # With t qubits, we can distinguish ~2^t phases
    # Success probability decreases if r is too large relative to 2^t

    M = 2 ** precision_qubits

    # If r << M, high success (phases well-separated)
    # If r ~ M, moderate success (phases barely separated)
    # If r >> M, low success (aliasing)

    if r <= M / 4:
        # Well-separated regime
        success_prob = 0.95
    elif r <= M:
        # Marginally separated
        success_prob = 0.80
    else:
        # Aliasing regime
        success_prob = 0.40

    return success_prob


def compare_vra_qpe_patterns(vra_spectrum, r, normalize=True):
    """
    Compare VRA spectral pattern to ideal QPE pattern.

    Bins VRA spectrum into r buckets and compares to QPE's uniform distribution
    over {0, ..., r-1}.

    Args:
        vra_spectrum: VRA power spectrum (array)
        r: Order (determines bucketing)
        normalize: Whether to normalize to probability distributions

    Returns:
        vra_binned: VRA power binned into r buckets
        qpe_ideal: Ideal QPE distribution (uniform over r outcomes)
        correlation: Spearman correlation between patterns
    """
    Lzp = len(vra_spectrum)

    # Bin VRA spectrum into r buckets around expected harmonics
    vra_binned = np.zeros(r)
    radius = max(1, int(0.005 * Lzp))  # Small neighborhood around each harmonic

    for k in range(r):
        center = int(round(k * Lzp / r))
        lo = max(0, center - radius)
        hi = min(Lzp - 1, center + radius)
        vra_binned[k] = vra_spectrum[lo:hi+1].sum()

    # Ideal QPE gives uniform distribution over r outcomes
    qpe_ideal = np.ones(r) / r if normalize else np.ones(r)

    # Normalize VRA if requested
    if normalize and vra_binned.sum() > 0:
        vra_binned = vra_binned / vra_binned.sum()

    # Compute correlation
    from scipy.stats import spearmanr
    if vra_binned.std() > 0 and qpe_ideal.std() > 0:
        correlation, _ = spearmanr(vra_binned, qpe_ideal)
    else:
        correlation = 0.0

    return vra_binned, qpe_ideal, correlation


# Example usage
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    r = 168  # Example order
    shots = 10000

    # Generate QPE histogram
    hist, bin_edges = qpe_histogram(r, shots=shots, bins=r)

    # Plot
    plt.figure(figsize=(12, 5))
    plt.bar(bin_edges[:-1], hist, width=1.0, alpha=0.7)
    plt.xlabel("Measurement Outcome (phase bin)")
    plt.ylabel("Count")
    plt.title(f"QPE Histogram for r={r} (shots={shots})")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("/tmp/qpe_example.png", dpi=150)
    print(f"QPE histogram generated: mean={hist.mean():.1f}, std={hist.std():.1f}")
    print(f"Expected uniform: {shots/r:.1f} per bin")
