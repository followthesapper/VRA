#!/usr/bin/env python3
"""
Phase 4.1 Robustness Figure Generation
=======================================

Generate figures for:
1. Noise injection degradation curves
2. Adversarial base selection comparison
3. Pathological orders performance

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
import numpy as np
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime


def load_latest_data(data_dir):
    """Load most recent data file from directory"""
    files = list(Path(data_dir).glob("*.json"))
    if not files:
        return None

    latest = max(files, key=lambda p: p.stat().st_mtime)
    with open(latest, 'r') as f:
        return json.load(f)


def plot_noise_degradation(data, output_dir):
    """Plot precision degradation curves for different noise types"""

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    noise_types = ['gaussian', 'phase_jitter', 'quantization']
    noise_labels = ['Gaussian Noise', 'Phase Jitter', 'Quantization']
    regime_colors = {'HIGH_SNR': '#ff9999', 'TRANSITION': '#66b3ff', 'LOW_SNR': '#99ff99'}

    for idx, (noise_type, noise_label) in enumerate(zip(noise_types, noise_labels)):
        ax = axes[idx]

        # Collect data by regime
        for test_case in data['test_cases']:
            regime = test_case['regime']
            N = test_case['N']
            r = test_case['r']
            rho = test_case['rho']

            # Extract noise test results for this type
            noise_results = [nt for nt in test_case['noise_tests']
                           if nt['noise_type'] == noise_type]

            if not noise_results:
                continue

            # Organize by noise level
            noise_levels = []
            precisions = []

            for nr in noise_results:
                noise_levels.append(nr['noise_level'])
                # Average precision across M values
                avg_prec = np.mean([t['precision'] for t in nr['M_tests']])
                precisions.append(avg_prec)

            # Sort by noise level
            sorted_pairs = sorted(zip(noise_levels, precisions))
            noise_levels = [p[0] for p in sorted_pairs]
            precisions = [p[1] for p in sorted_pairs]

            # Plot
            label = f"{regime} (ρ={rho:.3f})"
            ax.plot(noise_levels, precisions, marker='o', markersize=8,
                   linewidth=2.5, label=label, color=regime_colors[regime],
                   alpha=0.8)

        ax.set_xlabel('Noise Level', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Precision', fontsize=12, fontweight='bold')
        ax.set_title(f'{noise_label}\nRobustness', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, 1.05])
        ax.legend(fontsize=10)

        # Add horizontal reference line at 90%
        ax.axhline(0.9, color='red', linestyle='--', alpha=0.5, linewidth=1.5)

    plt.suptitle('VRA Noise Robustness: Precision vs. Noise Level\n(Averaged across M values)',
                fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_noise_degradation.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def plot_noise_concentration(data, output_dir):
    """Plot concentration vs M for different noise levels"""

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    regimes = ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']
    regime_labels = ['HIGH SNR', 'TRANSITION', 'LOW SNR']

    # Focus on Gaussian noise
    for idx, (regime, regime_label) in enumerate(zip(regimes, regime_labels)):
        ax = axes[idx]

        # Find test case for this regime
        test_case = next((tc for tc in data['test_cases'] if tc['regime'] == regime), None)

        if not test_case:
            continue

        # Get Gaussian noise results
        gaussian_results = [nt for nt in test_case['noise_tests']
                          if nt['noise_type'] == 'gaussian']

        # Plot concentration vs M for different noise levels
        for nr in gaussian_results:
            noise_level = nr['noise_level']
            M_vals = [t['M'] for t in nr['M_tests']]
            concentrations = [t['concentration'] for t in nr['M_tests']]

            label = f"σ = {noise_level:.2f}"
            ax.plot(M_vals, concentrations, marker='o', markersize=7,
                   linewidth=2, label=label, alpha=0.8)

        ax.set_xlabel('Number of Bases (M)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Concentration', fontsize=12, fontweight='bold')
        ax.set_title(f'{regime_label}\n(ρ={test_case["rho"]:.3f})',
                    fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, title='Gaussian Noise')
        ax.set_xscale('log', base=2)

    plt.suptitle('Concentration vs M: Impact of Gaussian Noise',
                fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_noise_concentration.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def plot_adversarial_comparison(data, output_dir):
    """Plot comparison of adversarial base selection strategies"""

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    regimes = ['HIGH SNR', 'TRANSITION', 'LOW SNR']

    for idx, test_case in enumerate(data['adversarial_base_selection']):
        ax = axes[idx]

        N = test_case['N']
        r = test_case['r']
        rho = test_case['rho']

        # Extract strategies
        strategies = test_case['strategies']

        # For each strategy, plot precision vs M
        for strategy_result in strategies:
            strategy = strategy_result['strategy']
            M_vals = [t['M'] for t in strategy_result['M_tests']]
            precisions = [t['precision'] for t in strategy_result['M_tests']]

            # Style by strategy
            if strategy == 'max_phase_spread':
                marker, linestyle, color = 'v', '--', '#e74c3c'
                label = 'Max Phase Spread (adversarial)'
            elif strategy == 'clustered_phases':
                marker, linestyle, color = '^', '-.', '#f39c12'
                label = 'Clustered Phases (adversarial)'
            elif strategy == 'random':
                marker, linestyle, color = 's', ':', '#9b59b6'
                label = 'Random Selection'
            else:  # default
                marker, linestyle, color = 'o', '-', '#2ecc71'
                label = 'Default (sequential)'

            ax.plot(M_vals, precisions, marker=marker, markersize=8,
                   linestyle=linestyle, linewidth=2.5, label=label,
                   color=color, alpha=0.8)

        ax.set_xlabel('Number of Bases (M)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Precision', fontsize=12, fontweight='bold')
        ax.set_title(f'{regimes[idx]}\nN={N}, r={r} (ρ={rho:.3f})',
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0.85, 1.05])
        ax.legend(fontsize=9)
        ax.set_xscale('log', base=2)

        # Add reference line at 95%
        ax.axhline(0.95, color='gray', linestyle='--', alpha=0.3)

    plt.suptitle('Adversarial Base Selection: Impact on Precision\n(VRA robust to adversarial strategies)',
                fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_adversarial_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def plot_pathological_orders(data, output_dir):
    """Plot performance on pathological orders"""

    if len(data['pathological_orders']) == 0:
        print("No pathological order data to plot")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Extract data
    orders = []
    precisions = []
    recalls = []
    structures = []

    for po in data['pathological_orders']:
        orders.append(po['r'])
        precisions.append(po['precision'])
        recalls.append(po['recall'])
        structures.append(po['structure_type'])

    # Plot 1: Precision and Recall bars
    x = np.arange(len(orders))
    width = 0.35

    bars1 = ax1.bar(x - width/2, precisions, width, label='Precision',
                   color='#3498db', alpha=0.8)
    bars2 = ax1.bar(x + width/2, recalls, width, label='Recall',
                   color='#e74c3c', alpha=0.8)

    ax1.set_xlabel('Order (r)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Metric Value', fontsize=12, fontweight='bold')
    ax1.set_title('Pathological Orders: Precision & Recall\n(M=16, N=1009)',
                 fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"r={r}\n{s.replace('_', ' ')}"
                         for r, s in zip(orders, structures)],
                        fontsize=9)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_ylim([0, 1.05])

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                    f'{height:.0%}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Plot 2: Scatter of recall vs order size
    colors = ['#e74c3c' if 'large_prime' in s else '#f39c12' if 'highly' in s else '#3498db'
              for s in structures]

    for i, (r, rec, struct, color) in enumerate(zip(orders, recalls, structures, colors)):
        ax2.scatter(r, rec, s=200, color=color, alpha=0.7,
                   edgecolors='black', linewidth=1.5,
                   label=struct.replace('_', ' ') if i == structures.index(struct) else "")

    ax2.set_xlabel('Order (r)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Recall', fontsize=12, fontweight='bold')
    ax2.set_title('Recall vs Order Size\n(Larger orders → more bins → lower recall)',
                 fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 1.05])

    # Remove duplicate legend entries
    handles, labels = ax2.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax2.legend(by_label.values(), by_label.keys(), fontsize=10)

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_pathological_orders.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def generate_all_figures():
    """Generate all Phase 4.1 robustness figures"""

    print("Generating Phase 4.1 Robustness Figures")
    print("=" * 70)

    # Output directory
    output_dir = Path(__file__).parent.parent.parent / "Figures" / "Phase4_1_Robustness"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\n1. Loading noise injection data...")
    noise_data = load_latest_data(Path(__file__).parent.parent.parent / "Data" / "Phase4_Robustness" / "Noise_Injection")

    if noise_data:
        print("   Generating noise degradation curves...")
        plot_noise_degradation(noise_data, output_dir)

        print("   Generating concentration plots...")
        plot_noise_concentration(noise_data, output_dir)
    else:
        print("   WARNING: No noise injection data found")

    # Load adversarial data
    print("\n2. Loading adversarial test data...")
    adv_data = load_latest_data(Path(__file__).parent.parent.parent / "Data" / "Phase4_Robustness" / "Adversarial_Tests")

    if adv_data:
        print("   Generating adversarial comparison...")
        plot_adversarial_comparison(adv_data, output_dir)

        print("   Generating pathological orders plot...")
        plot_pathological_orders(adv_data, output_dir)
    else:
        print("   WARNING: No adversarial test data found")

    print(f"\n{'='*70}")
    print(f"All figures saved to: {output_dir}")


if __name__ == '__main__':
    generate_all_figures()
