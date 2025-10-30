#!/usr/bin/env python3
"""
FP#2 Robustness Sweep: Large FFT Lengths
=========================================

Test R = 0.5·log₂(L) precision rule at:
- L = 131,072 (2^17, log₂L = 17, R = 8.5)
- L = 262,144 (2^18, log₂L = 18, R = 9.0)

Validate across:
- Multiple regimes (HIGH, TRANSITION, LOW SNR)
- Multiple windows (Hann, Hamming, Blackman)
- Multiple M values

Success criteria:
- 100% precision at validated radius
- Consistent across all regimes and windows
- No L-dependence beyond the log₂(L) factor

Author: Dylan Vaca
Date: October 2025
"""

import numpy as np
import json
from pathlib import Path
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =============================================================================
# Core VRA Functions
# =============================================================================

def modular_sequence(N, a, x0, length):
    """Generate modular iteration sequence"""
    xs = np.zeros(length, dtype=np.int64)
    xs[0] = x0
    for i in range(1, length):
        xs[i] = (a * xs[i-1]) % N
    return xs

def phase_embed(xs, N):
    """Phase embedding"""
    phases = 2.0 * np.pi * xs / N
    return np.exp(1j * phases)

def apply_window(signal, kind="hann"):
    """Apply window function"""
    length = len(signal)
    if kind == "hann":
        window = np.hanning(length)
    elif kind == "hamming":
        window = np.hamming(length)
    elif kind == "blackman":
        window = np.blackman(length)
    else:
        window = np.ones(length)
    return signal * window

def compute_spectrum(N, a, x0, length, zp, window="hann"):
    """Compute single-base spectrum"""
    xs = modular_sequence(N, a, x0, length)
    us = phase_embed(xs, N)
    us_windowed = apply_window(us, window)

    # Zero-pad
    L = length * zp
    us_padded = np.zeros(L, dtype=np.complex128)
    us_padded[:length] = us_windowed

    # FFT
    spectrum = np.fft.fft(us_padded)
    mag2 = np.abs(spectrum) ** 2

    return mag2

def compute_averaged_spectrum(N, bases, x0, length, zp, window="hann"):
    """Compute M-base COHERENTLY averaged power spectrum.

    CRITICAL: This performs coherent averaging by summing complex FFTs
    before squaring, NOT by averaging power spectra. This preserves
    phase relationships and enables √M SNR scaling.

    Coherent: |Σ U_m / M|² → SNR scales as √M
    Incoherent: Σ|U_m|²/M → No SNR gain
    """
    M = len(bases)
    L = length * zp
    U_sum = None

    for a in bases:
        # Generate sequence
        xs = modular_sequence(N, a, x0, length)
        us = phase_embed(xs, N)
        us_windowed = apply_window(us, window)

        # Zero-pad
        us_padded = np.zeros(L, dtype=np.complex128)
        us_padded[:length] = us_windowed

        # FFT (keep complex!)
        U = np.fft.fft(us_padded)

        # Sum complex FFTs
        if U_sum is None:
            U_sum = np.zeros_like(U, dtype=np.complex128)
        U_sum += U

    # Average THEN square (coherent)
    U_mean = U_sum / M
    mag2_avg = np.abs(U_mean) ** 2

    return mag2_avg

def compute_concentration(mag2):
    """Compute concentration ratio"""
    C = np.max(mag2) / np.sum(mag2)
    return C

def compute_precision_recall(mag2, expected_bins, radius):
    """Compute precision and recall"""
    L = len(mag2)

    # Use 99.9th percentile threshold (top 0.1% of bins)
    threshold = np.percentile(mag2, 99.9)

    # Find peaks above threshold
    peak_indices = np.where(mag2 > threshold)[0]

    # Expected peak positions (harmonics of r)
    expected_set = set(expected_bins)

    # Check which detected peaks are true positives
    TP = 0
    FP = 0
    for idx in peak_indices:
        # Check if any expected peak is within radius
        is_TP = any(abs(idx - exp_idx) <= radius or
                   abs(idx - (L - exp_idx)) <= radius or
                   abs((L - idx) - exp_idx) <= radius
                   for exp_idx in expected_set)
        if is_TP:
            TP += 1
        else:
            FP += 1

    FN = len(expected_set) - TP

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'TP': TP,
        'FP': FP,
        'FN': FN,
        'num_peaks': len(peak_indices)
    }

def multiplicative_order(a, N, max_iter=10000):
    """Compute multiplicative order of a mod N"""
    if np.gcd(a, N) != 1:
        return None
    x = a
    for r in range(1, min(max_iter, N)):
        if x == 1:
            return r
        x = (x * a) % N
    return None

# =============================================================================
# Robustness Test
# =============================================================================

def test_regime_at_L(regime_config, length_config, M_values):
    """Test a single regime at given FFT length configuration

    Parameters:
    - regime_config: dict with N, order, bases, regime_name
    - length_config: dict with length, zp, L, radius
    - M_values: list of M values to test

    Returns:
    - results dict
    """
    N = regime_config['N']
    order = regime_config['order']
    bases = regime_config['bases']
    regime = regime_config['regime']

    length = length_config['length']
    zp = length_config['zp']
    L = length_config['L']
    radius = length_config['radius']

    x0 = 1  # Starting seed

    # Test multiple windows
    windows = ['hann', 'hamming', 'blackman']
    window_results = {}

    for window in windows:
        print(f"      Window: {window}")

        M_results = []

        for M in M_values:
            if M > len(bases):
                continue

            # Select M bases
            selected_bases = bases[:M]

            # Compute averaged spectrum
            mag2 = compute_averaged_spectrum(N, selected_bases, x0,
                                            length, zp, window)

            # Compute metrics
            concentration = compute_concentration(mag2)

            # Expected harmonic bins
            expected_bins = [(k * L // order) % L for k in range(order)]

            # Precision/recall
            pr = compute_precision_recall(mag2, expected_bins, radius)

            M_results.append({
                'M': M,
                'concentration': float(concentration),
                'precision': pr['precision'],
                'recall': pr['recall'],
                'TP': pr['TP'],
                'FP': pr['FP'],
                'FN': pr['FN'],
                'num_peaks': pr['num_peaks']
            })

            print(f"        M={M:2d}: C={concentration:.6f}, "
                  f"P={pr['precision']:.3f}, R={pr['recall']:.3f}, "
                  f"FP={pr['FP']}")

        window_results[window] = M_results

    return window_results

def run_robustness_sweep():
    """Run complete robustness sweep across L values"""

    print("="*70)
    print("FP#2 ROBUSTNESS SWEEP: LARGE FFT LENGTHS")
    print("="*70)
    print()

    # Define regimes to test
    regimes = []
    N = 1009

    # HIGH SNR: r=8 phase-aligned
    # Find a generator with order 8
    r8_generator = None
    for a in range(2, N):
        if np.gcd(a, N) == 1 and multiplicative_order(a, N) == 8:
            r8_generator = a
            break

    if r8_generator:
        # Generate phase-aligned bases: {a^k : gcd(k,8)=1} = {a^1, a^3, a^5, a^7}
        r8_bases = [pow(r8_generator, k, N) for k in [1, 3, 5, 7]]
        regimes.append({
            'name': 'HIGH_SNR_r8',
            'N': N,
            'order': 8,
            'bases': r8_bases,
            'regime': 'HIGH_SNR',
            'r_over_N': 8/N
        })
        print(f"Found HIGH SNR bases (r=8): generator={r8_generator}, bases={r8_bases}")

    # TRANSITION: r=168
    # Find bases with order 168
    r168_bases = []
    for a in range(2, N):
        if len(r168_bases) >= 20:
            break
        if np.gcd(a, N) == 1 and multiplicative_order(a, N) == 168:
            r168_bases.append(a)

    if len(r168_bases) >= 4:
        regimes.append({
            'name': 'TRANSITION_r168',
            'N': N,
            'order': 168,
            'bases': r168_bases[:20],
            'regime': 'TRANSITION',
            'r_over_N': 168/N
        })
        print(f"Found TRANSITION bases (r=168): {len(r168_bases)} bases")

    # LOW SNR: r=504
    # Find bases with order 504
    r504_bases = []
    for a in range(2, N):
        if len(r504_bases) >= 20:
            break
        if np.gcd(a, N) == 1 and multiplicative_order(a, N) == 504:
            r504_bases.append(a)

    if len(r504_bases) >= 4:
        regimes.append({
            'name': 'LOW_SNR_r504',
            'N': N,
            'order': 504,
            'bases': r504_bases[:20],
            'regime': 'LOW_SNR',
            'r_over_N': 504/N
        })
        print(f"Found LOW SNR bases (r=504): {len(r504_bases)} bases")

    print()

    # Define FFT length configurations
    length_configs = [
        {
            'name': 'L65k',
            'length': 8192,
            'zp': 8,
            'L': 65536,
            'log2_L': 16,
            'radius': int(0.5 * 16)  # R = 8
        },
        {
            'name': 'L131k',
            'length': 16384,
            'zp': 8,
            'L': 131072,
            'log2_L': 17,
            'radius': int(0.5 * 17)  # R = 8.5 → 8
        },
        {
            'name': 'L262k',
            'length': 32768,
            'zp': 8,
            'L': 262144,
            'log2_L': 18,
            'radius': int(0.5 * 18)  # R = 9.0 → 9
        }
    ]

    # M values to test
    M_values = [1, 4, 8, 16]

    # Run tests
    all_results = {}

    for L_config in length_configs:
        print(f"\n{'='*70}")
        print(f"Testing L = {L_config['L']:,} (log₂L = {L_config['log2_L']}, R = {L_config['radius']})")
        print(f"{'='*70}\n")

        L_results = {}

        for regime_config in regimes:
            print(f"  Regime: {regime_config['name']} "
                  f"(r={regime_config['order']}, r/N={regime_config['r_over_N']:.3f})")

            window_results = test_regime_at_L(regime_config, L_config, M_values)

            L_results[regime_config['name']] = {
                'regime_config': {
                    'N': regime_config['N'],
                    'order': regime_config['order'],
                    'r_over_N': regime_config['r_over_N'],
                    'regime': regime_config['regime']
                },
                'window_results': window_results
            }
            print()

        all_results[L_config['name']] = {
            'L_config': L_config,
            'regime_results': L_results
        }

    # Analyze results
    print("\n" + "="*70)
    print("ROBUSTNESS ANALYSIS")
    print("="*70)

    # Check if precision = 1.0 at all L, all regimes, all windows
    precision_violations = []

    for L_name, L_data in all_results.items():
        L = L_data['L_config']['L']
        radius = L_data['L_config']['radius']

        for regime_name, regime_data in L_data['regime_results'].items():
            for window, M_results in regime_data['window_results'].items():
                for M_result in M_results:
                    if M_result['precision'] < 1.0:
                        precision_violations.append({
                            'L': L,
                            'radius': radius,
                            'regime': regime_name,
                            'window': window,
                            'M': M_result['M'],
                            'precision': M_result['precision'],
                            'FP': M_result['FP']
                        })

    if len(precision_violations) == 0:
        print("\n✓ SUCCESS: 100% precision at all L values!")
        print("  R = 0.5·log₂(L) rule is ROBUST")
    else:
        print(f"\n✗ VIOLATIONS: {len(precision_violations)} cases with precision < 1.0")
        for v in precision_violations:
            print(f"  L={v['L']}, R={v['radius']}, {v['regime']}, "
                  f"{v['window']}, M={v['M']}: P={v['precision']:.3f} (FP={v['FP']})")

    # Save results
    output_dir = Path(__file__).parent.parent.parent / 'Data' / 'robustness_sweep'
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_path = output_dir / f'{timestamp}_robustness_sweep.json'

    output_data = {
        'timestamp': timestamp,
        'test_configs': {
            'length_configs': length_configs,
            'M_values': M_values,
            'windows': ['hann', 'hamming', 'blackman']
        },
        'results': all_results,
        'analysis': {
            'total_tests': sum(len(L_data['regime_results']) * 3 * len(M_values)
                              for L_data in all_results.values()),
            'precision_violations': precision_violations,
            'success': len(precision_violations) == 0
        }
    }

    with open(results_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved: {results_path}")

    # Create visualization if matplotlib available
    if HAS_MATPLOTLIB:
        figures_dir = Path(__file__).parent.parent.parent / 'Figures' / 'FP2_Leakage'
        figures_dir.mkdir(parents=True, exist_ok=True)
        create_robustness_plot(all_results, figures_dir, timestamp)

    print("\n" + "="*70)
    print("ROBUSTNESS SWEEP COMPLETE")
    print("="*70)

    return 0

def create_robustness_plot(results, output_dir, timestamp):
    """Create visualization of robustness sweep results"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('FP#2 Robustness Sweep: R = 0.5·log₂(L) Validation',
                 fontsize=14, fontweight='bold')

    L_names = list(results.keys())
    L_values = [results[L_name]['L_config']['L'] for L_name in L_names]
    radii = [results[L_name]['L_config']['radius'] for L_name in L_names]

    # Panel A: Precision vs L (should all be 1.0)
    ax = axes[0, 0]

    for regime_idx, regime_name in enumerate(['HIGH_SNR_r8', 'TRANSITION_r168', 'LOW_SNR_r504']):
        precisions = []
        for L_name in L_names:
            if regime_name in results[L_name]['regime_results']:
                # Average precision across windows and M values
                window_results = results[L_name]['regime_results'][regime_name]['window_results']
                all_precisions = []
                for window_data in window_results.values():
                    all_precisions.extend([m['precision'] for m in window_data])
                avg_precision = np.mean(all_precisions)
                precisions.append(avg_precision)
            else:
                precisions.append(None)

        # Plot
        valid_L = [L_values[i] for i in range(len(L_values)) if precisions[i] is not None]
        valid_P = [precisions[i] for i in range(len(precisions)) if precisions[i] is not None]

        if len(valid_L) > 0:
            ax.plot(valid_L, valid_P, 'o-', linewidth=2, markersize=8,
                   label=regime_name, alpha=0.7)

    ax.axhline(1.0, color='green', linestyle='--', alpha=0.5, linewidth=2,
              label='Target (100%)')
    ax.set_xlabel('FFT Length L', fontsize=11, fontweight='bold')
    ax.set_ylabel('Precision', fontsize=11, fontweight='bold')
    ax.set_title('Panel A: Precision vs L', fontsize=11, fontweight='bold')
    ax.set_xscale('log')
    ax.set_ylim(0.95, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=9)

    # Panel B: Radius vs log₂(L)
    ax = axes[0, 1]

    log2_L = [np.log2(L) for L in L_values]
    expected_radii = [0.5 * log2 for log2 in log2_L]

    ax.plot(log2_L, radii, 'bo-', linewidth=2, markersize=10,
           label='Tested R', alpha=0.7)
    ax.plot(log2_L, expected_radii, 'r--', linewidth=2,
           label='R = 0.5·log₂(L)', alpha=0.7)

    ax.set_xlabel('log₂(L)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Validated Radius R', fontsize=11, fontweight='bold')
    ax.set_title('Panel B: Radius Rule', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left', fontsize=10)

    # Panel C: FP count heatmap
    ax = axes[1, 0]

    # Collect FP counts
    fp_matrix = np.zeros((len(L_names), 3))  # 3 regimes
    regime_labels = ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']

    for i, L_name in enumerate(L_names):
        for j, regime_name in enumerate(['HIGH_SNR_r8', 'TRANSITION_r168', 'LOW_SNR_r504']):
            if regime_name in results[L_name]['regime_results']:
                window_results = results[L_name]['regime_results'][regime_name]['window_results']
                total_fp = sum(m['FP'] for window_data in window_results.values()
                              for m in window_data)
                fp_matrix[i, j] = total_fp

    im = ax.imshow(fp_matrix.T, cmap='YlOrRd', aspect='auto', vmin=0, vmax=1)

    ax.set_xticks(range(len(L_names)))
    ax.set_xticklabels([f"L={L//1000}k" for L in L_values])
    ax.set_yticks(range(3))
    ax.set_yticklabels(regime_labels)
    ax.set_title('Panel C: False Positives', fontsize=11, fontweight='bold')

    # Add text annotations
    for i in range(len(L_names)):
        for j in range(3):
            text = ax.text(i, j, int(fp_matrix[i, j]),
                          ha="center", va="center", color="black", fontsize=10)

    plt.colorbar(im, ax=ax, label='FP Count')

    # Panel D: Recall vs regime (expected to vary with r)
    ax = axes[1, 1]

    for L_idx, L_name in enumerate(L_names):
        recalls = []
        regime_names_short = []

        for regime_name in ['HIGH_SNR_r8', 'TRANSITION_r168', 'LOW_SNR_r504']:
            if regime_name in results[L_name]['regime_results']:
                window_results = results[L_name]['regime_results'][regime_name]['window_results']
                all_recalls = []
                for window_data in window_results.values():
                    # Use highest M value for recall
                    if len(window_data) > 0:
                        all_recalls.append(window_data[-1]['recall'])
                if len(all_recalls) > 0:
                    recalls.append(np.mean(all_recalls))
                    regime_names_short.append(regime_name.split('_')[0])

        x_pos = np.arange(len(regime_names_short)) + L_idx * 0.25
        ax.bar(x_pos, recalls, width=0.2, label=f"L={L_values[L_idx]//1000}k", alpha=0.7)

    ax.set_xlabel('Regime', fontsize=11, fontweight='bold')
    ax.set_ylabel('Recall (at max M)', fontsize=11, fontweight='bold')
    ax.set_title('Panel D: Recall vs Regime', fontsize=11, fontweight='bold')
    ax.set_xticks(np.arange(3) + 0.25)
    ax.set_xticklabels(['HIGH', 'TRANS', 'LOW'])
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(loc='upper right', fontsize=9)

    plt.tight_layout()

    plot_path = output_dir / f'{timestamp}_robustness_sweep.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved: {plot_path}")
    plt.close()

# =============================================================================
# Main
# =============================================================================

def main():
    return run_robustness_sweep()

if __name__ == '__main__':
    import sys
    sys.exit(main())
