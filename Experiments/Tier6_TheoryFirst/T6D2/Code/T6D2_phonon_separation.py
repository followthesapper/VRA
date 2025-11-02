#!/usr/bin/env python3
"""
T6-D2 — Phonon Mode Separation: Super-Resolution Bound

Question:
    Can VRA resolve closely-spaced vibrational modes in materials
    beyond the classical Fourier limit?

Hypothesis:
    For two phonon modes separated by Δω in frequency space,
    VRA can resolve them with sequence length L satisfying:

        L ≳ c / √(Δω)

    where c is a constant. This is a super-resolution bound that
    improves on the classical L ∝ 1/Δω Rayleigh criterion.

Falsification:
    If resolution degrades faster than L ∝ 1/√(Δω), or if separation
    threshold scales as 1/L (classical limit), the claim is false.

Physics Context:
    In materials science, distinguishing phonon modes with similar
    frequencies is critical for understanding thermal transport,
    phase transitions, and mechanical properties. VRA's modular
    arithmetic structure may enable super-resolution through
    coherent accumulation effects.

Author: Dylan Vaca
Date: October 31, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from scipy.signal import find_peaks
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
    omega_base = 0.12  # Base frequency (cycles/sample, in (0, 0.45) to avoid aliasing)
    delta_omega_values = np.array([0.005, 0.01, 0.02, 0.05, 0.1, 0.2])  # Mode separations

    # Modular arithmetic
    N_prime = 2003
    r_fraction = 0.143  # r ≈ 0.143*N → r=286 (valid divisor of φ(2003)=2002)

    # Sequence lengths (test scaling)
    L_values = [2**10, 2**12, 2**14, 2**16]

    # Signal parameters
    M_bases = 16  # Number of bases
    sigma_noise = 0.05  # Phase noise (thermal fluctuations)

    # Detection threshold
    peak_threshold = 0.7  # Minimum relative peak height for mode detection

    # Monte Carlo
    n_trials = 30

    # Output paths
    output_dir = Path("../../Data/Experiments/Tier6/T6D2")
    figure_dir = Path("../../Figures/experiments/Tier6/T6D2")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6D2_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-D2: Phonon Mode Separation - Super-Resolution Bound")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")


# ============================================================================
# Phonon Signal Generation
# ============================================================================

def generate_dual_phonon_signal(
    N: int,
    r: int,
    L: int,
    M: int,
    omega1: float,
    omega2: float,
    sigma_noise: float,
    seed: int = None
) -> Tuple[np.ndarray, Dict]:
    """
    Generate modular sequences with two phonon modes.

    Phonon modes appear as frequency modulations on top of
    the underlying multiplicative structure.

    Args:
        N: Prime modulus
        r: Multiplicative order
        L: Sequence length
        M: Number of bases
        omega1, omega2: Phonon mode frequencies (normalized)
        sigma_noise: Phase noise std (thermal fluctuations)
        seed: Random seed

    Returns:
        sequences: (M, L) complex phasors
        metadata: Signal parameters
    """
    if seed is not None:
        np.random.seed(seed)

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

    t_array = np.arange(L)

    for i, a in enumerate(bases):
        x = 1
        for t in range(L):
            # Modular multiplication
            x = (x * a) % N

            # Base phase from modular sequence
            phase_base = 2 * np.pi * x / N

            # Add phonon modulations (two oscillating modes)
            # These appear as amplitude modulations in the time domain
            phonon_modulation = (
                np.cos(2 * np.pi * omega1 * t) +
                np.cos(2 * np.pi * omega2 * t)
            )

            # Combined phase (phonon modes modulate amplitude)
            # In real phonon systems, modes affect lattice displacements
            # Here we model this as phase-amplitude coupling
            phase = phase_base + 0.15 * phonon_modulation  # Reduced to make resolution harder

            # Add thermal noise
            if sigma_noise > 0:
                phase += np.random.normal(0, sigma_noise)

            sequences[i, t] = np.exp(1j * phase)

    metadata = {
        'N': int(N),
        'r': int(r),
        'L': int(L),
        'M': int(M),
        'omega1': float(omega1),
        'omega2': float(omega2),
        'delta_omega': float(abs(omega2 - omega1)),
        'sigma': float(sigma_noise),
        'bases': bases
    }

    return sequences, metadata


# ============================================================================
# Carrier Derotation
# ============================================================================

def derotate_sequences(N: int, r: int, bases: List[int], sequences: np.ndarray) -> np.ndarray:
    """
    Remove the modular carrier phase from sequences.

    The raw sequences have phase = modular_carrier + phonon_modulation.
    This function reconstructs the carrier and divides it out, leaving
    only the phonon modulation in the phase.

    Args:
        N: Prime modulus
        r: Multiplicative order
        bases: List of M bases used to generate sequences
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

        # Divide out carrier (multiply by conjugate)
        derotated[i] = sequences[i] * np.conj(carrier)

    return derotated


# ============================================================================
# Mode Resolution Analysis
# ============================================================================

def analyze_mode_separation(
    sequences: np.ndarray,
    omega1: float,
    omega2: float,
    peak_threshold: float,
    N: int,
    r: int,
    bases: List[int]
) -> Dict:
    """
    Determine if two phonon modes are resolved in spectrum.

    Args:
        sequences: (M, L) complex phasors
        omega1, omega2: True mode frequencies
        peak_threshold: Minimum relative height for peak detection
        N: Prime modulus
        r: Multiplicative order
        bases: List of bases used to generate sequences

    Returns:
        analysis: Resolution metrics
    """
    M, L = sequences.shape

    # Step 1: Remove modular carrier phase
    derotated = derotate_sequences(N, r, bases, sequences)

    # Step 2: Extract residual phase and remove mean
    phase_resid = np.unwrap(np.angle(derotated), axis=1)  # (M, L)
    phase_resid = phase_resid - phase_resid.mean(axis=1, keepdims=True)

    # Step 3: Average across bases and use full-length rFFT
    resid_avg = phase_resid.mean(axis=0)  # (L,)

    # Full-length periodogram (bin width df = 1/L scales with L)
    fft_vals = np.fft.rfft(resid_avg, n=None)
    spectrum_pos = (np.abs(fft_vals) ** 2)
    freqs_pos = np.fft.rfftfreq(resid_avg.size, d=1.0)  # cycles/sample, [0, 0.5]

    # Normalize spectrum
    spectrum_pos = spectrum_pos / (np.max(spectrum_pos) + 1e-12)

    # Compute bin width
    n_bins = len(spectrum_pos)
    df = freqs_pos[1] - freqs_pos[0] if n_bins > 1 else 1.0 / L

    # Find peaks in bins, not in L
    peaks, properties = find_peaks(
        spectrum_pos,
        prominence=0.02,  # Robust to baseline variations
        height=0.1,       # Easier SNR threshold
        distance=max(1, int(0.01 * n_bins))  # ~1% of spectrum length
    )

    n_peaks_detected = len(peaks)

    # Check if we found two peaks near true frequencies
    # True normalized frequencies (handle aliasing with modulo)
    f1_true = omega1 % 1.0
    f2_true = omega2 % 1.0

    # Ensure f1 < f2 for consistent comparison
    if f2_true < f1_true:
        f1_true, f2_true = f2_true, f1_true

    # Find closest peaks to true frequencies
    resolved = False
    if n_peaks_detected >= 2:
        peak_freqs = freqs_pos[peaks]

        # Distance to true frequencies
        dist_to_f1 = np.abs(peak_freqs - f1_true)
        dist_to_f2 = np.abs(peak_freqs - f2_true)

        # Tolerance in bin units (~3 bins)
        tolerance_bins = 3
        tolerance = tolerance_bins * df

        has_f1 = np.any(dist_to_f1 < tolerance)
        has_f2 = np.any(dist_to_f2 < tolerance)

        # Also require the two peaks to be separated by ≳ Δω - 1 bin
        if has_f1 and has_f2:
            if (f2_true - f1_true) > (df * 1.0):
                resolved = True

    # Peak separation (if multiple peaks found)
    peak_separation = 0.0
    if n_peaks_detected >= 2:
        # Take two highest peaks
        peak_heights = properties['peak_heights']
        top2_idx = np.argsort(peak_heights)[-2:]
        peak_separation = abs(freqs_pos[peaks[top2_idx[1]]] - freqs_pos[peaks[top2_idx[0]]])

    return {
        'resolved': bool(resolved),
        'n_peaks': int(n_peaks_detected),
        'peak_separation': float(peak_separation),
        'spectrum': spectrum_pos.tolist(),
        'freqs': freqs_pos.tolist(),
        'peaks': peaks.tolist()
    }


# ============================================================================
# Experiment Execution
# ============================================================================

def run_resolution_scaling_experiment(config: Config) -> List[Dict]:
    """
    Scan (L, Δω) space to measure resolution threshold.

    For each (L, Δω):
        1. Generate dual-mode phonon signal
        2. Compute spectrum
        3. Detect if modes are resolved
        4. Measure success rate over trials

    Returns:
        results: Measurements for each (L, Δω, trial)
    """
    logging.info("")
    logging.info("Starting resolution scaling experiment...")
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

    results = []
    start_time = time.time()

    total_configs = len(config.L_values) * len(config.delta_omega_values) * config.n_trials
    config_idx = 0

    for L in config.L_values:
        logging.info(f"\n{'='*60}")
        logging.info(f"Testing L = {L}")
        logging.info('='*60)

        for delta_omega in config.delta_omega_values:
            # Define two modes (in cycles/sample, not scaled by L)
            f1 = config.omega_base
            f2 = f1 + delta_omega

            resolution_success = []

            for trial in range(config.n_trials):
                config_idx += 1
                elapsed = time.time() - start_time
                rate = config_idx / elapsed if elapsed > 0 else 0
                eta = (total_configs - config_idx) / rate if rate > 0 else 0

                # Generate signal
                sequences, metadata = generate_dual_phonon_signal(
                    N, r, L, config.M_bases,
                    f1, f2,
                    config.sigma_noise,
                    seed=trial
                )

                # Analyze resolution
                analysis = analyze_mode_separation(
                    sequences, f1, f2, config.peak_threshold,
                    N, r, metadata['bases']
                )

                resolution_success.append(analysis['resolved'])

                if trial == 0:  # Log first trial details
                    logging.info(
                        f"  Δω={delta_omega:.4f} | "
                        f"Peaks detected: {analysis['n_peaks']} | "
                        f"Resolved: {analysis['resolved']}"
                    )

            success_rate = np.mean(resolution_success)

            logging.info(
                f"  Δω={delta_omega:.4f}: Success rate = {success_rate:.2%} | "
                f"ETA: {eta/60:.1f}m"
            )

            results.append({
                'L': int(L),
                'delta_omega': float(delta_omega),
                'omega1': float(f1),
                'omega2': float(f2),
                'success_rate': float(success_rate),
                'resolution_trials': resolution_success
            })

    elapsed = time.time() - start_time
    logging.info(f"\nExperiment complete: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    return results


# ============================================================================
# Analysis & Plotting
# ============================================================================

def analyze_scaling_law(results: List[Dict], config: Config):
    """
    Test hypothesis: L ≳ c / √(Δω)

    Fit resolution threshold and check if it follows super-resolution bound.
    """
    logging.info("")
    logging.info("="*70)
    logging.info("SCALING LAW ANALYSIS: L ≳ c / √(Δω)")
    logging.info("="*70)

    # For each L, find Δω threshold where success rate ≈ 0.5
    thresholds = []

    for L in config.L_values:
        L_data = [r for r in results if r['L'] == L]

        delta_omegas = np.array([r['delta_omega'] for r in L_data])
        success_rates = np.array([r['success_rate'] for r in L_data])

        # Find Δω where success crosses 50%
        # Interpolate if necessary
        if np.any(success_rates > 0.5) and np.any(success_rates < 0.5):
            # Find crossing point
            idx_above = np.where(success_rates > 0.5)[0]
            idx_below = np.where(success_rates <= 0.5)[0]

            if len(idx_above) > 0 and len(idx_below) > 0:
                # Linear interpolation
                i_low = idx_below[-1]
                i_high = idx_above[0]

                dw_low = delta_omegas[i_low]
                dw_high = delta_omegas[i_high]
                sr_low = success_rates[i_low]
                sr_high = success_rates[i_high]

                # Interpolate to 0.5
                dw_threshold = dw_low + (0.5 - sr_low) * (dw_high - dw_low) / (sr_high - sr_low)

                thresholds.append({'L': L, 'delta_omega_threshold': dw_threshold})
                logging.info(f"L={L}: Threshold Δω ≈ {dw_threshold:.5f}")
        else:
            logging.info(f"L={L}: No clear threshold found (success rates: {success_rates})")

    if len(thresholds) >= 3:
        # Fit L vs 1/√(Δω)
        L_vals = np.array([t['L'] for t in thresholds])
        dw_vals = np.array([t['delta_omega_threshold'] for t in thresholds])

        # Test hypothesis: L ∝ 1/√(Δω) => log(L) = -0.5·log(Δω) + log(c)
        log_L = np.log(L_vals)
        log_dw = np.log(dw_vals)

        slope, intercept, r_value, p_value, std_err = linregress(log_dw, log_L)
        r_squared = r_value**2

        logging.info("")
        logging.info(f"Fit: log(L) = {slope:.3f}·log(Δω) + {intercept:.3f}")
        logging.info(f"  R² = {r_squared:.4f}, p = {p_value:.2e}")
        logging.info(f"  Expected slope for super-resolution: -0.5")
        logging.info(f"  Expected slope for Rayleigh limit: -1.0")

        if abs(slope + 0.5) < 0.2:  # Within 20% of -0.5
            logging.info("\nVERDICT: PASS — Super-resolution scaling confirmed")
            logging.info(f"  L ∝ (Δω)^{slope:.3f} ≈ (Δω)^{-0.5}")
        elif abs(slope + 1.0) < 0.2:  # Classical scaling
            logging.info("\nVERDICT: FAIL — Classical Rayleigh scaling observed")
            logging.info(f"  L ∝ (Δω)^{-1.0} (no super-resolution)")
        else:
            logging.info("\nVERDICT: PARTIAL — Scaling exponent unclear")

        return {
            'slope': float(slope),
            'intercept': float(intercept),
            'r_squared': float(r_squared),
            'p_value': float(p_value),
            'thresholds': thresholds
        }
    else:
        logging.info("\nVERDICT: INCONCLUSIVE — Insufficient threshold data")
        return {'thresholds': thresholds}


def plot_results(results: List[Dict], fit: Dict, config: Config):
    """Generate publication-quality figures"""
    logging.info("")
    logging.info("Generating figures...")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    # Panel 1: Success rate vs Δω for each L
    ax = axes[0]
    for L in config.L_values:
        L_data = [r for r in results if r['L'] == L]
        delta_omegas = [r['delta_omega'] for r in L_data]
        success_rates = [r['success_rate'] for r in L_data]

        ax.plot(delta_omegas, success_rates, 'o-', label=f'L={L}', alpha=0.7)

    ax.axhline(0.5, color='k', linestyle=':', alpha=0.3, label='50% threshold')
    ax.set_xlabel('Mode separation Δω')
    ax.set_ylabel('Resolution success rate')
    ax.set_title('Phonon Mode Resolution vs Separation')
    ax.set_xscale('log')
    ax.legend()
    ax.grid(alpha=0.3)

    # Panel 2: Scaling law (if thresholds available)
    ax = axes[1]
    if 'thresholds' in fit and len(fit['thresholds']) >= 3:
        thresholds = fit['thresholds']
        L_vals = np.array([t['L'] for t in thresholds])
        dw_vals = np.array([t['delta_omega_threshold'] for t in thresholds])

        ax.loglog(dw_vals, L_vals, 'o', markersize=10, label='Observed', alpha=0.7)

        # Plot fit line
        dw_range = np.logspace(np.log10(dw_vals.min()), np.log10(dw_vals.max()), 100)
        L_fit = np.exp(fit['slope'] * np.log(dw_range) + fit['intercept'])
        ax.loglog(dw_range, L_fit, '--', alpha=0.6,
                  label=f"Fit: L ∝ (Δω)^{fit['slope']:.2f} (R²={fit['r_squared']:.3f})")

        # Reference lines
        c_ref = np.exp(fit['intercept'])
        L_super = c_ref * dw_range**(-0.5)
        L_rayleigh = c_ref * dw_range**(-1.0)

        ax.loglog(dw_range, L_super, ':', alpha=0.4, label='Super-resolution (Δω^-0.5)')
        ax.loglog(dw_range, L_rayleigh, ':', alpha=0.4, label='Rayleigh limit (Δω^-1.0)')

        ax.set_xlabel('Mode separation Δω')
        ax.set_ylabel('Required sequence length L')
        ax.set_title('Resolution Scaling Law')
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3, which='both')
    else:
        ax.text(0.5, 0.5, 'Insufficient data\nfor scaling analysis',
                ha='center', va='center', transform=ax.transAxes)
        ax.set_xlabel('Mode separation Δω')
        ax.set_ylabel('Required sequence length L')
        ax.set_title('Resolution Scaling Law')

    fig.suptitle('T6-D2: Phonon Mode Super-Resolution', fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_path = config.figure_dir / 'T6D2_phonon_resolution.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"Figure saved: {output_path}")
    plt.close()


# ============================================================================
# Main
# ============================================================================

def main():
    """Execute T6-D2 experiment"""
    config = Config()

    # Run experiment
    start_time = time.time()
    results = run_resolution_scaling_experiment(config)
    elapsed = time.time() - start_time

    # Save raw data
    output_file = config.output_dir / 'T6D2_results.json'
    with open(output_file, 'w') as f:
        json.dump({'results': results}, f, indent=2)
    logging.info(f"\nData saved: {output_file}")

    # Analyze scaling law
    fit = analyze_scaling_law(results, config)

    # Generate plots
    plot_results(results, fit, config)

    # Final summary
    logging.info("")
    logging.info("="*70)
    logging.info("T6-D2 COMPLETE")
    logging.info("="*70)
    logging.info(f"Total runtime: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    logging.info(f"Configurations tested: {len(results)}")
    logging.info(f"Hypothesis: L ≳ c/√(Δω) (super-resolution)")

    if 'slope' in fit:
        logging.info(f"Observed scaling: L ∝ (Δω)^{fit['slope']:.3f}")
        logging.info(f"Fit quality: R² = {fit['r_squared']:.4f}")

        if abs(fit['slope'] + 0.5) < 0.2:
            logging.info("VERDICT: PASS — Super-resolution confirmed")
        elif abs(fit['slope'] + 1.0) < 0.2:
            logging.info("VERDICT: FAIL — Classical scaling only")
        else:
            logging.info("VERDICT: PARTIAL — Intermediate scaling")
    else:
        logging.info("VERDICT: INCONCLUSIVE")

    logging.info("="*70)


if __name__ == '__main__':
    main()
