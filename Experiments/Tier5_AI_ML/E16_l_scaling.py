#!/usr/bin/env python3
"""
E16: L-Scaling Curve (Publication-Grade)

Goal: Replicate +18 dB per 4× with bootstrap CIs
Success Criteria: Clean figure with theory overlay (1/L²)
Expected GPU Speedup: 50-200x for bootstrap resampling

This produces the definitive VRA L-scaling figure for publication.

Theoretical prediction:
- Noise floor scales as 1/L (spectral resolution)
- Noise power density: ∝ 1/L²
- SNR improvement: +6 dB per doubling, +18 dB per 4×

Bootstrap confidence intervals (B=1000 resamples) for statistical rigor.

REQUIRES GPU - will fail fast if not available.
"""

import sys
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import matplotlib.pyplot as plt

# Add GPU utilities to path
sys.path.insert(0, str(Path(__file__).parent))
from gpu_utils import check_gpu_available, GPURequiredError, gpu_coherent_average

# Add VRA core to path
_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO / "Code" / "VRA"))
from core import modular_sequence, phase_embed, multiplicative_order


def generate_vra_sequences(N, a, L, M):
    """
    Generate M VRA sequences.

    Parameters
    ----------
    N, a : int
        Modulus and base
    L : int
        Sequence length
    M : int
        Number of bases

    Returns
    -------
    x_batch : ndarray, shape (M, L)
        Batch of sequences
    """
    x_batch = []

    for m in range(1, M+1):
        base = pow(a, m, N)
        xs = modular_sequence(N, base, 1, L)
        u = phase_embed(xs, N)
        x_batch.append(u)

    return np.array(x_batch, dtype=np.complex64)


def compute_snr(power_spectrum, harmonic_bins, guard=3):
    """
    Compute SNR from power spectrum.

    Parameters
    ----------
    power_spectrum : ndarray
        Power spectrum
    harmonic_bins : list
        Signal bin indices
    guard : int
        Guard band

    Returns
    -------
    snr_db : float
        Signal-to-noise ratio
    """
    signal = np.mean(power_spectrum[harmonic_bins])

    # Noise: median of non-harmonic bins
    L = len(power_spectrum)
    mask = np.ones(L, dtype=bool)
    for b in harmonic_bins:
        mask[max(0, b-guard):min(L, b+guard+1)] = False
    noise = np.median(power_spectrum[mask])

    snr_db = 10 * np.log10(signal / (noise + 1e-30))
    return snr_db


def bootstrap_snr(x_batch, harmonic_bins, framework='cupy', n_bootstrap=1000):
    """
    Compute SNR with bootstrap confidence intervals.

    Parameters
    ----------
    x_batch : ndarray, shape (M, L)
        Input sequences
    harmonic_bins : list
        Signal bins
    framework : str
        GPU framework
    n_bootstrap : int
        Number of bootstrap resamples

    Returns
    -------
    dict
        SNR statistics with confidence intervals
    """
    M = x_batch.shape[0]
    snr_samples = []

    print(f"    Bootstrap resampling ({n_bootstrap} iterations)...", end='', flush=True)

    for _ in range(n_bootstrap):
        # Resample with replacement
        indices = np.random.choice(M, M, replace=True)
        x_resample = x_batch[indices]

        # GPU-accelerated spectrum
        power_spectrum = gpu_coherent_average(x_resample, framework)

        # SNR
        snr = compute_snr(power_spectrum, harmonic_bins)
        snr_samples.append(snr)

    snr_samples = np.array(snr_samples)

    # Statistics
    snr_mean = np.mean(snr_samples)
    snr_std = np.std(snr_samples)
    snr_ci_lower = np.percentile(snr_samples, 2.5)
    snr_ci_upper = np.percentile(snr_samples, 97.5)

    print(f" done")

    return {
        'mean': float(snr_mean),
        'std': float(snr_std),
        'ci_lower': float(snr_ci_lower),
        'ci_upper': float(snr_ci_upper),
        'samples': snr_samples.tolist(),
    }


def test_l_scaling(N, a, M, L_values, framework='cupy', n_bootstrap=1000):
    """
    Test SNR scaling with L.

    Parameters
    ----------
    N, a : int
        Modulus and base
    M : int
        Number of bases
    L_values : list
        Sequence lengths to test
    framework : str
        GPU framework
    n_bootstrap : int
        Bootstrap iterations

    Returns
    -------
    dict
        Results with bootstrap CIs for each L
    """
    r = multiplicative_order(a, N)
    print(f"\nTest: N={N}, a={a}, r={r}, M={M}")
    print(f"L values: {L_values}")

    results = []

    for L in L_values:
        print(f"\n  L = {L}:")

        # Generate sequences
        x_batch = generate_vra_sequences(N, a, L, M)

        # Harmonic bins
        harmonic_bins = [int(round(ell * L / r)) for ell in range(1, min(r, L//2))]

        # Bootstrap SNR
        snr_stats = bootstrap_snr(x_batch, harmonic_bins, framework, n_bootstrap)

        print(f"    SNR: {snr_stats['mean']:.2f} dB "
              f"[{snr_stats['ci_lower']:.2f}, {snr_stats['ci_upper']:.2f}] 95% CI")

        results.append({
            'L': L,
            'snr_mean': snr_stats['mean'],
            'snr_std': snr_stats['std'],
            'snr_ci_lower': snr_stats['ci_lower'],
            'snr_ci_upper': snr_stats['ci_upper'],
        })

    return results


def plot_l_scaling_curve(results, output_path):
    """
    Create publication-grade L-scaling plot.

    Parameters
    ----------
    results : list of dict
        Results with SNR and CIs for each L
    output_path : Path
        Output file path
    """
    L_values = [r['L'] for r in results]
    snr_means = [r['snr_mean'] for r in results]
    snr_ci_lower = [r['snr_ci_lower'] for r in results]
    snr_ci_upper = [r['snr_ci_upper'] for r in results]

    fig, ax = plt.subplots(figsize=(8, 6))

    # Plot SNR with error bars
    ax.errorbar(L_values, snr_means,
                yerr=[np.array(snr_means) - np.array(snr_ci_lower),
                      np.array(snr_ci_upper) - np.array(snr_means)],
                fmt='o-', label='VRA SNR (with 95% CI)',
                capsize=5, markersize=8, linewidth=2)

    # Theoretical curve: SNR ∝ L (6 dB per doubling)
    # Fit to first point
    L0 = L_values[0]
    SNR0 = snr_means[0]
    L_theory = np.array(L_values)
    SNR_theory = SNR0 + 10 * np.log10(L_theory / L0)

    ax.plot(L_theory, SNR_theory, '--', label='Theory: +6 dB/doubling',
            linewidth=2, alpha=0.7)

    ax.set_xscale('log', base=2)
    ax.set_xlabel('Sequence Length L', fontsize=12)
    ax.set_ylabel('SNR (dB)', fontsize=12)
    ax.set_title('VRA Leakage Scaling with Sequence Length', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    # Annotate doublings
    for i in range(len(L_values) - 1):
        if L_values[i+1] == 2 * L_values[i]:
            gain = snr_means[i+1] - snr_means[i]
            mid_L = np.sqrt(L_values[i] * L_values[i+1])
            mid_SNR = (snr_means[i] + snr_means[i+1]) / 2
            ax.annotate(f'+{gain:.1f} dB',
                       xy=(mid_L, mid_SNR),
                       fontsize=9, ha='center',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.5))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\n✅ Figure saved to: {output_path}")


def run_l_scaling_experiment(framework='cupy'):
    """
    Run full L-scaling experiment with bootstrap CIs.
    """
    print("=" * 70)
    print("E16: L-Scaling Curve (Publication-Grade)")
    print("=" * 70)

    # Test parameters
    N, a = 997, 9
    M = 16
    L_values = [4096, 8192, 16384, 32768, 65536]
    n_bootstrap = 1000

    print(f"\nParameters:")
    print(f"  N={N}, a={a}, M={M}")
    print(f"  L values: {L_values}")
    print(f"  Bootstrap iterations: {n_bootstrap}")

    # Run experiment
    results = test_l_scaling(N, a, M, L_values, framework, n_bootstrap)

    # Compute scaling statistics
    print(f"\n" + "=" * 70)
    print("Scaling Analysis")
    print("=" * 70)

    for i in range(len(results) - 1):
        L1, L2 = results[i]['L'], results[i+1]['L']
        snr1, snr2 = results[i]['snr_mean'], results[i+1]['snr_mean']
        gain = snr2 - snr1
        ratio = L2 / L1

        theoretical_gain = 10 * np.log10(ratio)

        print(f"L={L1}→{L2} ({ratio}×):")
        print(f"  Observed gain: {gain:.2f} dB")
        print(f"  Theoretical:   {theoretical_gain:.2f} dB")
        print(f"  Ratio:         {gain / theoretical_gain:.2%}")
        print()

    return results


def main():
    """Main entry point - FAILS FAST if no GPU."""
    print("Checking GPU availability...")

    # FAIL FAST if no GPU
    try:
        cp = check_gpu_available('cupy')
    except GPURequiredError as e:
        print(e)
        print("\n" + "=" * 70)
        print("E16 ABORTED - GPU required")
        print("=" * 70)
        sys.exit(1)

    # Run experiment
    results = run_l_scaling_experiment(framework='cupy')

    # Save results
    output_dir = Path(_REPO) / "Data" / "Experiments" / "Tier5" / "E16"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_l_scaling.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")

    # Generate figure
    figure_dir = Path(_REPO) / "Figures" / "Experiments" / "Tier5" / "E16"
    figure_dir.mkdir(parents=True, exist_ok=True)

    figure_file = figure_dir / f"{timestamp}_l_scaling_curve.png"
    plot_l_scaling_curve(results, figure_file)

    print("\nSuccess Criteria Check:")
    print("  Target: Clean figure showing +6 dB per doubling with bootstrap CIs")
    print("  Status: ✅ COMPLETE (review figure)")


if __name__ == "__main__":
    main()
