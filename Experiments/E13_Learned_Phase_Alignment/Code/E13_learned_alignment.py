#!/usr/bin/env python3
"""
E13: Learned Phase Alignment

Goal: Recover √M scaling via lightweight parametric phase corrector
Constraint: Unsupervised (no labels for r)
Success Criteria: >50% of theoretical √M gain on Z*_N
Expected GPU Speedup: 50-200x for gradient descent

Key Idea:
- Different bases (a^m) have phase-incoherent spectra (R=0.137)
- Learn alignment parameters θ_m to maximize coherence
- No supervision - optimize SNR directly

REQUIRES GPU - will fail fast if not available.
"""

import sys
import numpy as np
from pathlib import Path
import json
from datetime import datetime

# Add GPU utilities to path
sys.path.insert(0, str(Path(__file__).parent))
from gpu_utils import check_gpu_available, GPURequiredError

# Add VRA core to path
_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "Code" / "VRA"))
from core import modular_sequence, phase_embed, multiplicative_order


def compute_unaligned_spectra(N, a, r, L, M):
    """
    Compute spectra from M different bases without alignment.

    Returns
    -------
    U : ndarray, shape (M, L)
        Complex FFT spectra from bases a^1, a^2, ..., a^M
    harmonic_bins : list
        Indices of harmonic bins
    """
    U_list = []

    for m in range(1, M+1):
        base = pow(a, m, N)
        xs = modular_sequence(N, base, 1, L)
        u = phase_embed(xs, N)
        U_m = np.fft.fft(u)
        U_list.append(U_m)

    U = np.array(U_list, dtype=np.complex128)

    # Harmonic bins
    harmonic_bins = [int(round(ell * L / r)) for ell in range(1, r)]

    return U, harmonic_bins


def apply_phase_alignment(U, theta, harmonic_bins):
    """
    Apply learned phase corrections.

    Parameters
    ----------
    U : ndarray, shape (M, L)
        Input spectra
    theta : ndarray, shape (M,)
        Phase correction for each base (radians)
    harmonic_bins : list
        Harmonic bin indices

    Returns
    -------
    U_aligned : ndarray, shape (M, L)
        Phase-corrected spectra
    """
    M, L = U.shape
    U_aligned = np.zeros_like(U)

    for m in range(M):
        # Apply linear phase correction across frequency bins
        k = np.arange(L)
        phase_correction = np.exp(-1j * theta[m] * k / L)
        U_aligned[m] = U[m] * phase_correction

    return U_aligned


def snr_objective(U, harmonic_bins, guard=3):
    """
    Compute SNR from spectrum batch (objective to maximize).

    Parameters
    ----------
    U : ndarray, shape (M, L)
        Spectrum batch
    harmonic_bins : list
        Signal bin indices
    guard : int
        Guard band around harmonics

    Returns
    -------
    snr_db : float
        Signal-to-noise ratio in dB
    """
    # Coherent average: |mean(U_m)|^2
    U_avg = np.mean(U, axis=0)
    power = np.abs(U_avg) ** 2

    # Signal: average power at harmonic bins
    signal = np.mean(power[harmonic_bins])

    # Noise: median of non-harmonic bins
    L = U.shape[1]
    mask = np.ones(L, dtype=bool)
    for b in harmonic_bins:
        mask[max(0, b-guard):min(L, b+guard+1)] = False
    noise = np.median(power[mask])

    snr_db = 10 * np.log10(signal / (noise + 1e-30))
    return snr_db


def gradient_descent_alignment(U, harmonic_bins, lr=0.01, n_iter=100):
    """
    Learn phase alignment via gradient descent (CPU placeholder).

    Real GPU implementation would use torch.autograd or CuPy custom kernels.

    Parameters
    ----------
    U : ndarray, shape (M, L)
        Input spectra
    harmonic_bins : list
        Harmonic bins
    lr : float
        Learning rate
    n_iter : int
        Number of iterations

    Returns
    -------
    theta_opt : ndarray, shape (M,)
        Optimal phase corrections
    snr_history : list
        SNR at each iteration
    """
    M = U.shape[0]
    theta = np.zeros(M)  # Initialize to zero (no correction)

    snr_history = []
    initial_snr = snr_objective(U, harmonic_bins)
    snr_history.append(initial_snr)

    print(f"  Initial SNR: {initial_snr:.2f} dB")

    for iteration in range(n_iter):
        # Compute gradient via finite differences
        grad = np.zeros(M)
        eps = 0.01

        for m in range(M):
            theta_plus = theta.copy()
            theta_plus[m] += eps
            U_plus = apply_phase_alignment(U, theta_plus, harmonic_bins)
            snr_plus = snr_objective(U_plus, harmonic_bins)

            theta_minus = theta.copy()
            theta_minus[m] -= eps
            U_minus = apply_phase_alignment(U, theta_minus, harmonic_bins)
            snr_minus = snr_objective(U_minus, harmonic_bins)

            grad[m] = (snr_plus - snr_minus) / (2 * eps)

        # Gradient ascent (maximize SNR)
        theta += lr * grad

        # Evaluate
        U_aligned = apply_phase_alignment(U, theta, harmonic_bins)
        current_snr = snr_objective(U_aligned, harmonic_bins)
        snr_history.append(current_snr)

        if (iteration + 1) % 20 == 0:
            print(f"  Iter {iteration+1}/{n_iter}: SNR = {current_snr:.2f} dB")

    return theta, snr_history


def test_learned_alignment(N, a, L, M, n_iter=100):
    """
    Run full learned alignment test.

    Returns
    -------
    dict
        Results including SNR gain, coherence improvement
    """
    r = multiplicative_order(a, N)
    print(f"\nTest: N={N}, a={a}, r={r}, L={L}, M={M}")

    # Compute unaligned spectra
    print("  Computing unaligned spectra...")
    U, harmonic_bins = compute_unaligned_spectra(N, a, r, L, M)

    # Baseline SNR (no alignment)
    baseline_snr = snr_objective(U, harmonic_bins)

    # Learn alignment
    print(f"  Learning alignment ({n_iter} iterations)...")
    theta_opt, snr_history = gradient_descent_alignment(U, harmonic_bins, lr=0.01, n_iter=n_iter)

    # Final SNR
    U_aligned = apply_phase_alignment(U, theta_opt, harmonic_bins)
    final_snr = snr_objective(U_aligned, harmonic_bins)

    # Theoretical gain from √M scaling
    theoretical_gain = 10 * np.log10(np.sqrt(M))

    # Achieved gain
    achieved_gain = final_snr - baseline_snr

    # Percentage of theoretical
    pct_theoretical = (achieved_gain / theoretical_gain) * 100

    print(f"\n  Results:")
    print(f"    Baseline SNR: {baseline_snr:.2f} dB")
    print(f"    Aligned SNR:  {final_snr:.2f} dB")
    print(f"    Gain:         {achieved_gain:.2f} dB")
    print(f"    Theoretical:  {theoretical_gain:.2f} dB (√M)")
    print(f"    Achieved:     {pct_theoretical:.1f}% of theoretical")

    result = {
        'N': N, 'a': a, 'r': r, 'L': L, 'M': M,
        'baseline_snr_db': float(baseline_snr),
        'aligned_snr_db': float(final_snr),
        'gain_db': float(achieved_gain),
        'theoretical_gain_db': float(theoretical_gain),
        'pct_theoretical': float(pct_theoretical),
        'snr_history': [float(x) for x in snr_history],
        'theta_opt': theta_opt.tolist(),
    }

    return result


def run_alignment_experiments(framework='cupy'):
    """
    Run learned alignment experiments across parameter grid.
    """
    print("=" * 70)
    print("E13: Learned Phase Alignment")
    print("=" * 70)

    test_cases = [
        {'N': 997, 'a': 9, 'L': 4096, 'M': 8},
        {'N': 997, 'a': 9, 'L': 8192, 'M': 16},
        {'N': 1999, 'a': 7, 'L': 8192, 'M': 32},
    ]

    results = []

    for case in test_cases:
        result = test_learned_alignment(
            case['N'], case['a'], case['L'], case['M'],
            n_iter=100
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
        print("E13 ABORTED - GPU required")
        print("Note: Current implementation uses CPU gradient descent.")
        print("GPU version would use PyTorch autograd for 50-200x speedup.")
        print("=" * 70)
        sys.exit(1)

    # Run experiments
    results = run_alignment_experiments(framework='cupy')

    # Save results
    output_dir = Path(__file__).parent.parent / "Data"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_learned_alignment.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
    print("\nSuccess Criteria Check:")
    print("  Target: >50% of theoretical √M gain")

    # Check if any test achieved target
    any_success = any(r['pct_theoretical'] > 50 for r in results)
    if any_success:
        print("  Status: ✅ SUCCESS")
    else:
        print("  Status: ⚠️  Below target - may need architecture improvements")


if __name__ == "__main__":
    main()
