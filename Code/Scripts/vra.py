#!/usr/bin/env python3
"""
VRA Command Line Interface
===========================

Simple CLI for running Vaca Resonance Analysis.

Examples:
    # Run analysis for N=1009, r=168, M values 1,4,8,16
    python vra.py run --N 1009 --r 168 --M 1,4,8,16

    # Run with custom FFT length and output directory
    python vra.py run --N 1009 --r 168 --M 1,4,8,16 --L 65536 --output results/

    # Show examples
    python vra.py examples

Author: Dylan Vaca
Date: October 2025
"""

import argparse
import sys
from pathlib import Path

# Add Code directory to path
CODE_DIR = Path(__file__).parent.parent / "VRA"
sys.path.insert(0, str(CODE_DIR))

try:
    from core import (
        modular_sequence,
        phase_embed,
        apply_window,
        compute_spectrum,
        compute_averaged_spectrum,
        compute_concentration,
        compute_precision_recall,
        validated_radius,
        classify_regime,
        multiplicative_order
    )
    import numpy as np
except ImportError as e:
    print(f"Error: Failed to import VRA core functions: {e}", file=sys.stderr)
    print("Make sure you're running from the VRA directory.", file=sys.stderr)
    sys.exit(1)


def run_analysis(args):
    """Run VRA analysis"""
    N = args.N
    r = args.r
    M_values = [int(m.strip()) for m in args.M.split(',')]
    L = args.L if args.L else max(8192, r * 8)
    x0 = args.seed
    window = args.window
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"VRA Analysis")
    print(f"=" * 60)
    print(f"Modulus N:        {N}")
    print(f"Order r:          {r}")
    print(f"r/N ratio:        {r/N:.4f}")
    print(f"M values:         {M_values}")
    print(f"FFT length L:     {L}")
    print(f"Window:           {window}")
    print(f"Seed x0:          {x0}")
    print(f"=" * 60)

    # Classify regime
    regime, base_req = classify_regime(N, r)
    print(f"\nRegime: {regime}")
    print(f"Base requirement: {base_req}")

    # Compute validated radius
    R = validated_radius(L)
    print(f"Validated radius R: {R} bins")

    # Find bases with order r
    print(f"\nFinding bases with order r={r}...")
    max_M = max(M_values)
    bases = []

    for a in range(2, N):
        if len(bases) >= max_M:
            break
        if np.gcd(a, N) == 1:
            order = multiplicative_order(a, N)
            if order == r:
                bases.append(a)

    if len(bases) < max_M:
        print(f"Warning: Only found {len(bases)} bases with order {r}")
        print(f"Requested M={max_M}, will use available bases")
        M_values = [m for m in M_values if m <= len(bases)]

    print(f"Found {len(bases)} bases: {bases[:10]}{'...' if len(bases) > 10 else ''}")

    # Run analysis for each M
    results = []
    print(f"\nRunning analysis...")

    for M in M_values:
        print(f"\n  M = {M}:")
        bases_subset = bases[:M]

        # Compute averaged spectrum
        mag2_avg = compute_averaged_spectrum(
            N, bases_subset, x0, L // 8, zp=8, window=window
        )

        # Compute concentration
        concentration = compute_concentration(mag2_avg)
        print(f"    Concentration: {concentration:.6f}")

        # Compute precision/recall
        expected_bins = [(k * L // r) % L for k in range(r)]
        metrics = compute_precision_recall(mag2_avg, expected_bins, R)
        print(f"    Precision: {metrics['precision']:.1%}")
        print(f"    Recall: {metrics['recall']:.1%}")
        print(f"    F1: {metrics['f1']:.3f}")
        print(f"    Peaks detected: {metrics['num_peaks']}")

        results.append({
            'M': M,
            'concentration': float(concentration),
            'precision': float(metrics['precision']),
            'recall': float(metrics['recall']),
            'f1': float(metrics['f1']),
            'num_peaks': int(metrics['num_peaks'])
        })

    # Compute √M fit if multiple M values
    if len(M_values) >= 3:
        sqrt_M = np.sqrt(M_values)
        concentrations = [r['concentration'] for r in results]
        slope, intercept = np.polyfit(sqrt_M, concentrations, 1)

        # R²
        ss_res = np.sum((concentrations - (slope * sqrt_M + intercept))**2)
        ss_tot = np.sum((concentrations - np.mean(concentrations))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        print(f"\n√M Fit:")
        print(f"  Slope: {slope:.6f}")
        print(f"  R²: {r_squared:.4f}")

        # Save results
        import json
        from datetime import datetime

        output_file = output_dir / f"vra_N{N}_r{r}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_data = {
            'parameters': {
                'N': N,
                'r': r,
                'r_over_N': r / N,
                'L': L,
                'window': window,
                'regime': regime,
                'base_requirement': base_req
            },
            'M_values': M_values,
            'results': results,
            'sqrt_m_fit': {
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': float(r_squared)
            }
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\nResults saved to: {output_file}")


def show_examples():
    """Show usage examples"""
    examples = """
VRA CLI Examples
================

1. TRANSITION regime (r=168, N=1009):
   python vra.py run --N 1009 --r 168 --M 1,4,8,16

2. LOW SNR regime (r=504, N=1009):
   python vra.py run --N 1009 --r 504 --M 1,4,8,16,32

3. HIGH SNR regime with custom parameters:
   python vra.py run --N 1009 --r 8 --M 1,4,8,16,32 --L 8192 --window hann

4. Custom output directory:
   python vra.py run --N 1009 --r 168 --M 1,4,8 --output my_results/

Regime Guidelines:
------------------
- HIGH SNR (r/N < 0.15): Phase-aligned bases recommended, L ≤ 8192
- TRANSITION (0.15 ≤ r/N < 0.26): Any bases work, L ≤ 262144
- LOW SNR (r/N ≥ 0.26): Any bases work, robust to large L
"""
    print(examples)


def main():
    parser = argparse.ArgumentParser(
        description="VRA - Vaca Resonance Analysis CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run VRA analysis')
    run_parser.add_argument('--N', type=int, required=True, help='Modulus')
    run_parser.add_argument('--r', type=int, required=True, help='Multiplicative order')
    run_parser.add_argument('--M', type=str, required=True, help='Comma-separated M values (e.g., 1,4,8,16)')
    run_parser.add_argument('--L', type=int, help='FFT length (default: auto)')
    run_parser.add_argument('--window', type=str, default='hann',
                          choices=['hann', 'hamming', 'blackman', 'none'],
                          help='Window function')
    run_parser.add_argument('--seed', type=int, default=1, help='Starting seed x0')
    run_parser.add_argument('--output', type=str, default='results',
                          help='Output directory')

    # Examples command
    examples_parser = subparsers.add_parser('examples', help='Show usage examples')

    args = parser.parse_args()

    if args.command == 'run':
        run_analysis(args)
    elif args.command == 'examples':
        show_examples()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
