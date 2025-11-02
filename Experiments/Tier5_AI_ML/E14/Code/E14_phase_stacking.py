#!/usr/bin/env python3
"""
E14: Phase-Aligned Stacking (Deterministic Validation)

Goal: Validate phase alignment with L=Q·r, window=none
Success Criteria: +1-2 dB per doubling with proper alignment
Expected GPU Speedup: 10-30x for batch FFT

This is the DETERMINISTIC validation of phase alignment theory.
Based on E1D_shifted_copies_FIXED.py which showed perfect M² power scaling.

Key Requirements:
1. L = Q * r (exact multiple of period)
2. De-rotation of time shifts
3. No windowing (breaks circular symmetry)

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
_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO / "Code" / "VRA"))
from core import modular_sequence, phase_embed, multiplicative_order


def generate_shifted_sequences(N, a, L, M, shifts):
    """
    Generate M shifted copies of same modular sequence.

    Parameters
    ----------
    N, a : int
        Modulus and base
    L : int
        Sequence length (must be multiple of r)
    M : int
        Number of shifts
    shifts : array_like, shape (M,)
        Circular shift amounts

    Returns
    -------
    x_batch : ndarray, shape (M, L)
        Batch of shifted sequences
    """
    # Generate base sequence
    xs = modular_sequence(N, a, 1, L)
    u = phase_embed(xs, N)

    x_batch = []
    for shift in shifts:
        u_shifted = np.roll(u, shift)
        x_batch.append(u_shifted)

    return np.array(x_batch, dtype=np.complex64)


def coherent_stack_with_derotation(spectra, shifts, L):
    """
    Stack spectra with de-rotation of time shift phase slopes.

    Parameters
    ----------
    spectra : ndarray, shape (M, L)
        FFT spectra from shifted sequences
    shifts : array_like, shape (M,)
        Circular shift amounts used
    L : int
        Sequence length

    Returns
    -------
    power_spectrum : ndarray, shape (L,)
        Power spectrum of coherently stacked result
    """
    M = spectra.shape[0]
    k = np.arange(L)

    # De-rotate each spectrum
    U_sum = np.zeros(L, dtype=np.complex128)
    for m in range(M):
        # Undo phase slope from circular shift
        phase_correction = np.exp(+1j * 2 * np.pi * k * shifts[m] / L)
        U_corrected = spectra[m] * phase_correction
        U_sum += U_corrected

    # Coherent average
    U_avg = U_sum / M

    # Power spectrum
    power = np.abs(U_avg) ** 2

    # Also compute raw power (before /M) for M² scaling check
    power_raw = np.abs(U_sum) ** 2

    return power, power_raw


def measure_snr(power, harmonic_bins, guard=3):
    """
    Measure SNR from power spectrum.

    Parameters
    ----------
    power : ndarray
        Power spectrum
    harmonic_bins : list
        Signal bin indices
    guard : int
        Guard band

    Returns
    -------
    snr_db : float
        Signal-to-noise ratio
    signal_power : float
        Mean signal power
    """
    signal = np.mean(power[harmonic_bins])

    # Noise: median of non-harmonic bins
    L = len(power)
    mask = np.ones(L, dtype=bool)
    for b in harmonic_bins:
        mask[max(0, b-guard):min(L, b+guard+1)] = False
    noise = np.median(power[mask])

    snr_db = 10 * np.log10(signal / (noise + 1e-30))
    return snr_db, signal


def test_phase_stacking(N, a, M_values, framework='cupy'):
    """
    Test phase-aligned stacking with deterministic signal.

    Returns
    -------
    dict
        Results showing M² power scaling and SNR behavior
    """
    r = multiplicative_order(a, N)

    # CRITICAL: L must be exact multiple of r
    Q = 2048
    L = r * Q

    print(f"\nTest: N={N}, a={a}, r={r}")
    print(f"  L = {Q} × {r} = {L} (exact periodicity)")

    # Harmonic bins
    harmonic_bins = [int(round(ell * L / r)) for ell in range(1, r)]

    results = []
    signal_baseline = None

    for M in M_values:
        print(f"\n  M={M}:")

        # Generate evenly-spaced shifts
        shifts = np.linspace(0, L-1, M, dtype=int)

        # Generate shifted sequences
        x_batch = generate_shifted_sequences(N, a, L, M, shifts)

        # GPU-accelerated batch FFT
        spectra = gpu_fft_batch(x_batch, framework)

        # Coherent stacking with de-rotation
        power, power_raw = coherent_stack_with_derotation(spectra, shifts, L)

        # Measure SNR
        snr_db, signal_power = measure_snr(power, harmonic_bins)
        snr_raw_db, signal_power_raw = measure_snr(power_raw, harmonic_bins)

        # Track M² scaling
        if signal_baseline is None:
            signal_baseline = signal_power_raw

        signal_gain_db = 10 * np.log10(signal_power_raw / signal_baseline)

        print(f"    SNR (normalized): {snr_db:.2f} dB")
        print(f"    Signal power gain: {signal_gain_db:+.2f} dB (raw |U_sum|²)")

        results.append({
            'M': M,
            'snr_normalized_db': float(snr_db),
            'snr_raw_db': float(snr_raw_db),
            'signal_power_raw': float(signal_power_raw),
            'signal_gain_db': float(signal_gain_db),
        })

    # Check M² scaling
    print(f"\n  M² Scaling Check (raw power):")
    for i in range(len(results) - 1):
        if M_values[i+1] == 2 * M_values[i]:
            gain = results[i+1]['signal_gain_db'] - results[i]['signal_gain_db']
            print(f"    M={M_values[i]}→{M_values[i+1]}: {gain:+.2f} dB (expected: +6.0 dB)")

    result = {
        'N': N, 'a': a, 'r': r, 'L': L, 'Q': Q,
        'M_values': M_values,
        'results': results,
    }

    return result


def run_stacking_experiments(framework='cupy'):
    """
    Run phase-aligned stacking validation experiments.
    """
    print("=" * 70)
    print("E14: Phase-Aligned Stacking (Deterministic Validation)")
    print("=" * 70)

    test_cases = [
        {'N': 997, 'a': 9, 'M_values': [4, 8, 16, 32, 64]},
        {'N': 1999, 'a': 7, 'M_values': [4, 8, 16, 32]},
    ]

    all_results = []

    for case in test_cases:
        result = test_phase_stacking(
            case['N'], case['a'], case['M_values'], framework
        )
        all_results.append(result)

    return all_results


def main():
    """Main entry point - FAILS FAST if no GPU."""
    print("Checking GPU availability...")

    # FAIL FAST if no GPU
    try:
        cp = check_gpu_available('cupy')
    except GPURequiredError as e:
        print(e)
        print("\n" + "=" * 70)
        print("E14 ABORTED - GPU required")
        print("=" * 70)
        sys.exit(1)

    # Run experiments
    results = run_stacking_experiments(framework='cupy')

    # Save results
    output_dir = Path(_REPO) / "Data" / "Experiments" / "Tier5" / "E14"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_phase_stacking.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
    print("\nSuccess Criteria Check:")
    print("  Target: Perfect M² power scaling (+6 dB per doubling)")
    print("  Status: [Review results above]")
    print("\nKey Validation:")
    print("  - L = Q × r (exact periodicity) ✓")
    print("  - De-rotation applied ✓")
    print("  - No windowing ✓")


if __name__ == "__main__":
    main()
