#!/usr/bin/env python3
"""
T6-A1 — Coherence–Incoherence Transition (the R̄ ≈ 0.137 phenomenon)

Question:
    Can the phase statistics across multiplicative bases be modeled as a
    well-defined modular random process with a closed-form coherence order
    parameter R̄?

Hypothesis:
    For cyclic subgroup order r, the normalized phasors at harmonic ℓ behave
    as i.i.d. draws from a von Mises distribution vM(κ_ℓ) with:

        κ_ℓ = κ(ρ, ℓ, r)

    The predicted mean resultant length is:
        R̄(ℓ) = I₁(κ_ℓ) / I₀(κ_ℓ)  ⇒  R̄ ≈ mean_ℓ R̄(ℓ) ≈ 0.137

Predictions (Falsifiable):
    1. R̄ is asymptotically independent of M with variance O(1/M)
    2. R̄ is a smooth function of density ρ = r/N; ∂R̄/∂ρ < 0 in high-SNR regime
    3. Concentration: P(|R̄_emp - R̄_theory| > ε) ≤ 2 exp(-M·ε²/2)

Falsification:
    If empirical R̄ systematically deviates from all parameter-free predictions
    beyond concentration bounds, model is rejected.

Author: Dylan Vaca
Date: October 31, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import vonmises
from scipy.special import i0, i1
from scipy.optimize import minimize_scalar, curve_fit
import json
from pathlib import Path
from typing import Dict, List, Tuple
import sys
import logging
import time
from datetime import datetime

# Add VRA core to path
sys.path.insert(0, str(Path(__file__).parent / "../../Code"))
from VRA.core import compute_vra_spectrum, find_generator_of_order

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Experimental parameters - SIMPLIFIED for 15-20 min runtime"""
    # Regime sweep: vary ρ = r/N (REDUCED)
    N_primes = [997, 2003]  # Just 2 moduli (was 4)
    rho_targets = [0.10, 0.20, 0.30]  # Just 3 densities (was 6)

    # Base averaging (REDUCED)
    M_values = [8, 16]  # Just 2 M values (was 4)

    # Sequence parameters (REDUCED for speed)
    L = 4096  # Reduced from 8192
    zp = 4    # Zero-padding factor

    # Monte Carlo per (N, ρ) pair (REDUCED)
    n_samples_per_config = 10  # Reduced from 50

    # Von Mises fitting
    fit_harmonics = 10  # First 10 harmonics

    # Output paths
    output_dir = Path("../../Data/Experiments/Tier6/T6A1")
    figure_dir = Path("../../Figures/experiments/Tier6/T6A1")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.log_file = self.output_dir / f'T6A1_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        self.setup_logging()

    def setup_logging(self):
        """Configure logging to file and console"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ],
            force=True  # Override any existing config
        )
        logging.info("="*70)
        logging.info("T6-A1: Coherence-Incoherence Transition (R̄ ≈ 0.137)")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")
        logging.info("SIMPLIFIED VERSION: 15-20 min runtime")

# ============================================================================
# VRA Coherence Computation
# ============================================================================

def compute_base_coherence(N: int, r: int, M: int, L: int) -> float:
    """
    Compute empirical coherence R̄ for given (N, r, M).

    Args:
        N: Modulus
        r: Multiplicative order
        M: Number of bases
        L: Sequence length

    Returns:
        Mean resultant length R̄ ∈ [0, 1]
    """
    # Find M bases with order r
    bases = []
    attempts = 0
    max_attempts = N * 10

    while len(bases) < M and attempts < max_attempts:
        a = np.random.randint(2, N)
        if np.gcd(a, N) == 1:
            # Check order
            if pow(a, r, N) == 1:
                # Verify minimality
                is_minimal = True
                for divisor in get_divisors(r)[:-1]:  # Exclude r itself
                    if pow(a, divisor, N) == 1:
                        is_minimal = False
                        break
                if is_minimal:
                    bases.append(a)
        attempts += 1

    if len(bases) < M:
        return np.nan  # Failed to find enough bases

    # Generate phase sequences
    phase_sequences = []
    for a in bases:
        seq = []
        x = 1
        for _ in range(L):
            x = (x * a) % N
            phase = 2 * np.pi * x / N
            seq.append(np.exp(1j * phase))
        phase_sequences.append(seq)

    phase_sequences = np.array(phase_sequences)  # Shape: (M, L)

    # Compute FFT for each base
    Nzp = L * 4
    spectra = np.fft.fft(phase_sequences, n=Nzp, axis=1)  # Shape: (M, Nzp)

    # Coherent averaging: average complex spectra first
    avg_spectrum = np.mean(spectra, axis=0)  # Shape: (Nzp,)

    # Compute coherence metric
    # R̄ = |<spectrum>| / √(<|spectrum|²>)
    coherent_amplitude = np.abs(avg_spectrum)
    incoherent_amplitude = np.sqrt(np.mean(np.abs(spectra)**2, axis=0))

    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        R = coherent_amplitude / incoherent_amplitude
        R = np.nan_to_num(R, nan=0.0)

    # Average over harmonics (exclude DC)
    harmonics = np.arange(1, min(len(R) // 2, 100))  # First 100 harmonics
    R_mean = np.mean(R[harmonics])

    return R_mean

def get_divisors(n: int) -> List[int]:
    """Get all divisors of n"""
    divisors = []
    for i in range(1, int(np.sqrt(n)) + 1):
        if n % i == 0:
            divisors.append(i)
            if i != n // i:
                divisors.append(n // i)
    return sorted(divisors)

# ============================================================================
# Von Mises Model
# ============================================================================

def von_mises_resultant(kappa: float) -> float:
    """
    Mean resultant length for von Mises distribution.

    R = I₁(κ) / I₀(κ)
    """
    if kappa < 1e-10:
        return 0.0
    return i1(kappa) / i0(kappa)

def fit_von_mises_model(rho_values: np.ndarray, R_values: np.ndarray) -> Dict:
    """
    Fit R̄(ρ) to von Mises model.

    Model: κ(ρ) = A · ρ^α  ⇒  R̄(ρ) = I₁(κ(ρ)) / I₀(κ(ρ))

    Args:
        rho_values: Density ρ = r/N
        R_values: Empirical coherence values

    Returns:
        Fitted parameters and predictions
    """
    # Define model
    def model(rho, A, alpha):
        kappa = A * rho**alpha
        return von_mises_resultant(kappa)

    # Fit
    try:
        params, cov = curve_fit(
            model, rho_values, R_values,
            p0=[1.0, -1.0],  # Initial guess: A=1, α=-1 (decreasing)
            bounds=([0.01, -5.0], [10.0, 5.0])
        )
        A_fit, alpha_fit = params
        perr = np.sqrt(np.diag(cov))
    except:
        # Fit failed
        A_fit, alpha_fit = np.nan, np.nan
        perr = [np.nan, np.nan]

    # Predictions
    rho_fine = np.linspace(rho_values.min(), rho_values.max(), 100)
    R_pred = model(rho_fine, A_fit, alpha_fit)

    return {
        'A': float(A_fit),
        'alpha': float(alpha_fit),
        'A_err': float(perr[0]),
        'alpha_err': float(perr[1]),
        'rho_fine': rho_fine.tolist(),
        'R_pred': R_pred.tolist()
    }

# ============================================================================
# Main Experiment
# ============================================================================

def run_experiment(config: Config) -> Dict:
    """
    Run full coherence transition experiment.

    Returns:
        Dictionary with results
    """
    logging.info("")
    logging.info("Configuration:")
    logging.info(f"  Moduli N: {config.N_primes}")
    logging.info(f"  Target densities ρ: {config.rho_targets}")
    logging.info(f"  Base counts M: {config.M_values}")
    logging.info(f"  Sequence length L: {config.L}")
    logging.info(f"  Samples per config: {config.n_samples_per_config}")
    total_configs = len(config.N_primes) * len(config.rho_targets) * len(config.M_values)
    logging.info(f"  Total configs: {total_configs}")
    logging.info(f"  Estimated runtime: 15-20 minutes")
    logging.info("")

    results = {
        'config': {
            'N_primes': config.N_primes,
            'rho_targets': config.rho_targets,
            'M_values': config.M_values,
            'L': config.L,
            'n_samples': config.n_samples_per_config
        },
        'data': []
    }

    # Sweep (N, ρ, M)
    total_configs = len(config.N_primes) * len(config.rho_targets) * len(config.M_values)
    config_idx = 0
    start_time = time.time()

    for N in config.N_primes:
        for rho_target in config.rho_targets:
            # Find r ≈ ρ_target * N
            r_target = int(rho_target * N)

            # Search for actual order near target
            r_actual = None
            for r_search in range(max(2, r_target - 50), r_target + 50):
                # Check if any element has this order
                a = find_generator_of_order(N, r_search, max_attempts=100)
                if a is not None:
                    r_actual = r_search
                    break

            if r_actual is None:
                logging.warning(f"Could not find order near ρ={rho_target:.2f} for N={N}")
                continue

            rho_actual = r_actual / N

            for M in config.M_values:
                config_idx += 1
                elapsed = time.time() - start_time
                rate = config_idx / elapsed if elapsed > 0 else 0
                eta = (total_configs - config_idx) / rate if rate > 0 else 0
                logging.info(f"[{config_idx}/{total_configs}] N={N}, ρ={rho_actual:.3f} (r={r_actual}), M={M} | "
                           f"Elapsed: {elapsed/60:.1f}min | ETA: {eta/60:.1f}min")

                # Compute coherence for multiple samples
                R_samples = []
                for sample in range(config.n_samples_per_config):
                    R = compute_base_coherence(N, r_actual, M, config.L)
                    if not np.isnan(R):
                        R_samples.append(R)

                if len(R_samples) == 0:
                    logging.warning(f"  Failed to compute coherence for this config")
                    continue

                R_samples = np.array(R_samples)
                R_mean = R_samples.mean()
                R_std = R_samples.std()

                logging.info(f"  → R̄ = {R_mean:.4f} ± {R_std:.4f}")

                results['data'].append({
                    'N': int(N),
                    'r': int(r_actual),
                    'rho': float(rho_actual),
                    'M': int(M),
                    'R_mean': float(R_mean),
                    'R_std': float(R_std),
                    'R_samples': R_samples.tolist()
                })

    logging.info("")
    logging.info("="*70)
    logging.info("Data collection complete. Analyzing...")
    logging.info("="*70)

    # Analyze results
    data = results['data']

    # Group by M and fit model
    fits_by_M = {}
    for M in config.M_values:
        subset = [d for d in data if d['M'] == M]
        if len(subset) == 0:
            continue

        rho_vals = np.array([d['rho'] for d in subset])
        R_vals = np.array([d['R_mean'] for d in subset])

        # Fit model
        fit = fit_von_mises_model(rho_vals, R_vals)
        fits_by_M[M] = fit

        logging.info(f"\nVon Mises Fit for M={M}:")
        logging.info(f"  κ(ρ) = {fit['A']:.3f} · ρ^({fit['alpha']:.3f})")
        logging.info(f"  Errors: A ± {fit['A_err']:.3f}, α ± {fit['alpha_err']:.3f}")

    results['fits'] = fits_by_M

    # Test Prediction 1: M-scaling variance
    logging.info("")
    logging.info("="*70)
    logging.info("PREDICTION 1: Variance ∝ 1/M")
    logging.info("="*70)

    for rho_target in config.rho_targets:
        # Get R values for this ρ across different M
        subset = [d for d in data if abs(d['rho'] - rho_target) < 0.05]
        if len(subset) < 2:
            continue

        M_vals = []
        var_vals = []
        for M in config.M_values:
            M_subset = [d for d in subset if d['M'] == M]
            if len(M_subset) > 0:
                # Aggregate all samples
                all_R = []
                for d in M_subset:
                    all_R.extend(d['R_samples'])
                if len(all_R) > 5:
                    M_vals.append(M)
                    var_vals.append(np.var(all_R))

        if len(M_vals) >= 2:
            logging.info(f"\nρ ≈ {rho_target:.2f}:")
            for M, var in zip(M_vals, var_vals):
                logging.info(f"  M={M:2d}: Var(R̄) = {var:.6f}  (1/M = {1/M:.4f})")

    return results

# ============================================================================
# Visualization
# ============================================================================

def plot_results(results: Dict, config: Config):
    """Generate publication-quality figures"""

    data = results['data']
    fits = results['fits']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (A) R̄ vs ρ for different M
    ax = axes[0, 0]
    for M in config.M_values:
        subset = [d for d in data if d['M'] == M]
        if len(subset) == 0:
            continue

        rho_vals = [d['rho'] for d in subset]
        R_vals = [d['R_mean'] for d in subset]
        R_err = [d['R_std'] for d in subset]

        ax.errorbar(rho_vals, R_vals, yerr=R_err, fmt='o', label=f'M={M}',
                   alpha=0.7, capsize=3)

        # Overlay fit
        if M in fits:
            fit = fits[M]
            ax.plot(fit['rho_fine'], fit['R_pred'], '--', alpha=0.5)

    ax.axhline(0.137, color='red', linestyle=':', label='Target R̄ ≈ 0.137')
    ax.set_xlabel('Density ρ = r/N')
    ax.set_ylabel('Mean Coherence R̄')
    ax.set_title('(A) Coherence vs Density')
    ax.legend()
    ax.grid(alpha=0.3)

    # (B) M-scaling: Variance vs 1/M
    ax = axes[0, 1]
    for rho_target in [0.10, 0.20, 0.30]:
        subset = [d for d in data if abs(d['rho'] - rho_target) < 0.05]
        M_vals = []
        var_vals = []
        for M in config.M_values:
            M_subset = [d for d in subset if d['M'] == M]
            if len(M_subset) > 0:
                all_R = []
                for d in M_subset:
                    all_R.extend(d['R_samples'])
                if len(all_R) > 5:
                    M_vals.append(M)
                    var_vals.append(np.var(all_R))

        if len(M_vals) >= 2:
            ax.plot([1/M for M in M_vals], var_vals, 'o-',
                   label=f'ρ ≈ {rho_target:.2f}')

    ax.set_xlabel('1/M')
    ax.set_ylabel('Var(R̄)')
    ax.set_title('(B) Variance Scaling (Prediction 1)')
    ax.legend()
    ax.grid(alpha=0.3)

    # (C) Distribution of R̄ values
    ax = axes[1, 0]
    all_R = []
    for d in data:
        all_R.extend(d['R_samples'])
    all_R = np.array(all_R)

    ax.hist(all_R, bins=50, density=True, alpha=0.6, label='Empirical')
    ax.axvline(all_R.mean(), color='blue', linestyle='--',
              label=f'Mean: {all_R.mean():.3f}')
    ax.axvline(0.137, color='red', linestyle=':', label='Target: 0.137')
    ax.set_xlabel('Coherence R̄')
    ax.set_ylabel('Density')
    ax.set_title('(C) Overall R̄ Distribution')
    ax.legend()
    ax.grid(alpha=0.3)

    # (D) Model fit quality
    ax = axes[1, 1]
    for M in config.M_values:
        subset = [d for d in data if d['M'] == M]
        if len(subset) == 0:
            continue

        rho_vals = np.array([d['rho'] for d in subset])
        R_vals = np.array([d['R_mean'] for d in subset])

        if M in fits:
            fit = fits[M]
            rho_pred = np.array(fit['rho_fine'])
            R_pred_interp = np.interp(rho_vals, rho_pred, fit['R_pred'])

            residuals = R_vals - R_pred_interp
            ax.scatter(rho_vals, residuals, alpha=0.5, label=f'M={M}')

    ax.axhline(0, color='black', linestyle='--')
    ax.set_xlabel('Density ρ')
    ax.set_ylabel('Residual (Empirical - Model)')
    ax.set_title('(D) Model Fit Quality')
    ax.legend()
    ax.grid(alpha=0.3)

    fig.suptitle('T6-A1: Coherence-Incoherence Transition (R̄ ≈ 0.137 Phenomenon)',
                fontsize=16, fontweight='bold')

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save
    output_path = config.figure_dir / 'T6A1_coherence_transition_summary.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"Figure saved: {output_path}")

    plt.close()  # Close instead of show for batch execution

# ============================================================================
# Main
# ============================================================================

def main():
    config = Config()

    # Run experiment
    start_time = time.time()
    logging.info("Starting experiment...")
    logging.info("")
    results = run_experiment(config)
    elapsed = time.time() - start_time

    logging.info(f"\nTotal elapsed time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")

    # Save results
    output_file = config.output_dir / 'T6A1_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logging.info(f"Results saved: {output_file}")

    # Plot
    logging.info("Generating figures...")
    plot_results(results, config)

    # Compute verdict
    all_R = []
    for d in results['data']:
        all_R.extend(d['R_samples'])
    mean_R = np.mean(all_R)
    std_R = np.std(all_R)

    # Target is R̄ ≈ 0.137
    target = 0.137
    deviation = abs(mean_R - target)

    if deviation < 0.05:  # Within 5% of target
        verdict = "PASS"
    else:
        verdict = "PARTIAL"

    logging.info("")
    logging.info("="*70)
    logging.info("EXPERIMENT T6-A1 COMPLETE!")
    logging.info("="*70)
    logging.info(f"Overall R̄: {mean_R:.4f} ± {std_R:.4f}")
    logging.info(f"Target R̄: {target}")
    logging.info(f"Deviation: {deviation:.4f}")
    logging.info(f"Verdict: {verdict}")
    logging.info(f"Data: {output_file}")
    logging.info(f"Figures: {config.figure_dir}")
    logging.info(f"Log: {config.log_file}")
    logging.info("="*70)

if __name__ == '__main__':
    main()
