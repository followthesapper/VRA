#!/usr/bin/env python3
"""
Phase 1.3 Benchmark Figure Generation
======================================

Generate comparison figures for VRA vs. baseline methods:
1. Runtime comparison by method
2. Runtime scaling with M
3. Coherent vs Incoherent comparison
4. Success rate comparison

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


def load_benchmark_data():
    """Load most recent benchmark results"""
    data_dir = Path(__file__).parent.parent.parent / "Data" / "benchmarks"
    files = list(data_dir.glob("*_benchmark_results.json"))

    if not files:
        return None

    latest = max(files, key=lambda p: p.stat().st_mtime)
    with open(latest, 'r') as f:
        return json.load(f)


def plot_runtime_comparison(data, output_dir):
    """Plot runtime comparison across methods"""

    fig, ax = plt.subplots(figsize=(12, 6))

    # Collect runtimes by method
    method_runtimes = {
        'Brute Force': [],
        'Baby-Step\nGiant-Step': [],
        'Single-Base\nFFT': [],
        'Incoherent\nAveraging': [],
        'VRA\nCoherent': []
    }

    for test_case in data['test_cases']:
        # Brute force
        if test_case['methods']['brute_force']['applicable']:
            method_runtimes['Brute Force'].append(
                test_case['methods']['brute_force']['runtime']
            )

        # BSGS
        if test_case['methods']['bsgs']['applicable']:
            method_runtimes['Baby-Step\nGiant-Step'].append(
                test_case['methods']['bsgs']['runtime']
            )

        # Single FFT (take first M value)
        method_runtimes['Single-Base\nFFT'].append(
            test_case['methods']['single_fft'][0]['runtime']
        )

        # Incoherent (average across M values)
        inc_runtimes = [r['runtime'] for r in test_case['methods']['incoherent_averaging']]
        method_runtimes['Incoherent\nAveraging'].append(np.mean(inc_runtimes))

        # VRA (average across M values)
        vra_runtimes = [r['runtime'] for r in test_case['methods']['vra_coherent']]
        method_runtimes['VRA\nCoherent'].append(np.mean(vra_runtimes))

    # Box plot
    methods = list(method_runtimes.keys())
    data_to_plot = [method_runtimes[m] for m in methods if len(method_runtimes[m]) > 0]
    labels = [m for m in methods if len(method_runtimes[m]) > 0]

    bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)

    # Color code
    colors = ['#ff9999', '#ffcc99', '#99ccff', '#ffb3ba', '#95e1d3']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_ylabel('Runtime (seconds)', fontsize=12)
    ax.set_title('Runtime Comparison: VRA vs. Baseline Methods\n(8 test cases, averaged across M values)',
                fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_yscale('log')

    # Add mean values as text
    for i, (method, runtimes) in enumerate([(m, method_runtimes[m]) for m in labels]):
        if len(runtimes) > 0:
            mean_val = np.mean(runtimes)
            ax.text(i+1, mean_val * 1.5, f'μ={mean_val:.4f}s',
                   ha='center', va='bottom', fontsize=9,
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_runtime_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def plot_scaling_with_M(data, output_dir):
    """Plot runtime scaling with M for averaging methods"""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    M_values = data['metadata']['M_values']

    # Collect data
    inc_by_M = {M: [] for M in M_values}
    vra_by_M = {M: [] for M in M_values}

    for test_case in data['test_cases']:
        for result in test_case['methods']['incoherent_averaging']:
            inc_by_M[result['M']].append(result['runtime'])

        for result in test_case['methods']['vra_coherent']:
            vra_by_M[result['M']].append(result['runtime'])

    # Plot 1: Both methods
    M_vals = sorted(inc_by_M.keys())
    inc_means = [np.mean(inc_by_M[M]) for M in M_vals]
    vra_means = [np.mean(vra_by_M[M]) for M in M_vals]
    inc_stds = [np.std(inc_by_M[M]) for M in M_vals]
    vra_stds = [np.std(vra_by_M[M]) for M in M_vals]

    ax1.errorbar(M_vals, inc_means, yerr=inc_stds, marker='o', markersize=8,
                linewidth=2, capsize=5, label='Incoherent Averaging', color='#ff6b6b')
    ax1.errorbar(M_vals, vra_means, yerr=vra_stds, marker='s', markersize=8,
                linewidth=2, capsize=5, label='VRA Coherent', color='#4ecdc4')

    ax1.set_xlabel('Number of Bases (M)', fontsize=12)
    ax1.set_ylabel('Mean Runtime (seconds)', fontsize=12)
    ax1.set_title('Runtime Scaling with M\n(Coherent vs. Incoherent)',
                 fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)
    ax1.set_xscale('log', base=2)

    # Plot 2: Speedup ratio
    speedup = [inc_means[i] / vra_means[i] for i in range(len(M_vals))]

    ax2.plot(M_vals, speedup, marker='D', markersize=10, linewidth=3,
            color='#95e1d3', markeredgecolor='black', markeredgewidth=1.5)
    ax2.axhline(1.0, color='red', linestyle='--', alpha=0.5, label='No speedup')

    ax2.set_xlabel('Number of Bases (M)', fontsize=12)
    ax2.set_ylabel('Speedup Factor\n(Incoherent / Coherent)', fontsize=12)
    ax2.set_title('VRA Coherent Speedup vs. Incoherent\n(Higher is better)',
                 fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_xscale('log', base=2)
    ax2.legend(fontsize=10)

    # Add speedup values as text
    for i, (M, sp) in enumerate(zip(M_vals, speedup)):
        ax2.text(M, sp + 0.05, f'{sp:.2f}×',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_scaling_with_M.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def plot_success_rates(data, output_dir):
    """Plot success rates for all methods"""

    fig, ax = plt.subplots(figsize=(10, 6))

    methods = ['Brute\nForce', 'BSGS', 'Single\nFFT', 'Incoherent\nAvg', 'VRA\nCoherent']
    success_rates = []
    applicable_counts = []

    # Brute force
    bf_success = sum(1 for tc in data['test_cases']
                     if tc['methods']['brute_force']['correct'])
    bf_total = sum(1 for tc in data['test_cases']
                   if tc['methods']['brute_force']['applicable'])
    success_rates.append(bf_success / bf_total if bf_total > 0 else 0)
    applicable_counts.append(bf_total)

    # BSGS
    bsgs_success = sum(1 for tc in data['test_cases']
                       if tc['methods']['bsgs']['correct'])
    bsgs_total = sum(1 for tc in data['test_cases']
                     if tc['methods']['bsgs']['applicable'])
    success_rates.append(bsgs_success / bsgs_total if bsgs_total > 0 else 0)
    applicable_counts.append(bsgs_total)

    # Single FFT
    sf_results = [r for tc in data['test_cases']
                  for r in tc['methods']['single_fft']]
    sf_success = sum(1 for r in sf_results if r['correct'])
    success_rates.append(sf_success / len(sf_results) if len(sf_results) > 0 else 0)
    applicable_counts.append(len(sf_results))

    # Incoherent
    inc_results = [r for tc in data['test_cases']
                   for r in tc['methods']['incoherent_averaging']]
    inc_success = sum(1 for r in inc_results if r['correct'])
    success_rates.append(inc_success / len(inc_results) if len(inc_results) > 0 else 0)
    applicable_counts.append(len(inc_results))

    # VRA
    vra_results = [r for tc in data['test_cases']
                   for r in tc['methods']['vra_coherent']]
    vra_success = sum(1 for r in vra_results if r['correct'])
    success_rates.append(vra_success / len(vra_results) if len(vra_results) > 0 else 0)
    applicable_counts.append(len(vra_results))

    # Bar plot
    colors = ['#2ecc71' if sr > 0.5 else '#e74c3c' for sr in success_rates]
    bars = ax.bar(methods, success_rates, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

    ax.set_ylabel('Success Rate', fontsize=12)
    ax.set_title('Order Detection Success Rate: VRA vs. Baselines\n(Direct order estimation from spectral peaks)',
                fontsize=13, fontweight='bold')
    ax.set_ylim([0, 1.05])
    ax.grid(True, alpha=0.3, axis='y')

    # Add percentages and counts
    for i, (bar, rate, count) in enumerate(zip(bars, success_rates, applicable_counts)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
               f'{rate:.0%}\n(n={count})',
               ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Add note
    ax.text(0.5, -0.15,
           'Note: FFT methods (including VRA) use precision/recall metrics in practice,\n'
           'not direct order estimation. This shows why that design choice is correct.',
           ha='center', va='top', transform=ax.transAxes,
           fontsize=9, style='italic',
           bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_success_rates.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def generate_all_figures():
    """Generate all Phase 1.3 benchmark figures"""

    print("Generating Phase 1.3 Benchmark Figures")
    print("=" * 70)

    # Load data
    data = load_benchmark_data()
    if data is None:
        print("ERROR: No benchmark data found")
        return

    # Output directory
    output_dir = Path(__file__).parent.parent.parent / "Figures" / "Phase1_3_Benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate figures
    print("\n1. Runtime Comparison...")
    plot_runtime_comparison(data, output_dir)

    print("\n2. Scaling with M...")
    plot_scaling_with_M(data, output_dir)

    print("\n3. Success Rates...")
    plot_success_rates(data, output_dir)

    print(f"\n{'='*70}")
    print(f"All figures saved to: {output_dir}")


if __name__ == '__main__':
    generate_all_figures()
