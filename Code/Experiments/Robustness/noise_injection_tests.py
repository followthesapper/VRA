#!/usr/bin/env python3
"""
Noise Injection Robustness Tests
=================================

Test VRA's robustness to various noise types:
1. Additive Gaussian noise (controlled SNR)
2. Phase jitter (timing errors)
3. Quantization effects (bit-depth reduction)

Addresses TODO.md Phase 4.1: "Noise injection experiments"

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "Core"))

import numpy as np
import json
from datetime import datetime
from core import (
    multiplicative_order,
    compute_concentration,
    compute_precision_recall,
    validated_radius,
    classify_regime
)


def generate_noisy_sequence(N, bases, x0, length, noise_type='gaussian', noise_level=0.1):
    """Generate modular sequence with injected noise

    Parameters:
        N (int): Modulus
        bases (list): Bases to average
        x0 (int): Initial value
        length (int): Sequence length
        noise_type (str): 'gaussian', 'phase_jitter', 'quantization'
        noise_level (float): Noise strength parameter

    Returns:
        complex sequence with noise
    """
    M = len(bases)
    sequences = []

    for a in bases:
        # Generate clean modular sequence
        x = x0
        seq = []
        for _ in range(length):
            x = (x * a) % N
            phase = 2 * np.pi * x / N

            if noise_type == 'gaussian':
                # Additive Gaussian noise in complex domain
                clean_val = np.exp(1j * phase)
                noise_real = np.random.normal(0, noise_level)
                noise_imag = np.random.normal(0, noise_level)
                noisy_val = clean_val + noise_real + 1j * noise_imag

            elif noise_type == 'phase_jitter':
                # Phase jitter (timing errors)
                jitter = np.random.normal(0, noise_level * 2 * np.pi)
                noisy_phase = phase + jitter
                noisy_val = np.exp(1j * noisy_phase)

            elif noise_type == 'quantization':
                # Quantize phase to n bits
                n_bits = max(1, int(16 - noise_level * 10))  # Reduce bits with noise
                n_levels = 2 ** n_bits
                quantized_phase = np.round(phase / (2 * np.pi) * n_levels) / n_levels * 2 * np.pi
                noisy_val = np.exp(1j * quantized_phase)

            else:
                raise ValueError(f"Unknown noise type: {noise_type}")

            seq.append(noisy_val)

        sequences.append(np.array(seq))

    return sequences


def compute_noisy_spectrum(N, bases, x0, length, zp, window, noise_type, noise_level):
    """Compute averaged spectrum with noise injection

    Returns:
        mag2_avg: Averaged power spectrum
    """
    sequences = generate_noisy_sequence(N, bases, x0, length, noise_type, noise_level)

    M = len(sequences)
    L = length * zp

    # Apply window and coherently average
    if window == 'hann':
        win = np.hanning(length)
    elif window == 'hamming':
        win = np.hamming(length)
    else:
        win = np.ones(length)

    U_sum = np.zeros(L, dtype=complex)

    for seq in sequences:
        # Apply window
        seq_windowed = seq * win

        # Zero-pad
        seq_padded = np.pad(seq_windowed, (0, L - len(seq_windowed)))

        # FFT
        U = np.fft.fft(seq_padded)

        # Coherently sum
        U_sum += U

    # Average and compute power
    U_avg = U_sum / M
    mag2_avg = np.abs(U_avg) ** 2

    return mag2_avg


def test_noise_robustness(N, r, bases, noise_types, noise_levels, M_values=[1, 4, 8, 16, 32]):
    """Test VRA robustness across noise types and levels

    Parameters:
        N (int): Modulus
        r (int): Order
        bases (list): Bases with order r
        noise_types (list): Types of noise to test
        noise_levels (list): Noise strength values
        M_values (list): Number of bases to average

    Returns:
        dict: Test results
    """
    results = {
        'N': int(N),
        'r': int(r),
        'rho': float(r / N),
        'regime': classify_regime(N, r)[0],
        'noise_tests': []
    }

    L = 65536
    length = L // 8
    R = validated_radius(L)
    expected_bins = [(k * L // r) % L for k in range(r)]

    print(f"\nTesting N={N}, r={r} (ρ={r/N:.4f})")
    print(f"Regime: {results['regime']}")

    for noise_type in noise_types:
        print(f"\n  Noise type: {noise_type}")

        for noise_level in noise_levels:
            print(f"    Level {noise_level:.3f}...", end=" ")

            noise_result = {
                'noise_type': noise_type,
                'noise_level': float(noise_level),
                'M_tests': []
            }

            for M in M_values:
                if M > len(bases):
                    continue

                # Compute noisy spectrum
                mag2_avg = compute_noisy_spectrum(
                    N, bases[:M], 1, length, 8, 'hann',
                    noise_type, noise_level
                )

                # Metrics
                concentration = compute_concentration(mag2_avg)
                metrics = compute_precision_recall(mag2_avg, expected_bins, R)

                noise_result['M_tests'].append({
                    'M': int(M),
                    'concentration': float(concentration),
                    'precision': float(metrics['precision']),
                    'recall': float(metrics['recall']),
                    'f1': float(metrics['f1'])
                })

            # Average precision across M values
            avg_precision = np.mean([t['precision'] for t in noise_result['M_tests']])
            print(f"Precision: {avg_precision:.1%}")

            results['noise_tests'].append(noise_result)

    return results


def find_bases_with_order(N, r, max_bases=50):
    """Find bases with given multiplicative order"""
    bases = []

    for a in range(2, N):
        if len(bases) >= max_bases:
            break

        if np.gcd(a, N) != 1:
            continue

        order = multiplicative_order(a, N, max_iter=N)
        if order == r:
            bases.append(a)

    return bases


def run_noise_injection_suite():
    """Run comprehensive noise injection tests"""

    print("VRA Noise Injection Robustness Tests")
    print("=" * 70)

    # Test cases (one per regime)
    test_cases = [
        (1009, 112),  # HIGH SNR: ρ ≈ 0.111
        (1009, 168),  # TRANSITION: ρ ≈ 0.167
        (1009, 504),  # LOW SNR: ρ ≈ 0.500
    ]

    # Noise types to test
    noise_types = ['gaussian', 'phase_jitter', 'quantization']

    # Noise levels
    noise_levels = [0.0, 0.01, 0.05, 0.10, 0.20, 0.50]

    all_results = {
        'metadata': {
            'date': datetime.now().isoformat(),
            'noise_types': noise_types,
            'noise_levels': noise_levels,
            'M_values': [1, 4, 8, 16, 32],
            'num_test_cases': len(test_cases)
        },
        'test_cases': []
    }

    for N, r in test_cases:
        print(f"\n{'='*70}")

        # Find bases
        bases = find_bases_with_order(N, r, max_bases=50)

        if len(bases) < 32:
            print(f"WARNING: Only found {len(bases)} bases for N={N}, r={r}")
            continue

        # Run noise tests
        result = test_noise_robustness(N, r, bases, noise_types, noise_levels)
        all_results['test_cases'].append(result)

    # Save results
    output_dir = Path(__file__).parent.parent.parent / "Data" / "Phase4_Robustness" / "Noise_Injection"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_noise_injection_results.json"

    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Results saved to: {output_file}")

    return all_results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VRA Noise Injection Tests')
    parser.add_argument('--quick', action='store_true',
                       help='Quick test (fewer noise levels)')

    args = parser.parse_args()

    if args.quick:
        print("Quick test mode")
        # Test single case with fewer noise levels
        N, r = 1009, 168
        bases = find_bases_with_order(N, r, max_bases=32)
        result = test_noise_robustness(
            N, r, bases,
            noise_types=['gaussian'],
            noise_levels=[0.0, 0.1, 0.5],
            M_values=[1, 8, 32]
        )
        print(json.dumps(result, indent=2))
    else:
        # Full test suite
        results = run_noise_injection_suite()
