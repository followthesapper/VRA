#!/usr/bin/env python3
"""
Generate publication-quality figures for E1: Spectral-Order Equivalence
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

def load_results(results_path):
    """Load E1 results from JSON"""
    with open(results_path) as f:
        return json.load(f)

def plot_precision_by_regime(data, out_dir):
    """Plot precision distribution by regime"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Group by regime
    regimes = {}
    for case in data:
        regime = case['regime']
        if regime not in regimes:
            regimes[regime] = []
        regimes[regime].append(case)

    # Plot 1: Box plot of precision by regime
    regime_order = ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']
    colors = ['#E74C3C', '#F39C12', '#27AE60']

    for i, regime in enumerate(regime_order):
        if regime in regimes:
            precisions = [c['precision'] for c in regimes[regime]]
            bp = ax1.boxplot([precisions], positions=[i], widths=0.6,
                            patch_artist=True, showmeans=True)
            bp['boxes'][0].set_facecolor(colors[i])
            bp['boxes'][0].set_alpha(0.7)

    ax1.set_xticks(range(len(regime_order)))
    ax1.set_xticklabels(['HIGH\nSNR', 'TRANSITION', 'LOW\nSNR'])
    ax1.set_ylabel('Precision', fontsize=12)
    ax1.set_title('Precision Distribution by Regime', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    ax1.axhline(y=0.98, color='g', linestyle='--', alpha=0.5, label='Target (TRANS/LOW)')
    ax1.axhline(y=0.85, color='orange', linestyle='--', alpha=0.5, label='Target (HIGH)')
    ax1.legend()

    # Plot 2: Precision vs ρ scatter
    for regime in regime_order:
        if regime in regimes:
            cases = regimes[regime]
            rhos = [c['r'] / c['N'] for c in cases]
            precs = [c['precision'] for c in cases]
            idx = regime_order.index(regime)
            ax2.scatter(rhos, precs, c=colors[idx], label=regime.replace('_', ' '),
                       s=60, alpha=0.7, edgecolors='black', linewidths=0.5)

    ax2.set_xlabel('ρ = r/N', fontsize=12)
    ax2.set_ylabel('Precision', fontsize=12)
    ax2.set_title('Precision vs. Order Density', fontsize=14, fontweight='bold')
    ax2.axhline(y=0.98, color='g', linestyle='--', alpha=0.3)
    ax2.axhline(y=0.85, color='orange', linestyle='--', alpha=0.3)
    ax2.axvline(x=0.146, color='gray', linestyle=':', alpha=0.5, label='Regime boundaries')
    ax2.axvline(x=0.263, color='gray', linestyle=':', alpha=0.5)
    ax2.legend()
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_dir / 'e1_precision_by_regime.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved: {out_dir / 'e1_precision_by_regime.png'}")

def plot_false_positives(data, out_dir):
    """Plot false positive analysis"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # FP by regime
    regime_order = ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']
    colors = ['#E74C3C', '#F39C12', '#27AE60']

    fp_by_regime = {}
    for case in data:
        regime = case['regime']
        if regime not in fp_by_regime:
            fp_by_regime[regime] = []
        fp_by_regime[regime].append(case['FP'])

    # Plot 1: FP distribution
    for i, regime in enumerate(regime_order):
        if regime in fp_by_regime:
            fps = fp_by_regime[regime]
            bp = ax1.boxplot([fps], positions=[i], widths=0.6,
                            patch_artist=True, showmeans=True)
            bp['boxes'][0].set_facecolor(colors[i])
            bp['boxes'][0].set_alpha(0.7)

    ax1.set_xticks(range(len(regime_order)))
    ax1.set_xticklabels(['HIGH\nSNR', 'TRANSITION', 'LOW\nSNR'])
    ax1.set_ylabel('False Positives', fontsize=12)
    ax1.set_title('False Positive Count by Regime', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    ax1.axhline(y=0, color='g', linestyle='--', alpha=0.5, label='Target (FP=0)')
    ax1.legend()

    # Plot 2: FP vs validated radius
    for regime in regime_order:
        cases = [c for c in data if c['regime'] == regime]
        if cases:
            Rs = [c['R'] for c in cases]
            FPs = [c['FP'] for c in cases]
            idx = regime_order.index(regime)
            ax2.scatter(Rs, FPs, c=colors[idx], label=regime.replace('_', ' '),
                       s=60, alpha=0.7, edgecolors='black', linewidths=0.5)

    ax2.set_xlabel('Validated Radius R', fontsize=12)
    ax2.set_ylabel('False Positives', fontsize=12)
    ax2.set_title('FP vs. Validated Radius', fontsize=14, fontweight='bold')
    ax2.axhline(y=0, color='g', linestyle='--', alpha=0.3)
    ax2.legend()
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_dir / 'e1_false_positives.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved: {out_dir / 'e1_false_positives.png'}")

def plot_summary_statistics(data, out_dir):
    """Plot overall summary statistics"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

    regime_order = ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']
    colors = ['#E74C3C', '#F39C12', '#27AE60']

    # Group data by regime
    stats = {}
    for regime in regime_order:
        cases = [c for c in data if c['regime'] == regime]
        if cases:
            stats[regime] = {
                'count': len(cases),
                'avg_precision': np.mean([c['precision'] for c in cases]),
                'avg_recall': np.mean([c['recall'] for c in cases]),
                'avg_fp': np.mean([c['FP'] for c in cases]),
                'pass_rate': sum(1 for c in cases if c['precision'] >= (0.85 if regime == 'HIGH_SNR' else 0.98)) / len(cases)
            }

    # Plot 1: Case counts
    ax1.bar(range(len(stats)), [stats[r]['count'] for r in stats.keys()],
           color=colors[:len(stats)], alpha=0.7, edgecolor='black')
    ax1.set_xticks(range(len(stats)))
    ax1.set_xticklabels([r.replace('_', '\n') for r in stats.keys()])
    ax1.set_ylabel('Number of Test Cases', fontsize=12)
    ax1.set_title('Test Coverage by Regime', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)

    # Plot 2: Average precision
    ax2.bar(range(len(stats)), [stats[r]['avg_precision'] for r in stats.keys()],
           color=colors[:len(stats)], alpha=0.7, edgecolor='black')
    ax2.set_xticks(range(len(stats)))
    ax2.set_xticklabels([r.replace('_', '\n') for r in stats.keys()])
    ax2.set_ylabel('Average Precision', fontsize=12)
    ax2.set_title('Mean Precision by Regime', fontsize=14, fontweight='bold')
    ax2.axhline(y=0.98, color='g', linestyle='--', alpha=0.5, label='Target (TRANS/LOW)')
    ax2.axhline(y=0.85, color='orange', linestyle='--', alpha=0.5, label='Target (HIGH)')
    ax2.set_ylim([0, 1.1])
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    # Plot 3: Pass rate
    ax3.bar(range(len(stats)), [stats[r]['pass_rate'] * 100 for r in stats.keys()],
           color=colors[:len(stats)], alpha=0.7, edgecolor='black')
    ax3.set_xticks(range(len(stats)))
    ax3.set_xticklabels([r.replace('_', '\n') for r in stats.keys()])
    ax3.set_ylabel('Pass Rate (%)', fontsize=12)
    ax3.set_title('Test Pass Rate by Regime', fontsize=14, fontweight='bold')
    ax3.axhline(y=100, color='g', linestyle='--', alpha=0.5)
    ax3.set_ylim([0, 110])
    ax3.grid(axis='y', alpha=0.3)

    # Plot 4: Average FP
    ax4.bar(range(len(stats)), [stats[r]['avg_fp'] for r in stats.keys()],
           color=colors[:len(stats)], alpha=0.7, edgecolor='black')
    ax4.set_xticks(range(len(stats)))
    ax4.set_xticklabels([r.replace('_', '\n') for r in stats.keys()])
    ax4.set_ylabel('Average False Positives', fontsize=12)
    ax4.set_title('Mean FP Count by Regime', fontsize=14, fontweight='bold')
    ax4.axhline(y=0, color='g', linestyle='--', alpha=0.5)
    ax4.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_dir / 'e1_summary_statistics.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved: {out_dir / 'e1_summary_statistics.png'}")

def main():
    parser = argparse.ArgumentParser(description='Generate E1 figures')
    parser.add_argument('--results', default='../../../Data/Experiments/Tier1/E1/E1_results.json')
    parser.add_argument('--out', default='../../../Figures/Experiments/Tier1')
    args = parser.parse_args()

    # Load data
    data = load_results(args.results)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating E1 figures from {len(data)} test cases...")
    print(f"Output directory: {out_dir}\n")

    # Generate all figures
    plot_precision_by_regime(data, out_dir)
    plot_false_positives(data, out_dir)
    plot_summary_statistics(data, out_dir)

    print(f"\n✓ All E1 figures generated successfully!")

if __name__ == '__main__':
    main()
