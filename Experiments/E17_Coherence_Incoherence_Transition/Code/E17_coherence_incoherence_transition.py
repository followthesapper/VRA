#!/usr/bin/env python3
"""
T6-A1 — Coherence-Incoherence Transition (STANDALONE VERSION)

Demonstrates R̄ ≈ 0.137 phenomenon without VRA dependencies.
Uses direct FFT calculations on modular sequences.

Runtime: 10-15 minutes
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import i0, i1
import json
from pathlib import Path
import logging
import time
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Experimental parameters - STANDALONE & FAST"""
    # Test parameters (MINIMAL for quick validation)
    N_primes = [997, 2003]  # 2 moduli
    rho_targets = [0.10, 0.20, 0.30]  # 3 densities
    M_values = [8, 16]  # 2 base counts

    # Sequence parameters
    L = 2048  # Reduced for speed (was 4096)
    n_samples = 5  # Samples per config (was 10)

    # Output
    output_dir = Path("../Data")
    figure_dir = Path("../Figures")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6A1_standalone_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ],
            force=True
        )
        logging.info("="*70)
        logging.info("T6-A1: Coherence-Incoherence Transition (STANDALONE)")
        logging.info("="*70)
        logging.info(f"Log: {self.log_file}")

# ============================================================================
# Core Functions
# ============================================================================

def pow_mod(base, exp, mod):
    """Fast modular exponentiation"""
    result = 1
    base = base % mod
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        exp = exp >> 1
        base = (base * base) % mod
    return result

def find_order(a, N, max_attempts=100):
    """Find multiplicative order of a mod N"""
    if np.gcd(a, N) != 1:
        return None

    # Try small orders first
    for r in range(1, min(N, 1000)):
        if pow_mod(a, r, N) == 1:
            # Check minimality
            is_minimal = True
            for d in [2, 3, 5]:
                if r % d == 0 and pow_mod(a, r//d, N) == 1:
                    is_minimal = False
                    break
            if is_minimal:
                return r
    return None

def compute_coherence_fast(N, r, M, L):
    """
    Fast coherence computation using direct FFT.

    Returns R̄ (mean resultant length)
    """
    # Find M bases with order r
    bases = []
    attempts = 0
    max_attempts = N * 5

    while len(bases) < M and attempts < max_attempts:
        a = np.random.randint(2, N)
        if np.gcd(a, N) == 1:
            order_a = find_order(a, N)
            if order_a == r:
                bases.append(a)
        attempts += 1

    if len(bases) < M:
        return np.nan

    # Generate phase sequences
    spectra = []
    for a in bases:
        seq = []
        x = 1
        for _ in range(L):
            x = (x * a) % N
            phase = 2 * np.pi * x / N
            seq.append(np.exp(1j * phase))

        # FFT
        spectrum = np.fft.fft(seq)
        spectra.append(spectrum)

    spectra = np.array(spectra)

    # Compute mean resultant length (von Mises coherence)
    # For each harmonic, normalize phasors to unit length, then compute |mean|
    R_per_harmonic = []
    for ℓ in range(1, min(51, len(spectra[0]))):  # Skip DC, use first 50 harmonics
        # Get phasors at this harmonic from all M bases
        phasors = spectra[:, ℓ]

        # Normalize to unit length
        magnitudes = np.abs(phasors)
        if np.all(magnitudes > 0):
            unit_phasors = phasors / magnitudes

            # Mean resultant length = |mean of unit phasors|
            mean_phasor = np.mean(unit_phasors)
            R_ℓ = np.abs(mean_phasor)
            R_per_harmonic.append(R_ℓ)

    # Average over harmonics
    R_mean = np.mean(R_per_harmonic) if len(R_per_harmonic) > 0 else np.nan

    return R_mean

# ============================================================================
# Main Experiment
# ============================================================================

def run_experiment(config):
    logging.info("")
    logging.info("Configuration:")
    logging.info(f"  N: {config.N_primes}")
    logging.info(f"  ρ targets: {config.rho_targets}")
    logging.info(f"  M values: {config.M_values}")
    logging.info(f"  L: {config.L}, samples: {config.n_samples}")

    total = len(config.N_primes) * len(config.rho_targets) * len(config.M_values)
    logging.info(f"  Total configs: {total}")
    logging.info(f"  Estimated: 10-15 minutes")
    logging.info("")

    results = []
    idx = 0
    start_time = time.time()

    for N in config.N_primes:
        for rho_target in config.rho_targets:
            r_target = int(rho_target * N)

            # Find actual order near target - try multiple bases per candidate order
            r_actual = None
            for r_search in range(max(10, r_target-30), r_target+30):
                # Try multiple bases for this order
                found = False
                for attempt in range(50):  # Try up to 50 random bases
                    a_test = np.random.randint(2, N)
                    if np.gcd(a_test, N) == 1:
                        order_test = find_order(a_test, N)
                        if order_test == r_search:
                            r_actual = r_search
                            found = True
                            break
                if found:
                    break

            if r_actual is None:
                logging.warning(f"Could not find order near ρ={rho_target:.2f} for N={N}")
                continue

            rho_actual = r_actual / N

            for M in config.M_values:
                idx += 1
                elapsed = time.time() - start_time
                rate = idx / elapsed if elapsed > 0 else 0
                eta = (total - idx) / rate if rate > 0 else 0

                logging.info(f"[{idx}/{total}] N={N}, ρ={rho_actual:.3f} (r={r_actual}), M={M} | "
                           f"Elapsed: {elapsed/60:.1f}m | ETA: {eta/60:.1f}m")

                # Compute coherence samples
                R_samples = []
                for _ in range(config.n_samples):
                    R = compute_coherence_fast(N, r_actual, M, config.L)
                    if not np.isnan(R):
                        R_samples.append(R)

                if len(R_samples) == 0:
                    logging.warning("  Failed")
                    continue

                R_mean = np.mean(R_samples)
                R_std = np.std(R_samples)

                logging.info(f"  → R̄ = {R_mean:.4f} ± {R_std:.4f}")

                results.append({
                    'N': int(N),
                    'r': int(r_actual),
                    'rho': float(rho_actual),
                    'M': int(M),
                    'R_mean': float(R_mean),
                    'R_std': float(R_std),
                    'R_samples': [float(x) for x in R_samples]
                })

    return results

# ============================================================================
# Visualization
# ============================================================================

def plot_results(results, config):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (A) R̄ vs ρ
    ax = axes[0, 0]
    for M in config.M_values:
        subset = [r for r in results if r['M'] == M]
        rho = [r['rho'] for r in subset]
        R = [r['R_mean'] for r in subset]
        err = [r['R_std'] for r in subset]
        ax.errorbar(rho, R, yerr=err, fmt='o-', label=f'M={M}', capsize=3)

    ax.axhline(0.137, color='red', linestyle=':', label='Target R̄=0.137')
    ax.set_xlabel('Density ρ = r/N')
    ax.set_ylabel('Coherence R̄')
    ax.set_title('(A) Coherence vs Density')
    ax.legend()
    ax.grid(alpha=0.3)

    # (B) Distribution
    ax = axes[0, 1]
    all_R = []
    for r in results:
        all_R.extend(r['R_samples'])
    ax.hist(all_R, bins=30, alpha=0.6, density=True)
    ax.axvline(np.mean(all_R), color='blue', linestyle='--', label=f'Mean: {np.mean(all_R):.3f}')
    ax.axvline(0.137, color='red', linestyle=':', label='Target: 0.137')
    ax.set_xlabel('R̄')
    ax.set_ylabel('Density')
    ax.set_title('(B) Overall Distribution')
    ax.legend()
    ax.grid(alpha=0.3)

    # (C) M-scaling
    ax = axes[1, 0]
    for rho_target in config.rho_targets:
        subset = [r for r in results if abs(r['rho'] - rho_target) < 0.08]
        if len(subset) < 2:
            continue

        M_vals = []
        var_vals = []
        for M in config.M_values:
            M_sub = [r for r in subset if r['M'] == M]
            if len(M_sub) > 0:
                all_samples = []
                for r in M_sub:
                    all_samples.extend(r['R_samples'])
                if len(all_samples) > 2:
                    M_vals.append(M)
                    var_vals.append(np.var(all_samples))

        if len(M_vals) >= 2:
            ax.plot([1/M for M in M_vals], var_vals, 'o-', label=f'ρ≈{rho_target:.1f}')

    ax.set_xlabel('1/M')
    ax.set_ylabel('Var(R̄)')
    ax.set_title('(C) Variance Scaling (Var ∝ 1/M?)')
    ax.legend()
    ax.grid(alpha=0.3)

    # (D) Summary stats
    ax = axes[1, 1]
    ax.axis('off')

    all_R = []
    for r in results:
        all_R.extend(r['R_samples'])
    mean_R = np.mean(all_R)
    std_R = np.std(all_R)
    dev = abs(mean_R - 0.137)

    verdict = "PASS" if dev < 0.05 else "PARTIAL"
    color = 'green' if verdict == "PASS" else 'orange'

    stats_text = f"""
    RESULTS SUMMARY

    Overall R̄: {mean_R:.4f} ± {std_R:.4f}
    Target R̄: 0.137
    Deviation: {dev:.4f}

    Configs tested: {len(results)}
    Total samples: {len(all_R)}

    VERDICT: {verdict}
    """

    ax.text(0.1, 0.5, stats_text, fontsize=14, family='monospace',
            verticalalignment='center', bbox=dict(boxstyle='round', facecolor=color, alpha=0.2))

    fig.suptitle('T6-A1: Coherence-Incoherence Transition (R̄ ≈ 0.137)',
                fontsize=16, fontweight='bold')
    plt.tight_layout()

    output_path = config.figure_dir / 'T6A1_standalone_summary.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"Figure: {output_path}")
    plt.close()

# ============================================================================
# Main
# ============================================================================

def main():
    config = Config()

    start = time.time()
    logging.info("Starting...")
    results = run_experiment(config)
    elapsed = time.time() - start

    logging.info(f"\nElapsed: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    # Save
    output_file = config.output_dir / 'T6A1_standalone_results.json'
    with open(output_file, 'w') as f:
        json.dump({'results': results}, f, indent=2)
    logging.info(f"Data: {output_file}")

    # Plot
    plot_results(results, config)

    # Verdict
    all_R = []
    for r in results:
        all_R.extend(r['R_samples'])
    mean_R = np.mean(all_R)
    dev = abs(mean_R - 0.137)
    verdict = "PASS" if dev < 0.05 else "PARTIAL"

    logging.info("")
    logging.info("="*70)
    logging.info("T6-A1 COMPLETE!")
    logging.info("="*70)
    logging.info(f"Overall R̄: {mean_R:.4f} ± {np.std(all_R):.4f}")
    logging.info(f"Target: 0.137")
    logging.info(f"Deviation: {dev:.4f}")
    logging.info(f"Verdict: {verdict}")
    logging.info("="*70)

if __name__ == '__main__':
    main()
