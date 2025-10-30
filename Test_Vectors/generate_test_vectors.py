#!/usr/bin/env python3
"""
Generate Canonical Test Vectors for VRA Replication Challenge
==============================================================

Creates 10 canonical test cases with expected outputs for independent verification.

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "Code" / "Core"))

import numpy as np
import json
from datetime import datetime
from vra_core import (
    multiplicative_order,
    compute_averaged_spectrum,
    compute_concentration,
    compute_precision_recall,
    validated_radius,
    classify_regime
)


def find_bases_with_order(N, r, count=10, max_attempts=10000):
    """Find bases with specified multiplicative order."""
    bases = []
    attempts = 0

    for a in range(2, N):
        if attempts >= max_attempts:
            break

        if np.gcd(a, N) == 1:  # Must be coprime
            if multiplicative_order(a, N) == r:
                bases.append(a)
                if len(bases) >= count:
                    break

        attempts += 1

    return bases


def generate_test_vector(test_id, N, r, M, L=500, seed=42):
    """
    Generate a single test vector with expected outputs.

    Parameters
    ----------
    test_id : int
        Test case identifier
    N : int
        Modulus
    r : int
        Target multiplicative order
    M : int
        Number of bases to average
    L : int
        Sequence length
    seed : int
        Random seed for base selection

    Returns
    -------
    test_vector : dict
        Complete test vector with inputs and expected outputs
    """
    np.random.seed(seed)

    # Find bases with order r
    bases = find_bases_with_order(N, r, count=M, max_attempts=10000)

    if len(bases) < M:
        raise ValueError(f"Could not find {M} bases with order {r} in Z_{N}")

    bases = bases[:M]
    x0 = 1  # Standard initial condition

    # Compute VRA outputs
    zp = 4  # zero padding factor
    mag2 = compute_averaged_spectrum(N, bases, x0, L, zp, window="hann")
    concentration = compute_concentration(mag2)

    # Get harmonic bins
    Lzp = L * zp  # Actual FFT length after zero padding
    R = validated_radius(Lzp)
    harmonic_bins = []
    for k in range(1, r):
        bin_idx = int(round(k * Lzp / r))
        harmonic_bins.append(bin_idx)

    # Compute precision/recall (returns dict)
    metrics = compute_precision_recall(mag2, harmonic_bins, R)
    precision = metrics['precision']
    recall = metrics['recall']
    tp = metrics['TP']
    fp = metrics['FP']
    fn = metrics['FN']

    # Classify regime
    regime = classify_regime(N, r)

    # Create test vector
    rho = r / N
    test_vector = {
        "test_id": test_id,
        "description": f"N={N}, r={r}, {regime} regime (ρ={rho:.3f})",
        "parameters": {
            "N": N,
            "r": r,
            "bases": bases,
            "x0": x0,
            "M": M,
            "L": L,
            "zp": zp,
            "seed": seed
        },
        "regime": {
            "rho": rho,
            "classification": regime,
            "boundary": "HIGH_SNR" if rho < 0.146 else "TRANSITION" if rho < 0.263 else "LOW_SNR"
        },
        "expected_outputs": {
            "harmonic_bins": harmonic_bins[:20],  # First 20 for brevity
            "concentration": float(concentration),
            "precision": float(precision),
            "recall": float(recall),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "num_peaks": int(metrics['num_peaks']),
            "radius": int(R)
        },
        "tolerance": {
            "harmonic_bins": "exact match (integer indices)",
            "concentration": 0.001,
            "precision": 0.01,
            "recall": 0.01
        }
    }

    return test_vector


def main():
    """Generate all 10 canonical test vectors."""

    print("Generating VRA Canonical Test Vectors")
    print("=" * 70)

    # Define 10 canonical test cases
    test_cases = [
        # (test_id, N, r, M, description)
        (1, 997, 83, 4, "HIGH SNR baseline"),
        (2, 1009, 168, 4, "TRANSITION regime boundary"),
        (3, 1009, 504, 16, "LOW SNR large order"),
        (4, 1009, 144, 16, "Pathological highly composite"),
        (5, 991, 99, 4, "HIGH SNR small modulus"),
        (6, 1021, 255, 8, "TRANSITION mid-range"),
        (7, 1013, 506, 16, "LOW SNR outlier modulus"),
        (8, 997, 332, 8, "HIGH ρ transition"),
        (9, 1009, 63, 4, "HIGH SNR small order"),
        (10, 1009, 336, 16, "Pathological 2^4 × 3 × 7")
    ]

    test_vectors = []

    for test_id, N, r, M, desc in test_cases:
        print(f"\nGenerating Test {test_id}/10: {desc}")
        print(f"  N={N}, r={r}, M={M}")

        try:
            vector = generate_test_vector(test_id, N, r, M, L=500, seed=42)
            test_vectors.append(vector)

            print(f"  ✅ Concentration: {vector['expected_outputs']['concentration']:.4f}")
            print(f"  ✅ Precision: {vector['expected_outputs']['precision']:.3f}")
            print(f"  ✅ Recall: {vector['expected_outputs']['recall']:.3f}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

    # Save test vectors
    output = {
        "metadata": {
            "version": "1.0.0",
            "date_generated": datetime.now().isoformat(),
            "num_test_vectors": len(test_vectors),
            "purpose": "VRA Independent Replication Challenge - Canonical Test Vectors",
            "random_seed": 42
        },
        "test_vectors": test_vectors
    }

    output_path = Path(__file__).parent / "test_vectors.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 70)
    print(f"✅ Generated {len(test_vectors)}/10 test vectors")
    print(f"📁 Saved to: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
