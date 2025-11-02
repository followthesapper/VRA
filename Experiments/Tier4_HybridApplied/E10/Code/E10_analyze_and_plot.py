#!/usr/bin/env python3
"""
E10 Analysis and Plotting
==========================

Analyze E10 results and generate figures demonstrating:
1. √M SNR scaling for coherent vs naive averaging
2. Precision/Recall tradeoff across alpha values
3. F1 score optimization
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

def load_results(results_path):
    """Load E10 results JSON."""
    with open(results_path, 'r') as f:
        return json.load(f)

def analyze_sqrt_m_scaling(results):
    """
    Analyze SNR scaling with M for both methods.

    Returns:
        coherent_snr: dict {M: mean_snr}
        naive_snr: dict {M: mean_snr}
    """
    data = results['results']
    M_values = sorted(set(r['M'] for r in data))

    coherent_snr = {}
    naive_snr = {}

    for M in M_values:
        # Get SNR for this M (averaged over trials and alphas)
        coherent_vals = [r['snr_db'] for r in data if r['M'] == M and r['method'] == 'coherent']
        naive_vals = [r['snr_db'] for r in data if r['M'] == M and r['method'] == 'naive']

        coherent_snr[M] = np.mean(coherent_vals)
        naive_snr[M] = np.mean(naive_vals)

    return coherent_snr, naive_snr

def analyze_pr_curves(results):
    """
    Analyze precision/recall curves across alpha values.

    Returns:
        pr_data: dict {method: {M: {alpha: (precision, recall, f1)}}}
    """
    data = results['results']
    alphas = results['meta']['alphas']
    M_values = results['meta']['M_values']

    pr_data = {'coherent': {}, 'naive': {}}

    for method in ['coherent', 'naive']:
        for M in M_values:
            pr_data[method][M] = {}
            for alpha in alphas:
                subset = [r for r in data if r['method'] == method and r['M'] == M and r['alpha'] == alpha]

                # Average over trials
                avg_p = np.mean([r['precision'] for r in subset])
                avg_r = np.mean([r['recall'] for r in subset])
                avg_f1 = np.mean([r['f1'] for r in subset])

                pr_data[method][M][alpha] = (avg_p, avg_r, avg_f1)

    return pr_data

def plot_sqrt_m_scaling(coherent_snr, naive_snr, output_dir):
    """Plot SNR vs M showing √M scaling for coherent method."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    M_vals = sorted(coherent_snr.keys())
    coherent_vals = [coherent_snr[M] for M in M_vals]
    naive_vals = [naive_snr[M] for M in M_vals]

    # Left: Linear scale
    ax1.plot(M_vals, coherent_vals, 'o-', linewidth=2, markersize=8, label='Coherent (VRA)', color='#2E86AB')
    ax1.plot(M_vals, naive_vals, 's-', linewidth=2, markersize=8, label='Naive', color='#A23B72')
    ax1.set_xlabel('Number of Trials (M)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('SNR (dB)', fontsize=12, fontweight='bold')
    ax1.set_title('SNR Scaling with M', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log', base=2)
    ax1.set_xticks(M_vals)
    ax1.set_xticklabels([str(m) for m in M_vals])

    # Add theoretical M line for coherent (SNR scales as M in dB)
    baseline_coherent = coherent_vals[0]
    theoretical = [baseline_coherent + 10 * np.log10(M / M_vals[0]) for M in M_vals]
    ax1.plot(M_vals, theoretical, '--', color='gray', alpha=0.6, label='Theoretical 10·log₁₀(M)', linewidth=2)
    ax1.legend(fontsize=11)

    # Right: SNR gain relative to M=4
    baseline_c = coherent_vals[0]
    baseline_n = naive_vals[0]

    gain_coherent = [snr - baseline_c for snr in coherent_vals]
    gain_naive = [snr - baseline_n for snr in naive_vals]

    ax2.plot(M_vals, gain_coherent, 'o-', linewidth=2, markersize=8, label='Coherent Gain', color='#2E86AB')
    ax2.plot(M_vals, gain_naive, 's-', linewidth=2, markersize=8, label='Naive Gain', color='#A23B72')
    ax2.set_xlabel('Number of Trials (M)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('SNR Gain (dB)', fontsize=12, fontweight='bold')
    ax2.set_title('SNR Gain Relative to M=4', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.set_xscale('log', base=2)
    ax2.set_xticks(M_vals)
    ax2.set_xticklabels([str(m) for m in M_vals])
    ax2.axhline(0, color='black', linewidth=0.5)

    plt.tight_layout()
    output_path = output_dir / 'E10_sqrt_m_scaling.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"[ok] Saved {output_path}")
    plt.close()

def plot_pr_tradeoff(pr_data, output_dir):
    """Plot precision/recall tradeoff for different M values."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    M_values = sorted(pr_data['coherent'].keys())
    colors = plt.cm.viridis(np.linspace(0, 1, len(M_values)))

    for idx, method in enumerate(['coherent', 'naive']):
        row = idx

        # Column 0: Precision vs Alpha
        ax = axes[row, 0]
        for i, M in enumerate(M_values):
            alphas = sorted(pr_data[method][M].keys())
            precisions = [pr_data[method][M][a][0] for a in alphas]
            ax.plot(alphas, precisions, 'o-', linewidth=2, markersize=6,
                   label=f'M={M}', color=colors[i])
        ax.set_xlabel('Alpha (α)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Precision', fontsize=11, fontweight='bold')
        ax.set_title(f'{method.capitalize()}: Precision vs α', fontsize=12, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim([-0.05, 1.05])

        # Column 1: Recall vs Alpha
        ax = axes[row, 1]
        for i, M in enumerate(M_values):
            alphas = sorted(pr_data[method][M].keys())
            recalls = [pr_data[method][M][a][1] for a in alphas]
            ax.plot(alphas, recalls, 's-', linewidth=2, markersize=6,
                   label=f'M={M}', color=colors[i])
        ax.set_xlabel('Alpha (α)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Recall', fontsize=11, fontweight='bold')
        ax.set_title(f'{method.capitalize()}: Recall vs α', fontsize=12, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim([-0.05, 1.05])

        # Column 2: F1 Score vs Alpha
        ax = axes[row, 2]
        for i, M in enumerate(M_values):
            alphas = sorted(pr_data[method][M].keys())
            f1s = [pr_data[method][M][a][2] for a in alphas]
            ax.plot(alphas, f1s, '^-', linewidth=2, markersize=6,
                   label=f'M={M}', color=colors[i])
        ax.set_xlabel('Alpha (α)', fontsize=11, fontweight='bold')
        ax.set_ylabel('F1 Score', fontsize=11, fontweight='bold')
        ax.set_title(f'{method.capitalize()}: F1 vs α', fontsize=12, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim([-0.05, 1.05])

    plt.tight_layout()
    output_path = output_dir / 'E10_pr_curves.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"[ok] Saved {output_path}")
    plt.close()

def plot_f1_heatmap(pr_data, output_dir):
    """Plot F1 score heatmap: M vs Alpha for both methods."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    M_values = sorted(pr_data['coherent'].keys())
    alphas = sorted(pr_data['coherent'][M_values[0]].keys())

    for ax, method in zip([ax1, ax2], ['coherent', 'naive']):
        # Build F1 matrix
        f1_matrix = np.zeros((len(alphas), len(M_values)))

        for i, alpha in enumerate(alphas):
            for j, M in enumerate(M_values):
                f1_matrix[i, j] = pr_data[method][M][alpha][2]

        im = ax.imshow(f1_matrix, aspect='auto', cmap='YlGnBu', vmin=0, vmax=1)
        ax.set_xticks(range(len(M_values)))
        ax.set_xticklabels([str(m) for m in M_values])
        ax.set_yticks(range(len(alphas)))
        ax.set_yticklabels([f'{a:.1f}' for a in alphas])
        ax.set_xlabel('Number of Trials (M)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Alpha (α)', fontsize=12, fontweight='bold')
        ax.set_title(f'{method.capitalize()}: F1 Score Heatmap', fontsize=13, fontweight='bold')

        # Add text annotations
        for i in range(len(alphas)):
            for j in range(len(M_values)):
                text = ax.text(j, i, f'{f1_matrix[i, j]:.2f}',
                              ha="center", va="center", color="black", fontsize=9)

        plt.colorbar(im, ax=ax, label='F1 Score')

    plt.tight_layout()
    output_path = output_dir / 'E10_f1_heatmap.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"[ok] Saved {output_path}")
    plt.close()

def main():
    # Paths
    repo_root = Path(__file__).parent.parent.parent
    results_path = repo_root / 'Data' / 'Experiments' / 'Tier4' / 'E10' / 'E10_stationary_tones_results.json'
    output_dir = repo_root / 'Figures' / 'Experiments' / 'Tier4'
    output_dir.mkdir(parents=True, exist_ok=True)

    print("E10 Analysis: VRA on Stationary Tones\n")

    # Load results
    print(f"Loading results from {results_path}")
    results = load_results(results_path)

    # Analyze √M scaling
    print("\n1. Analyzing √M SNR scaling...")
    coherent_snr, naive_snr = analyze_sqrt_m_scaling(results)
    plot_sqrt_m_scaling(coherent_snr, naive_snr, output_dir)

    # Print SNR summary
    print("\nSNR Summary:")
    print("  Coherent (VRA):")
    for M in sorted(coherent_snr.keys()):
        print(f"    M={M:3d}: {coherent_snr[M]:.2f} dB")
    print("\n  Naive:")
    for M in sorted(naive_snr.keys()):
        print(f"    M={M:3d}: {naive_snr[M]:.2f} dB")

    # Analyze PR curves
    print("\n2. Analyzing precision/recall curves...")
    pr_data = analyze_pr_curves(results)
    plot_pr_tradeoff(pr_data, output_dir)

    # F1 heatmap
    print("\n3. Creating F1 score heatmap...")
    plot_f1_heatmap(pr_data, output_dir)

    # Find optimal operating points
    print("\n4. Optimal operating points (max F1):")
    for method in ['coherent', 'naive']:
        print(f"\n  {method.capitalize()}:")
        for M in sorted(pr_data[method].keys()):
            best_alpha = max(pr_data[method][M].items(), key=lambda x: x[1][2])
            alpha, (p, r, f1) = best_alpha
            print(f"    M={M:3d}: α={alpha:.1f} → P={p:.3f}, R={r:.3f}, F1={f1:.3f}")

    print("\n✅ E10 analysis complete!")

if __name__ == "__main__":
    main()
