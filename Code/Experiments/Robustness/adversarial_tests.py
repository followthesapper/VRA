#!/usr/bin/env python3
"""
Adversarial Robustness Tests
=============================

Test VRA with adversarial inputs designed to break detection:
1. Worst-case base selection (adversarially chosen phases)
2. Pathological orders (large prime factors)
3. Hostile moduli (specific algebraic structure)

Addresses TODO.md Phase 4.1: "Adversarial testing"

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
    compute_averaged_spectrum,
    compute_concentration,
    compute_precision_recall,
    validated_radius,
    classify_regime
)


def find_bases_with_order(N, r, max_bases=100):
    """Find all bases with given order"""
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


def select_adversarial_bases(N, r, bases, M, strategy='max_phase_spread'):
    """Select M bases using adversarial strategy

    Parameters:
        N (int): Modulus
        r (int): Order
        bases (list): Available bases with order r
        M (int): Number to select
        strategy (str): Selection strategy

    Returns:
        list: M selected bases
    """
    if len(bases) < M:
        return bases[:M]

    if strategy == 'max_phase_spread':
        # Select bases with maximally spread initial phases
        # This tries to cause destructive interference
        phases = [(a % N) / N for a in bases]
        sorted_bases = [b for _, b in sorted(zip(phases, bases))]

        # Take every k-th base to maximize spread
        step = len(sorted_bases) // M
        selected = [sorted_bases[i * step] for i in range(M)]

    elif strategy == 'clustered_phases':
        # Select bases with similar phases (bad for coherent averaging)
        phases = [(a % N) / N for a in bases]
        sorted_bases = [b for _, b in sorted(zip(phases, bases))]

        # Take consecutive bases (clustered)
        selected = sorted_bases[:M]

    elif strategy == 'random':
        # Random selection (baseline)
        selected = list(np.random.choice(bases, M, replace=False))

    else:
        # Default: first M bases
        selected = bases[:M]

    return selected


def test_pathological_orders(N, max_tests=10):
    """Find orders with pathological structure

    Parameters:
        N (int): Modulus
        max_tests (int): Maximum orders to test

    Returns:
        list: (r, structure_type) tuples
    """
    pathological_orders = []

    # Find all unique orders
    orders = set()
    for a in range(2, min(N, 1000)):  # Limit search
        if np.gcd(a, N) == 1:
            r = multiplicative_order(a, N, max_iter=N)
            orders.add(r)

    orders = sorted(orders)

    for r in orders:
        if len(pathological_orders) >= max_tests:
            break

        # Check for pathological properties
        factors = prime_factors(r)

        # Large prime factor
        if len(factors) > 0 and max(factors) > r // 2:
            pathological_orders.append((r, 'large_prime_factor'))

        # Highly composite
        elif len(factors) > 5:
            pathological_orders.append((r, 'highly_composite'))

        # Prime order
        elif len(factors) == 1 and factors[0] == r:
            pathological_orders.append((r, 'prime_order'))

    return pathological_orders


def prime_factors(n):
    """Simple prime factorization"""
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def test_adversarial_base_selection(N, r, bases, M_values=[4, 8, 16, 32]):
    """Test VRA with adversarial base selection strategies

    Returns:
        dict: Results for different strategies
    """
    strategies = ['random', 'max_phase_spread', 'clustered_phases', 'default']

    L = 65536
    R = validated_radius(L)
    expected_bins = [(k * L // r) % L for k in range(r)]

    results = {
        'N': int(N),
        'r': int(r),
        'rho': float(r / N),
        'num_available_bases': len(bases),
        'strategies': []
    }

    print(f"\nTesting N={N}, r={r} ({len(bases)} bases available)")

    for strategy in strategies:
        print(f"  Strategy: {strategy:20s}", end=" ")

        strategy_result = {
            'strategy': strategy,
            'M_tests': []
        }

        for M in M_values:
            if M > len(bases):
                continue

            # Select bases
            selected_bases = select_adversarial_bases(N, r, bases, M, strategy)

            # Compute spectrum
            mag2_avg = compute_averaged_spectrum(
                N, selected_bases, x0=1, length=L//8, zp=8, window='hann'
            )

            # Metrics
            concentration = compute_concentration(mag2_avg)
            metrics = compute_precision_recall(mag2_avg, expected_bins, R)

            strategy_result['M_tests'].append({
                'M': int(M),
                'concentration': float(concentration),
                'precision': float(metrics['precision']),
                'recall': float(metrics['recall'])
            })

        avg_precision = np.mean([t['precision'] for t in strategy_result['M_tests']])
        print(f"Avg Precision: {avg_precision:.1%}")

        results['strategies'].append(strategy_result)

    return results


def run_adversarial_suite():
    """Run comprehensive adversarial tests"""

    print("VRA Adversarial Robustness Tests")
    print("=" * 70)

    # Test cases
    test_cases = [
        (997, 83),    # HIGH SNR
        (1009, 168),  # TRANSITION
        (1009, 504),  # LOW SNR
    ]

    all_results = {
        'metadata': {
            'date': datetime.now().isoformat(),
            'test_types': ['adversarial_base_selection', 'pathological_orders'],
            'M_values': [4, 8, 16, 32]
        },
        'adversarial_base_selection': [],
        'pathological_orders': []
    }

    print("\n" + "=" * 70)
    print("ADVERSARIAL BASE SELECTION")
    print("=" * 70)

    for N, r in test_cases:
        bases = find_bases_with_order(N, r, max_bases=100)

        if len(bases) < 32:
            print(f"Skipping N={N}, r={r}: insufficient bases ({len(bases)})")
            continue

        result = test_adversarial_base_selection(N, r, bases)
        all_results['adversarial_base_selection'].append(result)

    # Pathological orders test
    print("\n" + "=" * 70)
    print("PATHOLOGICAL ORDERS")
    print("=" * 70)

    N_test = 1009
    pathological = test_pathological_orders(N_test, max_tests=5)

    print(f"\nFound {len(pathological)} pathological orders in N={N_test}:")

    for r, structure_type in pathological:
        print(f"\n  r={r} ({structure_type})")

        bases = find_bases_with_order(N_test, r, max_bases=32)

        if len(bases) < 16:
            print(f"    Insufficient bases ({len(bases)})")
            continue

        # Test with M=16
        mag2_avg = compute_averaged_spectrum(
            N_test, bases[:16], x0=1, length=8192, zp=8, window='hann'
        )

        R = validated_radius(65536)
        expected_bins = [(k * 65536 // r) % 65536 for k in range(r)]
        metrics = compute_precision_recall(mag2_avg, expected_bins, R)

        path_result = {
            'N': N_test,
            'r': int(r),
            'structure_type': structure_type,
            'num_bases': len(bases),
            'M': 16,
            'precision': float(metrics['precision']),
            'recall': float(metrics['recall'])
        }

        all_results['pathological_orders'].append(path_result)

        print(f"    M=16: Precision={metrics['precision']:.1%}, Recall={metrics['recall']:.1%}")

    # Save results
    output_dir = Path(__file__).parent.parent.parent / "Data" / "Phase4_Robustness" / "Adversarial_Tests"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_adversarial_results.json"

    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Results saved to: {output_file}")

    return all_results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VRA Adversarial Tests')
    parser.add_argument('--quick', action='store_true',
                       help='Quick test')

    args = parser.parse_args()

    if args.quick:
        print("Quick test mode")
        N, r = 1009, 168
        bases = find_bases_with_order(N, r, max_bases=50)
        result = test_adversarial_base_selection(N, r, bases, M_values=[8, 16])
        print(json.dumps(result, indent=2))
    else:
        # Full adversarial suite
        results = run_adversarial_suite()
