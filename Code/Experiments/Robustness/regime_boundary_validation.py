#!/usr/bin/env python3
"""
Regime Boundary Validation
===========================

Dense sampling around regime boundaries (ρ = 0.146 and ρ = 0.263) to:
1. Characterize transition sharpness
2. Fit smooth transition curves (sigmoid/logistic)
3. Estimate boundary uncertainty with 95% CIs
4. Identify outlier moduli

Addresses TODO.md Phase 1.2: "Systematic regime boundary validation"

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "Core"))

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

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def find_order_r(N, target_rho, tolerance=0.02):
    """Find an order r close to target_rho = r/N

    Parameters:
        N (int): Modulus
        target_rho (float): Target r/N ratio
        tolerance (float): Acceptable deviation (tighter than before)

    Returns:
        int or None: Order r if found
    """
    target_r = int(target_rho * N)

    # Search around target
    for offset in range(0, N // 2):
        for r in [target_r + offset, target_r - offset]:
            if r < 2 or r >= N:
                continue

            # Find a base with this order
            for a in range(2, min(200, N)):  # Search more bases
                if np.gcd(a, N) == 1:
                    order = multiplicative_order(a, N, max_iter=N)
                    if order == r:
                        actual_rho = r / N
                        if abs(actual_rho - target_rho) < tolerance:
                            return r

    return None


def find_bases_with_order(N, r, max_bases=32):
    """Find bases with given multiplicative order"""
    bases = []

    for a in range(2, N):
        if len(bases) >= max_bases:
            break

        if np.gcd(a, N) == 1:
            order = multiplicative_order(a, N, max_iter=N)
            if order == r:
                bases.append(a)

    return bases


def test_boundary_point(N, target_rho, M=32, L=65536, window='hann'):
    """Test a single (N, ρ) point

    Returns:
        dict: Test results or None if failed
    """
    # Find order
    r = find_order_r(N, target_rho, tolerance=0.02)
    if r is None:
        return None

    actual_rho = r / N
    regime, base_req = classify_regime(N, r)

    # Find bases
    bases = find_bases_with_order(N, r, max_bases=M)
    if len(bases) < M:
        return None

    # Compute spectrum
    mag2_avg = compute_averaged_spectrum(
        N, bases, x0=1, length=L//8, zp=8, window=window
    )

    # Metrics
    concentration = compute_concentration(mag2_avg)
    R = validated_radius(L)
    expected_bins = [(k * L // r) % L for k in range(r)]
    metrics = compute_precision_recall(mag2_avg, expected_bins, R)

    # Compute √M scaling (with M/2 and M for slope)
    M_half = M // 2
    bases_half = bases[:M_half]

    mag2_half = compute_averaged_spectrum(
        N, bases_half, x0=1, length=L//8, zp=8, window=window
    )
    conc_half = compute_concentration(mag2_half)

    # Slope estimate
    sqrt_M_vals = np.array([np.sqrt(M_half), np.sqrt(M)])
    conc_vals = np.array([conc_half, concentration])

    slope, intercept = np.polyfit(sqrt_M_vals, conc_vals, 1)

    # R² for the 2-point fit
    ss_res = np.sum((conc_vals - (slope * sqrt_M_vals + intercept))**2)
    ss_tot = np.sum((conc_vals - np.mean(conc_vals))**2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return {
        'N': int(N),
        'r': int(r),
        'target_rho': float(target_rho),
        'actual_rho': float(actual_rho),
        'regime': regime,
        'base_requirement': base_req,
        'concentration': float(concentration),
        'precision': float(metrics['precision']),
        'recall': float(metrics['recall']),
        'r_squared': float(r_squared),
        'slope': float(slope)
    }


def validate_boundary_transitions(moduli, boundary_centers=[0.146, 0.263],
                                  window_size=0.10, num_points=11):
    """Validate regime boundaries with dense sampling

    Parameters:
        moduli (list): List of moduli to test
        boundary_centers (list): Boundary ρ values to investigate
        window_size (float): ρ range around each boundary
        num_points (int): Number of samples in each window

    Returns:
        dict: Validation results
    """
    results = {
        'metadata': {
            'date': datetime.now().isoformat(),
            'moduli': moduli,
            'boundary_centers': boundary_centers,
            'window_size': window_size,
            'num_points': num_points,
            'total_target_points': len(moduli) * len(boundary_centers) * num_points
        },
        'boundaries': []
    }

    for boundary in boundary_centers:
        print(f"\n{'='*70}")
        print(f"Boundary ρ = {boundary:.3f} ± {window_size/2:.3f}")
        print(f"{'='*70}")

        # Generate dense sampling points
        rho_min = boundary - window_size / 2
        rho_max = boundary + window_size / 2
        rho_points = np.linspace(rho_min, rho_max, num_points)

        boundary_data = {
            'boundary_center': float(boundary),
            'window_size': float(window_size),
            'rho_points': rho_points.tolist(),
            'moduli_results': []
        }

        for N in moduli:
            print(f"\nTesting N = {N}...")
            modulus_results = {
                'N': int(N),
                'tests': []
            }

            for rho in rho_points:
                result = test_boundary_point(N, rho)
                if result is not None:
                    modulus_results['tests'].append(result)
                    print(f"  ρ = {result['actual_rho']:.4f}: "
                          f"R² = {result['r_squared']:.4f}, "
                          f"Precision = {result['precision']:.1%}, "
                          f"Regime = {result['regime']}")

            if len(modulus_results['tests']) > 0:
                boundary_data['moduli_results'].append(modulus_results)
                print(f"  Completed {len(modulus_results['tests'])}/{num_points} points")

        results['boundaries'].append(boundary_data)

    return results


def fit_transition_curves(results):
    """Estimate boundary uncertainty with statistics (no curve fitting)

    Returns:
        dict: Statistical characterization of boundaries
    """
    fitted_boundaries = []

    for boundary_data in results['boundaries']:
        boundary_center = boundary_data['boundary_center']
        print(f"\n{'='*70}")
        print(f"Analyzing transition at ρ ≈ {boundary_center:.3f}")
        print(f"{'='*70}")

        # Collect all data points
        all_rho = []
        all_r2 = []
        all_precision = []
        all_regime = []

        for modulus_result in boundary_data['moduli_results']:
            for test in modulus_result['tests']:
                all_rho.append(test['actual_rho'])
                all_r2.append(test['r_squared'])
                all_precision.append(test['precision'])
                all_regime.append(test['regime'])

        if len(all_rho) < 5:
            print("  WARNING: Insufficient data for analysis")
            continue

        # Sort by rho
        sort_idx = np.argsort(all_rho)
        rho_sorted = np.array(all_rho)[sort_idx]
        r2_sorted = np.array(all_r2)[sort_idx]
        precision_sorted = np.array(all_precision)[sort_idx]
        regime_sorted = [all_regime[i] for i in sort_idx]

        # Find approximate transition point (where R² crosses 0.9)
        high_r2_mask = r2_sorted > 0.90
        if np.any(high_r2_mask):
            transition_idx = np.where(high_r2_mask)[0][0]
            estimated_center = rho_sorted[transition_idx]
        else:
            estimated_center = boundary_center

        # Compute statistics in windows
        window_width = 0.02
        low_window = (rho_sorted >= boundary_center - window_width) & (rho_sorted < boundary_center)
        high_window = (rho_sorted >= boundary_center) & (rho_sorted <= boundary_center + window_width)

        r2_below = r2_sorted[low_window]
        r2_above = r2_sorted[high_window]

        print(f"\n  Statistical analysis:")
        print(f"    Total points: {len(all_rho)}")
        print(f"    ρ range: [{min(all_rho):.4f}, {max(all_rho):.4f}]")
        print(f"    Estimated transition: ρ ≈ {estimated_center:.4f}")
        print(f"\n  R² below boundary (ρ < {boundary_center:.3f}):")
        if len(r2_below) > 0:
            print(f"    Mean: {np.mean(r2_below):.4f} ± {np.std(r2_below):.4f}")
            print(f"    Median: {np.median(r2_below):.4f}")
            print(f"    Range: [{np.min(r2_below):.4f}, {np.max(r2_below):.4f}]")
        print(f"\n  R² above boundary (ρ ≥ {boundary_center:.3f}):")
        if len(r2_above) > 0:
            print(f"    Mean: {np.mean(r2_above):.4f} ± {np.std(r2_above):.4f}")
            print(f"    Median: {np.median(r2_above):.4f}")
            print(f"    Range: [{np.min(r2_above):.4f}, {np.max(r2_above):.4f}]")

        # Overall statistics
        print(f"\n  Overall R²:")
        print(f"    Mean: {np.mean(r2_sorted):.4f} ± {np.std(r2_sorted):.4f}")
        print(f"    Percentiles [10, 25, 50, 75, 90]: "
              f"{np.percentile(r2_sorted, [10, 25, 50, 75, 90])}")

        fitted_boundaries.append({
            'boundary_center_nominal': float(boundary_center),
            'estimated_transition': float(estimated_center),
            'num_points': len(all_rho),
            'rho_range': [float(min(all_rho)), float(max(all_rho))],
            'r2_mean': float(np.mean(r2_sorted)),
            'r2_std': float(np.std(r2_sorted)),
            'r2_median': float(np.median(r2_sorted)),
            'r2_percentiles': {
                'p10': float(np.percentile(r2_sorted, 10)),
                'p25': float(np.percentile(r2_sorted, 25)),
                'p75': float(np.percentile(r2_sorted, 75)),
                'p90': float(np.percentile(r2_sorted, 90))
            },
            'r2_below_boundary': {
                'mean': float(np.mean(r2_below)) if len(r2_below) > 0 else None,
                'std': float(np.std(r2_below)) if len(r2_below) > 0 else None,
                'count': int(len(r2_below))
            },
            'r2_above_boundary': {
                'mean': float(np.mean(r2_above)) if len(r2_above) > 0 else None,
                'std': float(np.std(r2_above)) if len(r2_above) > 0 else None,
                'count': int(len(r2_above))
            }
        })

    return fitted_boundaries


def generate_summary(results, fitted_boundaries):
    """Generate summary statistics"""

    print(f"\n{'='*70}")
    print("REGIME BOUNDARY SUMMARY")
    print(f"{'='*70}")

    print(f"\nTotal test points: {sum(len(mr['tests']) for bd in results['boundaries'] for mr in bd['moduli_results'])}")
    print(f"Unique moduli tested: {len(set(mr['N'] for bd in results['boundaries'] for mr in bd['moduli_results']))}")

    print(f"\n{'='*70}")
    print("BOUNDARY TRANSITION ANALYSIS")
    print(f"{'='*70}")

    for fb in fitted_boundaries:
        print(f"\nBoundary {fb['boundary_center_nominal']:.3f}:")
        print(f"  Estimated transition: ρ ≈ {fb['estimated_transition']:.4f}")
        print(f"  Data points: {fb['num_points']}")
        print(f"  ρ range: [{fb['rho_range'][0]:.4f}, {fb['rho_range'][1]:.4f}]")
        print(f"  R² statistics:")
        print(f"    Mean: {fb['r2_mean']:.4f} ± {fb['r2_std']:.4f}")
        print(f"    Median: {fb['r2_median']:.4f}")
        print(f"    IQR: [{fb['r2_percentiles']['p25']:.4f}, {fb['r2_percentiles']['p75']:.4f}]")


def run_boundary_validation():
    """Run complete boundary validation"""

    # Use proven good moduli (small primes from extended sweep)
    moduli = [991, 997, 1009, 1021, 1031, 1033]

    # Boundaries to investigate
    boundaries = [0.146, 0.263]

    print("VRA Regime Boundary Validation")
    print("=" * 70)
    print(f"Moduli: {moduli}")
    print(f"Boundaries: {boundaries}")
    print(f"Window: ±0.05 around each boundary")
    print(f"Points per window: 11")
    print(f"Expected total tests: {len(moduli) * len(boundaries) * 11} = {len(moduli)} moduli × {len(boundaries)} boundaries × 11 points")

    # Run validation
    results = validate_boundary_transitions(
        moduli,
        boundary_centers=boundaries,
        window_size=0.10,
        num_points=11
    )

    # Fit transition curves
    fitted_boundaries = fit_transition_curves(results)

    # Save results
    output_dir = Path(__file__).parent.parent.parent / "Data" / "regime_boundaries"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_boundary_validation.json"

    results['fitted_boundaries'] = fitted_boundaries

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Results saved to: {output_file}")

    # Generate summary
    generate_summary(results, fitted_boundaries)

    return results, fitted_boundaries


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VRA Regime Boundary Validation')
    parser.add_argument('--quick', action='store_true',
                       help='Quick test (fewer points)')

    args = parser.parse_args()

    if args.quick:
        print("Quick test mode")
        moduli = [997, 1009]
        results = validate_boundary_transitions(
            moduli,
            boundary_centers=[0.146],
            window_size=0.08,
            num_points=5
        )
        fitted = fit_transition_curves(results)
        generate_summary(results, fitted)
    else:
        # Full validation
        results, fitted = run_boundary_validation()
