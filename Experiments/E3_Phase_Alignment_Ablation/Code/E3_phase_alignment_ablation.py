#!/usr/bin/env python3
"""
E3: Phase Alignment Ablation (HIGH-SNR)
=======================================

Goal:
  In HIGH-SNR regime (rho < 0.146), phase-aligned bases outperform random or adversarial
  configurations by at least 8–12% precision.

Pass Criteria:
  Δprecision(aligned − random) ≥ 0.08 (95% CI > 0)

Outputs:
  - JSON with bootstrap confidence intervals and pass/fail verdict
  - Optional figures showing precision distributions

Author: Dylan Vaca
Date: October 2025
"""

import argparse
import json
import numpy as np
from pathlib import Path
from numpy.random import default_rng
from typing import List, Dict

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Code" / "VRA"))

from core import (
    compute_averaged_spectrum,
    compute_precision_recall,
    multiplicative_order,
    classify_regime,
    validated_radius,
)

def bootstrap_ci(diff: np.ndarray, n_boot: int = 10000, alpha: float = 0.05):
    """Compute bootstrap confidence interval for mean difference."""
    rng = default_rng(123)
    means = [np.mean(rng.choice(diff, len(diff), replace=True)) for _ in range(n_boot)]
    low, high = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (low, high)

def expected_bins(r: int, Lzp: int):
    """Generate all expected harmonic bin locations for order r."""
    return [int(round(k * Lzp / r)) for k in range(1, r)]

def run_case(N: int, a_list: List[int], r: int, L: int, zp: int, window: str) -> Dict:
    """Run one ablation case: aligned vs random vs adversarial bases."""
    M = len(a_list)
    Lzp = L * zp
    R = validated_radius(Lzp)
    hb = expected_bins(r, Lzp)

    # Phase-aligned bases (powers of same base)
    mag2_aligned = compute_averaged_spectrum(N, a_list, x0=1, length=L, zp=zp, window=window)
    aligned_metrics = compute_precision_recall(mag2_aligned, hb, R)

    # Random permutation of same bases
    rng = default_rng(42)
    random_bases = list(rng.permutation(a_list))
    mag2_random = compute_averaged_spectrum(N, random_bases, x0=1, length=L, zp=zp, window=window)
    random_metrics = compute_precision_recall(mag2_random, hb, R)

    # Adversarial (reversed order)
    adversarial = a_list[::-1]
    mag2_adv = compute_averaged_spectrum(N, adversarial, x0=1, length=L, zp=zp, window=window)
    adv_metrics = compute_precision_recall(mag2_adv, hb, R)

    return {
        "N": N,
        "r": r,
        "L": L,
        "window": window,
        "precision_aligned": aligned_metrics["precision"],
        "recall_aligned": aligned_metrics["recall"],
        "f1_aligned": aligned_metrics["f1"],
        "precision_random": random_metrics["precision"],
        "recall_random": random_metrics["recall"],
        "f1_random": random_metrics["f1"],
        "precision_adv": adv_metrics["precision"],
        "recall_adv": adv_metrics["recall"],
        "f1_adv": adv_metrics["f1"],
    }

def run_grid(out_dir: Path):
    Ns = [1009, 1013]
    L = 16384
    zp = 8
    window = "hann"
    all_rows = []

    for N in Ns:
        for a in range(2, N):
            if np.gcd(a, N) == 1:
                try:
                    r = multiplicative_order(a, N)
                    rho = r / N
                    if rho < 0.146:  # HIGH-SNR regime criterion
                        # Generate phase-aligned bases: a, a^2, a^3, ..., a^8
                        a_list = [pow(a, i, N) for i in range(1, 9)]
                        res = run_case(N, a_list, r, L, zp, window)
                        res.update({"rho": rho})
                        all_rows.append(res)
                except Exception:
                    continue

    out_json = out_dir / "E3_phase_alignment_results.json"
    with open(out_json, "w") as f:
        json.dump(all_rows, f, indent=2)
    print(f"✅ Saved: {out_json}")

    # Compute Δprecision = aligned - random
    diffs = np.array([r["precision_aligned"] - r["precision_random"] for r in all_rows])
    mean_diff = np.mean(diffs)
    ci = bootstrap_ci(diffs)

    passed = bool(mean_diff >= 0.08 and ci[0] > 0)

    summary = {
        "mean_diff": float(mean_diff),
        "ci_95": [float(ci[0]), float(ci[1])],
        "pass": passed,
        "criteria": "Δprecision >= 0.08 and CI>0",
    }

    with open(out_dir / "E3_phase_alignment_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"✅ E3 Summary: Δ={mean_diff:.3f}, 95%CI={ci}, PASS={passed}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../Data")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_grid(out_dir)

if __name__ == "__main__":
    main()