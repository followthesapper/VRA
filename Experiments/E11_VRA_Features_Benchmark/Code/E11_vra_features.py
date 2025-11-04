#!/usr/bin/env python3
"""
E11: VRA Features for Periodicity Detection

Goal: Benchmark VRA-derived features vs MUSIC/Goertzel on real datasets
Success Criteria: +3-5 dB effective SNR or +5-10% F1 at same latency
Expected GPU Speedup: 10-50x for large (M, L)

Datasets:
- Audio (pitch detection)
- ECG/PPG (heart rate)
- Industrial vibration (machinery diagnostics)
- Grid frequency (power systems)

REQUIRES GPU - will fail fast if not available.
"""

import sys
import numpy as np
from pathlib import Path
import json
from datetime import datetime

# Add GPU utilities to path
sys.path.insert(0, str(Path(__file__).parent))
from gpu_utils import check_gpu_available, GPURequiredError, gpu_coherent_average

# Add VRA core to path
_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "Code" / "VRA"))
from core import modular_sequence, phase_embed, multiplicative_order


def vra_feature_extraction(x_signal, N, a, L, M, framework='cupy'):
    """
    Extract VRA-based features from signal on GPU.

    Parameters
    ----------
    x_signal : ndarray, shape (total_samples,)
        Input signal (can be real-valued)
    N : int
        Modulus for VRA
    a : int
        Base for multiplicative group
    L : int
        Sequence length
    M : int
        Number of bases to average
    framework : str
        'cupy' or 'torch'

    Returns
    -------
    features : dict
        Extracted features including harmonic peaks, SNR, coherence
    """
    cp = check_gpu_available(framework)

    # Generate M modular sequences (different bases: a, a^2, ..., a^M)
    r = multiplicative_order(a, N)
    x_batch = []

    for m in range(1, M+1):
        base = pow(a, m, N)
        xs = modular_sequence(N, base, 1, L)
        # Embed signal values into phase (simple modulation)
        # This is a placeholder - real implementation would use signal values
        u = phase_embed(xs, N)
        x_batch.append(u)

    x_batch = np.array(x_batch, dtype=np.complex64)  # (M, L)

    # GPU-accelerated coherent average
    power_spectrum = gpu_coherent_average(x_batch, framework)

    # Extract features
    Lzp = len(power_spectrum)

    # Harmonic bin locations
    harmonic_bins = [int(round(ell * Lzp / r)) for ell in range(1, r)]

    # Peak power at harmonics
    harmonic_power = power_spectrum[harmonic_bins]

    # Background noise level (exclude harmonics ± guard)
    guard = 3
    mask = np.ones(Lzp, dtype=bool)
    for b in harmonic_bins:
        mask[max(0, b-guard):min(Lzp, b+guard+1)] = False
    noise_floor = np.median(power_spectrum[mask])

    # SNR estimate
    signal_power = np.mean(harmonic_power)
    snr_db = 10 * np.log10(signal_power / (noise_floor + 1e-30))

    features = {
        'harmonic_peaks': harmonic_power.tolist(),
        'noise_floor': float(noise_floor),
        'snr_db': float(snr_db),
        'peak_frequency_bin': int(harmonic_bins[np.argmax(harmonic_power)]),
        'fundamental_bin': harmonic_bins[0],
        'num_harmonics': len(harmonic_bins),
    }

    return features


def baseline_goertzel(x_signal, target_freqs, fs, N_samples):
    """
    Baseline: Goertzel algorithm for specific frequencies.

    Parameters
    ----------
    x_signal : ndarray
        Input signal
    target_freqs : list
        Target frequencies in Hz
    fs : float
        Sampling rate
    N_samples : int
        Number of samples to process

    Returns
    -------
    dict
        Goertzel features
    """
    # Placeholder implementation
    # Real version would implement Goertzel algorithm
    return {
        'method': 'goertzel',
        'snr_db': 0.0,
        'detection_latency_ms': 0.0,
    }


def baseline_music(x_signal, num_sources, L):
    """
    Baseline: MUSIC algorithm for frequency estimation.

    Parameters
    ----------
    x_signal : ndarray
        Input signal
    num_sources : int
        Number of signal sources
    L : int
        Subspace dimension

    Returns
    -------
    dict
        MUSIC features
    """
    # Placeholder implementation
    # Real version would implement MUSIC algorithm
    return {
        'method': 'music',
        'snr_db': 0.0,
        'detection_latency_ms': 0.0,
    }


def run_benchmark_suite(framework='cupy'):
    """
    Run full benchmark comparing VRA vs baselines.

    Success Criteria:
    - VRA should achieve +3-5 dB effective SNR over Goertzel
    - OR +5-10% higher F1 score at same latency
    """
    print("=" * 70)
    print("E11: VRA Features for Periodicity Detection")
    print("=" * 70)

    # Test parameters
    test_cases = [
        {
            'name': 'Audio Pitch Detection',
            'N': 997,
            'a': 9,
            'L': 8192,
            'M': 16,
            'fs': 44100,
        },
        {
            'name': 'ECG Heart Rate',
            'N': 997,
            'a': 9,
            'L': 16384,
            'M': 32,
            'fs': 1000,
        },
        {
            'name': 'Industrial Vibration',
            'N': 1999,
            'a': 7,
            'L': 32768,
            'M': 64,
            'fs': 10000,
        },
    ]

    results = []

    for case in test_cases:
        print(f"\nTest Case: {case['name']}")
        print(f"  N={case['N']}, a={case['a']}, L={case['L']}, M={case['M']}")

        # Generate synthetic test signal
        # Real implementation would load actual datasets
        x_signal = np.random.randn(case['L'])

        # VRA features
        try:
            vra_features = vra_feature_extraction(
                x_signal, case['N'], case['a'], case['L'], case['M'], framework
            )
            print(f"  VRA SNR: {vra_features['snr_db']:.2f} dB")
        except Exception as e:
            print(f"  VRA FAILED: {e}")
            vra_features = {'snr_db': -np.inf}

        # Baseline: Goertzel
        goertzel_features = baseline_goertzel(x_signal, [440.0], case['fs'], case['L'])
        print(f"  Goertzel SNR: {goertzel_features['snr_db']:.2f} dB")

        # Baseline: MUSIC
        music_features = baseline_music(x_signal, 1, case['L'] // 4)
        print(f"  MUSIC SNR: {music_features['snr_db']:.2f} dB")

        result = {
            'test_case': case['name'],
            'parameters': case,
            'vra': vra_features,
            'goertzel': goertzel_features,
            'music': music_features,
        }
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
        print("E11 ABORTED - GPU required")
        print("=" * 70)
        sys.exit(1)

    # Run benchmarks
    results = run_benchmark_suite(framework='cupy')

    # Save results
    output_dir = Path(__file__).parent.parent / "Data"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_vra_features_benchmark.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
    print("\nSuccess Criteria Check:")
    print("  Target: +3-5 dB SNR improvement over Goertzel")
    print("  Status: [Manual review required with real datasets]")


if __name__ == "__main__":
    main()
