#!/usr/bin/env python3
"""
Phase 1.2 Figure Generation
============================

Generate figures for:
1. Extended moduli sweep (30 diverse moduli types)
2. Regime boundary validation (dense sampling)

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "Core"))

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


def plot_extended_moduli_overview(data, output_dir):
    """Plot R² vs ρ for all moduli types"""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Color map for modulus types
    type_colors = {
        'small': '#1f77b4',
        'safe': '#ff7f0e',
        'Carmichael': '#2ca02c',
        'prime': '#d62728',
        'semiprime': '#9467bd'
    }

    # Collect data by type
    type_data = {}

    for modulus_result in data['results']:
        N = modulus_result['N']
        mtype = modulus_result['modulus_type'].split()[0]

        if mtype not in type_data:
            type_data[mtype] = {'rho': [], 'r2': [], 'N': [], 'regime': []}

        for test in modulus_result['test_points']:
            type_data[mtype]['rho'].append(test['actual_rho'])
            type_data[mtype]['r2'].append(test['sqrt_m_fit']['r_squared'])
            type_data[mtype]['N'].append(N)
            type_data[mtype]['regime'].append(test['regime'])

    # Plot 1: R² vs ρ by modulus type
    for mtype, tdata in type_data.items():
        color = type_colors.get(mtype, 'gray')
        ax1.scatter(tdata['rho'], tdata['r2'],
                   label=mtype, alpha=0.6, s=50, color=color)

    # Add regime boundaries
    ax1.axvline(0.146, color='red', linestyle='--', alpha=0.5, label='Boundary 1')
    ax1.axvline(0.263, color='orange', linestyle='--', alpha=0.5, label='Boundary 2')

    ax1.set_xlabel('ρ = r/N', fontsize=12)
    ax1.set_ylabel('R² (√M fit)', fontsize=12)
    ax1.set_title('Extended Moduli Sweep: R² vs ρ\n(30 diverse moduli)', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9, loc='lower left')
    ax1.set_ylim([-0.05, 1.05])

    # Plot 2: R² distribution by regime
    regime_r2 = {'HIGH_SNR': [], 'TRANSITION': [], 'LOW_SNR': []}

    for modulus_result in data['results']:
        for test in modulus_result['test_points']:
            regime = test['regime']
            r2 = test['sqrt_m_fit']['r_squared']
            regime_r2[regime].append(r2)

    regimes = ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']
    regime_labels = ['HIGH SNR\n(ρ < 0.146)', 'TRANSITION\n(0.146–0.263)', 'LOW SNR\n(ρ > 0.263)']

    bp = ax2.boxplot([regime_r2[r] for r in regimes if len(regime_r2[r]) > 0],
                     labels=[regime_labels[i] for i, r in enumerate(regimes) if len(regime_r2[r]) > 0],
                     patch_artist=True)

    colors = ['#ff9999', '#66b3ff', '#99ff99']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax2.set_ylabel('R² (√M fit)', fontsize=12)
    ax2.set_title('R² Distribution by Regime\n(All moduli types)', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_ylim([-0.05, 1.05])

    # Add statistics
    for i, regime in enumerate([r for r in regimes if len(regime_r2[r]) > 0]):
        r2_vals = regime_r2[regime]
        median = np.median(r2_vals)
        mean = np.mean(r2_vals)
        ax2.text(i+1, 0.05, f'n={len(r2_vals)}\nμ={mean:.3f}\nM={median:.3f}',
                ha='center', va='bottom', fontsize=9, bbox=dict(boxstyle='round',
                facecolor='white', alpha=0.7))

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_extended_moduli_overview.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def plot_modulus_type_comparison(data, output_dir):
    """Compare performance across modulus types"""

    fig, ax = plt.subplots(figsize=(12, 8))

    # Collect statistics by type
    type_stats = {}

    for modulus_result in data['results']:
        mtype = modulus_result['modulus_type'].split()[0]

        if mtype not in type_stats:
            type_stats[mtype] = {'r2': [], 'precision': [], 'count': 0}

        for test in modulus_result['test_points']:
            type_stats[mtype]['r2'].append(test['sqrt_m_fit']['r_squared'])
            type_stats[mtype]['precision'].append(np.mean(test['precisions']))
            type_stats[mtype]['count'] += 1

    # Sort by mean R²
    types_sorted = sorted(type_stats.keys(),
                         key=lambda t: np.mean(type_stats[t]['r2']),
                         reverse=True)

    y_pos = np.arange(len(types_sorted))

    # Plot horizontal bars
    means = [np.mean(type_stats[t]['r2']) for t in types_sorted]
    stds = [np.std(type_stats[t]['r2']) for t in types_sorted]
    counts = [type_stats[t]['count'] for t in types_sorted]

    bars = ax.barh(y_pos, means, xerr=stds, alpha=0.7, capsize=5)

    # Color code by performance
    for i, (bar, mean_val) in enumerate(zip(bars, means)):
        if mean_val > 0.9:
            bar.set_color('#99ff99')  # Green
        elif mean_val > 0.7:
            bar.set_color('#ffff99')  # Yellow
        else:
            bar.set_color('#ff9999')  # Red

    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"{t} (n={counts[i]})" for i, t in enumerate(types_sorted)])
    ax.set_xlabel('Mean R² (√M fit)', fontsize=12)
    ax.set_title('VRA Performance by Modulus Type\n(Extended Sweep)',
                fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.set_xlim([0, 1.05])

    # Add vertical reference line at 0.9
    ax.axvline(0.9, color='green', linestyle='--', alpha=0.5, label='R² = 0.9')
    ax.legend()

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_modulus_type_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def plot_boundary_validation(data, output_dir):
    """Plot regime boundary validation results"""

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax_idx, boundary_data in enumerate(data['boundaries']):
        ax = axes[ax_idx]
        boundary_center = boundary_data['boundary_center']

        # Collect all points
        all_rho = []
        all_r2 = []
        all_precision = []
        all_N = []

        for modulus_result in boundary_data['moduli_results']:
            N = modulus_result['N']
            for test in modulus_result['tests']:
                all_rho.append(test['actual_rho'])
                all_r2.append(test['r_squared'])
                all_precision.append(test['precision'])
                all_N.append(N)

        # Sort by rho
        sort_idx = np.argsort(all_rho)
        rho_sorted = np.array(all_rho)[sort_idx]
        r2_sorted = np.array(all_r2)[sort_idx]
        precision_sorted = np.array(all_precision)[sort_idx]
        N_sorted = np.array(all_N)[sort_idx]

        # Scatter plot
        scatter = ax.scatter(rho_sorted, r2_sorted, c=N_sorted,
                           cmap='viridis', s=100, alpha=0.7, edgecolors='black')

        # Boundary line
        ax.axvline(boundary_center, color='red', linestyle='--',
                  linewidth=2, label=f'Boundary: ρ = {boundary_center:.3f}')

        # Moving average
        window = 5
        if len(rho_sorted) >= window:
            r2_smooth = np.convolve(r2_sorted, np.ones(window)/window, mode='valid')
            rho_smooth = rho_sorted[window-1:]
            ax.plot(rho_smooth, r2_smooth, 'r-', linewidth=2,
                   alpha=0.5, label='Moving avg (n=5)')

        ax.set_xlabel('ρ = r/N', fontsize=12)
        ax.set_ylabel('R² (√M fit)', fontsize=12)
        ax.set_title(f'Boundary Validation: ρ = {boundary_center:.3f}\n'
                    f'(n={len(all_rho)} points, 6 moduli)',
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        ax.set_ylim([-0.05, 1.05])

        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Modulus N', fontsize=10)

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_boundary_validation.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def generate_all_figures():
    """Generate all Phase 1.2 figures"""

    print("Generating Phase 1.2 Figures")
    print("=" * 70)

    # Output directory
    output_dir = Path(__file__).parent.parent.parent / "Figures" / "Phase1_2_Validation"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extended moduli sweep
    print("\n1. Extended Moduli Sweep Figures...")
    extended_data = load_latest_data(Path(__file__).parent.parent.parent / "Data" / "extended_moduli")

    if extended_data:
        plot_extended_moduli_overview(extended_data, output_dir)
        plot_modulus_type_comparison(extended_data, output_dir)
    else:
        print("  WARNING: No extended moduli data found")

    # Boundary validation
    print("\n2. Regime Boundary Validation Figures...")
    boundary_data = load_latest_data(Path(__file__).parent.parent.parent / "Data" / "regime_boundaries")

    if boundary_data:
        plot_boundary_validation(boundary_data, output_dir)
    else:
        print("  WARNING: No boundary validation data found")

    print(f"\n{'='*70}")
    print(f"All figures saved to: {output_dir}")


if __name__ == '__main__':
    generate_all_figures()
