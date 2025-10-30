#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prove VRA Novelty (single-file test harness)
============================================

Usage
-----
$ python prove_novelty.py [--force]
    --force : re-run comparisons even if a JSON already exists

This script:
  • Generates or reuses E1/E4 comparison results (VRA vs. RPT)
  • Runs bootstrap *and* permutation tests
  • Checks pre-registered thresholds:
        E1-overall:     Δprecision ≥ 0.05 with 95% CI > 0
        E1-high-SNR:    Δprecision ≥ 0.10 with 95% CI > 0
        E4-runtime:     median speedup ≥ 1.3×
  • Prints a compact verdict and writes a report to Data/Novelty/novelty_ci_report.txt
  • Exits 0 if NOVEL, 2 if PARTIAL, 3 if NOT NOVEL
"""

import argparse
import json
import os
import sys
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

# Local imports: adjust these to your actual module paths if needed.
from compare_vra_rpt import generate_test_grid, sweep_grid  # expects your shared module
from novelty_stat_tests import (
    load_results,
    analyze_overall_advantage,
    analyze_by_regime,
    analyze_runtime_advantage,
    check_novelty_criteria,
    classify_regime,
)

RESULTS_JSON = Path("Data/Novelty/e1_vra_vs_rpt_results.json")
REPORT_TXT   = Path("Data/Novelty/novelty_ci_report.txt")


def permutation_test_mean_diff(x: np.ndarray, y: np.ndarray, B: int = 10000, seed: int = 0) -> float:
    """Two-sided permutation test p-value for difference in means of x and y."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    obs = float(abs(np.mean(x) - np.mean(y)))

    pooled = np.concatenate([x, y])
    nx = len(x)
    count = 0
    for _ in range(B):
        rng.shuffle(pooled)
        x_perm = pooled[:nx]
        y_perm = pooled[nx:]
        if abs(np.mean(x_perm) - np.mean(y_perm)) >= obs:
            count += 1
    return (count + 1) / (B + 1)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-run comparisons even if results exist")
    args = parser.parse_args(argv)

    # 1) Ensure results exist (or regenerate)
    if args.force or not RESULTS_JSON.exists():
        RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
        print("[info] Generating E1/E4 comparison results...")
        grid = generate_test_grid()
        sweep_grid(grid, base_strategy="random", out_json=str(RESULTS_JSON), verbose=True)
    else:
        print(f"[info] Using existing results: {RESULTS_JSON}")

    # 2) Load results
    results = load_results(str(RESULTS_JSON))
    if not results:
        print("[error] No results found; cannot proceed.", file=sys.stderr)
        return 3

    # 3) Bootstrap-based analyses
    overall = analyze_overall_advantage(results)
    by_regime = analyze_by_regime(results)
    runtime = analyze_runtime_advantage(results)

    # 4) Independent permutation checks
    import numpy as np
    prec_vra = np.array([r["precision_vra"] for r in results], float)
    prec_rpt = np.array([r["precision_rpt"] for r in results], float)
    p_perm_overall = permutation_test_mean_diff(prec_vra, prec_rpt, B=20000, seed=1)

    p_perm_high = None
    if "HIGH" in by_regime:
        grp = [r for r in results if classify_regime(r["rho"]) == "HIGH"]
        pv = np.array([r["precision_vra"] for r in grp], float)
        pr = np.array([r["precision_rpt"] for r in grp], float)
        p_perm_high = permutation_test_mean_diff(pv, pr, B=20000, seed=2)

    # 5) Threshold checks
    criteria = check_novelty_criteria(overall, by_regime, runtime)

    # 6) Report
    lines = []
    lines.append("=" * 70)
    lines.append("VRA NOVELTY: STATISTICAL TEST REPORT")
    lines.append("=" * 70 + "\n")
    lines.append(f"n_cases: {overall['n_cases']}")
    lines.append("")
    lines.append("E1: Overall accuracy advantage (VRA - RPT)")
    lines.append(f"  mean Δprecision = {overall['precision_diff']:.3f}")
    lines.append(f"  95% bootstrap CI = [{overall['precision_ci'][0]:.3f}, {overall['precision_ci'][1]:.3f}]")
    lines.append(f"  permutation p-value (two-sided) = {p_perm_overall:.3e}")
    lines.append(f"  PASS? {criteria['E1_overall']['pass']} (threshold Δ≥0.05 & CI>0)")
    lines.append("")
    if 'HIGH' in by_regime:
        high = by_regime['HIGH']
        lines.append("E1: High-SNR regime")
        lines.append(f"  mean Δprecision = {high['precision_diff']:.3f}")
        lines.append(f"  95% bootstrap CI = [{high['precision_ci'][0]:.3f}, {high['precision_ci'][1]:.3f}]")
        lines.append(f"  permutation p-value (two-sided) = {p_perm_high:.3e}" if p_perm_high is not None else "  permutation p-value: N/A")
        lines.append(f"  PASS? {criteria['E1_HIGH_SNR']['pass']} (threshold Δ≥0.10 & CI>0)\n")
    else:
        lines.append("E1: High-SNR regime — not available in results.\n")

    if 'median_speedup' in runtime:
        lines.append("E4: Runtime advantage")
        lines.append(f"  median speedup (RPT/VRA) = {runtime['median_speedup']:.2f}×")
        lines.append(f"  95% CI (empirical) = [{runtime['ci_95'][0]:.2f}×, {runtime['ci_95'][1]:.2f}×]")
        lines.append(f"  PASS? {criteria['E4_runtime']['pass']} (threshold ≥1.3×)\n")
    else:
        lines.append("E4: Runtime advantage — insufficient data.\n")

    # Verdict
    passes = sum(1 for k, v in criteria.items() if isinstance(v, dict) and v.get("pass"))
    total  = sum(1 for k, v in criteria.items() if isinstance(v, dict) and "pass" in v)
    if passes >= 2:
        verdict = "✅ NOVEL"
        exit_code = 0
    elif passes == 1:
        verdict = "⚠️ PARTIAL NOVELTY"
        exit_code = 2
    else:
        verdict = "❌ NOT NOVEL"
        exit_code = 3

    lines.append("=" * 70)
    lines.append(f"VERDICT: {verdict}  (passed {passes}/{total} criteria)")
    lines.append("=" * 70)

    REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\n[ok] Wrote: {REPORT_TXT}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
