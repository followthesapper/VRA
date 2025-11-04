#!/usr/bin/env python3
"""
VRA Test Vector Verification Script
====================================

Verifies that your VRA implementation produces results matching our canonical test vectors.

This is the Bronze Challenge for the VRA Replication Challenge.

Usage:
    python3 verify_test_vectors.py                    # Run verification
    python3 verify_test_vectors.py --output-report    # Generate report for submission

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "Code" / "VRA"))

import json
import numpy as np
import argparse
from datetime import datetime

try:
    from core import (
        compute_averaged_spectrum,
        compute_concentration,
        compute_precision_recall,
        validated_radius,
        classify_regime
    )
    VRA_AVAILABLE = True
except ImportError:
    VRA_AVAILABLE = False
    print("⚠️  Warning: vra_core not found. Using test-only mode.")


def load_test_vectors():
    """Load canonical test vectors."""
    vectors_path = Path(__file__).parent / "test_vectors.json"

    if not vectors_path.exists():
        raise FileNotFoundError(f"Test vectors not found at: {vectors_path}")

    with open(vectors_path) as f:
        data = json.load(f)

    return data


def verify_single_test_vector(test_vector):
    """
    Verify a single test vector.

    Returns
    -------
    result : dict
        Verification result with pass/fail and details
    """
    test_id = test_vector['test_id']
    params = test_vector['parameters']
    expected = test_vector['expected_outputs']
    tolerance = test_vector['tolerance']

    # Extract parameters
    N = params['N']
    r = params['r']
    bases = params['bases']
    x0 = params['x0']
    M = params['M']
    L = params['L']
    zp = params['zp']

    # Compute VRA outputs
    mag2 = compute_averaged_spectrum(N, bases, x0, L, zp, window="hann")
    concentration = compute_concentration(mag2)

    # Get harmonic bins
    Lzp = L * zp
    R = validated_radius(Lzp)
    harmonic_bins = []
    for k in range(1, r):
        bin_idx = int(round(k * Lzp / r))
        harmonic_bins.append(bin_idx)

    # Compute precision/recall
    metrics = compute_precision_recall(mag2, harmonic_bins, R)
    precision = metrics['precision']
    recall = metrics['recall']

    # Verify results
    checks = []

    # Check concentration
    concentration_match = abs(concentration - expected['concentration']) <= tolerance['concentration']
    checks.append({
        'metric': 'concentration',
        'expected': expected['concentration'],
        'observed': float(concentration),
        'tolerance': tolerance['concentration'],
        'pass': concentration_match
    })

    # Check precision
    precision_match = abs(precision - expected['precision']) <= tolerance['precision']
    checks.append({
        'metric': 'precision',
        'expected': expected['precision'],
        'observed': float(precision),
        'tolerance': tolerance['precision'],
        'pass': precision_match
    })

    # Check recall
    recall_match = abs(recall - expected['recall']) <= tolerance['recall']
    checks.append({
        'metric': 'recall',
        'expected': expected['recall'],
        'observed': float(recall),
        'tolerance': tolerance['recall'],
        'pass': recall_match
    })

    # Check harmonic bins (first 20)
    harmonic_bins_match = harmonic_bins[:20] == expected['harmonic_bins']
    checks.append({
        'metric': 'harmonic_bins',
        'expected': expected['harmonic_bins'][:5],  # Just show first 5
        'observed': harmonic_bins[:5],
        'tolerance': 'exact match',
        'pass': harmonic_bins_match
    })

    # Overall pass/fail
    all_passed = all(check['pass'] for check in checks)

    return {
        'test_id': test_id,
        'description': test_vector['description'],
        'passed': all_passed,
        'checks': checks
    }


def print_verification_result(result):
    """Print a single verification result."""
    test_id = result['test_id']
    desc = result['description']
    passed = result['passed']

    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\nTest {test_id}/10: {status}")
    print(f"  {desc}")

    if not passed:
        print("  Failed checks:")
        for check in result['checks']:
            if not check['pass']:
                print(f"    - {check['metric']}: expected {check['expected']:.4f}, got {check['observed']:.4f}")


def main():
    parser = argparse.ArgumentParser(
        description='Verify VRA test vectors (Bronze Replication Challenge)'
    )
    parser.add_argument(
        '--output-report',
        action='store_true',
        help='Generate verification report for submission'
    )

    args = parser.parse_args()

    if not VRA_AVAILABLE:
        print("\n❌ Error: VRA core library not available.")
        print("Please ensure vra_core.py is in Code/Core/")
        sys.exit(1)

    print("VRA Test Vector Verification - Bronze Replication Challenge")
    print("=" * 70)

    # Load test vectors
    data = load_test_vectors()
    test_vectors = data['test_vectors']

    print(f"Loaded {len(test_vectors)} canonical test vectors")
    print(f"Generated: {data['metadata']['date_generated']}")

    # Verify each test vector
    results = []

    for test_vector in test_vectors:
        try:
            result = verify_single_test_vector(test_vector)
            results.append(result)
            print_verification_result(result)

        except Exception as e:
            print(f"\n❌ FAIL - Test {test_vector['test_id']}/10: Exception occurred")
            print(f"  Error: {e}")
            results.append({
                'test_id': test_vector['test_id'],
                'description': test_vector['description'],
                'passed': False,
                'error': str(e)
            })

    # Summary
    num_passed = sum(1 for r in results if r['passed'])
    num_total = len(results)

    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Total tests: {num_total}")
    print(f"Passed: {num_passed}")
    print(f"Failed: {num_total - num_passed}")
    print(f"Success rate: {100 * num_passed / num_total:.1f}%")

    if num_passed == num_total:
        print("\n🎉 ✅ All test vectors verified!")
        print("\nCongratulations! You have completed the Bronze Replication Challenge.")
        print("To claim your Bronze Replicator badge:")
        print("1. Run with --output-report to generate verification report")
        print("2. Submit report as GitHub issue: 'Bronze Replication - [Your Name]'")
    else:
        print("\n❌ Some test vectors failed verification.")
        print("\nPlease check:")
        print("1. VRA implementation matches algorithm description")
        print("2. Random seed set to 42")
        print("3. Same parameters (N, r, bases, x0, L, zp)")
        print("4. Floating-point tolerance acceptable (<0.001 for concentration)")

    # Generate report if requested
    if args.output_report:
        report = {
            'verification_date': datetime.now().isoformat(),
            'test_vectors_version': data['metadata']['version'],
            'num_total': num_total,
            'num_passed': num_passed,
            'success_rate': num_passed / num_total,
            'results': results,
            'environment': {
                'python_version': sys.version,
                'numpy_version': np.__version__
            }
        }

        report_path = Path(f"verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Verification report saved to: {report_path}")
        print("Submit this file with your Bronze Replication Challenge submission!")

    sys.exit(0 if num_passed == num_total else 1)


if __name__ == "__main__":
    main()
