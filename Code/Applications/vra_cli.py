#!/usr/bin/env python3
"""
VRA Command-Line Interface
===========================

Simple CLI for running VRA order detection on custom parameters.

Usage:
    python3 vra_cli.py --N 1009 --r 168 --M 4
    python3 vra_cli.py --N 997 --find-order --base 2

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
    compute_precision_recall,
    validated_radius,
    classify_regime
)


def find_bases_with_order(N, r, M):
    """Find M bases with order r in Z_N."""
    bases = []
    for a in range(2, N):
        if len(bases) >= M:
            break
        if np.gcd(a, N) == 1:
            if multiplicative_order(a, N) == r:
                bases.append(a)
    return bases


def run_vra(N, r, M, L=500, verbose=True):
    """Run VRA and return results."""
    if verbose:
        print(f"\n{'='*70}")
        print(f"VRA Order Detection")
        print(f"{'='*70}")
        print(f"Parameters: N={N}, r={r}, M={M}, L={L}")

    # Find bases
    if verbose:
        print(f"\nFinding {M} bases with order {r}...")

    bases = find_bases_with_order(N, r, M)

    if len(bases) < M:
        print(f"❌ Error: Could only find {len(bases)}/{M} bases with order {r}")
        return None

    if verbose:
        print(f"✅ Found bases: {bases}")

    # Run VRA
    zp = 4
    mag2 = compute_averaged_spectrum(N, bases, 1, L, zp, window="hann")
    concentration = compute_concentration(mag2)

    # Expected harmonic bins
    Lzp = L * zp
    harmonic_bins = [int(round(k * Lzp / r)) for k in range(1, r)]

    # Compute precision/recall
    R = validated_radius(Lzp)
    metrics = compute_precision_recall(mag2, harmonic_bins, R)

    # Classify regime
    regime = classify_regime(N, r)

    if verbose:
        print(f"\nResults:")
        print(f"  Concentration: {concentration:.4f}")
        print(f"  Precision: {metrics['precision']:.3f}")
        print(f"  Recall: {metrics['recall']:.3f}")
        print(f"  True Positives: {metrics['TP']}")
        print(f"  False Positives: {metrics['FP']}")
        print(f"  Regime: {regime}")
        print(f"  ρ = r/N = {r/N:.4f}")

    return {
        'N': N,
        'r': r,
        'M': M,
        'bases': bases,
        'concentration': float(concentration),
        'precision': float(metrics['precision']),
        'recall': float(metrics['recall']),
        'regime': regime,
        'rho': r / N
    }


def main():
    parser = argparse.ArgumentParser(
        description='VRA Command-Line Tool for Multiplicative Order Detection'
    )
    parser.add_argument('--N', type=int, required=True, help='Modulus')
    parser.add_argument('--r', type=int, help='Target multiplicative order')
    parser.add_argument('--M', type=int, default=4, help='Number of bases to average (default: 4)')
    parser.add_argument('--L', type=int, default=500, help='Sequence length (default: 500)')
    parser.add_argument('--find-order', action='store_true', help='Find order of given base')
    parser.add_argument('--base', type=int, help='Base to find order of (requires --find-order)')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')

    args = parser.parse_args()

    verbose = not args.quiet

    # Mode 1: Find order of a base
    if args.find_order:
        if args.base is None:
            print("❌ Error: --base required with --find-order")
            sys.exit(1)

        if np.gcd(args.base, args.N) != 1:
            print(f"❌ Error: base {args.base} not coprime to N={args.N}")
            sys.exit(1)

        r = multiplicative_order(args.base, args.N)
        if r is None:
            print(f"❌ Could not compute order (max iterations exceeded)")
            sys.exit(1)

        print(f"ord_{args.N}({args.base}) = {r}")
        rho = r / args.N
        regime = classify_regime(args.N, r)
        print(f"ρ = {rho:.4f}, Regime: {regime}")
        sys.exit(0)

    # Mode 2: Run VRA
    if args.r is None:
        print("❌ Error: --r (target order) required for VRA detection")
        sys.exit(1)

    result = run_vra(args.N, args.r, args.M, args.L, verbose=verbose)

    if result is None:
        sys.exit(1)

    # Exit with precision as success indicator
    if result['precision'] >= 0.95:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
