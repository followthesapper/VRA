#!/usr/bin/env python3
"""
Analyze Cross-Moduli Sweep Results
===================================

Extract statistics from the 4-moduli × 7-regime-point robustness sweep
to validate VRA regime boundaries generalize beyond N=1009.

Author: Dylan Vaca
Date: October 2025
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict

def load_results(json_path):
    """Load cross-moduli sweep results"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def classify_regime(rho):
    """Classify regime based on ρ value"""
    if rho < 0.146:
        return 'HIGH_SNR'
    elif rho < 0.263:
        return 'TRANSITION'
    else:
        return 'LOW_SNR'

def analyze_by_regime(data):
    """Group results by regime and compute statistics"""

    # Collect data by regime
    regime_data = defaultdict(lambda: {
        'r_squared': [],
        'slopes': [],
        'precisions': [],
        'data_points': []
    })

    for modulus_result in data['results']:
        N = modulus_result['N']

        for test_point in modulus_result['test_points']:
            rho = test_point['actual_rho']
            r = test_point['r']
            regime = classify_regime(rho)

            # Skip if insufficient bases for meaningful fit
            if len(test_point['M_values']) < 3:
                continue

            r_sq = test_point['sqrt_m_fit']['r_squared']
            slope = test_point['sqrt_m_fit']['slope']

            # Average precision across M values
            avg_precision = np.mean(test_point['precisions'])

            regime_data[regime]['r_squared'].append(r_sq)
            regime_data[regime]['slopes'].append(slope)
            regime_data[regime]['precisions'].append(avg_precision)
            regime_data[regime]['data_points'].append({
                'N': N,
                'r': r,
                'rho': rho,
                'r_squared': r_sq,
                'slope': slope,
                'precision': avg_precision
            })

    # Compute summary statistics
    summary = {}
    for regime in ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']:
        if not regime_data[regime]['r_squared']:
            summary[regime] = None
            continue

        r_sq_array = np.array(regime_data[regime]['r_squared'])
        slope_array = np.array(regime_data[regime]['slopes'])
        prec_array = np.array(regime_data[regime]['precisions'])

        summary[regime] = {
            'n_points': len(r_sq_array),
            'r_squared': {
                'mean': np.mean(r_sq_array),
                'median': np.median(r_sq_array),
                'std': np.std(r_sq_array),
                'min': np.min(r_sq_array),
                'max': np.max(r_sq_array),
                'q25': np.percentile(r_sq_array, 25),
                'q75': np.percentile(r_sq_array, 75)
            },
            'slope': {
                'mean': np.mean(slope_array),
                'median': np.median(slope_array),
                'std': np.std(slope_array),
                'min': np.min(slope_array),
                'max': np.max(slope_array)
            },
            'precision': {
                'mean': np.mean(prec_array),
                'median': np.median(prec_array),
                'min': np.min(prec_array),
                'max': np.max(prec_array)
            },
            'data_points': regime_data[regime]['data_points']
        }

    return summary

def estimate_regime_boundaries(data):
    """Estimate regime boundary ρ values from cross-moduli data"""

    # Collect all (ρ, R²) pairs
    rho_rsq_pairs = []

    for modulus_result in data['results']:
        N = modulus_result['N']

        for test_point in modulus_result['test_points']:
            # Skip insufficient data
            if len(test_point['M_values']) < 3:
                continue

            rho = test_point['actual_rho']
            r_sq = test_point['sqrt_m_fit']['r_squared']

            rho_rsq_pairs.append((rho, r_sq, N, test_point['r']))

    # Sort by ρ
    rho_rsq_pairs.sort()

    # Find transition points
    # HIGH/TRANSITION boundary: where R² consistently exceeds 0.90
    # TRANSITION/LOW boundary: where R² consistently exceeds 0.95

    boundaries = {
        'high_transition': None,
        'transition_low': None
    }

    # Look for R² > 0.90 boundary (HIGH → TRANSITION)
    for i, (rho, r_sq, N, r) in enumerate(rho_rsq_pairs):
        if r_sq > 0.90:
            # Check if next few points also exceed 0.90
            if i + 1 < len(rho_rsq_pairs) and rho_rsq_pairs[i+1][1] > 0.90:
                boundaries['high_transition'] = rho
                break

    # Look for R² > 0.95 boundary (TRANSITION → LOW)
    for i, (rho, r_sq, N, r) in enumerate(rho_rsq_pairs):
        if rho > 0.20 and r_sq > 0.95:  # Start looking after ρ=0.20
            # Check if subsequent points maintain > 0.95
            if i + 1 < len(rho_rsq_pairs) and rho_rsq_pairs[i+1][1] > 0.95:
                boundaries['transition_low'] = rho
                break

    return boundaries, rho_rsq_pairs

def print_summary(summary, boundaries):
    """Print formatted summary statistics"""

    print("=" * 80)
    print("CROSS-MODULI ROBUSTNESS SWEEP ANALYSIS")
    print("=" * 80)
    print()
    print("Moduli tested: N = 997, 1009, 1013, 2017")
    print("Target ρ points: 0.01, 0.10, 0.15, 0.20, 0.26, 0.40, 0.50")
    print()

    print("-" * 80)
    print("REGIME STATISTICS")
    print("-" * 80)

    for regime in ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']:
        if summary[regime] is None:
            continue

        stats = summary[regime]
        print(f"\n{regime}:")
        print(f"  Data points: {stats['n_points']}")
        print(f"  R² statistics:")
        print(f"    Mean:   {stats['r_squared']['mean']:.4f}")
        print(f"    Median: {stats['r_squared']['median']:.4f}")
        print(f"    Std:    {stats['r_squared']['std']:.4f}")
        print(f"    Range:  [{stats['r_squared']['min']:.4f}, {stats['r_squared']['max']:.4f}]")
        print(f"    IQR:    [{stats['r_squared']['q25']:.4f}, {stats['r_squared']['q75']:.4f}]")
        print(f"  Slope statistics:")
        print(f"    Mean:   {stats['slope']['mean']:.6f}")
        print(f"    Median: {stats['slope']['median']:.6f}")
        print(f"    Range:  [{stats['slope']['min']:.6f}, {stats['slope']['max']:.6f}]")
        print(f"  Precision:")
        print(f"    Mean:   {stats['precision']['mean']:.1%}")
        print(f"    Range:  [{stats['precision']['min']:.1%}, {stats['precision']['max']:.1%}]")

    print()
    print("-" * 80)
    print("REGIME BOUNDARY ESTIMATES")
    print("-" * 80)
    print(f"  HIGH/TRANSITION boundary: ρ ≈ {boundaries['high_transition']:.3f}")
    print(f"  TRANSITION/LOW boundary:  ρ ≈ {boundaries['transition_low']:.3f}")
    print()
    print("  (Original N=1009 estimates: ρ₁ = 0.146, ρ₂ = 0.263)")
    print()

    print("-" * 80)
    print("DETAILED DATA POINTS")
    print("-" * 80)

    for regime in ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']:
        if summary[regime] is None:
            continue

        print(f"\n{regime}:")
        print(f"  {'N':>6} {'r':>6} {'ρ':>8} {'R²':>8} {'Slope':>12} {'Prec':>8}")
        print(f"  {'-'*6} {'-'*6} {'-'*8} {'-'*8} {'-'*12} {'-'*8}")

        for dp in sorted(summary[regime]['data_points'], key=lambda x: (x['N'], x['rho'])):
            print(f"  {dp['N']:6d} {dp['r']:6d} {dp['rho']:8.4f} "
                  f"{dp['r_squared']:8.4f} {dp['slope']:12.6f} "
                  f"{dp['precision']:8.1%}")

    print()
    print("=" * 80)

def save_summary(summary, boundaries, rho_rsq_pairs, output_file):
    """Save summary to JSON"""

    output_data = {
        'date': str(Path(output_file).name),
        'regime_statistics': {},
        'boundaries': boundaries,
        'all_points': []
    }

    # Format statistics
    for regime in ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']:
        if summary[regime] is not None:
            output_data['regime_statistics'][regime] = {
                'n_points': summary[regime]['n_points'],
                'r_squared': summary[regime]['r_squared'],
                'slope': summary[regime]['slope'],
                'precision': summary[regime]['precision']
            }

    # Add all points
    for rho, r_sq, N, r in rho_rsq_pairs:
        output_data['all_points'].append({
            'N': int(N),
            'r': int(r),
            'rho': float(rho),
            'r_squared': float(r_sq),
            'regime': classify_regime(rho)
        })

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"Summary saved to: {output_file}")

def main():
    # Load data
    data_file = Path(__file__).parent.parent.parent / 'Data' / 'cross_moduli' / '20251029_220803_cross_moduli_sweep.json'

    if not data_file.exists():
        print(f"ERROR: Data file not found: {data_file}")
        return

    print(f"Loading: {data_file}")
    data = load_results(data_file)

    # Analyze by regime
    summary = analyze_by_regime(data)

    # Estimate boundaries
    boundaries, rho_rsq_pairs = estimate_regime_boundaries(data)

    # Print summary
    print_summary(summary, boundaries)

    # Save summary
    output_dir = Path(__file__).parent.parent.parent / 'Data' / 'cross_moduli'
    output_file = output_dir / '20251029_220803_cross_moduli_summary.json'
    save_summary(summary, boundaries, rho_rsq_pairs, output_file)

if __name__ == '__main__':
    main()
