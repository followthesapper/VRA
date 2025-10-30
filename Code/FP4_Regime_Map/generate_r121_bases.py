#!/usr/bin/env python3
"""
Generate r=121 Same-Order Bases
================================

Find bases with order 121 modulo 1009 for transition regime testing.
r/N = 121/1009 ≈ 0.12 (early TRANSITION regime)

Author: Dylan Vaca
Date: October 2025
"""

import numpy as np
import json
from pathlib import Path

def multiplicative_order(a, N, max_iter=10000):
    """Compute multiplicative order of a mod N"""
    if np.gcd(a, N) != 1:
        return None
    x = a
    for r in range(1, min(max_iter, N)):
        if x == 1:
            return r
        x = (x * a) % N
    return None

def find_bases_with_order(N, target_order, max_bases=100):
    """Find bases with specific order"""
    bases = []

    print(f"Searching for bases with order {target_order} modulo {N}...")

    for a in range(2, N):
        if np.gcd(a, N) != 1:
            continue

        r = multiplicative_order(a, N)

        if r == target_order:
            bases.append(int(a))
            print(f"  Found: a={a}, order={r} ({len(bases)} found)")

            if len(bases) >= max_bases:
                break

    return bases

def main():
    N = 1009
    target_order = 126  # 126 = 2 × 3^2 × 7, divides φ(1009)=1008
    max_bases = 100

    print("="*60)
    print("GENERATE r=126 BASES FOR TRANSITION REGIME TEST")
    print("="*60)
    print(f"r/N = {target_order/N:.3f} (early TRANSITION)")
    print()

    bases = find_bases_with_order(N, target_order, max_bases)

    print()
    print(f"Found {len(bases)} bases with order {target_order}")
    print(f"First 10: {bases[:10]}")

    # Save configuration
    config = {
        'N': N,
        'order': target_order,
        'bases': bases
    }

    output_path = Path("same_order_bases_1009_r121.json")
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved to: {output_path}")
    print()
    print("="*60)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
