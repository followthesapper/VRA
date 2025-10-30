#!/usr/bin/env python3
"""
Generate Figures from Cross-Moduli and Baseline Results
========================================================

Creates publication-quality figures:
1. Cross-moduli regime map (R² vs ρ)
2. Baseline concentration vs √M plots
3. Regime statistics comparison

Author: Dylan Vaca
Date: October 2025
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# Set publication-quality defaults
plt.rcParams.update({
    'font.size': 10,
    'font.family': 'serif',
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.titlesize': 13,
    'lines.linewidth': 1.5,
    'lines.markersize': 6
})

def classify_regime(rho):
    """Classify regime based on ρ value"""
    if rho < 0.146:
        return 'HIGH_SNR'
    elif rho < 0.263:
        return 'TRANSITION'
    else:
        return 'LOW_SNR'

def load_cross_moduli_data(json_path):
    """Load cross-moduli sweep results"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def load_baseline_data(json_path):
    """Load baseline revalidation results"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def plot_cross_moduli_regime_map(data, output_file):
    """Generate regime map: R² vs ρ for all moduli"""

    fig, ax = plt.subplots(figsize=(8, 5))

    # Define colors for each modulus
    colors = {997: 'C0', 1009: 'C1', 1013: 'C2', 2017: 'C3'}
    markers = {997: 'o', 1009: 's', 1013: '^', 2017: 'D'}

    # Plot data by modulus
    for modulus_result in data['results']:
        N = modulus_result['N']
        rhos = []
        r_squared = []

        for test_point in modulus_result['test_points']:
            # Skip insufficient data
            if len(test_point['M_values']) < 3:
                continue

            rhos.append(test_point['actual_rho'])
            r_squared.append(test_point['sqrt_m_fit']['r_squared'])

        ax.scatter(rhos, r_squared,
                  color=colors[N], marker=markers[N],
                  s=80, alpha=0.7,
                  label=f'$N={N}$', edgecolors='black', linewidth=0.5)

    # Add regime boundaries
    ax.axvline(0.146, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='HIGH/TRANS')
    ax.axvline(0.263, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='TRANS/LOW')

    # Add regime labels
    ax.text(0.05, 0.95, 'HIGH SNR', transform=ax.transAxes,
            fontsize=10, va='top', ha='left', color='gray', alpha=0.7)
    ax.text(0.35, 0.95, 'TRANSITION', transform=ax.transAxes,
            fontsize=10, va='top', ha='center', color='gray', alpha=0.7)
    ax.text(0.75, 0.95, 'LOW SNR', transform=ax.transAxes,
            fontsize=10, va='top', ha='center', color='gray', alpha=0.7)

    # Add R² thresholds
    ax.axhline(0.90, color='green', linestyle='--', linewidth=0.8, alpha=0.3)
    ax.axhline(0.95, color='green', linestyle='--', linewidth=0.8, alpha=0.3)

    ax.set_xlabel(r'$\rho = r/N$')
    ax.set_ylabel(r'$R^2$ ($\sqrt{M}$ fit)')
    ax.set_title('VRA Cross-Modulus Validation: Regime Map')
    ax.legend(loc='lower right', framealpha=0.95)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-0.02, 0.52)
    ax.set_ylim(0.5, 1.05)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_file}")

def plot_baseline_sqrt_m_fits(data, output_file):
    """Generate concentration vs √M plots for baseline tests"""

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    # Select 3 key tests: r=8, r=168, r=504
    test_indices = [3, 1, 0]  # HIGH SNR (r=8), TRANSITION (r=168), LOW SNR (r=504)
    titles = ['HIGH SNR\n$r=8$, $\\rho=0.008$',
              'TRANSITION\n$r=168$, $\\rho=0.167$',
              'LOW SNR\n$r=504$, $\\rho=0.500$']

    for idx, (test_idx, title) in enumerate(zip(test_indices, titles)):
        ax = axes[idx]
        test = data['tests'][test_idx]

        # Extract data
        M_values = np.array(test['M_values'])
        concentrations = np.array([res['concentration'] for res in test['results']])

        sqrt_M = np.sqrt(M_values)

        # Plot data points
        ax.scatter(sqrt_M, concentrations, s=60, alpha=0.7,
                  color='C0', edgecolors='black', linewidth=0.5)

        # Plot fit line
        slope = test['sqrt_m_fit']['slope']
        intercept = test['sqrt_m_fit']['intercept']
        r_squared = test['sqrt_m_fit']['r_squared']

        sqrt_M_fit = np.linspace(sqrt_M.min(), sqrt_M.max(), 100)
        conc_fit = slope * sqrt_M_fit + intercept

        ax.plot(sqrt_M_fit, conc_fit, 'r--', linewidth=1.5, alpha=0.7,
               label=f'$R^2={r_squared:.3f}$')

        ax.set_xlabel(r'$\sqrt{M}$')
        if idx == 0:
            ax.set_ylabel('Concentration $C_M$')
        ax.set_title(title)
        ax.legend(loc='best', framealpha=0.95)
        ax.grid(True, alpha=0.3)

    fig.suptitle('VRA Baseline: Concentration vs $\sqrt{M}$ (Corrected Implementation)',
                 fontsize=13, y=1.02)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_file}")

def plot_regime_statistics_comparison(cross_moduli_summary, output_file):
    """Generate regime statistics comparison bar chart"""

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    regimes = ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']
    regime_labels = ['HIGH SNR', 'TRANSITION', 'LOW SNR']
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']

    # Extract statistics
    r2_means = []
    r2_stds = []
    precisions = []
    n_points = []

    for regime in regimes:
        if regime in cross_moduli_summary:
            stats = cross_moduli_summary[regime]
            r2_means.append(stats['r_squared']['mean'])
            r2_stds.append(stats['r_squared']['std'])
            precisions.append(stats['precision']['mean'] * 100)
            n_points.append(stats['n_points'])
        else:
            r2_means.append(0)
            r2_stds.append(0)
            precisions.append(0)
            n_points.append(0)

    # Plot 1: R² mean with std
    ax1 = axes[0]
    bars = ax1.bar(regime_labels, r2_means, yerr=r2_stds,
                   color=colors, alpha=0.7, capsize=5,
                   edgecolor='black', linewidth=1)
    ax1.axhline(0.90, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax1.axhline(0.95, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax1.set_ylabel(r'$R^2$ (mean $\pm$ std)')
    ax1.set_title('$\sqrt{M}$ Fit Quality')
    ax1.set_ylim(0.7, 1.05)
    ax1.grid(True, axis='y', alpha=0.3)

    # Plot 2: Precision
    ax2 = axes[1]
    bars = ax2.bar(regime_labels, precisions,
                   color=colors, alpha=0.7,
                   edgecolor='black', linewidth=1)
    ax2.axhline(100, color='green', linestyle='--', linewidth=1, alpha=0.5)
    ax2.set_ylabel('Precision (%)')
    ax2.set_title('Peak Detection Precision')
    ax2.set_ylim(95, 101)
    ax2.grid(True, axis='y', alpha=0.3)

    # Plot 3: Number of data points
    ax3 = axes[2]
    bars = ax3.bar(regime_labels, n_points,
                   color=colors, alpha=0.7,
                   edgecolor='black', linewidth=1)
    ax3.set_ylabel('Number of test points')
    ax3.set_title('Cross-Modulus Coverage')
    ax3.grid(True, axis='y', alpha=0.3)

    fig.suptitle('Cross-Modulus Statistics by Regime', fontsize=13, y=1.00)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_file}")

def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / 'Data'
    figures_dir = base_dir / 'Figures' / 'Validation'
    figures_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load data
    print("Loading data...")
    cross_moduli_file = data_dir / 'cross_moduli' / '20251029_220803_cross_moduli_sweep.json'
    baseline_file = data_dir / 'baseline_revalidation' / '20251029_220722_baseline_revalidation.json'
    cross_moduli_summary_file = data_dir / 'cross_moduli' / '20251029_220803_cross_moduli_summary.json'

    cross_moduli_data = load_cross_moduli_data(cross_moduli_file)
    baseline_data = load_baseline_data(baseline_file)

    with open(cross_moduli_summary_file, 'r') as f:
        cross_moduli_summary = json.load(f)['regime_statistics']

    # Generate figures
    print("\nGenerating figures...")

    # Figure 1: Cross-moduli regime map
    plot_cross_moduli_regime_map(
        cross_moduli_data,
        figures_dir / f'{timestamp}_cross_moduli_regime_map.png'
    )

    # Figure 2: Baseline √M fits
    plot_baseline_sqrt_m_fits(
        baseline_data,
        figures_dir / f'{timestamp}_baseline_sqrt_m_fits.png'
    )

    # Figure 3: Regime statistics comparison
    plot_regime_statistics_comparison(
        cross_moduli_summary,
        figures_dir / f'{timestamp}_regime_statistics.png'
    )

    print("\nAll figures generated successfully!")
    print(f"Output directory: {figures_dir}")

if __name__ == '__main__':
    main()
