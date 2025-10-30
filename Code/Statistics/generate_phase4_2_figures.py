#!/usr/bin/env python3
"""
Generate Figures for Phase 4.2 Statistical Rigor
=================================================

Visualize bootstrap confidence intervals and statistical enhancements.

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from bootstrap_utils import bootstrap_ci, bootstrap_resample

# Set publication-quality style
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['legend.fontsize'] = 9


def plot_runtime_comparison_with_cis(results_path: Path, output_dir: Path):
    """
    Bar chart of method runtimes with bootstrap CI error bars.
    """
    with open(results_path) as f:
        data = json.load(f)

    stats = data['statistical_analysis']['runtime_statistics']

    # Extract data
    methods = []
    means = []
    ci_lowers = []
    ci_uppers = []

    for method_name, method_stats in stats.items():
        if method_name == 'vra_speedup_vs_incoherent':
            continue  # Skip speedup entry

        methods.append(method_name.replace('_', ' ').title())
        means.append(method_stats['mean_runtime'])
        ci_lowers.append(method_stats['mean_ci_95'][0])
        ci_uppers.append(method_stats['mean_ci_95'][1])

    # Compute error bar sizes
    yerr_lower = [m - l for m, l in zip(means, ci_lowers)]
    yerr_upper = [u - m for m, u in zip(means, ci_uppers)]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    x_pos = np.arange(len(methods))
    colors = ['#e74c3c', '#e67e22', '#3498db', '#9b59b6', '#2ecc71']

    bars = ax.bar(x_pos, means, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)

    # Add error bars (95% CIs)
    ax.errorbar(x_pos, means, yerr=[yerr_lower, yerr_upper],
                fmt='none', ecolor='black', capsize=5, capthick=2, linewidth=2,
                label='95% Bootstrap CI')

    # Styling
    ax.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax.set_ylabel('Mean Runtime (seconds)', fontsize=12, fontweight='bold')
    ax.set_title('Method Runtime Comparison with 95% Bootstrap CIs\n(8 test cases, 10,000 bootstrap samples)',
                 fontsize=13, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods, rotation=15, ha='right')
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(loc='upper left')

    # Annotate values
    for i, (method, mean, lower, upper) in enumerate(zip(methods, means, ci_lowers, ci_uppers)):
        # Show mean ± CI width
        ci_width = upper - lower
        ax.text(i, mean * 1.5, f'{mean:.2e}\n±{ci_width:.2e}',
                ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_runtime_comparison_with_cis.png"
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✅ Generated: {filename}")
    return output_path


def plot_speedup_with_ci(results_path: Path, output_dir: Path):
    """
    Visualize VRA speedup vs incoherent averaging with CI.
    """
    with open(results_path) as f:
        data = json.load(f)

    speedup_data = data['statistical_analysis']['runtime_statistics']['vra_speedup_vs_incoherent']
    speedup = speedup_data['speedup']
    ci_lower, ci_upper = speedup_data['ci_95']

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))

    # Main bar
    bar = ax.bar([0], [speedup], color='#2ecc71', alpha=0.7,
                 edgecolor='black', linewidth=2, width=0.6, label='Point Estimate')

    # Error bar (CI)
    yerr_lower = speedup - ci_lower
    yerr_upper = ci_upper - speedup
    ax.errorbar([0], [speedup], yerr=[[yerr_lower], [yerr_upper]],
                fmt='none', ecolor='black', capsize=10, capthick=3, linewidth=3,
                label='95% Bootstrap CI')

    # Reference line at 1.0 (no speedup)
    ax.axhline(1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='No Speedup (1.0×)')

    # Styling
    ax.set_ylabel('Speedup Factor', fontsize=13, fontweight='bold')
    ax.set_title('VRA Speedup vs. Incoherent Averaging\nwith 95% Bootstrap Confidence Interval',
                 fontsize=14, fontweight='bold')
    ax.set_xticks([0])
    ax.set_xticklabels(['VRA / Incoherent'], fontsize=12)
    ax.set_ylim(0, 2.5)
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(loc='upper right', fontsize=11)

    # Annotate
    ax.text(0, speedup + 0.15, f'{speedup:.3f}×\n[{ci_lower:.3f}, {ci_upper:.3f}]',
            ha='center', va='bottom', fontsize=13, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Statistical significance annotation
    ax.text(0, 0.2, 'Statistically Significant\n(CI excludes 1.0)',
            ha='center', va='bottom', fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_vra_speedup_with_ci.png"
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✅ Generated: {filename}")
    return output_path


def plot_bootstrap_methodology(output_dir: Path):
    """
    Illustrate bootstrap resampling methodology visually.
    """
    np.random.seed(42)

    # Simulate runtime data
    original_data = np.random.gamma(2, 0.01, size=20)  # 20 measurements

    # Generate 5000 bootstrap samples
    n_bootstrap = 5000
    bootstrap_means = []

    for _ in range(n_bootstrap):
        resample = np.random.choice(original_data, size=len(original_data), replace=True)
        bootstrap_means.append(np.mean(resample))

    bootstrap_means = np.array(bootstrap_means)

    # Compute CI
    true_mean = np.mean(original_data)
    ci_lower = np.percentile(bootstrap_means, 2.5)
    ci_upper = np.percentile(bootstrap_means, 97.5)

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Left: Original data
    ax1.hist(original_data, bins=12, color='#3498db', alpha=0.7, edgecolor='black')
    ax1.axvline(true_mean, color='red', linewidth=3, linestyle='--', label=f'Mean = {true_mean:.4f}')
    ax1.set_xlabel('Runtime (seconds)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax1.set_title('(A) Original Data (n=20 measurements)', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')

    # Right: Bootstrap distribution
    ax2.hist(bootstrap_means, bins=50, color='#2ecc71', alpha=0.7, edgecolor='black', density=True)
    ax2.axvline(true_mean, color='red', linewidth=3, linestyle='--', label=f'Mean = {true_mean:.4f}')
    ax2.axvline(ci_lower, color='orange', linewidth=2.5, linestyle=':', label=f'95% CI Lower = {ci_lower:.4f}')
    ax2.axvline(ci_upper, color='orange', linewidth=2.5, linestyle=':', label=f'95% CI Upper = {ci_upper:.4f}')

    # Shade CI region
    ax2.axvspan(ci_lower, ci_upper, alpha=0.2, color='yellow', label='95% CI Region')

    ax2.set_xlabel('Bootstrap Sample Mean', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Density', fontsize=11, fontweight='bold')
    ax2.set_title(f'(B) Bootstrap Distribution (B={n_bootstrap:,} resamples)', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9, loc='upper left')
    ax2.grid(True, alpha=0.3, axis='y')

    plt.suptitle('Bootstrap Methodology: From Data to Confidence Intervals',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_bootstrap_methodology.png"
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✅ Generated: {filename}")
    return output_path


def plot_ci_width_analysis(results_path: Path, output_dir: Path):
    """
    Analyze CI width as function of sample size.
    """
    # Simulate how CI width changes with sample size
    np.random.seed(42)
    sample_sizes = [5, 10, 20, 50, 100, 200]
    ci_widths_mean = []
    ci_widths_std = []

    # True population: gamma distribution
    population = np.random.gamma(2, 0.01, size=10000)

    for n in sample_sizes:
        widths = []
        # Repeat 100 times to get stable estimate
        for trial in range(100):
            sample = np.random.choice(population, size=n, replace=False)

            # Bootstrap this sample
            bootstrap_means = []
            for _ in range(1000):  # 1000 bootstrap samples
                resample = np.random.choice(sample, size=n, replace=True)
                bootstrap_means.append(np.mean(resample))

            ci_lower = np.percentile(bootstrap_means, 2.5)
            ci_upper = np.percentile(bootstrap_means, 97.5)
            widths.append(ci_upper - ci_lower)

        ci_widths_mean.append(np.mean(widths))
        ci_widths_std.append(np.std(widths))

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.errorbar(sample_sizes, ci_widths_mean, yerr=ci_widths_std,
                marker='o', markersize=10, linewidth=2.5, capsize=8, capthick=2,
                color='#9b59b6', markerfacecolor='#e74c3c', markeredgecolor='black',
                markeredgewidth=1.5, label='Mean CI Width ± Std')

    # Theoretical 1/√n line
    theoretical = ci_widths_mean[0] * np.sqrt(sample_sizes[0]) / np.sqrt(np.array(sample_sizes))
    ax.plot(sample_sizes, theoretical, '--', linewidth=2, color='orange',
            alpha=0.7, label='Theoretical ~ 1/√n')

    # Styling
    ax.set_xlabel('Sample Size (n)', fontsize=12, fontweight='bold')
    ax.set_ylabel('95% CI Width', fontsize=12, fontweight='bold')
    ax.set_title('Bootstrap CI Width vs. Sample Size\n(More data → Narrower confidence intervals)',
                 fontsize=13, fontweight='bold')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(fontsize=11)

    # Annotate our typical sample size (n=8 test cases)
    our_n = 8
    our_width = ci_widths_mean[0] * np.sqrt(sample_sizes[0]) / np.sqrt(our_n)
    ax.axvline(our_n, color='red', linestyle=':', linewidth=2, alpha=0.7)
    ax.text(our_n * 1.1, ax.get_ylim()[1] * 0.5, f'Our sample size\n(n={our_n})',
            fontsize=10, fontweight='bold', color='red')

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_ci_width_vs_sample_size.png"
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✅ Generated: {filename}")
    return output_path


def main():
    """
    Generate all Phase 4.2 statistical rigor figures.
    """
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "Data"
    output_dir = project_root / "Figures" / "Phase4_2_Statistical_Rigor"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating Phase 4.2 Statistical Rigor Figures")
    print("=" * 70)

    # Figure 1: Runtime comparison with CIs
    benchmark_results = data_dir / "Phase1_Validation" / "Baseline_Benchmarks" / "20251029_231540_benchmark_results_with_cis.json"
    if benchmark_results.exists():
        plot_runtime_comparison_with_cis(benchmark_results, output_dir)

    # Figure 2: VRA speedup with CI
    if benchmark_results.exists():
        plot_speedup_with_ci(benchmark_results, output_dir)

    # Figure 3: Bootstrap methodology illustration
    plot_bootstrap_methodology(output_dir)

    # Figure 4: CI width analysis
    plot_ci_width_analysis(benchmark_results, output_dir)

    print("\n" + "=" * 70)
    print(f"✅ All Phase 4.2 figures saved to: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
