#!/usr/bin/env python3
"""
Cross-Moduli Robustness Sweep
==============================

Test VRA regime boundaries and √M scaling across multiple moduli to validate
that empirical thresholds (ρ=0.146, 0.263) generalize beyond N=1009.

Test moduli: N=997, N=1013, N=2017 (all prime)
Test orders: Selected to cover HIGH/TRANSITION/LOW SNR regimes

This addresses the generalization concern: "Single modulus tested (N=1009)".

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


def find_order_r(N, target_rho, tolerance=0.05):
    """Find an order r close to target_rho = r/N

    Parameters:
        N (int): Modulus
        target_rho (float): Target r/N ratio
        tolerance (float): Acceptable deviation

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
            for a in range(2, min(100, N)):
                if np.gcd(a, N) == 1:
                    order = multiplicative_order(a, N, max_iter=N)
                    if order == r:
                        actual_rho = r / N
                        if abs(actual_rho - target_rho) < tolerance:
                            return r

    return None


def find_bases_with_order(N, r, max_bases=50):
    """Find bases with given multiplicative order

    Parameters:
        N (int): Modulus
        r (int): Target order
        max_bases (int): Maximum bases to find

    Returns:
        list: Bases with order r
    """
    bases = []

    for a in range(2, N):
        if len(bases) >= max_bases:
            break

        if np.gcd(a, N) == 1:
            order = multiplicative_order(a, N, max_iter=N)
            if order == r:
                bases.append(a)

    return bases


def test_modulus(N, test_points, M_values=[1, 4, 8, 16, 32], L=65536,
                 window='hann', num_bootstrap=100):
    """Test VRA on a single modulus across regime points

    Parameters:
        N (int): Modulus
        test_points (list): List of target r/N ratios
        M_values (list): M values for √M sweep
        L (int): FFT length
        window (str): Window function
        num_bootstrap (int): Bootstrap samples for CI

    Returns:
        dict: Test results
    """
    print(f"\n{'='*70}")
    print(f"Testing N = {N}")
    print(f"{'='*70}")

    results = {
        'N': N,
        'test_points': []
    }

    for target_rho in test_points:
        print(f"\nTarget ρ = {target_rho:.3f}...")

        # Find order near target
        r = find_order_r(N, target_rho, tolerance=0.05)
        if r is None:
            print(f"  WARNING: No order found near ρ={target_rho}")
            continue

        actual_rho = r / N
        regime, base_req = classify_regime(N, r)

        print(f"  Found r = {r} (ρ = {actual_rho:.4f})")
        print(f"  Regime: {regime}, Base requirement: {base_req}")

        # Find bases
        max_M = max(M_values)
        bases = find_bases_with_order(N, r, max_bases=max_M)

        if len(bases) < max_M:
            print(f"  WARNING: Only found {len(bases)} bases, need {max_M}")
            M_values_actual = [m for m in M_values if m <= len(bases)]
        else:
            M_values_actual = M_values

        print(f"  Found {len(bases)} bases")
        print(f"  Testing M = {M_values_actual}")

        # Run M sweep
        concentrations = []
        precisions = []
        recalls = []

        R = validated_radius(L)
        expected_bins = [(k * L // r) % L for k in range(r)]

        for M in M_values_actual:
            bases_subset = bases[:M]

            # Compute averaged spectrum
            mag2_avg = compute_averaged_spectrum(
                N, bases_subset, x0=1, length=L//8, zp=8, window=window
            )

            # Metrics
            concentration = compute_concentration(mag2_avg)
            metrics = compute_precision_recall(mag2_avg, expected_bins, R)

            concentrations.append(float(concentration))
            precisions.append(float(metrics['precision']))
            recalls.append(float(metrics['recall']))

        # Compute √M fit
        sqrt_M = np.sqrt(M_values_actual)
        slope, intercept = np.polyfit(sqrt_M, concentrations, 1)

        ss_res = np.sum((concentrations - (slope * sqrt_M + intercept))**2)
        ss_tot = np.sum((concentrations - np.mean(concentrations))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Bootstrap confidence intervals
        bootstrap_slopes = []
        bootstrap_r2s = []

        for _ in range(num_bootstrap):
            # Resample with replacement
            indices = np.random.choice(len(M_values_actual), len(M_values_actual), replace=True)
            sqrt_M_boot = sqrt_M[indices]
            conc_boot = np.array(concentrations)[indices]

            slope_boot, intercept_boot = np.polyfit(sqrt_M_boot, conc_boot, 1)

            ss_res_boot = np.sum((conc_boot - (slope_boot * sqrt_M_boot + intercept_boot))**2)
            ss_tot_boot = np.sum((conc_boot - np.mean(conc_boot))**2)
            r2_boot = 1 - (ss_res_boot / ss_tot_boot) if ss_tot_boot > 0 else 0

            bootstrap_slopes.append(slope_boot)
            bootstrap_r2s.append(r2_boot)

        # Compute 95% CI
        slope_ci = np.percentile(bootstrap_slopes, [2.5, 97.5])
        r2_ci = np.percentile(bootstrap_r2s, [2.5, 97.5])

        print(f"  √M Fit: slope = {slope:.6f} [{slope_ci[0]:.6f}, {slope_ci[1]:.6f}]")
        print(f"          R² = {r_squared:.4f} [{r2_ci[0]:.4f}, {r2_ci[1]:.4f}]")
        print(f"  Precision: {np.mean(precisions):.1%}")

        results['test_points'].append({
            'target_rho': float(target_rho),
            'r': int(r),
            'actual_rho': float(actual_rho),
            'regime': regime,
            'base_requirement': base_req,
            'num_bases_found': len(bases),
            'M_values': M_values_actual,
            'concentrations': concentrations,
            'precisions': precisions,
            'recalls': recalls,
            'sqrt_m_fit': {
                'slope': float(slope),
                'slope_ci': [float(slope_ci[0]), float(slope_ci[1])],
                'intercept': float(intercept),
                'r_squared': float(r_squared),
                'r_squared_ci': [float(r2_ci[0]), float(r2_ci[1])]
            }
        })

    return results


def run_full_sweep():
    """Run complete cross-moduli robustness sweep"""

    # Test moduli (all prime)
    moduli = [997, 1009, 1013, 2017]

    # Test points covering regimes
    test_points = [
        0.01,   # HIGH SNR
        0.10,   # HIGH SNR boundary
        0.15,   # TRANSITION boundary
        0.20,   # Mid TRANSITION
        0.26,   # LOW SNR boundary
        0.40,   # Mid LOW SNR
        0.50    # Deep LOW SNR
    ]

    M_values = [1, 4, 8, 16, 32]
    L = 65536

    print("VRA Cross-Moduli Robustness Sweep")
    print("=" * 70)
    print(f"Test moduli: {moduli}")
    print(f"Target ρ points: {test_points}")
    print(f"M values: {M_values}")
    print(f"FFT length L: {L}")
    print(f"Bootstrap samples: 100")

    all_results = {
        'metadata': {
            'date': datetime.now().isoformat(),
            'moduli': moduli,
            'target_rho_points': test_points,
            'M_values': M_values,
            'L': L,
            'num_bootstrap': 100
        },
        'results': []
    }

    for N in moduli:
        result = test_modulus(N, test_points, M_values=M_values, L=L, num_bootstrap=100)
        all_results['results'].append(result)

    # Save results
    output_dir = Path(__file__).parent.parent.parent / "Data" / "cross_moduli"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_cross_moduli_sweep.json"

    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Results saved to: {output_file}")

    # Generate summary
    generate_summary(all_results)

    return all_results


def generate_summary(results):
    """Generate summary statistics across moduli"""

    print(f"\n{'='*70}")
    print("SUMMARY: R² Statistics by Regime")
    print(f"{'='*70}")

    # Collect R² by regime
    regime_r2 = {'HIGH_SNR': [], 'TRANSITION': [], 'LOW_SNR': []}

    for modulus_result in results['results']:
        N = modulus_result['N']
        for test_point in modulus_result['test_points']:
            regime = test_point['regime']
            r2 = test_point['sqrt_m_fit']['r_squared']
            rho = test_point['actual_rho']
            regime_r2[regime].append((N, rho, r2))

    for regime, values in regime_r2.items():
        if len(values) == 0:
            continue

        r2_values = [v[2] for v in values]
        print(f"\n{regime}:")
        print(f"  Count: {len(values)}")
        print(f"  R² range: [{min(r2_values):.4f}, {max(r2_values):.4f}]")
        print(f"  R² mean: {np.mean(r2_values):.4f} ± {np.std(r2_values):.4f}")
        print(f"  Test points:")
        for N, rho, r2 in values:
            print(f"    N={N}, ρ={rho:.4f}: R²={r2:.4f}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VRA Cross-Moduli Robustness Sweep')
    parser.add_argument('--quick', action='store_true',
                       help='Quick test (fewer points)')

    args = parser.parse_args()

    if args.quick:
        print("Quick test mode - testing subset")
        # Quick test
        results = test_modulus(997, [0.15, 0.26, 0.50], M_values=[1, 4, 8, 16],
                              L=32768, num_bootstrap=50)
    else:
        # Full sweep
        results = run_full_sweep()
