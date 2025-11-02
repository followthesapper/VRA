#!/usr/bin/env python3
"""
T6-B3 — Matter/Antimatter CP-Phase Toy Model

Question:
    Can VRA detect tiny systematic phase biases analogous to CP violation
    in particle physics?

Hypothesis:
    For a phase-biased signal with CP-violating parameter φ,
    the asymmetry metric S(φ) should be:

        S(φ) ≈ c·φ  (odd function, linear for small φ)

    where c > 0 is a sensitivity coefficient.

Falsification:
    If S(φ) shows no linear correlation with φ, or if sensitivity c ≈ 0,
    the claim is false.

Physics Analogy:
    In particle physics, matter/antimatter asymmetry manifests as tiny
    phase differences in decay rates. This toy model tests if VRA can
    detect such subtle biases in multiplicative sequences.

Author: Dylan Vaca
Date: October 31, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import time
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Experimental parameters"""
    # CP-violation phase biases (in radians)
    phi_values = np.array([0.0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2])

    # Modular arithmetic
    N_primes = [997, 2003, 5003]  # Test universality across primes
    r_fraction = 0.143  # r ≈ 0.143*N → r=286 (valid divisor of φ(2003)=2002)

    # Signal parameters
    L_values = [2**12, 2**14, 2**16]  # Sequence lengths
    M_bases = 16  # Fixed number of bases

    # Noise model
    sigma_noise = 0.01  # Small phase noise

    # Monte Carlo
    n_trials = 50

    # Output paths
    output_dir = Path("../../Data/Experiments/Tier6/T6B3")
    figure_dir = Path("../../Figures/experiments/Tier6/T6B3")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6B3_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        self.setup_logging()

    def setup_logging(self):
        """Configure logging to file and console"""
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
        logging.info("T6-B3: Matter/Antimatter CP-Phase Toy Model")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")


# ============================================================================
# CP-Biased Signal Generation
# ============================================================================

def generate_cp_biased_sequence(N: int, r: int, phi: float, L: int,
                                 M: int, sigma_noise: float = 0.01,
                                 seed: int = None) -> Tuple[np.ndarray, Dict]:
    """
    Generate modular sequences with CP-violating phase bias.

    Args:
        N: Prime modulus
        r: Target multiplicative order
        phi: CP-violating phase bias (radians)
        L: Sequence length
        M: Number of bases
        sigma_noise: Phase noise std
        seed: Random seed

    Returns:
        sequences: (M, L) complex phasors
        metadata: Signal parameters
    """
    if seed is not None:
        np.random.seed(seed)

    # Find bases near order r (approximate for speed)
    bases = []
    attempts = 0
    max_attempts = 10000
    while len(bases) < M and attempts < max_attempts:
        a = np.random.randint(2, N)
        if np.gcd(a, N) == 1:
            # Quick order check (not rigorous, but fast for toy model)
            if pow(a, r, N) == 1:
                bases.append(a)
        attempts += 1

    if len(bases) < M:
        logging.warning(f"Only found {len(bases)}/{M} bases for N={N}, r={r}")
        M = len(bases)

    # Generate sequences with CP bias
    sequences = np.zeros((M, L), dtype=complex)

    for i, a in enumerate(bases):
        x = 1
        for t in range(L):
            # Modular multiplication
            x = (x * a) % N

            # Convert to phase with CP bias
            # φ_CP: systematic bias (analogous to weak phase in particle physics)
            phase_base = 2 * np.pi * x / N

            # Apply CP bias: half bases get +φ, half get -φ (matter/antimatter)
            phase_bias = phi if i < M//2 else -phi
            phase = phase_base + phase_bias

            # Add thermal noise
            if sigma_noise > 0:
                phase += np.random.normal(0, sigma_noise)

            sequences[i, t] = np.exp(1j * phase)

    metadata = {
        'N': int(N),
        'r': int(r),
        'phi': float(phi),
        'L': int(L),
        'M': int(M),
        'sigma': float(sigma_noise)
    }

    return sequences, metadata


# ============================================================================
# CP Asymmetry Metric
# ============================================================================

def compute_cp_asymmetry(sequences: np.ndarray, r: int) -> float:
    """
    Compute CP asymmetry from biased sequences.

    The asymmetry metric compares "matter" vs "antimatter" subgroups.

    Args:
        sequences: (M, L) complex phasors
        r: Expected periodicity

    Returns:
        S: CP asymmetry (should be ~c·φ for small φ)
    """
    M, L = sequences.shape
    M_half = M // 2

    # Split into "matter" (first half) and "antimatter" (second half)
    matter_seqs = sequences[:M_half, :]
    antimatter_seqs = sequences[M_half:, :]

    # Compute FFT for both groups
    matter_fft = np.fft.fft(matter_seqs, axis=1)
    antimatter_fft = np.fft.fft(antimatter_seqs, axis=1)

    # Focus on fundamental harmonic (ℓ=1 at f=L/r)
    # For simplicity, use nearest integer bin
    f_fundamental = L // r
    if f_fundamental >= L // 2:
        f_fundamental = 1  # Safety fallback

    # Extract phasors at fundamental
    matter_phasor = matter_fft[:, f_fundamental]
    antimatter_phasor = antimatter_fft[:, f_fundamental]

    # Compute mean phasors
    matter_mean = np.mean(matter_phasor)
    antimatter_mean = np.mean(antimatter_phasor)

    # CP asymmetry: difference in phases
    # For unbiased (φ=0), both should point same direction (S≈0)
    # For biased (φ>0), they should differ (S∝φ)

    # Method 1: Phase difference
    phase_matter = np.angle(matter_mean)
    phase_antimatter = np.angle(antimatter_mean)
    S_phase = np.sin(phase_matter - phase_antimatter)  # Odd function, bounded

    # Method 2: Imaginary part of cross-correlation (more robust)
    cross_corr = matter_mean * np.conj(antimatter_mean)
    S_imag = np.imag(cross_corr) / (np.abs(matter_mean) * np.abs(antimatter_mean) + 1e-10)

    # Use imaginary part (naturally odd under φ → -φ)
    return float(S_imag)


# ============================================================================
# Experiment Execution
# ============================================================================

def run_cp_phase_scan(config: Config) -> List[Dict]:
    """
    Scan CP-violating phase φ and measure asymmetry S(φ).

    Returns:
        results: List of measurements for each (N, L, φ) combination
    """
    logging.info("")
    logging.info("Starting CP-phase scan...")
    logging.info(f"φ values: {config.phi_values}")
    logging.info(f"N primes: {config.N_primes}")
    logging.info(f"L values: {config.L_values}")
    logging.info(f"M bases: {config.M_bases}, trials: {config.n_trials}")
    logging.info("")

    results = []
    total_configs = len(config.N_primes) * len(config.L_values) * len(config.phi_values)
    config_idx = 0
    start_time = time.time()

    for N in config.N_primes:
        r = int(config.r_fraction * N)

        # Find divisor of N-1 close to r
        for candidate in range(r, r + 100):
            if (N - 1) % candidate == 0:
                r = candidate
                break

        logging.info(f"\nTesting N={N}, r={r} (ρ={r/N:.4f})")

        for L in config.L_values:
            logging.info(f"  L={L}...")

            for phi in config.phi_values:
                config_idx += 1
                elapsed = time.time() - start_time
                rate = config_idx / elapsed if elapsed > 0 else 0
                eta = (total_configs - config_idx) / rate if rate > 0 else 0

                # Run trials
                S_samples = []
                for trial in range(config.n_trials):
                    sequences, metadata = generate_cp_biased_sequence(
                        N, r, phi, L, config.M_bases, config.sigma_noise, seed=trial
                    )
                    S = compute_cp_asymmetry(sequences, r)
                    S_samples.append(S)

                S_mean = float(np.mean(S_samples))
                S_std = float(np.std(S_samples))

                if config_idx % 5 == 0 or phi == config.phi_values[-1]:
                    logging.info(f"    [{config_idx}/{total_configs}] φ={phi:.4f}: S={S_mean:.6f}±{S_std:.6f} | "
                                f"ETA: {eta/60:.1f}m")

                results.append({
                    'N': int(N),
                    'r': int(r),
                    'L': int(L),
                    'phi': float(phi),
                    'S_mean': S_mean,
                    'S_std': S_std,
                    'S_samples': [float(x) for x in S_samples]
                })

    elapsed = time.time() - start_time
    logging.info(f"\nScan complete: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    return results


# ============================================================================
# Analysis & Plotting
# ============================================================================

def analyze_linearity(results: List[Dict], config: Config):
    """
    Test hypothesis: S(φ) ≈ c·φ (linear, odd function).

    Perform linear regression and report sensitivity c and R².
    """
    logging.info("")
    logging.info("="*70)
    logging.info("LINEARITY ANALYSIS: S(φ) = c·φ + b")
    logging.info("="*70)

    # Group by (N, L)
    from collections import defaultdict
    grouped = defaultdict(list)
    for r in results:
        key = (r['N'], r['L'])
        grouped[key].append((r['phi'], r['S_mean']))

    # Fit each group
    fits = []
    for (N, L), data in grouped.items():
        phi_vals = np.array([d[0] for d in data])
        S_vals = np.array([d[1] for d in data])

        # Linear regression
        slope, intercept, r_value, p_value, std_err = linregress(phi_vals, S_vals)
        r_squared = r_value**2

        logging.info(f"N={N}, L={L}: S(φ) = {slope:.4f}·φ + {intercept:.6f}")
        logging.info(f"  R² = {r_squared:.6f}, p = {p_value:.2e}")
        logging.info(f"  Sensitivity c = {slope:.4f} (should be > 0 and consistent)")

        fits.append({
            'N': N,
            'L': L,
            'slope': float(slope),
            'intercept': float(intercept),
            'r_squared': float(r_squared),
            'p_value': float(p_value)
        })

    # Overall verdict
    logging.info("")
    all_positive = all(f['slope'] > 0 for f in fits)
    all_significant = all(f['r_squared'] > 0.9 for f in fits)
    mean_r2 = np.mean([f['r_squared'] for f in fits])

    if all_positive and all_significant:
        logging.info(f"VERDICT: PASS — Linear scaling confirmed (mean R²={mean_r2:.4f})")
    elif all_positive:
        logging.info(f"VERDICT: PARTIAL — Positive slope but weak fit (mean R²={mean_r2:.4f})")
    else:
        logging.info(f"VERDICT: FAIL — No consistent linear relationship")

    return fits


def plot_results(results: List[Dict], fits: List[Dict], config: Config):
    """Generate publication-quality figures"""
    logging.info("")
    logging.info("Generating figures...")

    # Group by L for multi-panel plot
    L_values_present = sorted(set(r['L'] for r in results))
    n_panels = len(L_values_present)

    fig, axes = plt.subplots(1, n_panels, figsize=(5*n_panels, 4))
    if n_panels == 1:
        axes = [axes]

    for idx, L in enumerate(L_values_present):
        ax = axes[idx]

        # Plot data for each N
        for N in config.N_primes:
            data = [r for r in results if r['L'] == L and r['N'] == N]
            if not data:
                continue

            phi_vals = [r['phi'] for r in data]
            S_means = [r['S_mean'] for r in data]
            S_stds = [r['S_std'] for r in data]

            ax.errorbar(phi_vals, S_means, yerr=S_stds, fmt='o-',
                       label=f'N={N}', capsize=3, alpha=0.7)

        # Plot fit lines
        for fit in fits:
            if fit['L'] == L:
                phi_range = np.linspace(0, config.phi_values[-1], 100)
                S_fit = fit['slope'] * phi_range + fit['intercept']
                ax.plot(phi_range, S_fit, '--', alpha=0.5,
                       label=f"N={fit['N']} fit (R²={fit['r_squared']:.3f})")

        ax.axhline(0, color='k', linestyle=':', alpha=0.3)
        ax.set_xlabel('CP-violating phase φ (rad)')
        ax.set_ylabel('Asymmetry S(φ)')
        ax.set_title(f'L={L}')
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    fig.suptitle('T6-B3: CP-Phase Sensitivity S(φ) ≈ c·φ', fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_path = config.figure_dir / 'T6B3_cp_phase_summary.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"Figure saved: {output_path}")
    plt.close()


# ============================================================================
# Main
# ============================================================================

def main():
    """Execute T6-B3 experiment"""
    config = Config()

    # Run experiment
    start_time = time.time()
    results = run_cp_phase_scan(config)
    elapsed = time.time() - start_time

    # Save raw data
    output_file = config.output_dir / 'T6B3_results.json'
    with open(output_file, 'w') as f:
        json.dump({'results': results}, f, indent=2)
    logging.info(f"\nData saved: {output_file}")

    # Analyze linearity
    fits = analyze_linearity(results, config)

    # Generate plots
    plot_results(results, fits, config)

    # Final summary
    logging.info("")
    logging.info("="*70)
    logging.info("T6-B3 COMPLETE")
    logging.info("="*70)
    logging.info(f"Total runtime: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    logging.info(f"Configurations tested: {len(results)}")
    logging.info(f"Hypothesis: S(φ) = c·φ (linear, odd)")
    mean_r2 = np.mean([f['r_squared'] for f in fits])
    all_positive = all(f['slope'] > 0 for f in fits)
    logging.info(f"Mean R²: {mean_r2:.4f}")
    logging.info(f"All slopes positive: {all_positive}")

    if mean_r2 > 0.9 and all_positive:
        logging.info("VERDICT: PASS")
    elif all_positive:
        logging.info("VERDICT: PARTIAL")
    else:
        logging.info("VERDICT: FAIL")
    logging.info("="*70)


if __name__ == '__main__':
    main()
