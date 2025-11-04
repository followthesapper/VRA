#!/usr/bin/env python3
"""
E1C Analysis and Visualization
================================

Analyze E1C results to determine if VRA's √M scaling holds with proper CFAR detection.

Key Questions:
1. Does recall increase with √M? (Should show R² ≥ 0.8 with positive slope)
2. Does harmonic SNR increase linearly with √M?
3. Do CFAR and MAD detectors agree?
4. Does LOW_SNR regime achieve ≥60% recall with M=64?

Author: VRA Experimental Team
Date: October 2025
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def linear_regression(x, y):
    """
    Simple linear regression: y = slope * x + intercept
    Returns: slope, intercept, r_squared
    """
    x = np.array(x)
    y = np.array(y)
    n = len(x)

    # Compute slope and intercept
    x_mean = np.mean(x)
    y_mean = np.mean(y)

    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    if denominator == 0:
        return 0.0, y_mean, 0.0

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # Compute R²
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)

    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return slope, intercept, r_squared


def load_results(results_file):
    """Load E1C results from JSON."""
    with open(results_file, 'r') as f:
        return json.load(f)


def analyze_sqrt_m_scaling(results, metric_key='cfar_recall'):
    """
    Analyze whether metric scales with √M.

    Returns:
        dict with 'slope', 'r_squared', 'correlation', 'mean_by_M'
    """
    M_values = sorted(list(set(r['M'] for r in results)))
    sqrt_M = np.array([np.sqrt(M) for M in M_values])

    mean_metric = []
    for M in M_values:
        cases = [r[metric_key] for r in results if r['M'] == M]
        mean_metric.append(np.mean(cases) if cases else 0.0)

    mean_metric = np.array(mean_metric)

    # Linear regression: metric = slope * √M + intercept
    slope, intercept, r_squared = linear_regression(sqrt_M, mean_metric)

    return {
        'M_values': M_values,
        'sqrt_M': sqrt_M.tolist(),
        'mean_metric': mean_metric.tolist(),
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_squared,
        'correlation': np.sqrt(r_squared) if slope >= 0 else -np.sqrt(r_squared),
    }


def analyze_by_regime(results, M_values):
    """Compute mean metrics by regime and M."""
    regimes = ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']

    by_regime = {}
    for regime in regimes:
        by_regime[regime] = {}
        for M in M_values:
            cases = [r for r in results if r['regime'] == regime and r['M'] == M]
            if cases:
                by_regime[regime][M] = {
                    'cfar_precision': np.mean([c['cfar_precision'] for c in cases]),
                    'cfar_recall': np.mean([c['cfar_recall'] for c in cases]),
                    'cfar_f1': np.mean([c['cfar_f1'] for c in cases]),
                    'mad_recall': np.mean([c['mad_recall'] for c in cases]),
                    'topk_recall': np.mean([c['topk_recall'] for c in cases]),
                    'harmonic_snr_db': np.mean([c['harmonic_snr_db'] for c in cases]),
                    'n_cases': len(cases),
                }

    return by_regime


def plot_sqrt_m_scaling(results, out_dir):
    """Generate figures showing √M scaling for all detectors."""
    M_values = sorted(list(set(r['M'] for r in results)))

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # 1. CFAR Recall vs √M (all regimes)
    ax = axes[0, 0]
    for regime, color in [('HIGH_SNR', 'green'), ('TRANSITION', 'orange'), ('LOW_SNR', 'red')]:
        regime_cases = [r for r in results if r['regime'] == regime]
        if not regime_cases:
            continue

        sqrt_M = [np.sqrt(M) for M in M_values]
        mean_recall = []
        for M in M_values:
            cases = [r['cfar_recall'] for r in regime_cases if r['M'] == M]
            mean_recall.append(np.mean(cases) if cases else 0.0)

        ax.plot(sqrt_M, mean_recall, 'o-', color=color, label=regime, linewidth=2, markersize=8)

        # Fit line (E4-style with smooth line)
        if len(sqrt_M) >= 3 and min(mean_recall) < 0.95:
            slope, intercept, r_squared = linear_regression(sqrt_M, mean_recall)
            x_fit = np.linspace(min(sqrt_M), max(sqrt_M), 50)
            y_fit = slope * x_fit + intercept
            ax.plot(x_fit, y_fit, '--', color=color, alpha=0.5,
                   label=f'{regime} fit (R²={r_squared:.3f})')

    ax.set_xlabel('√M', fontsize=12)
    ax.set_ylabel('CFAR Recall', fontsize=12)
    ax.set_title('Recall vs √M (CFAR Detector)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.axhline(0.60, color='black', linestyle=':', label='Target (60%)')

    # 2. Harmonic SNR vs √M
    ax = axes[0, 1]
    for regime, color in [('HIGH_SNR', 'green'), ('TRANSITION', 'orange'), ('LOW_SNR', 'red')]:
        regime_cases = [r for r in results if r['regime'] == regime]
        if not regime_cases:
            continue

        sqrt_M = [np.sqrt(M) for M in M_values]
        mean_snr = []
        for M in M_values:
            cases = [r['harmonic_snr_db'] for r in regime_cases if r['M'] == M]
            mean_snr.append(np.mean(cases) if cases else 0.0)

        ax.plot(sqrt_M, mean_snr, 'o-', color=color, label=regime, linewidth=2, markersize=8)

    ax.set_xlabel('√M', fontsize=12)
    ax.set_ylabel('Harmonic SNR (dB)', fontsize=12)
    ax.set_title('SNR vs √M (Should Increase Linearly)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)

    # 3. Detector Comparison (LOW_SNR only)
    ax = axes[1, 0]
    low_snr = [r for r in results if r['regime'] == 'LOW_SNR']
    if low_snr:
        sqrt_M = [np.sqrt(M) for M in M_values]

        for detector, label, color in [
            ('cfar_recall', 'CFAR', 'blue'),
            ('mad_recall', 'MAD', 'purple'),
            ('topk_recall', 'Top-K (Oracle)', 'gold')
        ]:
            mean_recall = []
            for M in M_values:
                cases = [r[detector] for r in low_snr if r['M'] == M]
                mean_recall.append(np.mean(cases) if cases else 0.0)

            ax.plot(sqrt_M, mean_recall, 'o-', color=color, label=label, linewidth=2, markersize=8)

        ax.axhline(0.60, color='black', linestyle=':', label='Target (60%)')

    ax.set_xlabel('√M', fontsize=12)
    ax.set_ylabel('Recall', fontsize=12)
    ax.set_title('Detector Comparison (LOW_SNR Regime)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)

    # 4. Precision vs M (should stay high)
    ax = axes[1, 1]
    for regime, color in [('HIGH_SNR', 'green'), ('TRANSITION', 'orange'), ('LOW_SNR', 'red')]:
        regime_cases = [r for r in results if r['regime'] == regime]
        if not regime_cases:
            continue

        mean_prec = []
        for M in M_values:
            cases = [r['cfar_precision'] for r in regime_cases if r['M'] == M]
            mean_prec.append(np.mean(cases) if cases else 0.0)

        ax.plot(M_values, mean_prec, 'o-', color=color, label=regime, linewidth=2, markersize=8)

    ax.axhline(0.85, color='black', linestyle=':', label='Target (85%)')
    ax.set_xlabel('M (number of bases)', fontsize=12)
    ax.set_ylabel('CFAR Precision', fontsize=12)
    ax.set_title('Precision vs M (Should Stay High)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    out_file = Path(out_dir) / 'E1C_sqrt_m_scaling.png'
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✅ Saved figure: {out_file}")


def plot_low_snr_focus(results, out_dir):
    """Focused plot on LOW_SNR regime - the critical test."""
    low_snr = [r for r in results if r['regime'] == 'LOW_SNR']
    if not low_snr:
        print("⚠️  No LOW_SNR cases found")
        return

    M_values = sorted(list(set(r['M'] for r in low_snr)))

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Recall vs √M for all 3 detectors
    ax = axes[0]
    sqrt_M = [np.sqrt(M) for M in M_values]

    for detector, label, color, marker in [
        ('cfar_recall', 'CFAR (α=1.8)', 'blue', 'o'),
        ('mad_recall', 'MAD (κ=8.0)', 'purple', 's'),
        ('topk_recall', 'Top-K (Oracle)', 'gold', '^')
    ]:
        mean_recall = []
        std_recall = []
        for M in M_values:
            cases = [r[detector] for r in low_snr if r['M'] == M]
            mean_recall.append(np.mean(cases) if cases else 0.0)
            std_recall.append(np.std(cases) if cases else 0.0)

        ax.errorbar(sqrt_M, mean_recall, yerr=std_recall,
                   fmt=marker + '-', color=color, label=label,
                   linewidth=2, markersize=10, capsize=5, alpha=0.8)

        # Fit line for CFAR
        if detector == 'cfar_recall' and len(sqrt_M) >= 2:
            slope, intercept, r_squared = linear_regression(sqrt_M, mean_recall)
            fit_line = [slope * x + intercept for x in sqrt_M]
            ax.plot(sqrt_M, fit_line, '--', color=color, alpha=0.5,
                   label=f'CFAR fit (R²={r_squared:.3f}, slope={slope:.3f})')

    ax.axhline(0.60, color='red', linestyle=':', linewidth=2, label='Pass Threshold (60%)')
    ax.set_xlabel('√M (square root of number of bases)', fontsize=12)
    ax.set_ylabel('Recall', fontsize=12)
    ax.set_title('LOW_SNR Recall vs √M: Does VRA Scale?', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    ax.set_ylim([0, 1.0])

    # Right: Raw M vs Recall (easier to read specific values)
    ax = axes[1]
    for detector, label, color, marker in [
        ('cfar_recall', 'CFAR', 'blue', 'o'),
        ('mad_recall', 'MAD', 'purple', 's'),
        ('topk_recall', 'Top-K', 'gold', '^')
    ]:
        mean_recall = []
        for M in M_values:
            cases = [r[detector] for r in low_snr if r['M'] == M]
            mean_recall.append(np.mean(cases) if cases else 0.0)

        ax.plot(M_values, mean_recall, marker + '-', color=color, label=label,
               linewidth=2, markersize=10)

    ax.axhline(0.60, color='red', linestyle=':', linewidth=2, label='Target (60%)')
    ax.set_xlabel('M (number of bases)', fontsize=12)
    ax.set_ylabel('Recall', fontsize=12)
    ax.set_title('LOW_SNR Recall vs M (Direct View)', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    ax.set_ylim([0, 1.0])
    ax.set_xticks(M_values)

    plt.tight_layout()
    out_file = Path(out_dir) / 'E1C_low_snr_critical_test.png'
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✅ Saved figure: {out_file}")


def compute_verdict(results):
    """
    Determine pass/fail verdict for E1C.

    Pass Criteria:
    1. Recall (LOW_SNR, M=64) ≥ 0.60 with CFAR
    2. √M correlation R² ≥ 0.8 (positive slope)
    3. Harmonic SNR increases with √M
    """
    # Criterion 1: LOW_SNR recall with M=64
    low_snr_m64 = [r['cfar_recall'] for r in results
                   if r['regime'] == 'LOW_SNR' and r['M'] == 64]

    criterion1_pass = False
    if low_snr_m64:
        mean_recall_m64 = np.mean(low_snr_m64)
        criterion1_pass = mean_recall_m64 >= 0.60
    else:
        mean_recall_m64 = None

    # Criterion 2: √M scaling (R² ≥ 0.8, positive slope)
    scaling = analyze_sqrt_m_scaling(results, 'cfar_recall')
    criterion2_pass = (scaling['r_squared'] >= 0.8) and (scaling['slope'] > 0)

    # Criterion 3: SNR increases with √M
    snr_scaling = analyze_sqrt_m_scaling(results, 'harmonic_snr_db')
    criterion3_pass = snr_scaling['slope'] > 0

    overall_pass = criterion1_pass and criterion2_pass and criterion3_pass

    verdict = {
        'overall_pass': bool(overall_pass),
        'criterion1': {
            'description': 'Recall (LOW_SNR, M=64) ≥ 0.60',
            'pass': bool(criterion1_pass),
            'value': float(mean_recall_m64) if mean_recall_m64 is not None else None,
            'target': 0.60,
        },
        'criterion2': {
            'description': '√M correlation R² ≥ 0.8 (positive slope)',
            'pass': bool(criterion2_pass),
            'r_squared': float(scaling['r_squared']),
            'slope': float(scaling['slope']),
            'target_r2': 0.80,
        },
        'criterion3': {
            'description': 'Harmonic SNR increases with √M',
            'pass': bool(criterion3_pass),
            'snr_slope': float(snr_scaling['slope']),
        },
    }

    return verdict


def main():
    results_file = Path("../Data/E1C_results.json")
    out_dir = Path("../Figures")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("E1C Analysis: √M Scaling with Proper CFAR Detection")
    print("=" * 70)

    # Load results
    results = load_results(results_file)
    print(f"Loaded {len(results)} test cases")

    M_values = sorted(list(set(r['M'] for r in results)))
    print(f"M values tested: {M_values}")

    # Analyze by regime
    by_regime = analyze_by_regime(results, M_values)

    print("\n" + "=" * 70)
    print("RESULTS BY REGIME AND M")
    print("=" * 70)

    for regime in ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']:
        print(f"\n{regime}:")
        if regime not in by_regime or not by_regime[regime]:
            print("  No data")
            continue

        for M in M_values:
            if M in by_regime[regime]:
                d = by_regime[regime][M]
                print(f"  M={M:3d}: CFAR Recall={d['cfar_recall']:.3f}, "
                      f"Prec={d['cfar_precision']:.3f}, "
                      f"SNR={d['harmonic_snr_db']:6.2f}dB, "
                      f"MAD Recall={d['mad_recall']:.3f}, "
                      f"TopK={d['topk_recall']:.3f} "
                      f"({d['n_cases']} cases)")

    # √M Scaling Analysis
    print("\n" + "=" * 70)
    print("√M SCALING ANALYSIS (CFAR Recall)")
    print("=" * 70)

    scaling = analyze_sqrt_m_scaling(results, 'cfar_recall')
    print(f"Slope:         {scaling['slope']:.4f}")
    print(f"R²:            {scaling['r_squared']:.4f}")
    print(f"Correlation:   {scaling['correlation']:.4f}")

    if scaling['slope'] > 0:
        print("✓ Positive slope - recall INCREASES with √M")
    else:
        print("✗ Negative/zero slope - recall does NOT increase with √M")

    if scaling['r_squared'] >= 0.8:
        print("✓ Strong linear correlation (R² ≥ 0.8)")
    else:
        print(f"✗ Weak correlation (R² = {scaling['r_squared']:.3f} < 0.8)")

    # SNR Scaling
    print("\n" + "=" * 70)
    print("HARMONIC SNR SCALING")
    print("=" * 70)

    snr_scaling = analyze_sqrt_m_scaling(results, 'harmonic_snr_db')
    print(f"SNR Slope:     {snr_scaling['slope']:.4f} dB per √M")
    print(f"R²:            {snr_scaling['r_squared']:.4f}")

    if snr_scaling['slope'] > 0:
        print("✓ SNR increases with √M as expected")
    else:
        print("✗ SNR does NOT increase with √M")

    # Compute Verdict
    print("\n" + "=" * 70)
    print("PASS/FAIL VERDICT")
    print("=" * 70)

    verdict = compute_verdict(results)

    for i, key in enumerate(['criterion1', 'criterion2', 'criterion3'], 1):
        crit = verdict[key]
        status = "✅ PASS" if crit['pass'] else "❌ FAIL"
        print(f"\nCriterion {i}: {crit['description']}")
        print(f"  Status: {status}")
        if 'value' in crit and crit['value'] is not None:
            print(f"  Observed: {crit['value']:.3f}, Target: {crit['target']:.2f}")
        if 'r_squared' in crit:
            print(f"  R² = {crit['r_squared']:.3f}, Slope = {crit['slope']:.4f}")
        if 'snr_slope' in crit:
            print(f"  SNR slope = {crit['snr_slope']:.4f} dB per √M")

    print("\n" + "=" * 70)
    if verdict['overall_pass']:
        print("OVERALL: ✅ PASS - VRA's √M scaling is CONFIRMED")
        print("Interpretation: E1B failure was detector artifact. VRA is VIABLE.")
    else:
        print("OVERALL: ❌ FAIL - VRA does not show proper √M scaling")
        print("Interpretation: VRA has fundamental sensitivity limits.")
    print("=" * 70)

    # Generate figures
    print("\nGenerating figures...")
    plot_sqrt_m_scaling(results, out_dir)
    plot_low_snr_focus(results, out_dir)

    # Save verdict
    verdict_file = Path(results_file).parent / "E1C_verdict.json"
    with open(verdict_file, 'w') as f:
        json.dump(verdict, f, indent=2)

    print(f"\n✅ Analysis complete. Verdict saved to {verdict_file}")


if __name__ == "__main__":
    main()
