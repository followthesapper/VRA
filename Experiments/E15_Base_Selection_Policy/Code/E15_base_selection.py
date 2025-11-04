#!/usr/bin/env python3
"""
E15: Base Selection Policy

Goal: Predict coherence R from cheap proxies, choose optimal bases
Success Criteria: +2-4 dB SNR over random base choice at fixed M
Expected GPU Speedup: 20-100x for policy search/optimization

Key Idea:
- Different bases (a^1, a^2, ...) have varying coherence (E1D: R̄=0.137)
- Can we predict which bases will be coherent without full FFT?
- Learn policy: Base features → Expected coherence R

Features to explore:
1. Order of base: r_m = ord_N(a^m)
2. Quadratic residue status
3. Index m (power of generator)
4. Subgroup structure

REQUIRES GPU - will fail fast if not available.
"""

import sys
import numpy as np
from pathlib import Path
import json
from datetime import datetime

# Add GPU utilities to path
sys.path.insert(0, str(Path(__file__).parent))
from gpu_utils import check_gpu_available, GPURequiredError, gpu_fft_batch

# Add VRA core to path
_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "Code" / "VRA"))
from core import modular_sequence, phase_embed, multiplicative_order


def compute_base_features(N, a, m):
    """
    Compute features for base a^m.

    Parameters
    ----------
    N : int
        Modulus
    a : int
        Generator base
    m : int
        Power (base = a^m mod N)

    Returns
    -------
    features : dict
        Features for this base
    """
    base = pow(a, m, N)

    # Order of this base
    r_m = multiplicative_order(base, N)

    # Quadratic residue (Legendre symbol for prime N)
    # Simplified check: is base a perfect square mod N?
    is_qr = pow(base, (N-1)//2, N) == 1 if N > 2 else False

    # Index within generator powers
    index = m

    features = {
        'base': base,
        'index': index,
        'order': r_m,
        'is_quadratic_residue': is_qr,
        'log_order': np.log(r_m),
    }

    return features


def measure_coherence(U_list, harmonic_bins):
    """
    Measure phase coherence R across spectra.

    Parameters
    ----------
    U_list : list of ndarray
        List of M complex spectra, each shape (L,)
    harmonic_bins : list
        Harmonic bin indices

    Returns
    -------
    R_mean : float
        Mean coherence across harmonic bins
    R_values : ndarray
        Coherence at each harmonic bin
    """
    U_stack = np.array(U_list)  # (M, L)

    R_values = []
    for k in harmonic_bins:
        # Extract phasors at bin k from all M spectra
        phasors = U_stack[:, k]

        # Normalize to unit magnitude
        phasors_norm = phasors / (np.abs(phasors) + 1e-30)

        # Resultant length
        R_k = np.abs(np.mean(phasors_norm))
        R_values.append(R_k)

    R_values = np.array(R_values)
    R_mean = np.mean(R_values)

    return R_mean, R_values


def compute_snr(U_list, harmonic_bins, guard=3):
    """
    Compute SNR from coherent average of spectra.

    Parameters
    ----------
    U_list : list of ndarray
        Spectra to average
    harmonic_bins : list
        Signal bins
    guard : int
        Guard band

    Returns
    -------
    snr_db : float
    """
    U_stack = np.array(U_list)
    U_avg = np.mean(U_stack, axis=0)
    power = np.abs(U_avg) ** 2

    signal = np.mean(power[harmonic_bins])

    L = len(power)
    mask = np.ones(L, dtype=bool)
    for b in harmonic_bins:
        mask[max(0, b-guard):min(L, b+guard+1)] = False
    noise = np.median(power[mask])

    snr_db = 10 * np.log10(signal / (noise + 1e-30))
    return snr_db


def test_base_selection(N, a, L, M, framework='cupy'):
    """
    Test base selection strategies.

    Parameters
    ----------
    N, a : int
        Modulus and generator
    L : int
        Sequence length
    M : int
        Number of bases to select
    framework : str
        GPU framework

    Returns
    -------
    dict
        Results comparing random vs optimized base selection
    """
    r = multiplicative_order(a, N)
    print(f"\nTest: N={N}, a={a}, r={r}, L={L}, M={M}")

    # Harmonic bins
    harmonic_bins = [int(round(ell * L / r)) for ell in range(1, min(r, L//2))]

    # Generate spectra for all candidate bases (a^1 to a^r)
    print(f"  Generating spectra for {r} candidate bases...")
    all_spectra = []
    base_features_list = []

    for m in range(1, min(r+1, 100)):  # Cap at 100 for efficiency
        base = pow(a, m, N)
        xs = modular_sequence(N, base, 1, L)
        u = phase_embed(xs, N)
        U = np.fft.fft(u)
        all_spectra.append(U)

        features = compute_base_features(N, a, m)
        base_features_list.append(features)

    n_candidates = len(all_spectra)
    print(f"  Computed {n_candidates} candidate spectra")

    # Strategy 1: Random selection
    print(f"\n  Strategy 1: Random selection")
    random_indices = np.random.choice(n_candidates, M, replace=False)
    random_spectra = [all_spectra[i] for i in random_indices]

    R_random, _ = measure_coherence(random_spectra, harmonic_bins)
    snr_random = compute_snr(random_spectra, harmonic_bins)

    print(f"    Coherence R: {R_random:.3f}")
    print(f"    SNR: {snr_random:.2f} dB")

    # Strategy 2: Select bases with smallest index (a^1, a^2, ...)
    print(f"\n  Strategy 2: Sequential (a^1, a^2, ...)")
    sequential_indices = list(range(M))
    sequential_spectra = [all_spectra[i] for i in sequential_indices]

    R_sequential, _ = measure_coherence(sequential_spectra, harmonic_bins)
    snr_sequential = compute_snr(sequential_spectra, harmonic_bins)

    print(f"    Coherence R: {R_sequential:.3f}")
    print(f"    SNR: {snr_sequential:.2f} dB")

    # Strategy 3: Greedy selection (maximize pairwise coherence)
    print(f"\n  Strategy 3: Greedy coherence-based")
    greedy_indices = [0]  # Start with a^1

    for _ in range(M - 1):
        best_idx = None
        best_R = -1

        # Try adding each remaining candidate
        for idx in range(n_candidates):
            if idx in greedy_indices:
                continue

            # Test coherence with current selection
            test_spectra = [all_spectra[i] for i in greedy_indices + [idx]]
            R_test, _ = measure_coherence(test_spectra, harmonic_bins)

            if R_test > best_R:
                best_R = R_test
                best_idx = idx

        if best_idx is not None:
            greedy_indices.append(best_idx)

    greedy_spectra = [all_spectra[i] for i in greedy_indices]

    R_greedy, _ = measure_coherence(greedy_spectra, harmonic_bins)
    snr_greedy = compute_snr(greedy_spectra, harmonic_bins)

    print(f"    Coherence R: {R_greedy:.3f}")
    print(f"    SNR: {snr_greedy:.2f} dB")
    print(f"    Selected indices: {greedy_indices[:10]}...")

    # Compare strategies
    print(f"\n  Comparison:")
    print(f"    Random:     SNR = {snr_random:.2f} dB, R = {R_random:.3f}")
    print(f"    Sequential: SNR = {snr_sequential:.2f} dB, R = {R_sequential:.3f}")
    print(f"    Greedy:     SNR = {snr_greedy:.2f} dB, R = {R_greedy:.3f}")
    print(f"    Greedy gain: {snr_greedy - snr_random:+.2f} dB over random")

    result = {
        'N': N, 'a': a, 'r': r, 'L': L, 'M': M,
        'n_candidates': n_candidates,
        'random': {
            'indices': random_indices.tolist(),
            'coherence': float(R_random),
            'snr_db': float(snr_random),
        },
        'sequential': {
            'indices': sequential_indices,
            'coherence': float(R_sequential),
            'snr_db': float(snr_sequential),
        },
        'greedy': {
            'indices': greedy_indices,
            'coherence': float(R_greedy),
            'snr_db': float(snr_greedy),
        },
        'gain_db': float(snr_greedy - snr_random),
    }

    return result


def run_selection_experiments(framework='cupy'):
    """
    Run base selection policy experiments.
    """
    print("=" * 70)
    print("E15: Base Selection Policy")
    print("=" * 70)

    test_cases = [
        {'N': 997, 'a': 9, 'L': 4096, 'M': 8},
        {'N': 997, 'a': 9, 'L': 8192, 'M': 16},
    ]

    results = []

    for case in test_cases:
        result = test_base_selection(
            case['N'], case['a'], case['L'], case['M'], framework
        )
        results.append(result)

    return results


def main():
    """Main entry point - FAILS FAST if no GPU."""
    print("Checking GPU availability...")

    # FAIL FAST if no GPU
    try:
        cp = check_gpu_available('cupy')
    except GPURequiredError as e:
        print(e)
        print("\n" + "=" * 70)
        print("E15 ABORTED - GPU required")
        print("=" * 70)
        sys.exit(1)

    # Run experiments
    results = run_selection_experiments(framework='cupy')

    # Save results
    output_dir = Path(__file__).parent.parent / "Data"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_base_selection.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
    print("\nSuccess Criteria Check:")
    print("  Target: +2-4 dB SNR over random base choice")

    # Check if any test achieved target
    any_success = any(r['gain_db'] >= 2.0 for r in results)
    if any_success:
        print("  Status: ✅ SUCCESS")
    else:
        max_gain = max(r['gain_db'] for r in results)
        print(f"  Status: ⚠️  Best gain: {max_gain:.2f} dB (below 2 dB target)")


if __name__ == "__main__":
    main()
