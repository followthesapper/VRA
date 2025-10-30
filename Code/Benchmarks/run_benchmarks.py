#!/usr/bin/env python3
"""
VRA Benchmarking Suite
======================

Compare VRA against baseline methods across multiple test cases:
- Accuracy metrics (success rate, false positives/negatives)
- Runtime comparison
- Memory usage
- Scaling with N, r, M

Addresses TODO.md Phase 1.3: "Create comparative benchmarks"

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "Core"))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import json
import time
from datetime import datetime
from baseline_methods import (
    BruteForceOrder,
    SingleBaseFFT,
    IncoherentAveraging,
    BabyStepGiantStep,
    VRACoherentAveraging
)
from vra_core import multiplicative_order


def find_bases_with_order(N, r, max_bases=32):
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


def benchmark_suite(test_cases, M_values=[1, 4, 8, 16, 32]):
    """Run benchmarks across test cases

    Parameters:
        test_cases (list): List of (N, r) tuples
        M_values (list): Number of bases for averaging methods

    Returns:
        dict: Benchmark results
    """
    results = {
        'metadata': {
            'date': datetime.now().isoformat(),
            'num_test_cases': len(test_cases),
            'M_values': M_values
        },
        'test_cases': []
    }

    for N, r in test_cases:
        print(f"\n{'='*70}")
        print(f"Testing N = {N}, r = {r} (ρ = {r/N:.4f})")
        print(f"{'='*70}")

        rho = r / N

        # Find bases
        max_M = max(M_values)
        bases = find_bases_with_order(N, r, max_bases=max_M)

        if len(bases) < max_M:
            print(f"WARNING: Only found {len(bases)} bases, need {max_M}")
            M_values_actual = [m for m in M_values if m <= len(bases)]
        else:
            M_values_actual = M_values

        print(f"Found {len(bases)} bases, testing M = {M_values_actual}")

        test_result = {
            'N': int(N),
            'r': int(r),
            'rho': float(rho),
            'num_bases_found': len(bases),
            'methods': {}
        }

        # 1. Brute force (single base only)
        print("\n1. Brute Force...")
        bf = BruteForceOrder(N)
        start = time.time()
        found = bf.find_order(bases[0], max_iter=min(r * 2, N))
        runtime = time.time() - start

        test_result['methods']['brute_force'] = {
            'found_order': int(found) if found else None,
            'correct': (found == r),
            'runtime': float(runtime),
            'applicable': (r < 1000)  # Only practical for small orders
        }
        print(f"   Found: {found}, Runtime: {runtime:.4f}s")

        # 2. Baby-step giant-step (single base)
        print("\n2. Baby-Step Giant-Step...")
        bsgs = BabyStepGiantStep(N)
        start = time.time()
        found = bsgs.find_order(bases[0], upper_bound=min(r * 2, 10000))
        runtime = time.time() - start

        test_result['methods']['bsgs'] = {
            'found_order': int(found) if found else None,
            'correct': (found == r),
            'runtime': float(runtime),
            'applicable': (r < 10000)
        }
        print(f"   Found: {found}, Runtime: {runtime:.4f}s")

        # 3. Single-base FFT
        print("\n3. Single-Base FFT...")
        single_results = []

        for M in M_values_actual:
            sf = SingleBaseFFT(N)
            start = time.time()
            found = sf.find_order(bases[0])
            runtime = time.time() - start

            single_results.append({
                'M': int(M),
                'found_order': int(found) if found else None,
                'correct': (found == r),
                'runtime': float(runtime)
            })

        test_result['methods']['single_fft'] = single_results
        print(f"   Found: {found}, Runtime: {runtime:.4f}s")

        # 4. Incoherent averaging
        print("\n4. Incoherent Averaging...")
        incoherent_results = []

        for M in M_values_actual:
            inc = IncoherentAveraging(N)
            start = time.time()
            found = inc.find_order_multibase(bases[:M])
            runtime = time.time() - start

            incoherent_results.append({
                'M': int(M),
                'found_order': int(found) if found else None,
                'correct': (found == r),
                'runtime': float(runtime)
            })

            print(f"   M={M}: Found={found}, Runtime={runtime:.4f}s")

        test_result['methods']['incoherent_averaging'] = incoherent_results

        # 5. VRA Coherent averaging
        print("\n5. VRA Coherent Averaging...")
        coherent_results = []

        for M in M_values_actual:
            vra = VRACoherentAveraging(N)
            start = time.time()
            found = vra.find_order_multibase(bases[:M])
            runtime = time.time() - start

            coherent_results.append({
                'M': int(M),
                'found_order': int(found) if found else None,
                'correct': (found == r),
                'runtime': float(runtime)
            })

            print(f"   M={M}: Found={found}, Runtime={runtime:.4f}s")

        test_result['methods']['vra_coherent'] = coherent_results

        results['test_cases'].append(test_result)

    return results


def generate_benchmark_summary(results):
    """Generate summary statistics"""

    print(f"\n{'='*70}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*70}")

    methods = ['brute_force', 'bsgs', 'single_fft', 'incoherent_averaging', 'vra_coherent']

    for method in methods:
        print(f"\n{method.upper()}:")

        success_count = 0
        total_count = 0
        runtimes = []

        for test_case in results['test_cases']:
            method_result = test_case['methods'].get(method)

            if method in ['single_fft', 'incoherent_averaging', 'vra_coherent']:
                # These are lists of results for different M values
                for result in method_result:
                    total_count += 1
                    if result['correct']:
                        success_count += 1
                    runtimes.append(result['runtime'])
            else:
                # Single result
                if method_result is not None:
                    total_count += 1
                    if method_result['correct']:
                        success_count += 1
                    runtimes.append(method_result['runtime'])

        if total_count > 0:
            success_rate = success_count / total_count
            mean_runtime = np.mean(runtimes)
            median_runtime = np.median(runtimes)

            print(f"  Success rate: {success_count}/{total_count} ({success_rate:.1%})")
            print(f"  Runtime: mean={mean_runtime:.4f}s, median={median_runtime:.4f}s")
            print(f"  Runtime range: [{min(runtimes):.4f}, {max(runtimes):.4f}]s")
        else:
            print(f"  No applicable tests")


def run_full_benchmarks():
    """Run comprehensive benchmarks"""

    print("VRA Benchmarking Suite")
    print("=" * 70)

    # Test cases covering different regimes
    test_cases = [
        # HIGH SNR (ρ < 0.146)
        (997, 83),    # ρ ≈ 0.083
        (1009, 112),  # ρ ≈ 0.111
        (1021, 102),  # ρ ≈ 0.100

        # TRANSITION (0.146 ≤ ρ < 0.263)
        (997, 166),   # ρ ≈ 0.167
        (1009, 168),  # ρ ≈ 0.167
        (1021, 170),  # ρ ≈ 0.167

        # LOW SNR (ρ ≥ 0.263)
        (997, 332),   # ρ ≈ 0.333
        (1009, 336),  # ρ ≈ 0.333
    ]

    print(f"Test cases: {len(test_cases)}")
    for N, r in test_cases:
        print(f"  N={N}, r={r} (ρ={r/N:.3f})")

    # Run benchmarks
    results = benchmark_suite(test_cases, M_values=[1, 4, 8, 16, 32])

    # Save results
    output_dir = Path(__file__).parent.parent.parent / "Data" / "benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_benchmark_results.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Generate summary
    generate_benchmark_summary(results)

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VRA Benchmarking Suite')
    parser.add_argument('--quick', action='store_true',
                       help='Quick test (fewer cases)')

    args = parser.parse_args()

    if args.quick:
        print("Quick test mode")
        test_cases = [(997, 166), (1009, 168)]
        results = benchmark_suite(test_cases, M_values=[1, 4, 8, 16])
        generate_benchmark_summary(results)
    else:
        # Full benchmarks
        results = run_full_benchmarks()
