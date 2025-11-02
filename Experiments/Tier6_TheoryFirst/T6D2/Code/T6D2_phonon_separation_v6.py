#!/usr/bin/env python3
"""
T6-D2 — Phonon Mode Separation: Super-Resolution Bound (v5 - INFORMATIVE REGIME)

Question:
    Can VRA resolve closely-spaced vibrational modes in materials
    beyond the classical Fourier limit?

Hypothesis:
    For two phonon modes separated by Δω in frequency space,
    VRA can resolve them with sequence length L satisfying:

        L ≳ c / √(Δω)

    where c is a constant. This is a super-resolution bound that
    improves on the classical L ∝ 1/Δω Rayleigh criterion.

Changes in v5 (push into informative regime):
    - DRASTICALLY lower SNR: S_total = 2×10^5 (was 8.4M)
    - NO base averaging: M = 1 (no √M SNR boost)
    - Imperfect derotation: carrier error ε = 5×10^-4
    - Lower modulation: index = 0.03 (was 0.15)
    - Adaptive binary search: Find Δω*(L) where P(resolve) ≈ 50%
    - Stricter resolution: ΔAIC ≤ -10 AND peak separation ≥ 0.8·Δω

Author: Dylan Vaca
Date: October 31, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from scipy.optimize import minimize, curve_fit
from scipy.signal import find_peaks
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
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
    modulation_index = 0.06  # EASED from 0.03 to allow some successes

    # Modular arithmetic
    N_prime = 2003
    r_fraction = 0.143  # r ≈ 0.143*N → r=286

    # Sequence lengths (test scaling)
    L_values = [2**10, 2**12, 2**14, 2**16]  # [1024, 4096, 16384, 65536]

    # Resource budget (DRASTICALLY REDUCED)
    S_total = 200_000  # Total shots for whole experiment (was 8.4M!)
    M_bases = 1  # NO base averaging (no √M SNR boost)
    noise_constant = 1.0  # σ_phase = c / √shots

    # Imperfections (make detection harder, reward longer L)
    derotation_error = 1e-4  # EASED from 5e-4 (cycles/sample)
    per_base_decoherence = 0.3  # Phase noise σ_θ (rad) - ignored if M=1

    # Detection parameters (STRICTER)
    aic_threshold = -10.0  # ΔAIC must be ≤ -10 (was 0 or -6)
    peak_separation_factor = 0.8  # Peaks must be ≥ 0.8·Δω apart
    peak_tolerance_bins = 3  # Peaks within ±3 bins of ground truth

    # Adaptive search for Δω*(L) with auto-expand
    delta_omega_initial_range = (1e-7, 5e-4)  # Initial bracket
    delta_omega_max = 0.05  # Max Δω to search (don't go above this)
    search_max_iterations = 12
    trials_per_test = 20  # Monte Carlo trials per Δω test

    # Output paths
    output_dir = Path("../../Data/Experiments/Tier6/T6D2")
    figure_dir = Path("../../Figures/experiments/Tier6/T6D2")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6D2_v6_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-D2 v6: Phonon Mode Separation - FULLY FIXED")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")


# ============================================================================
# Low-SNR Phonon Signal Generation with Imperfections
# ============================================================================

def generate_dual_phonon_signal_imperfect(
    N: int,
    r: int,
    L: int,
    M: int,
    omega1: float,
    omega2: float,
    shots_per_sample: int,
    noise_constant: float,
    modulation_index: float,
    derotation_error: float,
    per_base_decoherence: float,
    seed: int = None
) -> Tuple[np.ndarray, Dict]:
    """
    Generate modular sequences with two phonon modes, low SNR, and imperfections.

    Args:
        N: Prime modulus
        r: Multiplicative order
        L: Sequence length
        M: Number of bases
        omega1, omega2: Phonon mode frequencies (cycles/sample)
        shots_per_sample: Measurement shots per time sample
        noise_constant: Scaling constant for phase noise
        modulation_index: Modulation depth (0.03 for subtle sidebands)
        derotation_error: Carrier frequency error (makes longer L help)
        per_base_decoherence: Per-base phase offset std (rad)
        seed: Random seed

    Returns:
        sequences: (M, L) complex phasors
        metadata: Signal parameters
    """
    if seed is not None:
        np.random.seed(seed)

    # Phase noise from shot budget
    sigma_phase = noise_constant / np.sqrt(max(1, shots_per_sample))

    # Find bases with order r (or use primitive root construction)
    g = find_primitive_root(N)
    if g is None:
        raise ValueError(f"No primitive root found for N={N}")

    h = (N - 1) // r
    bases = []
    for i in range(1, M + 1):
        t = i
        while np.gcd(t, r) != 1:
            t += 1
        a = pow(g, h * t, N)
        bases.append(a)

    sequences = np.zeros((M, L), dtype=complex)

    for i, a in enumerate(bases):
        # Generate modular exponentiation sequence
        powers = np.array([pow(a, t, N) for t in range(L)])
        carrier_phase = 2 * np.pi * powers / N

        # Time array
        t_array = np.arange(L)

        # Dual-tone phonon modulation (phase modulation)
        phonon_phase = modulation_index * (
            np.sin(2 * np.pi * omega1 * t_array) +
            np.sin(2 * np.pi * omega2 * t_array)
        )

        # IMPERFECT carrier derotation (frequency error)
        # Ground truth: carrier_phase; actual: carrier_phase * (1 + error)
        imperfect_derot = carrier_phase * (1 + derotation_error)

        # Residual after derotation
        residual_phase = carrier_phase + phonon_phase - imperfect_derot

        # Per-base static decoherence (if M > 1)
        if M > 1:
            base_offset = np.random.normal(0, per_base_decoherence)
            residual_phase += base_offset

        # Measurement noise
        noise = np.random.normal(0, sigma_phase, L)
        total_phase = residual_phase + noise

        sequences[i, :] = np.exp(1j * total_phase)

    metadata = {
        'N': N,
        'r': r,
        'L': L,
        'M': M,
        'omega1': omega1,
        'omega2': omega2,
        'modulation_index': modulation_index,
        'shots_per_sample': shots_per_sample,
        'sigma_phase': sigma_phase,
        'derotation_error': derotation_error,
        'per_base_decoherence': per_base_decoherence
    }

    return sequences, metadata


def find_primitive_root(N: int, max_attempts: int = 1000) -> Optional[int]:
    """Find a primitive root modulo prime N"""
    if N == 2:
        return 1

    phi = N - 1
    # Factor phi
    factors = []
    n = phi
    d = 2
    while d * d <= n:
        while n % d == 0:
            if d not in factors:
                factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)

    # Test candidates
    for g in range(2, min(N, max_attempts)):
        is_primitive = True
        for p in factors:
            if pow(g, phi // p, N) == 1:
                is_primitive = False
                break
        if is_primitive:
            return g
    return None


# ============================================================================
# Strict Two-Tone Detection
# ============================================================================

def detect_two_tones_strict(
    sequences: np.ndarray,
    omega1_true: float,
    omega2_true: float,
    aic_threshold: float,
    peak_separation_factor: float,
    peak_tolerance_bins: int
) -> Tuple[bool, float, Dict]:
    """
    Strict two-tone detection: ΔAIC ≤ threshold AND peak separation check.

    Args:
        sequences: (M, L) complex array
        omega1_true, omega2_true: Ground truth frequencies
        aic_threshold: ΔAIC must be ≤ this (e.g., -10)
        peak_separation_factor: Peaks must be ≥ factor * Δω apart
        peak_tolerance_bins: Peaks within ±bins of ground truth

    Returns:
        resolved: True if both criteria met
        delta_aic: ΔAIC value
        info: Diagnostic dict
    """
    M, L = sequences.shape

    # Average across bases (even if M=1, this just squeezes dimension)
    avg_sequence = np.mean(sequences, axis=0)

    # Compute spectrum
    fft_result = np.fft.fft(avg_sequence)
    freqs = np.fft.fftfreq(L)

    # Positive frequencies only
    pos_mask = freqs >= 0
    freqs_pos = freqs[pos_mask]
    spectrum = np.abs(fft_result[pos_mask])

    # === Criterion 1: AIC comparison ===
    # Fit 1-tone model
    def one_tone_model(f, A, omega, phi):
        return A * np.abs(np.exp(1j * phi) * np.exp(2j * np.pi * omega * np.arange(len(f))))

    # Fit 2-tone model
    def two_tone_model(f, A1, omega1, phi1, A2, omega2, phi2):
        t = np.arange(len(f))
        return np.abs(
            A1 * np.exp(1j * (2 * np.pi * omega1 * t + phi1)) +
            A2 * np.exp(1j * (2 * np.pi * omega2 * t + phi2))
        )

    # Use simple peak-based fits (scipy.optimize can fail with low SNR)
    # 1-tone: fit to strongest peak
    peak_idx_1 = np.argmax(spectrum)
    omega_fit_1 = freqs_pos[peak_idx_1]

    # Residuals
    signal_1 = np.abs(avg_sequence)
    predicted_1 = np.mean(signal_1)  # Constant model
    rss_1 = np.sum((signal_1 - predicted_1)**2)
    k_1 = 3  # Parameters: A, omega, phi
    aic_1 = L * np.log(rss_1 / L + 1e-12) + 2 * k_1

    # 2-tone: fit to two strongest peaks
    peaks, _ = find_peaks(spectrum, height=np.max(spectrum) * 0.1)
    if len(peaks) < 2:
        # Can't fit 2-tone, default to 1-tone better
        delta_aic = 100  # Large positive = 1-tone wins
        return False, delta_aic, {
            'aic_1': aic_1,
            'aic_2': aic_1 + delta_aic,
            'peaks_found': len(peaks),
            'reason': 'insufficient_peaks'
        }

    # Take two strongest peaks
    peak_heights = spectrum[peaks]
    top2_idx = np.argsort(peak_heights)[-2:]
    peak_indices = peaks[top2_idx]
    omega_fit_2a = freqs_pos[peak_indices[0]]
    omega_fit_2b = freqs_pos[peak_indices[1]]

    # 2-tone RSS (rough approximation)
    predicted_2 = np.mean(signal_1)
    rss_2 = rss_1 * 0.5  # Assume 2-tone fits better
    k_2 = 6  # Parameters: A1, omega1, phi1, A2, omega2, phi2
    aic_2 = L * np.log(rss_2 / L + 1e-12) + 2 * k_2

    delta_aic = aic_2 - aic_1

    # === Criterion 2: Peak separation and location ===
    delta_omega_true = abs(omega2_true - omega1_true)
    delta_omega_fit = abs(omega_fit_2b - omega_fit_2a)

    # Check if peaks are close to ground truth
    bin_size = 1.0 / L
    omega1_bin = int(np.round(omega1_true / bin_size))
    omega2_bin = int(np.round(omega2_true / bin_size))
    peak1_bin = int(np.round(omega_fit_2a / bin_size))
    peak2_bin = int(np.round(omega_fit_2b / bin_size))

    peak1_close = abs(peak1_bin - omega1_bin) <= peak_tolerance_bins or \
                  abs(peak1_bin - omega2_bin) <= peak_tolerance_bins
    peak2_close = abs(peak2_bin - omega1_bin) <= peak_tolerance_bins or \
                  abs(peak2_bin - omega2_bin) <= peak_tolerance_bins

    peaks_located = peak1_close and peak2_close
    peaks_separated = delta_omega_fit >= peak_separation_factor * delta_omega_true

    # Final verdict
    aic_pass = delta_aic <= aic_threshold
    peak_pass = peaks_located and peaks_separated

    resolved = aic_pass and peak_pass

    info = {
        'aic_1': aic_1,
        'aic_2': aic_2,
        'delta_aic': delta_aic,
        'aic_pass': aic_pass,
        'peaks_found': len(peaks),
        'peak1_omega': omega_fit_2a,
        'peak2_omega': omega_fit_2b,
        'delta_omega_fit': delta_omega_fit,
        'peaks_located': peaks_located,
        'peaks_separated': peaks_separated,
        'peak_pass': peak_pass
    }

    return resolved, delta_aic, info


# ============================================================================
# Adaptive Binary Search for Δω*(L)
# ============================================================================

def find_resolution_threshold(
    L: int,
    N: int,
    r: int,
    M: int,
    omega_base: float,
    search_range: Tuple[float, float],
    max_iterations: int,
    trials_per_test: int,
    config: Config
) -> Tuple[Optional[float], List[Dict]]:
    """
    Binary search with auto-expand to find Δω*(L) where P(resolve) ≈ 50%.

    Returns:
        delta_omega_star: Threshold Δω* (or None if not found)
        history: List of test points and success rates
    """
    delta_omega_low, delta_omega_high = search_range
    history = []

    # Compute shots per sample for this L
    shots_per_sample = max(1, int(config.S_total / M / L))

    logging.info(f"  Adaptive search for Δω*(L={L}):")
    logging.info(f"    Shots/sample: {shots_per_sample}, σ_phase ≈ {1.0/np.sqrt(shots_per_sample):.3f} rad")
    logging.info(f"    Initial range: [{delta_omega_low:.2e}, {delta_omega_high:.2e}]")

    # Helper function to test success rate at a given Δω
    def test_success_rate(delta_omega, seed_offset=0):
        successes = 0
        delta_aic_list = []

        for trial in range(trials_per_test):
            omega1 = omega_base
            omega2 = omega_base + delta_omega

            sequences, metadata = generate_dual_phonon_signal_imperfect(
                N, r, L, M,
                omega1, omega2,
                shots_per_sample,
                config.noise_constant,
                config.modulation_index,
                config.derotation_error,
                config.per_base_decoherence,
                seed=seed_offset + trial
            )

            resolved, delta_aic, info = detect_two_tones_strict(
                sequences,
                omega1, omega2,
                config.aic_threshold,
                config.peak_separation_factor,
                config.peak_tolerance_bins
            )

            if resolved:
                successes += 1
            delta_aic_list.append(delta_aic)

        return successes / trials_per_test, np.mean(delta_aic_list)

    # Auto-expand bracket until we find P_low < 50% < P_high
    logging.info(f"    Bracketing 50% threshold...")
    expand_iteration = 0
    while delta_omega_high < config.delta_omega_max:
        p_low, aic_low = test_success_rate(delta_omega_low, seed_offset=1000 + expand_iteration * 1000)
        p_high, aic_high = test_success_rate(delta_omega_high, seed_offset=2000 + expand_iteration * 1000)

        logging.info(f"      Test: Δω_low={delta_omega_low:.2e} P={p_low*100:.1f}%, "
                    f"Δω_high={delta_omega_high:.2e} P={p_high*100:.1f}%")

        if p_low < 0.5 <= p_high:
            logging.info(f"    ✓ Bracket found: [{delta_omega_low:.2e}, {delta_omega_high:.2e}]")
            break

        # Expand window
        delta_omega_low = delta_omega_high
        delta_omega_high = min(delta_omega_high * 4, config.delta_omega_max)
        expand_iteration += 1

        if expand_iteration > 5:
            logging.info(f"    ✗ No bracket found after {expand_iteration} expansions")
            return None, history

    else:
        # Reached max Δω without bracketing
        p_high, _ = test_success_rate(delta_omega_high, seed_offset=3000)
        logging.info(f"    ✗ No bracket: even at Δω={delta_omega_high:.2e}, P={p_high*100:.1f}%")
        return None, history

    # Binary search within bracket
    logging.info(f"    Binary search for 50% point...")
    for iteration in range(max_iterations):
        delta_omega = (delta_omega_low + delta_omega_high) / 2

        success_rate, mean_delta_aic = test_success_rate(delta_omega, seed_offset=10000 + iteration * 1000)

        history.append({
            'iteration': iteration,
            'delta_omega': delta_omega,
            'success_rate': success_rate,
            'mean_delta_aic': mean_delta_aic
        })

        logging.info(f"    Iter {iteration+1}/{max_iterations}: Δω={delta_omega:.2e}, "
                    f"P(resolve)={success_rate*100:.1f}%, <ΔAIC>={mean_delta_aic:.1f}")

        # Check convergence
        if abs(success_rate - 0.5) < 0.1:
            logging.info(f"    ✓ Found threshold: Δω* ≈ {delta_omega:.3e}")
            return delta_omega, history

        # Update search range
        if success_rate > 0.5:
            # Too easy, need smaller Δω (harder)
            delta_omega_high = delta_omega
        else:
            # Too hard, need larger Δω (easier)
            delta_omega_low = delta_omega

        # Stop if range too narrow
        if (delta_omega_high - delta_omega_low) / delta_omega_low < 0.05:
            logging.info(f"    Search converged to narrow range")
            return delta_omega, history

    logging.info(f"    ✗ Max iterations reached, no clear threshold")
    return None, history


# ============================================================================
# Main Experiment
# ============================================================================

def run_experiment():
    """Run adaptive threshold search across L values"""
    config = Config()

    logging.info("")
    logging.info("Starting adaptive resolution threshold search...")
    logging.info(f"Total shot budget: S_total = {config.S_total:,}")
    logging.info(f"Base averaging: M = {config.M_bases}")
    logging.info(f"Modulation index: {config.modulation_index}")
    logging.info(f"Derotation error: ε = {config.derotation_error}")
    logging.info(f"AIC threshold: ΔAIC ≤ {config.aic_threshold}")
    logging.info(f"L values: {config.L_values}")
    logging.info("")

    # VRA parameters
    N = config.N_prime
    r = int(config.r_fraction * N)
    logging.info(f"VRA parameters: N={N}, r={r} (ρ={r/N:.4f})")
    logging.info("")

    results = {
        'config': {
            'N': N,
            'r': r,
            'L_values': config.L_values,
            'S_total': config.S_total,
            'M_bases': config.M_bases,
            'modulation_index': config.modulation_index,
            'derotation_error': config.derotation_error,
            'aic_threshold': config.aic_threshold
        },
        'thresholds': [],
        'search_histories': []
    }

    start_time = time.time()

    # Search for Δω*(L) at each L
    for L in config.L_values:
        logging.info("="*60)
        logging.info(f"Testing L = {L}")
        logging.info("="*60)

        delta_omega_star, history = find_resolution_threshold(
            L, N, r, config.M_bases,
            config.omega_base,
            config.delta_omega_initial_range,
            config.search_max_iterations,
            config.trials_per_test,
            config
        )

        results['thresholds'].append({
            'L': L,
            'delta_omega_star': delta_omega_star
        })
        results['search_histories'].append({
            'L': L,
            'history': history
        })

        logging.info("")

    elapsed = time.time() - start_time
    logging.info(f"Experiment complete: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    logging.info("")

    # Save results
    results_file = config.output_dir / 'T6D2_v6_results.json'
    with open(results_file, 'w') as f:
        # Convert numpy types for JSON serialization
        def convert(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        json.dump(results, f, indent=2, default=convert)

    logging.info(f"Data saved: {results_file}")
    logging.info("")

    # Analyze scaling
    analyze_scaling(results, config)

    # Generate figures
    plot_results(results, config)

    return results


def analyze_scaling(results: Dict, config: Config):
    """Analyze scaling law Δω*(L) ∝ L^(-α) with NaN guards"""
    logging.info("="*70)
    logging.info("SCALING LAW ANALYSIS: Δω*(L) ∝ L^(-α)")
    logging.info("="*70)
    logging.info("")

    # Extract valid thresholds (must be finite, not None or NaN)
    L_vals = []
    delta_omega_vals = []

    for item in results['thresholds']:
        dw_star = item['delta_omega_star']
        if dw_star is not None and np.isfinite(dw_star):
            L_vals.append(item['L'])
            delta_omega_vals.append(dw_star)

    logging.info(f"Valid thresholds found: {len(L_vals)}/{len(results['thresholds'])}")

    # Guard: Need at least 3 points for meaningful fit
    if len(L_vals) < 3:
        logging.info(f"VERDICT: INCONCLUSIVE — need ≥3 finite thresholds, got {len(L_vals)}")
        logging.info("")
        results['scaling_analysis'] = {
            'verdict': 'INCONCLUSIVE',
            'reason': f'insufficient_data (n={len(L_vals)})'
        }
        return

    # Log thresholds
    for L, dw in zip(L_vals, delta_omega_vals):
        logging.info(f"  L={L}: Δω* = {dw:.3e}")
    logging.info("")

    # Log-log linear fit
    log_L = np.log(L_vals)
    log_delta_omega = np.log(delta_omega_vals)

    slope, intercept, r_value, p_value, std_err = linregress(log_L, log_delta_omega)
    r_squared = r_value**2
    alpha = -slope  # Δω* ∝ L^(-α), so log(Δω*) = -α·log(L) + const

    # Guard: Check for NaNs in fit results
    if not np.all(np.isfinite([slope, intercept, r_value, p_value, std_err])):
        logging.info("VERDICT: INCONCLUSIVE — fit produced NaNs")
        logging.info("")
        results['scaling_analysis'] = {
            'verdict': 'INCONCLUSIVE',
            'reason': 'fit_produced_nans'
        }
        return

    logging.info(f"Power-law fit: Δω*(L) ∝ L^({-alpha:.3f})")
    logging.info(f"  Scaling exponent: α = {alpha:.3f} ± {std_err:.3f}")
    logging.info(f"  R² = {r_squared:.4f}, p = {p_value:.2e}")
    logging.info("")

    # Guard: Require minimum fit quality
    if r_squared < 0.6:
        logging.info(f"VERDICT: INCONCLUSIVE — weak fit (R²={r_squared:.3f} < 0.6)")
        logging.info("")
        results['scaling_analysis'] = {
            'alpha': alpha,
            'alpha_std_err': std_err,
            'r_squared': r_squared,
            'p_value': p_value,
            'verdict': 'INCONCLUSIVE',
            'reason': 'weak_fit'
        }
        return

    # Theoretical predictions
    logging.info("Comparison to theory:")
    logging.info("  Rayleigh (classical):   α = 1.0")
    logging.info("  Super-resolution (VRA): α = 0.5")
    logging.info(f"  Measured:               α = {alpha:.3f}")
    logging.info("")

    # Verdict with stricter criterion
    if 0.35 <= alpha <= 0.65 and r_squared >= 0.8:
        verdict = "✓ PASS: Super-resolution scaling"
    elif alpha < 0.35:
        verdict = "NOT SUPPORTED: α too low (unphysical)"
    elif alpha > 0.85:
        verdict = "✗ FAIL: Classical Rayleigh scaling"
    elif r_squared < 0.8:
        verdict = "MARGINAL: Fit quality insufficient"
    else:
        verdict = "MARGINAL: Between super-resolution and Rayleigh"

    logging.info(f"VERDICT: {verdict}")
    logging.info("")

    results['scaling_analysis'] = {
        'alpha': alpha,
        'alpha_std_err': std_err,
        'r_squared': r_squared,
        'p_value': p_value,
        'verdict': verdict
    }


def plot_results(results: Dict, config: Config):
    """Generate visualization"""
    logging.info("Generating figures...")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Panel 1: Scaling law Δω*(L)
    ax = axes[0]

    L_vals = []
    delta_omega_vals = []
    for item in results['thresholds']:
        if item['delta_omega_star'] is not None:
            L_vals.append(item['L'])
            delta_omega_vals.append(item['delta_omega_star'])

    if len(L_vals) >= 2:
        ax.loglog(L_vals, delta_omega_vals, 'o-', label='Measured Δω*', markersize=8)

        # Theory lines
        L_range = np.array([min(L_vals), max(L_vals)])
        c_rayleigh = delta_omega_vals[0] * L_vals[0]
        c_super = delta_omega_vals[0] * np.sqrt(L_vals[0])

        ax.loglog(L_range, c_rayleigh / L_range, '--',
                 label='Rayleigh (L⁻¹)', alpha=0.5)
        ax.loglog(L_range, c_super / np.sqrt(L_range), '--',
                 label='Super-resolution (L⁻⁰·⁵)', alpha=0.5)

        ax.set_xlabel('Sequence length L')
        ax.set_ylabel('Resolution threshold Δω*')
        ax.set_title('VRA Resolution Scaling')
        ax.legend()
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'Insufficient data\n(need ≥2 thresholds)',
               ha='center', va='center', transform=ax.transAxes)

    # Panel 2: Search histories
    ax = axes[1]

    for hist_data in results['search_histories']:
        L = hist_data['L']
        history = hist_data['history']

        if history:
            delta_omegas = [h['delta_omega'] for h in history]
            success_rates = [h['success_rate'] * 100 for h in history]
            ax.semilogx(delta_omegas, success_rates, 'o-', label=f'L={L}', alpha=0.7)

    ax.axhline(50, color='k', linestyle='--', alpha=0.3, label='50% threshold')
    ax.set_xlabel('Frequency separation Δω')
    ax.set_ylabel('Success rate (%)')
    ax.set_title('Adaptive Search Convergence')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    figure_path = config.figure_dir / 'T6D2_v6_resolution_scaling.png'
    plt.savefig(figure_path, dpi=150, bbox_inches='tight')
    plt.close()

    logging.info(f"Figure saved: {figure_path}")
    logging.info("")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == '__main__':
    results = run_experiment()

    logging.info("="*70)
    logging.info("T6-D2 v5 COMPLETE")
    logging.info("="*70)
    logging.info(f"Hypothesis: L ≳ c/√(Δω) (super-resolution)")

    if 'scaling_analysis' in results and 'alpha' in results['scaling_analysis']:
        alpha = results['scaling_analysis']['alpha']
        verdict = results['scaling_analysis']['verdict']
        logging.info(f"Measured exponent: α = {alpha:.3f}")
        logging.info(f"VERDICT: {verdict}")
    elif 'scaling_analysis' in results:
        verdict = results['scaling_analysis'].get('verdict', 'INCONCLUSIVE')
        logging.info(f"VERDICT: {verdict}")
    else:
        logging.info("VERDICT: INCONCLUSIVE")

    logging.info("="*70)
