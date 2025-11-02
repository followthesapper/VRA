#!/usr/bin/env python3
"""
T6-D2 — Phonon Mode Separation: Super-Resolution Bound (v3)

Question:
    Can VRA resolve closely-spaced vibrational modes in materials
    beyond the classical Fourier limit?

Hypothesis:
    For two phonon modes separated by Δω in frequency space,
    VRA can resolve them with sequence length L satisfying:

        L ≳ c / √(Δω)

    where c is a constant. This is a super-resolution bound that
    improves on the classical L ∝ 1/Δω Rayleigh criterion.

Changes in v3:
    - Budgeted noise: Fixed total shots S_total, σ_phase ∝ 1/√(S_total/M/L)
    - Hypothesis testing: AIC-based 1-tone vs 2-tone fit (not peak counting)
    - No averaging before detection: Joint fit across all M bases
    - Fine Δω sweep: Down to 1e-4 to probe super-resolution
    - Scaling analysis: Extract Δω*_0.5(L) where P(resolve)≈50% and fit α

Author: Dylan Vaca
Date: October 31, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from scipy.optimize import minimize
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
    # Phonon mode parameters
    omega_base = 0.12  # Base frequency (cycles/sample)

    # Fine Δω sweep to probe super-resolution
    delta_omega_values = np.array([
        1e-4, 2e-4, 5e-4,
        1e-3, 2e-3, 5e-3,
        1e-2, 2e-2, 5e-2
    ])

    # Modular arithmetic
    N_prime = 2003
    r_fraction = 0.143  # r ≈ 0.143*N → r=286

    # Sequence lengths (test scaling)
    L_values = [2**10, 2**12, 2**14, 2**16]

    # Resource budget
    S_total = 8_400_000  # Total shots per configuration (ensures ~8 shots/sample at L=65536)
    M_bases = 16  # Number of bases
    noise_constant = 1.0  # σ_phase = c / √shots

    # Detection parameters
    aic_penalty = 6.0  # Evidence margin (stricter than AIC=2 to reduce flukes at low SNR)

    # Monte Carlo
    n_trials = 30

    # Output paths
    output_dir = Path("../../Data/Experiments/Tier6/T6D2")
    figure_dir = Path("../../Figures/experiments/Tier6/T6D2")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6D2_v3_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-D2 v3: Phonon Mode Separation - Super-Resolution Bound")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")


# ============================================================================
# Budgeted Phonon Signal Generation
# ============================================================================

def generate_dual_phonon_signal(
    N: int,
    r: int,
    L: int,
    M: int,
    omega1: float,
    omega2: float,
    shots_per_sample: int,
    noise_constant: float,
    seed: int = None
) -> Tuple[np.ndarray, Dict]:
    """
    Generate modular sequences with two phonon modes and budgeted noise.

    Args:
        N: Prime modulus
        r: Multiplicative order
        L: Sequence length
        M: Number of bases
        omega1, omega2: Phonon mode frequencies (cycles/sample)
        shots_per_sample: Measurement shots per time sample
        noise_constant: Scaling constant for phase noise
        seed: Random seed

    Returns:
        sequences: (M, L) complex phasors
        metadata: Signal parameters
    """
    if seed is not None:
        np.random.seed(seed)

    # Phase noise from shot budget
    sigma_phase = noise_constant / np.sqrt(max(1, shots_per_sample))

    # Find bases with order r
    bases = []
    attempts = 0
    max_attempts = 10000
    while len(bases) < M and attempts < max_attempts:
        a = np.random.randint(2, N)
        if np.gcd(a, N) == 1:
            if pow(a, r, N) == 1:
                bases.append(a)
        attempts += 1

    if len(bases) < M:
        logging.warning(f"Only found {len(bases)}/{M} bases for r={r}")
        M = len(bases)

    # Generate sequences with dual phonon modes
    sequences = np.zeros((M, L), dtype=complex)

    for i, a in enumerate(bases):
        x = 1
        for t in range(L):
            # Modular multiplication
            x = (x * a) % N

            # Base phase from modular sequence
            phase_base = 2 * np.pi * x / N

            # Add phonon modulations
            phonon_modulation = (
                np.cos(2 * np.pi * omega1 * t) +
                np.cos(2 * np.pi * omega2 * t)
            )

            # Combined phase (small modulation)
            phase = phase_base + 0.15 * phonon_modulation

            # Add shot noise
            phase += np.random.normal(0, sigma_phase)

            sequences[i, t] = np.exp(1j * phase)

    metadata = {
        'N': int(N),
        'r': int(r),
        'L': int(L),
        'M': int(M),
        'omega1': float(omega1),
        'omega2': float(omega2),
        'delta_omega': float(abs(omega2 - omega1)),
        'sigma_phase': float(sigma_phase),
        'shots_per_sample': int(shots_per_sample),
        'bases': bases
    }

    return sequences, metadata


# ============================================================================
# Carrier Derotation
# ============================================================================

def derotate_sequences(N: int, r: int, bases: List[int], sequences: np.ndarray) -> np.ndarray:
    """
    Remove the modular carrier phase from sequences.

    Args:
        N: Prime modulus
        r: Multiplicative order
        bases: List of M bases
        sequences: (M, L) complex phasors

    Returns:
        derotated: (M, L) complex phasors with carrier removed
    """
    M, L = sequences.shape
    derotated = np.empty_like(sequences, dtype=complex)

    for i, a in enumerate(bases):
        x = 1
        carrier = np.empty(L, dtype=complex)
        for t in range(L):
            x = (x * a) % N
            carrier[t] = np.exp(1j * (2 * np.pi * x / N))

        # Divide out carrier
        derotated[i] = sequences[i] * np.conj(carrier)

    return derotated


# ============================================================================
# Hypothesis Testing: 1-tone vs 2-tone Model
# ============================================================================

def fit_tone_model(phase_resid: np.ndarray, frequencies: List[float]) -> Dict:
    """
    Fit tone model to phase residuals using least squares.

    Args:
        phase_resid: (M, L) phase residuals across M bases
        frequencies: List of frequencies to fit

    Returns:
        result: Fit metrics (RSS, k_params, AIC)
    """
    M, L = phase_resid.shape
    t = np.arange(L)

    # Build design matrix for all frequencies
    # For each freq f: [cos(2πft), sin(2πft)]
    n_freqs = len(frequencies)
    X = np.empty((L, 2 * n_freqs))
    for i, f in enumerate(frequencies):
        X[:, 2*i] = np.cos(2 * np.pi * f * t)
        X[:, 2*i + 1] = np.sin(2 * np.pi * f * t)

    # Fit each base separately and sum RSS
    rss_total = 0.0
    for base_idx in range(M):
        y = phase_resid[base_idx, :]

        # Least squares: β = (X^T X)^{-1} X^T y
        coeffs, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)

        if residuals.size > 0:
            rss_total += residuals[0]
        else:
            # Compute manually if lstsq didn't return residuals
            y_pred = X @ coeffs
            rss_total += np.sum((y - y_pred)**2)

    k_params = 2 * n_freqs  # Number of parameters
    n_total = M * L  # Total number of observations

    # AIC = n*log(RSS/n) + 2k
    aic = n_total * np.log(rss_total / n_total + 1e-12) + 2 * k_params

    return {
        'rss': float(rss_total),
        'k_params': int(k_params),
        'aic': float(aic),
        'n_obs': int(n_total)
    }


def hypothesis_test_resolution(
    sequences: np.ndarray,
    omega1: float,
    omega2: float,
    N: int,
    r: int,
    bases: List[int],
    aic_penalty: float = 2.0
) -> Dict:
    """
    Test H1 (1 tone) vs H2 (2 tones) using AIC.

    Args:
        sequences: (M, L) complex phasors
        omega1, omega2: True mode frequencies
        N: Prime modulus
        r: Multiplicative order
        bases: List of bases
        aic_penalty: AIC penalty factor

    Returns:
        result: Decision and metrics
    """
    M, L = sequences.shape

    # Step 1: Remove modular carrier
    derotated = derotate_sequences(N, r, bases, sequences)

    # Step 2: Extract phase residuals (don't average across bases yet)
    phase_resid = np.unwrap(np.angle(derotated), axis=1)  # (M, L)
    phase_resid = phase_resid - phase_resid.mean(axis=1, keepdims=True)

    # Step 3: Fit models
    # H1: Single tone at mean frequency
    f_mean = (omega1 + omega2) / 2.0
    fit_1tone = fit_tone_model(phase_resid, [f_mean])

    # H2: Two tones
    fit_2tone = fit_tone_model(phase_resid, [omega1, omega2])

    # Step 4: Compare AICs
    delta_aic = fit_2tone['aic'] - fit_1tone['aic']

    # Choose H2 (resolved) if AIC improves by at least penalty
    resolved = (delta_aic < -aic_penalty)

    return {
        'resolved': bool(resolved),
        'delta_aic': float(delta_aic),
        'aic_1tone': float(fit_1tone['aic']),
        'aic_2tone': float(fit_2tone['aic']),
        'rss_1tone': float(fit_1tone['rss']),
        'rss_2tone': float(fit_2tone['rss'])
    }


# ============================================================================
# Experiment Execution
# ============================================================================

def run_resolution_scaling_experiment(config: Config) -> List[Dict]:
    """
    Scan (L, Δω) space to measure resolution threshold with budgeted noise.

    Returns:
        results: Measurements for each (L, Δω)
    """
    logging.info("")
    logging.info("Starting budgeted resolution scaling experiment...")
    logging.info(f"Total shots budget: S_total = {config.S_total:,}")
    logging.info(f"Δω values: {config.delta_omega_values}")
    logging.info(f"L values: {config.L_values}")
    logging.info(f"Trials: {config.n_trials}")
    logging.info("")

    # Setup VRA parameters
    N = config.N_prime
    r = int(config.r_fraction * N)

    # Find divisor of N-1 close to r
    for candidate in range(r, r + 100):
        if (N - 1) % candidate == 0:
            r = candidate
            break

    logging.info(f"VRA parameters: N={N}, r={r} (ρ={r/N:.4f})")
    logging.info("")

    results = []
    start_time = time.time()

    total_configs = len(config.L_values) * len(config.delta_omega_values) * config.n_trials
    config_idx = 0

    for L in config.L_values:
        # Compute shots per sample for this L
        shots_per_sample = max(1, config.S_total // (config.M_bases * L))
        sigma_expected = config.noise_constant / np.sqrt(shots_per_sample)

        logging.info(f"\n{'='*60}")
        logging.info(f"Testing L = {L}")
        logging.info(f"  Shots/sample = {shots_per_sample:,}")
        logging.info(f"  Expected σ_phase = {sigma_expected:.4f}")
        logging.info('='*60)

        for delta_omega in config.delta_omega_values:
            # Define two modes
            f1 = config.omega_base
            f2 = f1 + delta_omega

            resolution_success = []
            delta_aics = []

            for trial in range(config.n_trials):
                config_idx += 1
                elapsed = time.time() - start_time
                rate = config_idx / elapsed if elapsed > 0 else 0
                eta = (total_configs - config_idx) / rate if rate > 0 else 0

                # Generate signal with budgeted noise
                sequences, metadata = generate_dual_phonon_signal(
                    N, r, L, config.M_bases,
                    f1, f2,
                    shots_per_sample,
                    config.noise_constant,
                    seed=trial
                )

                # Hypothesis test
                test_result = hypothesis_test_resolution(
                    sequences, f1, f2,
                    N, r, metadata['bases'],
                    config.aic_penalty
                )

                resolution_success.append(test_result['resolved'])
                delta_aics.append(test_result['delta_aic'])

                if trial == 0:  # Log first trial
                    logging.info(
                        f"  Δω={delta_omega:.4e} | "
                        f"ΔAIC={test_result['delta_aic']:.1f} | "
                        f"Resolved: {test_result['resolved']}"
                    )

            success_rate = np.mean(resolution_success)
            mean_delta_aic = np.mean(delta_aics)

            logging.info(
                f"  Δω={delta_omega:.4e}: P(resolve) = {success_rate:.2%}, "
                f"<ΔAIC> = {mean_delta_aic:.1f} | ETA: {eta/60:.1f}m"
            )

            results.append({
                'L': int(L),
                'delta_omega': float(delta_omega),
                'omega1': float(f1),
                'omega2': float(f2),
                'success_rate': float(success_rate),
                'mean_delta_aic': float(mean_delta_aic),
                'shots_per_sample': int(shots_per_sample),
                'sigma_phase': float(metadata['sigma_phase']),
                'resolution_trials': resolution_success
            })

    elapsed = time.time() - start_time
    logging.info(f"\nExperiment complete: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    return results


# ============================================================================
# Scaling Analysis
# ============================================================================

def extract_threshold_scaling(results: List[Dict]) -> Dict:
    """
    Extract Δω*_0.5(L) threshold where P(resolve) ≈ 50% and fit scaling.

    Args:
        results: Experiment results

    Returns:
        scaling_analysis: Fit parameters and α exponent
    """
    logging.info("")
    logging.info("="*70)
    logging.info("SCALING LAW ANALYSIS: Δω*(L) ∝ L^(-α)")
    logging.info("="*70)

    # Group by L
    L_values = sorted(set(r['L'] for r in results))

    thresholds = []

    for L in L_values:
        # Get (Δω, P(resolve)) curve for this L
        L_results = [r for r in results if r['L'] == L]
        L_results.sort(key=lambda x: x['delta_omega'])

        delta_omegas = np.array([r['delta_omega'] for r in L_results])
        success_rates = np.array([r['success_rate'] for r in L_results])

        # Find Δω where success rate crosses 0.5
        if np.max(success_rates) >= 0.5 and np.min(success_rates) <= 0.5:
            # Linear interpolation
            idx = np.where(success_rates >= 0.5)[0]
            if len(idx) > 0:
                idx_above = idx[0]
                if idx_above > 0:
                    # Interpolate between idx_above-1 and idx_above
                    dw1, sr1 = delta_omegas[idx_above-1], success_rates[idx_above-1]
                    dw2, sr2 = delta_omegas[idx_above], success_rates[idx_above]

                    # Linear interpolation
                    if sr2 != sr1:
                        dw_threshold = dw1 + (0.5 - sr1) * (dw2 - dw1) / (sr2 - sr1)
                    else:
                        dw_threshold = dw1

                    thresholds.append((L, dw_threshold))
                    logging.info(f"L={L}: Δω*_0.5 = {dw_threshold:.4e}")
                else:
                    logging.info(f"L={L}: Success rate always ≥ 50% (threshold below min Δω)")
        else:
            if np.min(success_rates) > 0.5:
                logging.info(f"L={L}: Success rate always > 50% (threshold below min Δω)")
            else:
                logging.info(f"L={L}: Success rate always < 50% (threshold above max Δω)")

    # Fit scaling law Δω* ∝ L^(-α)
    if len(thresholds) >= 2:
        Ls = np.array([t[0] for t in thresholds])
        dws = np.array([t[1] for t in thresholds])

        # Log-log fit: log(Δω*) = -α*log(L) + log(c)
        log_L = np.log(Ls)
        log_dw = np.log(dws)

        slope, intercept, r_value, p_value, std_err = linregress(log_L, log_dw)
        alpha = -slope
        c = np.exp(intercept)

        logging.info("")
        logging.info(f"Fitted scaling: Δω*(L) ∝ L^({slope:.3f})")
        logging.info(f"Exponent α = {alpha:.3f} ± {std_err:.3f}")
        logging.info(f"Coefficient c = {c:.4e}")
        logging.info(f"R² = {r_value**2:.4f}, p = {p_value:.4e}")
        logging.info("")

        # Interpret result
        if alpha > 0.7:
            verdict = "CLASSICAL (α ≈ 1, Rayleigh limit)"
        elif 0.4 <= alpha <= 0.6:
            verdict = "SUPER-RESOLUTION (α ≈ 1/2)"
        else:
            verdict = f"INTERMEDIATE (α ≈ {alpha:.2f})"

        logging.info(f"VERDICT: {verdict}")

        return {
            'thresholds': thresholds,
            'alpha': float(alpha),
            'alpha_err': float(std_err),
            'c': float(c),
            'r_squared': float(r_value**2),
            'p_value': float(p_value),
            'verdict': verdict
        }
    else:
        logging.info("")
        logging.info("VERDICT: INCONCLUSIVE (insufficient threshold data)")
        return {
            'thresholds': thresholds,
            'verdict': "INCONCLUSIVE"
        }


# ============================================================================
# Plotting
# ============================================================================

def plot_results(results: List[Dict], scaling_analysis: Dict, config: Config):
    """Generate summary plots"""

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 1: Success rate vs Δω for each L
    ax = axes[0]
    L_values = sorted(set(r['L'] for r in results))
    colors = plt.cm.viridis(np.linspace(0, 1, len(L_values)))

    for L, color in zip(L_values, colors):
        L_results = [r for r in results if r['L'] == L]
        L_results.sort(key=lambda x: x['delta_omega'])

        delta_omegas = [r['delta_omega'] for r in L_results]
        success_rates = [r['success_rate'] for r in L_results]

        ax.plot(delta_omegas, success_rates, 'o-', color=color, label=f'L={L}', markersize=6)

    ax.axhline(0.5, color='red', linestyle='--', alpha=0.5, label='50% threshold')
    ax.set_xscale('log')
    ax.set_xlabel('Mode separation Δω (cycles/sample)')
    ax.set_ylabel('P(resolve | Δω, L)')
    ax.set_title('Resolution Detection Rate vs Frequency Separation')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Scaling law
    ax = axes[1]
    has_data = False
    if 'alpha' in scaling_analysis:
        thresholds = scaling_analysis['thresholds']
        if len(thresholds) >= 2:
            has_data = True
            Ls = np.array([t[0] for t in thresholds])
            dws = np.array([t[1] for t in thresholds])

            ax.loglog(Ls, dws, 'o', markersize=10, label='Measured Δω*_0.5')

            # Fit line
            alpha = scaling_analysis['alpha']
            c = scaling_analysis['c']
            L_fit = np.linspace(Ls.min(), Ls.max(), 100)
            dw_fit = c * L_fit**(-alpha)
            ax.loglog(L_fit, dw_fit, '--', label=f'Fit: L^({-alpha:.2f})')

            # Reference lines
            dw_rayleigh = (c * Ls[0]**(-1.0)) * L_fit**(-1.0)
            dw_super = (c * Ls[0]**(-0.5)) * L_fit**(-0.5)
            ax.loglog(L_fit, dw_rayleigh, ':', alpha=0.5, label='Rayleigh (α=1)')
            ax.loglog(L_fit, dw_super, ':', alpha=0.5, label='Super-res (α=0.5)')

    if not has_data:
        # Add text explaining why no data
        ax.text(0.5, 0.5, 'No threshold data\n(all curves at 0% or 100%)',
                ha='center', va='center', transform=ax.transAxes, fontsize=12)

    ax.set_xlabel('Sequence length L')
    ax.set_ylabel('Resolution threshold Δω*_0.5')
    ax.set_title('Scaling Law: Δω*(L) ∝ L^(-α)')
    if has_data:
        ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save
    figpath = config.figure_dir / 'T6D2_v3_resolution_scaling.png'
    plt.savefig(figpath, dpi=300, bbox_inches='tight')
    logging.info(f"Figure saved: {figpath}")
    plt.close()


# ============================================================================
# Main
# ============================================================================

def main():
    config = Config()

    # Run experiment
    results = run_resolution_scaling_experiment(config)

    # Save raw data
    output_file = config.output_dir / 'T6D2_v3_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logging.info(f"\nData saved: {output_file}")

    # Scaling analysis
    scaling_analysis = extract_threshold_scaling(results)

    # Save scaling data
    scaling_file = config.output_dir / 'T6D2_v3_scaling.json'
    with open(scaling_file, 'w') as f:
        json.dump(scaling_analysis, f, indent=2)

    # Plot
    logging.info("")
    logging.info("Generating figures...")
    plot_results(results, scaling_analysis, config)

    # Final summary
    logging.info("")
    logging.info("="*70)
    logging.info("T6-D2 v3 COMPLETE")
    logging.info("="*70)
    logging.info(f"Configurations tested: {len(results)}")
    logging.info(f"Hypothesis: L ≳ c/√(Δω) (super-resolution)")
    if 'verdict' in scaling_analysis:
        logging.info(f"VERDICT: {scaling_analysis['verdict']}")
    logging.info("="*70)


if __name__ == '__main__':
    main()
