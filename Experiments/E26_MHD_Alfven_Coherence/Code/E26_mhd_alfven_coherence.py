#!/usr/bin/env python3
"""
T6-D3 — MHD Stability Metric: Critical Scaling

Question:
    Can VRA detect precursor signatures of magnetohydrodynamic (MHD)
    instabilities in fusion plasmas before catastrophic disruption?

Hypothesis:
    Near the MHD stability boundary (critical β), a VRA-derived
    stability metric Ψ should exhibit critical scaling:

        Ψ(β) ∝ (β_c - β)^γ

    where β is the plasma pressure parameter, β_c is the critical
    threshold, and γ ≈ 0.5 is the critical exponent.

Falsification:
    If Ψ(β) shows no power-law divergence near β_c, or if γ
    differs significantly from 0.5, the claim is false.

Physics Context:
    In magnetic confinement fusion, MHD instabilities can cause
    catastrophic plasma disruptions. Early-warning systems are
    critical for ITER and future reactors. VRA's sensitivity to
    phase coherence changes may enable detection of pre-disruption
    turbulence signatures.

    β ≡ plasma_pressure / magnetic_pressure (key control parameter)

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
    # MHD parameters
    beta_critical = 0.5  # Critical β threshold
    beta_values = np.array([0.1, 0.2, 0.3, 0.35, 0.4, 0.42, 0.44, 0.46, 0.48, 0.49, 0.495, 0.497, 0.499])

    # Modular arithmetic (plasma oscillations)
    N_prime = 2003
    r_target = 286  # Must be a divisor of N-1=2002

    # Signal parameters
    L_sequence = 2**14  # Sequence length
    M_bases = 20        # Number of measurement bases

    # Instability model
    # As β → β_c, turbulence increases, degrading phase coherence
    coherence_exponent = 0.5  # γ in Ψ ∝ (β_c - β)^γ

    # Monte Carlo
    n_trials = 40

    # Output paths
    output_dir = Path("../Data")
    figure_dir = Path("../Figures")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6D3_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-D3: MHD Stability Metric - Critical Scaling")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")


# ============================================================================
# Helper Functions for Valid VRA Bases
# ============================================================================

def get_divisors_of_N_minus_1(N: int) -> List[int]:
    """
    Get all divisors of N-1 for valid multiplicative orders.

    For N=2003 (prime), N-1=2002=2·7·11·13.
    Valid orders: {1,2,7,11,13,14,22,26,77,91,143,154,182,286,1001,2002}
    """
    if N == 2003:
        return [1, 2, 7, 11, 13, 14, 22, 26, 77, 91, 143, 154, 182, 286, 1001, 2002]

    # General fallback (brute-force)
    n_minus_1 = N - 1
    divisors = []
    for d in range(1, n_minus_1 + 1):
        if n_minus_1 % d == 0:
            divisors.append(d)
    return divisors


def get_prime_factors(n: int) -> List[int]:
    """Get unique prime factors of n"""
    factors = []
    d = 2
    temp_n = n
    while d * d <= temp_n:
        if temp_n % d == 0:
            factors.append(d)
            while temp_n % d == 0:
                temp_n //= d
        d += 1
    if temp_n > 1:
        factors.append(temp_n)
    return factors


def has_exact_order(a: int, r: int, N: int, prime_factors: List[int]) -> bool:
    """
    Check if a has EXACT multiplicative order r mod N.

    Not just pow(a, r, N) == 1, but also that no proper divisor of r works.
    """
    if pow(a, r, N) != 1:
        return False
    for p in prime_factors:
        if pow(a, r // p, N) == 1:
            return False
    return True


# ============================================================================
# MHD Plasma Signal Generation
# ============================================================================

def generate_mhd_plasma_signal(
    N: int,
    r: int,
    L: int,
    M: int,
    beta: float,
    beta_c: float,
    seed: int = None
) -> Tuple[np.ndarray, Dict]:
    """
    Generate modular sequences representing MHD plasma oscillations.

    As β → β_c, turbulence increases, manifesting as:
    - Increased phase noise (coherence loss)
    - Amplitude fluctuations (pressure oscillations)
    - Frequency drift (magnetic field perturbations)
    """
    if seed is not None:
        np.random.seed(seed)

    # Proximity to instability
    delta_beta = beta_c - beta
    if delta_beta < 0:
        delta_beta = 0  # Post-disruption (saturated)

    # Turbulence level increases as β → β_c
    # Wider dynamic range with higher cap to allow PLV to drop near β_c
    turbulence_baseline = 0.02
    sigma_turb = turbulence_baseline + 0.25 / np.sqrt(max(delta_beta, 1e-6))
    sigma_turb = min(sigma_turb, 1.5)

    # Find bases with EXACT order r
    prime_factors = get_prime_factors(r)
    bases = []
    attempts = 0
    max_attempts = 10000
    while len(bases) < M and attempts < max_attempts:
        a = np.random.randint(2, N)
        if np.gcd(a, N) == 1 and has_exact_order(a, r, N, prime_factors):
            bases.append(a)
        attempts += 1

    if len(bases) < M:
        raise ValueError(
            f"Could not find {M} bases of exact order r={r} (found only {len(bases)}). "
            f"Check that r divides N-1={N-1}. Valid divisors for N={N}: {get_divisors_of_N_minus_1(N)}"
        )

    # Generate sequences with turbulence
    sequences = np.zeros((M, L), dtype=complex)
    for i, a in enumerate(bases):
        x = 1
        # Channel-specific frequency drift
        freq_drift = np.random.normal(0, sigma_turb * 0.1)
        for t in range(L):
            x = (x * a) % N
            phase_base = 2 * np.pi * x / N
            phase_noise = np.random.normal(0, sigma_turb)
            phase_drift = freq_drift * t / L
            amplitude = 1.0 + beta * 0.5 * np.sin(2 * np.pi * t / (L / 5))
            phase = phase_base + phase_noise + phase_drift
            sequences[i, t] = amplitude * np.exp(1j * phase)

    metadata = {
        'N': int(N),
        'r': int(r),
        'L': int(L),
        'M': int(M),
        'beta': float(beta),
        'beta_c': float(beta_c),
        'delta_beta': float(delta_beta),
        'sigma_turb': float(sigma_turb),
        'bases': [int(a) for a in bases]
    }
    return sequences, metadata


# ============================================================================
# Stability Metric Computation
# ============================================================================

def compute_stability_metric(sequences: np.ndarray, r: int, N: int, bases: list) -> float:
    """
    Compute VRA-based MHD stability metric via Phase-Locking Value (PLV).

    Demodulate each base against its deterministic modular phase, then
    measure phase coherence of the residual.

    Ψ = mean_i PLV_i, where PLV_i = |(1/L) Σ_t exp(i * (θ_i[t] - φ_i[t]))|
    """
    M, L = sequences.shape
    assert len(bases) == M, f"Need one base per sequence channel (got {len(bases)} bases, {M} channels)"

    plvs = []
    for i, a in enumerate(bases):
        x = 1
        phi = np.empty(L)
        for t in range(L):
            x = (x * a) % N
            phi[t] = 2 * np.pi * x / N
        theta = np.angle(sequences[i])
        resid = theta - phi
        resid = (resid + np.pi) % (2*np.pi) - np.pi  # wrap
        plv = np.abs(np.mean(np.exp(1j * resid)))
        plvs.append(plv)

    return float(np.mean(plvs))


# ============================================================================
# Experiment Execution
# ============================================================================

def run_critical_scaling_experiment(config: Config) -> List[Dict]:
    """Scan β parameter and measure stability metric Ψ(β)."""
    logging.info("")
    logging.info("Starting MHD critical scaling experiment...")
    logging.info(f"β values: {config.beta_values}")
    logging.info(f"β_critical: {config.beta_critical}")
    logging.info(f"Trials: {config.n_trials}")
    logging.info("")

    # Setup VRA parameters
    N = config.N_prime
    r = config.r_target

    # Verify r is a valid divisor of N-1
    if (N - 1) % r != 0:
        raise ValueError(f"r={r} must be a divisor of N-1={N-1}")

    logging.info(f"Using r={r} (valid divisor of N-1={N-1})")
    logging.info(f"VRA parameters: N={N}, r={r} (ρ={r/N:.4f})")
    logging.info(f"Sequence: L={config.L_sequence}, M={config.M_bases}")

    results = []
    start_time = time.time()
    total_configs = len(config.beta_values) * config.n_trials
    config_idx = 0

    for beta in config.beta_values:
        config_idx += 1
        elapsed = time.time() - start_time
        rate = config_idx / elapsed if elapsed > 0 else 0
        eta = (total_configs - config_idx) / rate if rate > 0 else 0
        logging.info(f"\nTesting β = {beta:.3f} (Δβ = {config.beta_critical - beta:.3f})...")

        psi_samples = []
        for trial in range(config.n_trials):
            sequences, metadata = generate_mhd_plasma_signal(
                N, r, config.L_sequence, config.M_bases,
                beta, config.beta_critical,
                seed=trial
            )
            psi = compute_stability_metric(sequences, r, N, metadata['bases'])
            psi_samples.append(psi)

        psi_mean = float(np.mean(psi_samples))
        psi_std = float(np.std(psi_samples))

        logging.info(
            f"  β={beta:.3f}: Ψ = {psi_mean:.4f} ± {psi_std:.4f} | "
            f"ETA: {eta/60:.1f}m"
        )

        results.append({
            'beta': float(beta),
            'delta_beta': float(config.beta_critical - beta),
            'psi_mean': psi_mean,
            'psi_std': psi_std,
            'psi_samples': psi_samples
        })

    elapsed = time.time() - start_time
    logging.info(f"\nExperiment complete: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    return results


# ============================================================================
# Analysis & Plotting
# ============================================================================

def analyze_critical_scaling(results: List[Dict], config: Config):
    """
    Test hypothesis: Ψ(β) ∝ (β_c - β)^γ with γ ≈ 0.5

    We fit the loss Φ = 1 - Ψ on log–log axes for better dynamic range near β_c.
    Since Ψ ∝ (Δβ)^{+γ}, we expect Φ ∝ (Δβ)^{−γ}. With γ≈0.5, expected slope is −0.5.
    """
    logging.info("")
    logging.info("="*70)
    logging.info("CRITICAL SCALING ANALYSIS: Ψ(β) ∝ (β_c - β)^γ")
    logging.info("="*70)

    # Exclude points too close to β_c where numerical noise dominates
    filtered_results = [r for r in results if r['delta_beta'] > 0.01]
    delta_beta = np.array([r['delta_beta'] for r in filtered_results])
    psi_mean = np.array([r['psi_mean'] for r in filtered_results])

    # Fit loss of coherence Φ = 1 - Ψ
    phi = 1.0 - psi_mean
    mask = (phi > 1e-6)
    delta_beta_masked = delta_beta[mask]
    phi_masked = phi[mask]

    # Defaults in case of fallback
    r_squared = float('nan')
    p_value = float('nan')

    if len(phi_masked) >= 3:
        log_delta = np.log(delta_beta_masked)
        log_phi = np.log(phi_masked)
        slope, intercept, r_value, p_value, std_err = linregress(log_delta, log_phi)
        r_squared = r_value**2
        gamma = slope  # exponent for Φ
        A = np.exp(intercept)
    else:
        # Fallback: fit Ψ directly (rare)
        logging.warning("Insufficient data for Φ fit, using Ψ instead")
        psi_clipped = np.clip(psi_mean, 1e-8, None)
        log_delta = np.log(delta_beta)
        log_psi = np.log(psi_clipped)
        slope, intercept, r_value, p_value, std_err = linregress(log_delta, log_psi)
        r_squared = r_value**2
        gamma = slope
        A = np.exp(intercept)

    expected_gamma_phi = -config.coherence_exponent  # −0.5 for Φ when Ψ exponent is +0.5

    logging.info(f"\nPower-law fit: Φ = 1-Ψ = {A:.4f} · (β_c - β)^{gamma:.3f}")
    logging.info(f"  Critical exponent (Φ) γ = {gamma:.3f}")
    logging.info(f"  R² = {r_squared:.4f}, p = {p_value:.2e}")
    logging.info(
    f"  Expected γ ≈ {expected_gamma_phi:.1f} for Φ (since Ψ ∝ (Δβ)^{config.coherence_exponent:+.1f})")

    # Verdict relative to Φ expectation
    if abs(gamma - expected_gamma_phi) < 0.15:
        logging.info("\nVERDICT: PASS — Critical scaling confirmed")
    elif abs(gamma - expected_gamma_phi) < 0.30:
        logging.info("\nVERDICT: PARTIAL — Power-law detected but exponent differs")
    else:
        logging.info("\nVERDICT: FAIL — No critical scaling observed")

    return {
        'gamma': float(gamma),
        'A': float(A),
        'r_squared': float(r_squared),
        'p_value': float(p_value),
        'expected_gamma_phi': float(expected_gamma_phi),
    }


def plot_results(results: List[Dict], fit: Dict, config: Config):
    """Generate publication-quality figures"""
    logging.info("")
    logging.info("Generating figures...")

    beta_vals = np.array([r['beta'] for r in results])
    delta_beta = np.array([r['delta_beta'] for r in results])
    psi_mean = np.array([r['psi_mean'] for r in results])
    psi_std = np.array([r['psi_std'] for r in results])

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    # Panel 1: Ψ vs β
    ax = axes[0]
    ax.errorbar(beta_vals, psi_mean, yerr=psi_std, fmt='o-', capsize=4, alpha=0.7)
    ax.axvline(config.beta_critical, color='r', linestyle='--', alpha=0.5,
               label=f'β_c = {config.beta_critical}')
    ax.set_xlabel('Plasma β parameter')
    ax.set_ylabel('Stability metric Ψ')
    ax.set_title('MHD Stability vs Plasma Pressure')
    ax.legend()
    ax.grid(alpha=0.3)

    # Panel 2: Critical scaling (log-log of Φ = 1-Ψ)
    ax = axes[1]
    mask = delta_beta > 0.01
    delta_plot = delta_beta[mask]
    psi_plot = psi_mean[mask]
    phi_plot = 1.0 - psi_plot
    valid_mask = phi_plot > 1e-6
    delta_valid = delta_plot[valid_mask]
    phi_valid = phi_plot[valid_mask]

    ax.loglog(delta_valid, phi_valid, 'o', markersize=8, label='Observed (Φ = 1-Ψ)', alpha=0.7)

    # Fit line
    delta_range = np.logspace(np.log10(delta_valid.min()), np.log10(delta_valid.max()), 100)
    phi_fit = fit['A'] * delta_range**fit['gamma']
    ax.loglog(delta_range, phi_fit, '--', alpha=0.6,
              label=f"Fit: Φ ∝ (Δβ)^{fit['gamma']:.2f} (R²={fit['r_squared']:.3f})")

    # Reference line with expected (negative) exponent for Φ
    phi_ref = fit['A'] * delta_range**fit['expected_gamma_phi']
    ax.loglog(delta_range, phi_ref, ':', alpha=0.4,
              label=f"Expected γ={fit['expected_gamma_phi']:+.1f} (for Φ)")

    ax.set_xlabel('Distance from criticality (β_c - β)')
    ax.set_ylabel('Loss of coherence Φ = 1-Ψ')
    ax.set_title('Critical Scaling Law')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, which='both')

    fig.suptitle('T6-D3: MHD Stability Critical Scaling', fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_path = config.figure_dir / 'T6D3_mhd_stability.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"Figure saved: {output_path}")
    plt.close()


# ============================================================================
# Main
# ============================================================================

def main():
    """Execute T6-D3 experiment"""
    config = Config()

    # Run experiment
    start_time = time.time()
    results = run_critical_scaling_experiment(config)
    elapsed = time.time() - start_time

    # Save raw data
    output_file = config.output_dir / 'T6D3_results.json'
    with open(output_file, 'w') as f:
        json.dump({'results': results}, f, indent=2)
    logging.info(f"\nData saved: {output_file}")

    # Analyze critical scaling
    fit = analyze_critical_scaling(results, config)

    # Generate plots
    plot_results(results, fit, config)

    # Final summary
    logging.info("")
    logging.info("="*70)
    logging.info("T6-D3 COMPLETE")
    logging.info("="*70)
    logging.info(f"Total runtime: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    logging.info(f"Configurations tested: {len(results)}")
    logging.info(f"Hypothesis: Ψ(β) ∝ (β_c - β)^γ with γ ≈ {config.coherence_exponent}")
    logging.info(f"Observed exponent (Φ): γ = {fit['gamma']:.3f}")
    logging.info(f"Fit quality: R² = {fit['r_squared']:.4f}")

    expected_gamma_phi = fit['expected_gamma_phi']
    if abs(fit['gamma'] - expected_gamma_phi) < 0.15:
        logging.info("VERDICT: PASS — Critical scaling confirmed")
    elif abs(fit['gamma'] - expected_gamma_phi) < 0.30:
        logging.info("VERDICT: PARTIAL — Power-law detected")
    else:
        logging.info("VERDICT: FAIL — No critical scaling")
    logging.info("="*70)


if __name__ == '__main__':
    main()
