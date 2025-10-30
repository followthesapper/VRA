#!/usr/bin/env python3
"""
Novelty Statistical Tests
==========================

Bootstrap-based statistical tests to determine if VRA is demonstrably
superior to RPT (Ramanujan Periodicity Transform) baseline.

Pass/Fail criteria from prior-art analysis:
    E1: VRA - RPT precision ≥ 0.05 (overall), ≥ 0.10 (HIGH-SNR)
    E2: Phase-aligned beats random/adversarial by ≥ 0.08-0.12 (HIGH-SNR)
    E3: VRA maintains robustness where RPT degrades
    E4: VRA ≥ 1.3× faster at matched precision

Author: Dylan Vaca
Date: October 2025
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


def bootstrap_diff(
    x: np.ndarray,
    y: np.ndarray,
    B: int = 10000,
    seed: int = 42
) -> Tuple[float, Tuple[float, float]]:
    """
    Bootstrap confidence interval for mean difference x - y.

    Parameters
    ----------
    x : np.ndarray
        First sample
    y : np.ndarray
        Second sample
    B : int
        Number of bootstrap samples
    seed : int
        Random seed

    Returns
    -------
    Tuple[float, Tuple[float, float]]
        (mean_diff, (ci_lower, ci_upper))
    """
    rng = np.random.default_rng(seed)
    n = len(x)
    diffs = np.empty(B)

    for b in range(B):
        idx = rng.integers(0, n, n)
        diffs[b] = np.mean(x[idx] - y[idx])

    ci = (np.percentile(diffs, 2.5), np.percentile(diffs, 97.5))
    mean_diff = float(np.mean(diffs))

    return mean_diff, (float(ci[0]), float(ci[1]))


def classify_regime(rho: float) -> str:
    """
    Classify regime based on ρ = r/N.

    Parameters
    ----------
    rho : float
        Ratio r/N

    Returns
    -------
    str
        "HIGH", "TRANSITION", or "LOW"
    """
    if rho < 0.146:
        return "HIGH"
    elif rho < 0.263:
        return "TRANSITION"
    else:
        return "LOW"


def load_results(json_path: str) -> List[Dict]:
    """Load comparison results from JSON."""
    with open(json_path, "r") as f:
        return json.load(f)


def analyze_overall_advantage(results: List[Dict]) -> Dict:
    """
    Analyze overall VRA advantage across all test cases.

    Parameters
    ----------
    results : List[Dict]
        Comparison results

    Returns
    -------
    Dict
        Summary statistics with bootstrap CIs
    """
    prec_vra = np.array([r["precision_vra"] for r in results])
    prec_rpt = np.array([r["precision_rpt"] for r in results])
    rec_vra = np.array([r["recall_vra"] for r in results])
    rec_rpt = np.array([r["recall_rpt"] for r in results])

    # Bootstrap differences
    prec_diff, prec_ci = bootstrap_diff(prec_vra, prec_rpt)
    rec_diff, rec_ci = bootstrap_diff(rec_vra, rec_rpt)

    # Mean values
    mean_prec_vra = float(np.mean(prec_vra))
    mean_prec_rpt = float(np.mean(prec_rpt))
    mean_rec_vra = float(np.mean(rec_vra))
    mean_rec_rpt = float(np.mean(rec_rpt))

    return {
        "n_cases": len(results),
        "precision_vra_mean": mean_prec_vra,
        "precision_rpt_mean": mean_prec_rpt,
        "precision_diff": prec_diff,
        "precision_ci": prec_ci,
        "recall_vra_mean": mean_rec_vra,
        "recall_rpt_mean": mean_rec_rpt,
        "recall_diff": rec_diff,
        "recall_ci": rec_ci,
    }


def analyze_by_regime(results: List[Dict]) -> Dict:
    """
    Break down advantage by regime (HIGH/TRANSITION/LOW SNR).

    Parameters
    ----------
    results : List[Dict]
        Comparison results

    Returns
    -------
    Dict
        Regime-specific statistics
    """
    by_regime = defaultdict(list)

    for r in results:
        regime = classify_regime(r["rho"])
        by_regime[regime].append(r)

    regime_stats = {}

    for regime_name, grp in by_regime.items():
        if not grp:
            continue

        prec_vra = np.array([r["precision_vra"] for r in grp])
        prec_rpt = np.array([r["precision_rpt"] for r in grp])

        prec_diff, prec_ci = bootstrap_diff(prec_vra, prec_rpt)

        regime_stats[regime_name] = {
            "n": len(grp),
            "precision_vra_mean": float(np.mean(prec_vra)),
            "precision_rpt_mean": float(np.mean(prec_rpt)),
            "precision_diff": prec_diff,
            "precision_ci": prec_ci,
        }

    return regime_stats


def analyze_sqrtM_scaling(results: List[Dict]) -> Dict:
    """
    Analyze √M scaling quality for VRA vs. RPT.

    Parameters
    ----------
    results : List[Dict]
        Comparison results

    Returns
    -------
    Dict
        Scaling fit quality metrics
    """
    by_regime = defaultdict(lambda: {"M": [], "C_vra": []})

    for r in results:
        regime = classify_regime(r["rho"])
        M = r["M"]
        C_vra = r["concentration_vra"]
        by_regime[regime]["M"].append(M)
        by_regime[regime]["C_vra"].append(C_vra)

    scaling_stats = {}

    for regime_name, data in by_regime.items():
        M = np.array(data["M"])
        C = np.array(data["C_vra"])

        if len(M) < 3:
            continue

        # Fit C = a + b * sqrt(M)
        X = np.vstack([np.ones_like(M), np.sqrt(M)]).T
        beta, residuals, rank, s = np.linalg.lstsq(X, C, rcond=None)

        # R² calculation
        ss_res = np.sum((C - X @ beta) ** 2)
        ss_tot = np.sum((C - np.mean(C)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        scaling_stats[regime_name] = {
            "n_points": len(M),
            "sqrt_M_slope": float(beta[1]),
            "intercept": float(beta[0]),
            "r_squared": float(r_squared),
        }

    return scaling_stats


def analyze_runtime_advantage(results: List[Dict]) -> Dict:
    """
    Analyze runtime speedup: VRA vs. RPT.

    Parameters
    ----------
    results : List[Dict]
        Comparison results

    Returns
    -------
    Dict
        Runtime statistics
    """
    speedups = np.array([r["speedup"] for r in results if r["speedup"] is not None])

    if len(speedups) == 0:
        return {"error": "No valid speedup data"}

    return {
        "n": len(speedups),
        "median_speedup": float(np.median(speedups)),
        "mean_speedup": float(np.mean(speedups)),
        "min_speedup": float(np.min(speedups)),
        "max_speedup": float(np.max(speedups)),
        "ci_95": (float(np.percentile(speedups, 2.5)), float(np.percentile(speedups, 97.5))),
    }


def check_novelty_criteria(
    overall: Dict,
    by_regime: Dict,
    runtime: Dict
) -> Dict:
    """
    Check pass/fail criteria for novelty claims.

    Criteria:
        E1: Overall precision advantage ≥ 0.05, HIGH-SNR ≥ 0.10
        E2: (Requires separate phase-alignment test)
        E3: (Requires robustness comparison)
        E4: Median speedup ≥ 1.3×

    Parameters
    ----------
    overall : Dict
        Overall statistics
    by_regime : Dict
        Regime-specific statistics
    runtime : Dict
        Runtime statistics

    Returns
    -------
    Dict
        Pass/fail for each criterion
    """
    results = {}

    # E1: Accuracy advantage
    e1_overall_pass = (
        overall["precision_diff"] >= 0.05
        and overall["precision_ci"][0] > 0  # CI entirely above 0
    )

    e1_high_pass = False
    if "HIGH" in by_regime:
        high = by_regime["HIGH"]
        e1_high_pass = (
            high["precision_diff"] >= 0.10
            and high["precision_ci"][0] > 0
        )

    results["E1_overall"] = {
        "pass": e1_overall_pass,
        "precision_diff": overall["precision_diff"],
        "ci": overall["precision_ci"],
        "threshold": 0.05,
    }

    results["E1_HIGH_SNR"] = {
        "pass": e1_high_pass,
        "precision_diff": by_regime.get("HIGH", {}).get("precision_diff", None),
        "ci": by_regime.get("HIGH", {}).get("precision_ci", None),
        "threshold": 0.10,
    }

    # E4: Runtime advantage
    e4_pass = False
    if "median_speedup" in runtime:
        e4_pass = runtime["median_speedup"] >= 1.3

    results["E4_runtime"] = {
        "pass": e4_pass,
        "median_speedup": runtime.get("median_speedup", None),
        "threshold": 1.3,
    }

    return results


def generate_novelty_report(
    results_json: str,
    out_txt: str = "Data/Novelty/VRA_novelty_report.txt"
) -> str:
    """
    Generate comprehensive novelty report from comparison results.

    Parameters
    ----------
    results_json : str
        Path to comparison results JSON
    out_txt : str
        Output report path

    Returns
    -------
    str
        Path to generated report
    """
    # Load results
    results = load_results(results_json)

    # Run analyses
    overall = analyze_overall_advantage(results)
    by_regime = analyze_by_regime(results)
    scaling = analyze_sqrtM_scaling(results)
    runtime = analyze_runtime_advantage(results)
    criteria = check_novelty_criteria(overall, by_regime, runtime)

    # Build report
    lines = []
    lines.append("=" * 70)
    lines.append("VRA NOVELTY EVALUATION REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Total test cases: {overall['n_cases']}")
    lines.append("")

    # Overall advantage
    lines.append("-" * 70)
    lines.append("OVERALL ACCURACY (E1)")
    lines.append("-" * 70)
    lines.append(f"VRA Precision:       {overall['precision_vra_mean']:.3f}")
    lines.append(f"RPT Precision:       {overall['precision_rpt_mean']:.3f}")
    lines.append(f"Difference (VRA-RPT): {overall['precision_diff']:.3f}")
    lines.append(f"95% CI:              [{overall['precision_ci'][0]:.3f}, {overall['precision_ci'][1]:.3f}]")
    lines.append("")
    lines.append(f"✅ PASS" if criteria["E1_overall"]["pass"] else f"❌ FAIL")
    lines.append(f"   Threshold: Δ ≥ 0.05 with CI > 0")
    lines.append("")

    # By regime
    lines.append("-" * 70)
    lines.append("REGIME-SPECIFIC ACCURACY")
    lines.append("-" * 70)
    for regime_name in ["HIGH", "TRANSITION", "LOW"]:
        if regime_name not in by_regime:
            continue
        stats = by_regime[regime_name]
        lines.append(f"\n{regime_name} SNR (n={stats['n']}):")
        lines.append(f"  VRA Precision: {stats['precision_vra_mean']:.3f}")
        lines.append(f"  RPT Precision: {stats['precision_rpt_mean']:.3f}")
        lines.append(f"  Difference:    {stats['precision_diff']:.3f} [{stats['precision_ci'][0]:.3f}, {stats['precision_ci'][1]:.3f}]")

        if regime_name == "HIGH":
            lines.append(f"  {'✅ PASS' if criteria['E1_HIGH_SNR']['pass'] else '❌ FAIL'} (threshold: Δ ≥ 0.10)")

    lines.append("")

    # √M Scaling
    lines.append("-" * 70)
    lines.append("√M SCALING QUALITY")
    lines.append("-" * 70)
    for regime_name, stats in scaling.items():
        lines.append(f"\n{regime_name} SNR:")
        lines.append(f"  R² fit:      {stats['r_squared']:.4f}")
        lines.append(f"  √M slope:    {stats['sqrt_M_slope']:.4f}")
        lines.append(f"  Intercept:   {stats['intercept']:.4f}")

    lines.append("")

    # Runtime
    lines.append("-" * 70)
    lines.append("RUNTIME COMPARISON (E4)")
    lines.append("-" * 70)
    if "median_speedup" in runtime:
        lines.append(f"Median speedup (RPT/VRA): {runtime['median_speedup']:.2f}×")
        lines.append(f"Mean speedup:             {runtime['mean_speedup']:.2f}×")
        lines.append(f"Range:                    [{runtime['min_speedup']:.2f}×, {runtime['max_speedup']:.2f}×]")
        lines.append(f"95% CI:                   [{runtime['ci_95'][0]:.2f}×, {runtime['ci_95'][1]:.2f}×]")
        lines.append("")
        lines.append(f"✅ PASS" if criteria["E4_runtime"]["pass"] else f"❌ FAIL")
        lines.append(f"   Threshold: Median speedup ≥ 1.3×")
    else:
        lines.append("⚠️  No valid runtime data")

    lines.append("")

    # Final verdict
    lines.append("=" * 70)
    lines.append("NOVELTY VERDICT")
    lines.append("=" * 70)

    passes = sum(1 for c in criteria.values() if c.get("pass", False))
    total = len([c for c in criteria.values() if "pass" in c])

    lines.append(f"Criteria passed: {passes}/{total}")
    lines.append("")

    if passes >= 2:
        lines.append("✅ VRA demonstrates NOVEL capability")
        lines.append("   VRA shows statistically significant advantages over RPT baseline")
        lines.append("   in accuracy and/or runtime. Contribution is publication-worthy.")
    elif passes >= 1:
        lines.append("⚠️  VRA shows PARTIAL novelty")
        lines.append("   Some advantages detected, but not across all criteria.")
        lines.append("   Consider repositioning contribution or strengthening claims.")
    else:
        lines.append("❌ VRA does NOT demonstrate clear novelty over RPT")
        lines.append("   No statistically significant advantages detected.")
        lines.append("   Major repositioning required before publication.")

    lines.append("")
    lines.append("=" * 70)
    lines.append("END REPORT")
    lines.append("=" * 70)

    # Write report
    report_text = "\n".join(lines)
    Path(out_txt).parent.mkdir(parents=True, exist_ok=True)
    Path(out_txt).write_text(report_text)

    return out_txt


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python novelty_stat_tests.py <results.json> [output.txt]")
        sys.exit(1)

    results_json = sys.argv[1]
    out_txt = sys.argv[2] if len(sys.argv) > 2 else "Data/Novelty/VRA_novelty_report.txt"

    print(f"Analyzing results from: {results_json}")
    report_path = generate_novelty_report(results_json, out_txt)
    print(f"Report saved to: {report_path}")
    print("\n" + Path(report_path).read_text())
