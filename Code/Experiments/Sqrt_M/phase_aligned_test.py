#!/usr/bin/env python3
"""
Phase-Aligned Small-Order Test
===============================

Test whether √M averaging works with phase-aligned base families
{a, a², a³, ...} even in HIGH SNR regime where it fails with random bases.

Goal: Explain r=8 "failure" from Phase 2 and prove phase alignment
      enables √M gain independent of SNR regime.

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
    print("Warning: matplotlib not available")

# =============================================================================
# Core Functions
# =============================================================================

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

def find_phase_aligned_bases(N, a, target_order, max_k=100):
    """
    Find powers of a that have the target order.

    Returns bases {a^k} where order(a^k) = target_order
    These bases have structured phase relationships.
    """
    phase_aligned = []

    for k in range(1, max_k):
        a_k = pow(a, k, N)
        if np.gcd(a_k, N) != 1:
            continue

        r_k = multiplicative_order(a_k, N)
        if r_k == target_order:
            phase_aligned.append(int(a_k))

    return phase_aligned

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
    """Apply Hann window"""
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

def compute_metrics(mag2):
    """Compute spectral metrics"""
    mag2_norm = mag2 / (np.sum(mag2) + 1e-16)

    # Concentration
    concentration = float(np.max(mag2_norm))

    # Entropy
    p = mag2_norm + 1e-16
    entropy = float(-np.sum(p * np.log2(p)))

    return {
        'concentration': concentration,
        'entropy': entropy
    }

def fit_sqrt_m(M_values, concentrations):
    """Fit concentration vs √M"""
    sqrt_M = np.sqrt(M_values)

    # Linear fit: C = intercept + slope * √M
    A = np.vstack([np.ones(len(sqrt_M)), sqrt_M]).T
    result = np.linalg.lstsq(A, concentrations, rcond=None)
    intercept, slope = result[0]

    # Compute R²
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
# Main Experiment
# =============================================================================

def run_phase_aligned_comparison(N, a_base, target_order, M_values, length=2048, zp=8):
    """
    Compare phase-aligned vs random same-order bases.

    Returns results for both sets.
    """
    print(f"\nFinding phase-aligned bases for N={N}, a={a_base}, target_order={target_order}...")

    # Find phase-aligned bases (powers of a_base with same order)
    phase_aligned_bases = find_phase_aligned_bases(N, a_base, target_order, max_k=200)
    print(f"  Found {len(phase_aligned_bases)} phase-aligned bases: {phase_aligned_bases[:10]}...")

    # Load random same-order bases from config
    random_config_path = Path(f"../../../../Phase2_Breakthrough_Testing/Code/same_order_bases_255_r{target_order}.json")
    if random_config_path.exists():
        with open(random_config_path, 'r') as f:
            random_config = json.load(f)
        random_bases = random_config['bases']
        print(f"  Loaded {len(random_bases)} random same-order bases from config")
    else:
        print(f"  Warning: Random config not found, using phase-aligned bases as baseline")
        random_bases = phase_aligned_bases

    # Test both sets
    results = {
        'phase_aligned': {'M_values': [], 'concentrations': [], 'entropies': []},
        'random': {'M_values': [], 'concentrations': [], 'entropies': []}
    }

    print(f"\nTesting phase-aligned bases:")
    for M in M_values:
        if M > len(phase_aligned_bases):
            print(f"  Skipping M={M} (only {len(phase_aligned_bases)} phase-aligned bases)")
            continue

        bases = phase_aligned_bases[:M]
        mag2 = compute_averaged_spectrum(N, bases, length, zp, window="hann")
        metrics = compute_metrics(mag2)

        results['phase_aligned']['M_values'].append(M)
        results['phase_aligned']['concentrations'].append(metrics['concentration'])
        results['phase_aligned']['entropies'].append(metrics['entropy'])

        print(f"  M={M:2d}: Conc={metrics['concentration']:.4f}, Entropy={metrics['entropy']:.2f}")

    print(f"\nTesting random same-order bases:")
    for M in M_values:
        if M > len(random_bases):
            print(f"  Skipping M={M} (only {len(random_bases)} random bases)")
            continue

        bases = random_bases[:M]
        mag2 = compute_averaged_spectrum(N, bases, length, zp, window="hann")
        metrics = compute_metrics(mag2)

        results['random']['M_values'].append(M)
        results['random']['concentrations'].append(metrics['concentration'])
        results['random']['entropies'].append(metrics['entropy'])

        print(f"  M={M:2d}: Conc={metrics['concentration']:.4f}, Entropy={metrics['entropy']:.2f}")

    # Fit √M for both sets
    if len(results['phase_aligned']['M_values']) > 0:
        fit_aligned = fit_sqrt_m(
            results['phase_aligned']['M_values'],
            results['phase_aligned']['concentrations']
        )
        results['phase_aligned']['fit'] = fit_aligned
        print(f"\nPhase-aligned √M fit:")
        print(f"  R² = {fit_aligned['r_squared']:.4f}")
        print(f"  Slope = {fit_aligned['slope']:.6f}")

    if len(results['random']['M_values']) > 0:
        fit_random = fit_sqrt_m(
            results['random']['M_values'],
            results['random']['concentrations']
        )
        results['random']['fit'] = fit_random
        print(f"\nRandom same-order √M fit:")
        print(f"  R² = {fit_random['r_squared']:.4f}")
        print(f"  Slope = {fit_random['slope']:.6f}")

    return {
        'config': {
            'N': N,
            'a_base': a_base,
            'target_order': target_order,
            'length': length,
            'zp': zp
        },
        'phase_aligned_bases': phase_aligned_bases,
        'random_bases': random_bases[:len(phase_aligned_bases)],  # Match length
        'results': results
    }

# =============================================================================
# Plotting
# =============================================================================

def plot_comparison(test_results, output_path):
    """Plot phase-aligned vs random comparison"""
    if not HAS_MATPLOTLIB:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    results = test_results['results']

    # Plot 1: Concentration vs √M
    ax = axes[0]

    # Phase-aligned
    M_aligned = results['phase_aligned']['M_values']
    C_aligned = [c * 100 for c in results['phase_aligned']['concentrations']]
    sqrt_M_aligned = np.sqrt(M_aligned)

    ax.scatter(sqrt_M_aligned, C_aligned, label='Phase-aligned bases',
               color='#2E86AB', marker='o', s=100, alpha=0.7)

    if 'fit' in results['phase_aligned']:
        fit = results['phase_aligned']['fit']
        pred_aligned = [p * 100 for p in fit['predictions']]
        ax.plot(sqrt_M_aligned, pred_aligned, '--', color='#2E86AB', linewidth=2,
                label=f"Phase-aligned fit (R²={fit['r_squared']:.3f})")

    # Random
    M_random = results['random']['M_values']
    C_random = [c * 100 for c in results['random']['concentrations']]
    sqrt_M_random = np.sqrt(M_random)

    ax.scatter(sqrt_M_random, C_random, label='Random same-order bases',
               color='#C73E1D', marker='s', s=100, alpha=0.7)

    if 'fit' in results['random']:
        fit = results['random']['fit']
        pred_random = [p * 100 for p in fit['predictions']]
        ax.plot(sqrt_M_random, pred_random, '--', color='#C73E1D', linewidth=2,
                label=f"Random fit (R²={fit['r_squared']:.3f})")

    ax.set_xlabel('√M', fontsize=12)
    ax.set_ylabel('Concentration (%)', fontsize=12)
    ax.set_title('√M Hypothesis: Phase-Aligned vs Random', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)

    # Plot 2: Bar chart of R²
    ax = axes[1]

    r2_aligned = results['phase_aligned'].get('fit', {}).get('r_squared', 0)
    r2_random = results['random'].get('fit', {}).get('r_squared', 0)

    ax.bar(['Phase-Aligned', 'Random'], [r2_aligned, r2_random],
           color=['#2E86AB', '#C73E1D'], alpha=0.7)
    ax.set_ylabel('R² (√M Fit Quality)', fontsize=12)
    ax.set_title('√M Fit Quality Comparison', fontsize=14, fontweight='bold')
    ax.set_ylim([0, 1.0])
    ax.axhline(y=0.9, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Excellent fit')
    ax.grid(axis='y', alpha=0.3)
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\nSaved plot: {output_path}")

# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Phase-Aligned Small-Order Test")
    parser.add_argument('--N', type=int, default=255, help='Modulus')
    parser.add_argument('--a', type=int, default=7, help='Base')
    parser.add_argument('--order', type=int, default=16, help='Target order')
    parser.add_argument('--M_values', nargs='+', type=int, default=[1, 2, 4, 8, 16],
                       help='M values to test')
    parser.add_argument('--length', type=int, default=2048, help='Sequence length')
    parser.add_argument('--zp', type=int, default=8, help='Zero-padding factor')
    parser.add_argument('--output', type=str, default='../Results/', help='Output directory')

    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("PHASE-ALIGNED SMALL-ORDER TEST")
    print("="*80)
    print("\nObjective: Test whether {a, a², a³, ...} recovers √M gain in HIGH SNR")

    # Run comparison
    results = run_phase_aligned_comparison(
        args.N,
        args.a,
        args.order,
        args.M_values,
        args.length,
        args.zp
    )

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"{timestamp}_phase_aligned_r{args.order}.json"

    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved: {json_path}")

    # Plot comparison
    plot_path = output_dir / f"{timestamp}_phase_aligned_comparison_r{args.order}.png"
    plot_comparison(results, plot_path)

    print("\n" + "="*80)
    print("PHASE-ALIGNED TEST COMPLETE")
    print("="*80)

    return 0

if __name__ == '__main__':
    sys.exit(main())
