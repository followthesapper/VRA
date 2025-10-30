#!/usr/bin/env python3
"""
Transition Regime Test: r=168
==============================

Test r=168 (TRANSITION regime) to map boundaries between LOW and HIGH SNR.

Measures:
- Concentration vs M
- √M fit quality
- Base variance
- Precision/recall

Author: Dylan Vaca
Date: October 2025
"""

import numpy as np
import json
import argparse
from pathlib import Path
from datetime import datetime
import sys

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
    n = len(signal)
    t = np.arange(n)
    if kind == "hann":
        w = 0.5 - 0.5 * np.cos(2 * np.pi * t / (n - 1))
    else:
        w = np.ones(n)
    return signal * w

def fft_complex(u, zp=1):
    """Zero-padded FFT"""
    if zp > 1:
        u_padded = np.zeros(len(u) * zp, dtype=np.complex128)
        u_padded[:len(u)] = u
        U = np.fft.fft(u_padded)
    else:
        U = np.fft.fft(u)
    return U

def compute_averaged_spectrum(N, bases, length, zp=8, window="hann"):
    """Compute averaged spectrum across M bases"""
    M = len(bases)
    U_sum = None

    for a in bases:
        xs = modular_sequence(N, a, 1, length)
        u = phase_embed(xs, N)
        u = apply_window(u, kind=window)
        U = fft_complex(u, zp=zp)

        if U_sum is None:
            U_sum = np.zeros_like(U, dtype=np.complex128)
        U_sum += U.astype(np.complex128)

    U_mean = U_sum / M
    mag2 = np.abs(U_mean) ** 2

    return mag2

def compute_concentration(mag2):
    """Compute concentration ratio"""
    mag2_norm = mag2 / (np.sum(mag2) + 1e-16)
    return float(np.max(mag2_norm))

def compute_entropy(mag2):
    """Compute spectral entropy"""
    mag2_norm = mag2 / (np.sum(mag2) + 1e-16)
    p = mag2_norm + 1e-16
    return float(-np.sum(p * np.log2(p)))

# =============================================================================
# Precision/Recall
# =============================================================================

def get_expected_bins(L, r):
    """Get expected peak bins"""
    expected = []
    for h in range(1, r + 1):
        k = round(h * L / r)
        expected.append(k % L)
    return sorted(set(expected))

def compute_precision_recall(mag2, expected_bins, radius):
    """Compute precision and recall"""
    L = len(mag2)

    # Find top peaks
    threshold = np.percentile(mag2, 99.9)
    peak_indices = np.where(mag2 > threshold)[0]

    # True positives
    TP = 0
    for k in peak_indices:
        for k_exp in expected_bins:
            dist = min(abs(k - k_exp), L - abs(k - k_exp))
            if dist <= radius:
                TP += 1
                break

    FP = len(peak_indices) - TP

    # For recall
    TP_recall = 0
    for k_exp in expected_bins:
        for k in peak_indices:
            dist = min(abs(k - k_exp), L - abs(k - k_exp))
            if dist <= radius:
                TP_recall += 1
                break

    FN = len(expected_bins) - TP_recall

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP_recall / (TP_recall + FN) if (TP_recall + FN) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'TP': TP,
        'FP': FP,
        'FN': FN,
        'num_peaks': len(peak_indices)
    }

# =============================================================================
# Base Variance Analysis
# =============================================================================

def compute_base_variance(N, bases, length, zp, window, num_trials=10):
    """Compute coefficient of variation across random base selections"""
    M = len(bases)
    concentrations = []

    for trial in range(num_trials):
        # Random selection
        selected = np.random.choice(bases, size=min(M, len(bases)), replace=False)

        mag2 = compute_averaged_spectrum(N, selected, length, zp, window)
        C = compute_concentration(mag2)
        concentrations.append(C)

    mean_C = np.mean(concentrations)
    std_C = np.std(concentrations)
    cv = std_C / mean_C if mean_C > 0 else 0

    return {
        'mean': float(mean_C),
        'std': float(std_C),
        'cv': float(cv),
        'concentrations': [float(c) for c in concentrations]
    }

# =============================================================================
# Fit Analysis
# =============================================================================

def fit_sqrt_m(M_values, concentrations):
    """Fit concentration vs √M"""
    sqrt_M = np.sqrt(M_values)

    A = np.vstack([np.ones(len(sqrt_M)), sqrt_M]).T
    result = np.linalg.lstsq(A, concentrations, rcond=None)
    intercept, slope = result[0]

    predictions = intercept + slope * sqrt_M
    ss_res = np.sum((concentrations - predictions) ** 2)
    ss_tot = np.sum((concentrations - np.mean(concentrations)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return {
        'intercept': float(intercept),
        'slope': float(slope),
        'r_squared': float(r_squared),
        'predictions': predictions.tolist()
    }

# =============================================================================
# Main Test
# =============================================================================

def run_transition_test(config_path, M_values, length, zp, window="hann"):
    """Run comprehensive transition regime test"""

    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)

    N = config['N']
    order = config['order']
    all_bases = config['bases']

    L = length * zp
    log_L = np.log2(L)

    # Validated radius
    R = int(0.5 * log_L)

    print(f"\n{'='*70}")
    print(f"TRANSITION REGIME TEST: r={order}")
    print(f"{'='*70}")
    print(f"\nConfiguration:")
    print(f"  N = {N}")
    print(f"  Order r = {order}")
    print(f"  r/N = {order/N:.3f}")
    print(f"  Available bases: {len(all_bases)}")
    print(f"  FFT length L = {L}")
    print(f"  log₂(L) = {log_L:.2f}")
    print(f"  Validated radius R = {R} bins")
    print()

    results = []
    expected_bins = get_expected_bins(L, order)

    for M in M_values:
        if M > len(all_bases):
            print(f"  Skipping M={M} (only {len(all_bases)} bases available)")
            continue

        print(f"  Testing M={M}...")

        # Use first M bases
        bases = all_bases[:M]

        # Compute spectrum
        mag2 = compute_averaged_spectrum(N, bases, length, zp, window)

        # Metrics
        concentration = compute_concentration(mag2)
        entropy = compute_entropy(mag2)

        # Precision/Recall
        pr = compute_precision_recall(mag2, expected_bins, R)

        # Base variance (only for M >= 4)
        if M >= 4 and M <= len(all_bases):
            base_var = compute_base_variance(N, all_bases, length, zp, window, num_trials=10)
        else:
            base_var = None

        result = {
            'M': M,
            'concentration': concentration,
            'entropy': entropy,
            'precision_recall': pr,
            'base_variance': base_var
        }

        results.append(result)

        print(f"    Concentration: {concentration:.4f}")
        print(f"    Precision: {pr['precision']:.3f}, Recall: {pr['recall']:.3f}")
        if base_var:
            print(f"    Base CV: {base_var['cv']:.4f}")

    # Fit √M
    M_arr = [r['M'] for r in results]
    C_arr = [r['concentration'] for r in results]

    fit_results = fit_sqrt_m(M_arr, C_arr)

    print(f"\n√M Fit:")
    print(f"  Slope: {fit_results['slope']:.6f}")
    print(f"  R²: {fit_results['r_squared']:.4f}")
    print(f"  Intercept: {fit_results['intercept']:.4f}")

    return {
        'config': {
            'N': N,
            'order': order,
            'r_over_N': order / N,
            'length': length,
            'zp': zp,
            'L': L,
            'window': window,
            'radius': R
        },
        'results': results,
        'sqrt_m_fit': fit_results
    }

# =============================================================================
# Plotting
# =============================================================================

def plot_transition_results(test_results, output_path):
    """Plot transition regime results"""
    if not HAS_MATPLOTLIB:
        return

    results = test_results['results']
    M_values = [r['M'] for r in results]
    concentrations = [r['concentration'] * 100 for r in results]
    fit = test_results['sqrt_m_fit']

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Plot 1: Concentration vs √M
    ax = axes[0]
    sqrt_M = np.sqrt(M_values)
    predictions = [p * 100 for p in fit['predictions']]

    ax.scatter(sqrt_M, concentrations, s=100, alpha=0.7, color='#2E86AB', label='Measured')
    ax.plot(sqrt_M, predictions, '--', linewidth=2, color='#C73E1D',
            label=f"√M fit (R²={fit['r_squared']:.3f})")

    ax.set_xlabel('√M', fontsize=12)
    ax.set_ylabel('Concentration (%)', fontsize=12)
    ax.set_title(f"r={test_results['config']['order']} Transition Regime", fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)

    # Plot 2: Precision/Recall vs M
    ax = axes[1]
    precisions = [r['precision_recall']['precision'] * 100 for r in results]
    recalls = [r['precision_recall']['recall'] * 100 for r in results]

    ax.plot(M_values, precisions, 'o-', linewidth=2, markersize=8,
            label='Precision', color='#2E86AB')
    ax.plot(M_values, recalls, 's--', linewidth=2, markersize=8,
            label='Recall', color='#C73E1D')

    ax.set_xlabel('M (Number of Bases)', fontsize=12)
    ax.set_ylabel('Precision / Recall (%)', fontsize=12)
    ax.set_title('Detection Metrics', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_ylim([0, 105])

    # Plot 3: Base Variance (CV) vs M
    ax = axes[2]
    M_with_cv = [r['M'] for r in results if r['base_variance'] is not None]
    cvs = [r['base_variance']['cv'] * 100 for r in results if r['base_variance'] is not None]

    if len(M_with_cv) > 0:
        ax.plot(M_with_cv, cvs, 'o-', linewidth=2, markersize=8, color='#06A77D')
        ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1,
                   alpha=0.5, label='CV = 1% (transition threshold)')

        ax.set_xlabel('M (Number of Bases)', fontsize=12)
        ax.set_ylabel('Coefficient of Variation (%)', fontsize=12)
        ax.set_title('Base Variance', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'No base variance data', ha='center', va='center',
                transform=ax.transAxes, fontsize=14)
        ax.axis('off')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\nSaved plot: {output_path}")

# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Transition Regime Test (r=168)")
    parser.add_argument('--config', type=str,
                       default='same_order_bases_1009_r168.json',
                       help='Path to base configuration JSON')
    parser.add_argument('--M_values', nargs='+', type=int,
                       default=[1, 4, 8, 16, 32, 48],
                       help='M values to test')
    parser.add_argument('--length', type=int, default=8192, help='Sequence length')
    parser.add_argument('--zp', type=int, default=8, help='Zero-padding factor')
    parser.add_argument('--window', type=str, default='hann', help='Window function')
    parser.add_argument('--output', type=str, default='../Results/', help='Output directory')

    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run test
    results = run_transition_test(
        args.config,
        args.M_values,
        args.length,
        args.zp,
        args.window
    )

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"{timestamp}_transition_r168.json"

    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved: {json_path}")

    # Plot
    plot_path = output_dir / f"{timestamp}_transition_r168.png"
    plot_transition_results(results, plot_path)

    print(f"\n{'='*70}")
    print("TRANSITION REGIME TEST COMPLETE")
    print(f"{'='*70}")

    return 0

if __name__ == '__main__':
    sys.exit(main())
