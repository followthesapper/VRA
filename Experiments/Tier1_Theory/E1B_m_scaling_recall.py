#!/usr/bin/env python3
"""
E1B: M-Scaling Recall Test
===========================

Purpose:
  Test whether increasing M (number of bases) from 16 to 64/128 can recover
  sufficient recall (≥80%) in LOW_SNR regime to make VRA practically viable.

Scientific Question:
  Does VRA's recall scale as √M as predicted by coherent-gain theory?
  If YES → VRA is viable with more bases
  If NO → VRA has fundamental sensitivity limits

Hypothesis:
  Recall should improve as √M (doubling M gives √2 ≈ 1.4× recall boost)
  M=64 should achieve 80-90% recall in LOW_SNR (if theory holds)

Pass Criteria:
  - Recall (LOW_SNR) ≥ 0.80 with M ≥ 64
  - Precision (all regimes) ≥ 0.90
  - √M scaling correlation R² ≥ 0.9

Outputs:
  - JSON with per-(M,N,r) results
  - Figures: recall vs √M, precision vs M, F1 by regime

Author: VRA Experimental Team
Date: October 2025
"""

import argparse
import json
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Code" / "VRA"))

from core import (
    compute_averaged_spectrum,
    compute_precision_recall,
    multiplicative_order,
    validated_radius,
    classify_regime,
)


def expected_bins(r: int, Lzp: int):
    """Generate all expected harmonic bin locations for order r."""
    return [int(round(k * Lzp / r)) for k in range(1, r)]


def find_bases_with_order(N: int, r: int, M_max: int):
    """Find up to M_max bases with multiplicative order r."""
    bases = []
    a = 2
    while len(bases) < M_max and a < N:
        if np.gcd(a, N) == 1:
            try:
                if multiplicative_order(a, N) == r:
                    bases.append(a)
            except Exception:
                pass
        a += 1
    return bases


def run_case(N: int, r: int, bases: list, M: int, L: int, window: str):
    """Run one test case with M bases."""
    if len(bases) < M:
        return None  # Not enough bases available

    selected_bases = bases[:M]  # Use first M bases

    Lzp = L * 4
    R = validated_radius(Lzp)
    hb = expected_bins(r, Lzp)

    mag2 = compute_averaged_spectrum(N, selected_bases, x0=1, length=L, zp=4, window=window)
    metrics = compute_precision_recall(mag2, hb, R)

    regime, _ = classify_regime(N, r)
    rho = r / N

    return {
        "N": N,
        "r": r,
        "rho": float(rho),
        "regime": regime,
        "M": M,
        "L": L,
        "window": window,
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "TP": metrics["TP"],
        "FP": metrics["FP"],
        "FN": metrics["FN"],
        "num_peaks": metrics["num_peaks"],
    }


def main(out_dir: str):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Parameters
    MODULI = [997, 1009, 1013, 2017, 3001]
    M_VALUES = [8, 16, 32, 64, 128]
    M_MAX = max(M_VALUES)
    L = 131072  # Same as E1
    WINDOW = "hamming"  # Best performer from E2

    all_results = []

    print(f"E1B: M-Scaling Recall Test")
    print(f"Testing M ∈ {M_VALUES}")
    print(f"Moduli: {MODULI}")
    print(f"L = {L}")
    print()

    for N in MODULI:
        print(f"Processing N={N}...")

        # Collect representative orders spanning regimes
        seen_orders = set()
        order_cases = []

        for a in range(2, min(N, 400)):
            if np.gcd(a, N) == 1:
                try:
                    r = multiplicative_order(a, N)
                    if r not in seen_orders:
                        seen_orders.add(r)
                        rho = r / N
                        regime, _ = classify_regime(N, r)
                        order_cases.append((r, rho, regime))
                except Exception:
                    pass

        # Select representative cases per regime
        order_cases.sort(key=lambda x: x[1])  # Sort by rho

        selected_orders = []
        for regime_name, (rho_lo, rho_hi) in [
            ('HIGH_SNR', (0.0, 0.146)),
            ('TRANSITION', (0.146, 0.263)),
            ('LOW_SNR', (0.263, 1.0))
        ]:
            regime_orders = [r for r, rho, regime in order_cases
                           if rho_lo <= rho < rho_hi]
            if regime_orders:
                # Pick 3 representative: low, mid, high within regime
                n = len(regime_orders)
                picks = [regime_orders[0], regime_orders[n//2], regime_orders[-1]] if n >= 3 else regime_orders
                selected_orders.extend(picks)

        # Remove duplicates
        selected_orders = list(set(selected_orders))

        print(f"  Selected {len(selected_orders)} representative orders")

        for r in selected_orders:
            # Find M_MAX bases with order r
            bases = find_bases_with_order(N, r, M_MAX)

            if len(bases) < M_MAX:
                print(f"  Warning: N={N}, r={r} - only found {len(bases)} bases (need {M_MAX})")
                if len(bases) < min(M_VALUES):
                    continue  # Skip if not enough for smallest M

            # Test all M values
            for M in M_VALUES:
                if len(bases) >= M:
                    result = run_case(N, r, bases, M, L, WINDOW)
                    if result:
                        all_results.append(result)

        print(f"  Completed N={N}: {len([r for r in all_results if r['N']==N])} cases")

    # Save results
    results_file = out_path / "E1B_results.json"
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print()
    print(f"✅ Saved {len(all_results)} results to {results_file}")

    # Quick summary
    print()
    print("="*70)
    print("QUICK SUMMARY")
    print("="*70)

    for M in M_VALUES:
        m_cases = [r for r in all_results if r['M'] == M]
        if not m_cases:
            continue

        by_regime = {'HIGH_SNR': [], 'TRANSITION': [], 'LOW_SNR': []}
        for case in m_cases:
            by_regime[case['regime']].append(case)

        print(f"\nM = {M} ({len(m_cases)} cases):")
        for regime in ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']:
            cases = by_regime[regime]
            if cases:
                avg_prec = np.mean([c['precision'] for c in cases])
                avg_recall = np.mean([c['recall'] for c in cases])
                avg_f1 = np.mean([c['f1'] for c in cases])
                print(f"  {regime:12s}: Prec={avg_prec:.3f}, Recall={avg_recall:.3f}, F1={avg_f1:.3f} ({len(cases)} cases)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E1B: M-Scaling Recall Test")
    parser.add_argument("--out", default="../../Data/Experiments/Tier1/E1B",
                       help="Output directory")
    args = parser.parse_args()

    main(args.out)
