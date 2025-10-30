#!/usr/bin/env python3
"""
Extended Moduli Robustness Sweep
=================================

Test VRA across 20+ diverse moduli types to validate generalization:
- Small primes (3-4 digit)
- Safe primes (N = 2p+1)
- Carmichael numbers
- Prime powers (p²)
- Semiprimes (RSA-like)
- Sophie Germain primes

Addresses TODO.md Phase 1.2: "Test 20+ diverse moduli"

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


def is_prime(n):
    """Simple primality test for small n"""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


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


def test_modulus(N, modulus_type, test_points, M_values=[1, 4, 8, 16, 32], L=65536,
                 window='hann', num_bootstrap=100):
    """Test VRA on a single modulus across regime points

    Parameters:
        N (int): Modulus
        modulus_type (str): Type description
        test_points (list): List of target r/N ratios
        M_values (list): M values for √M sweep
        L (int): FFT length
        window (str): Window function
        num_bootstrap (int): Bootstrap samples for CI

    Returns:
        dict: Test results
    """
    print(f"\n{'='*70}")
    print(f"Testing N = {N} ({modulus_type})")
    print(f"{'='*70}")

    results = {
        'N': N,
        'modulus_type': modulus_type,
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


def get_diverse_moduli():
    """Generate diverse moduli test set

    Returns:
        list of tuples: (N, modulus_type)
    """
    moduli = []

    # Small primes (3-4 digit)
    small_primes = [991, 997, 1009, 1013, 1021, 1031, 1033, 1039]
    for p in small_primes:
        if is_prime(p):
            moduli.append((p, "small prime"))

    # Safe primes (N = 2p+1 where both p and N are prime)
    # p is a Sophie Germain prime, N is a safe prime
    sophie_germain = [5, 11, 23, 29, 41, 53, 83, 89, 113, 131]
    for p in sophie_germain:
        N = 2 * p + 1
        if is_prime(N):
            moduli.append((N, f"safe prime (2*{p}+1)"))

    # Carmichael numbers (composite numbers with special properties)
    carmichael = [561, 1105, 1729]
    for N in carmichael:
        moduli.append((N, "Carmichael number"))

    # Prime powers (p²)
    prime_bases = [23, 29, 31, 37]
    for p in prime_bases:
        N = p * p
        moduli.append((N, f"prime power ({p}²)"))

    # Semiprimes (RSA-like: N = p*q)
    semiprime_pairs = [
        (31, 37),   # N = 1147
        (41, 43),   # N = 1763
        (47, 53),   # N = 2491
        (59, 61),   # N = 3599
        (67, 71),   # N = 4757
    ]
    for p, q in semiprime_pairs:
        N = p * q
        moduli.append((N, f"semiprime ({p}*{q})"))

    return moduli


def run_extended_sweep():
    """Run extended moduli sweep with 20+ diverse types"""

    moduli = get_diverse_moduli()

    # Test points covering regimes
    # Use fewer points per modulus to keep runtime reasonable
    test_points = [
        0.10,   # HIGH SNR
        0.15,   # TRANSITION boundary
        0.26,   # LOW SNR boundary
        0.40,   # Mid LOW SNR
    ]

    M_values = [1, 4, 8, 16, 32]
    L = 65536

    print("VRA Extended Moduli Sweep")
    print("=" * 70)
    print(f"Number of moduli: {len(moduli)}")
    print(f"Modulus types:")
    type_counts = {}
    for _, mtype in moduli:
        type_counts[mtype.split()[0]] = type_counts.get(mtype.split()[0], 0) + 1
    for mtype, count in sorted(type_counts.items()):
        print(f"  {mtype}: {count}")
    print(f"Target ρ points: {test_points}")
    print(f"M values: {M_values}")
    print(f"FFT length L: {L}")
    print(f"Bootstrap samples: 100")

    all_results = {
        'metadata': {
            'date': datetime.now().isoformat(),
            'num_moduli': len(moduli),
            'moduli': [{'N': N, 'type': mtype} for N, mtype in moduli],
            'target_rho_points': test_points,
            'M_values': M_values,
            'L': L,
            'num_bootstrap': 100
        },
        'results': []
    }

    for N, modulus_type in moduli:
        try:
            result = test_modulus(N, modulus_type, test_points,
                                 M_values=M_values, L=L, num_bootstrap=100)
            all_results['results'].append(result)
        except Exception as e:
            print(f"ERROR testing N={N}: {e}")
            continue

    # Save results
    output_dir = Path(__file__).parent.parent.parent / "Data" / "extended_moduli"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_extended_moduli_sweep.json"

    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Results saved to: {output_file}")

    # Generate summary
    generate_summary(all_results)

    return all_results


def generate_summary(results):
    """Generate summary statistics across moduli types"""

    print(f"\n{'='*70}")
    print("SUMMARY: Statistics by Modulus Type and Regime")
    print(f"{'='*70}")

    # Collect by type and regime
    type_regime_stats = {}

    for modulus_result in results['results']:
        N = modulus_result['N']
        mtype = modulus_result['modulus_type'].split()[0]  # First word

        if mtype not in type_regime_stats:
            type_regime_stats[mtype] = {'HIGH_SNR': [], 'TRANSITION': [], 'LOW_SNR': []}

        for test_point in modulus_result['test_points']:
            regime = test_point['regime']
            r2 = test_point['sqrt_m_fit']['r_squared']
            rho = test_point['actual_rho']
            precision = np.mean(test_point['precisions'])

            type_regime_stats[mtype][regime].append({
                'N': N,
                'rho': rho,
                'r2': r2,
                'precision': precision
            })

    # Print by modulus type
    for mtype in sorted(type_regime_stats.keys()):
        print(f"\n{mtype.upper()}:")

        for regime in ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']:
            data = type_regime_stats[mtype][regime]
            if len(data) == 0:
                continue

            r2_values = [d['r2'] for d in data]
            prec_values = [d['precision'] for d in data]

            print(f"  {regime}:")
            print(f"    Tests: {len(data)}")
            print(f"    R²: {np.mean(r2_values):.4f} ± {np.std(r2_values):.4f} "
                  f"[{min(r2_values):.4f}, {max(r2_values):.4f}]")
            print(f"    Precision: {np.mean(prec_values):.1%} ± {np.std(prec_values):.1%}")

    # Overall statistics by regime
    print(f"\n{'='*70}")
    print("OVERALL STATISTICS BY REGIME")
    print(f"{'='*70}")

    regime_all = {'HIGH_SNR': [], 'TRANSITION': [], 'LOW_SNR': []}

    for mtype in type_regime_stats:
        for regime in regime_all:
            regime_all[regime].extend(type_regime_stats[mtype][regime])

    for regime in ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']:
        data = regime_all[regime]
        if len(data) == 0:
            continue

        r2_values = [d['r2'] for d in data]
        prec_values = [d['precision'] for d in data]

        print(f"\n{regime}:")
        print(f"  Total tests: {len(data)}")
        print(f"  R²: {np.mean(r2_values):.4f} ± {np.std(r2_values):.4f}")
        print(f"      Median: {np.median(r2_values):.4f}")
        print(f"      Range: [{min(r2_values):.4f}, {max(r2_values):.4f}]")
        print(f"  Precision: {np.mean(prec_values):.1%} ± {np.std(prec_values):.1%}")
        print(f"             Median: {np.median(prec_values):.1%}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VRA Extended Moduli Sweep')
    parser.add_argument('--quick', action='store_true',
                       help='Quick test (fewer moduli)')
    parser.add_argument('--list-moduli', action='store_true',
                       help='List all moduli and exit')

    args = parser.parse_args()

    if args.list_moduli:
        moduli = get_diverse_moduli()
        print(f"Total moduli: {len(moduli)}\n")
        for N, mtype in moduli:
            print(f"N = {N:5d} ({mtype})")
    elif args.quick:
        print("Quick test mode - testing subset")
        moduli = get_diverse_moduli()[:5]
        for N, mtype in moduli:
            result = test_modulus(N, mtype, [0.15, 0.26], M_values=[1, 4, 8, 16],
                                 L=32768, num_bootstrap=50)
    else:
        # Full sweep
        results = run_extended_sweep()
