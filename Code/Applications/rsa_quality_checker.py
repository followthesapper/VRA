#!/usr/bin/env python3
"""
RSA Parameter Quality Checker
==============================

Uses VRA to assess the quality of RSA moduli by analyzing multiplicative
order structure. Helps identify weak or unusual RSA parameters.

Phase 4.3 - Extended Applications
Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "Core"))

import argparse
import numpy as np
from core import (
    multiplicative_order,
    compute_averaged_spectrum,
    compute_concentration,
    classify_regime
)


def analyze_rsa_modulus(N, num_samples=10, L=500):
    """
    Analyze RSA modulus for order structure quality.

    Parameters
    ----------
    N : int
        RSA modulus (should be product of two primes)
    num_samples : int
        Number of random bases to test
    L : int
        Sequence length for analysis

    Returns
    -------
    report : dict
        Quality assessment report
    """
    print(f"\n{'='*70}")
    print(f"RSA Modulus Quality Assessment")
    print(f"{'='*70}")
    print(f"N = {N}")
    print(f"Bit length: {N.bit_length()} bits")

    # Sample random bases
    np.random.seed(42)
    bases = []
    orders = []

    print(f"\nSampling {num_samples} random bases...")

    for _ in range(num_samples):
        # Random base coprime to N
        while True:
            a = np.random.randint(2, min(N, 10000))
            if np.gcd(a, N) == 1:
                bases.append(a)
                break

    # Compute orders
    for a in bases:
        try:
            r = multiplicative_order(a, N, max_iter=10000)
            if r is not None:
                orders.append(r)
        except:
            pass

    if len(orders) == 0:
        print("❌ Could not compute any multiplicative orders")
        return {'status': 'error', 'message': 'No orders computed'}

    # Statistics
    orders = np.array(orders)
    mean_order = np.mean(orders)
    std_order = np.std(orders)
    max_order = np.max(orders)
    min_order = np.min(orders)

    print(f"\nOrder Statistics:")
    print(f"  Bases tested: {len(orders)}/{num_samples}")
    print(f"  Mean order: {mean_order:.1f}")
    print(f"  Std dev: {std_order:.1f}")
    print(f"  Range: [{min_order}, {max_order}]")

    # Classify regimes
    regimes = []
    for r in orders:
        regime = classify_regime(N, r)
        regimes.append(regime)

    # Count regime distribution
    from collections import Counter
    regime_counts = Counter([r[0] if isinstance(r, tuple) else r for r in regimes])

    print(f"\nRegime Distribution:")
    for regime, count in regime_counts.items():
        pct = 100 * count / len(regimes)
        print(f"  {regime}: {count} ({pct:.1f}%)")

    # Quality assessment
    print(f"\n{'='*70}")
    print("QUALITY ASSESSMENT")
    print(f"{'='*70}")

    quality_score = 0
    warnings = []
    recommendations = []

    # Check 1: Order diversity
    unique_orders = len(set(orders))
    if unique_orders == len(orders):
        print("✅ Good order diversity (all unique)")
        quality_score += 25
    elif unique_orders > len(orders) * 0.7:
        print("⚠️  Moderate order diversity")
        quality_score += 15
        warnings.append("Some repeated orders detected")
    else:
        print("❌ Low order diversity (many repeated orders)")
        warnings.append("Poor order diversity - possible weak modulus")

    # Check 2: Order magnitude
    expected_order = N / 4  # For RSA with p,q ≈ √N
    if mean_order > expected_order * 0.1:
        print("✅ Orders have good magnitude")
        quality_score += 25
    else:
        print("❌ Orders are suspiciously small")
        warnings.append("Small orders may indicate weak modulus")
        recommendations.append("Verify N is product of two large primes")

    # Check 3: Regime balance
    if 'HIGH_SNR' in regime_counts:
        high_snr_pct = 100 * regime_counts['HIGH_SNR'] / len(regimes)
        if high_snr_pct > 30:
            print(f"✅ Good HIGH_SNR representation ({high_snr_pct:.1f}%)")
            quality_score += 25
        else:
            print(f"⚠️  Low HIGH_SNR representation ({high_snr_pct:.1f}%)")
            quality_score += 10
    else:
        print("❌ No HIGH_SNR orders found")
        warnings.append("All orders in TRANSITION/LOW_SNR")

    # Check 4: Standard deviation
    cv = std_order / mean_order if mean_order > 0 else 0
    if cv > 0.3:
        print(f"✅ Good order variability (CV = {cv:.2f})")
        quality_score += 25
    elif cv > 0.1:
        print(f"⚠️  Moderate order variability (CV = {cv:.2f})")
        quality_score += 15
    else:
        print(f"❌ Low order variability (CV = {cv:.2f})")
        warnings.append("Orders are too similar")

    # Overall rating
    print(f"\n{'='*70}")
    print(f"OVERALL QUALITY SCORE: {quality_score}/100")

    if quality_score >= 80:
        rating = "EXCELLENT"
        emoji = "🟢"
        summary = "RSA modulus appears cryptographically sound"
    elif quality_score >= 60:
        rating = "GOOD"
        emoji = "🟡"
        summary = "RSA modulus acceptable but some concerns"
    elif quality_score >= 40:
        rating = "FAIR"
        emoji = "🟠"
        summary = "RSA modulus may have weaknesses"
    else:
        rating = "POOR"
        emoji = "🔴"
        summary = "RSA modulus shows signs of weakness"

    print(f"{emoji} Rating: {rating}")
    print(f"{'='*70}")
    print(f"\n{summary}")

    if warnings:
        print(f"\n⚠️  Warnings:")
        for w in warnings:
            print(f"  - {w}")

    if recommendations:
        print(f"\n💡 Recommendations:")
        for r in recommendations:
            print(f"  - {r}")

    return {
        'N': N,
        'bit_length': N.bit_length(),
        'num_bases_tested': len(orders),
        'mean_order': float(mean_order),
        'std_order': float(std_order),
        'regime_distribution': dict(regime_counts),
        'quality_score': quality_score,
        'rating': rating,
        'warnings': warnings,
        'recommendations': recommendations
    }


def main():
    parser = argparse.ArgumentParser(
        description='Assess RSA modulus quality using VRA order structure analysis'
    )
    parser.add_argument(
        'modulus',
        type=int,
        help='RSA modulus N to analyze'
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=20,
        help='Number of random bases to test (default: 20)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output with detailed analysis'
    )

    args = parser.parse_args()

    # Sanity checks
    if args.modulus < 100:
        print("❌ Error: Modulus too small (must be > 100)")
        sys.exit(1)

    if args.modulus.bit_length() < 512:
        print(f"⚠️  Warning: Modulus is small ({args.modulus.bit_length()} bits)")
        print("   RSA typically uses 2048-4096 bit moduli")

    # Run analysis
    report = analyze_rsa_modulus(args.modulus, num_samples=args.samples)

    if report.get('status') == 'error':
        sys.exit(1)

    # Exit code based on quality
    if report['quality_score'] >= 60:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
