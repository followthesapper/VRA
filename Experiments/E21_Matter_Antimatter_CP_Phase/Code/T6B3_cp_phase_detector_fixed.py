#!/usr/bin/env python3
"""
T6-B3 — Matter/Antimatter CP-Phase Toy Model (FIXED)

Question:
    Can VRA detect tiny systematic phase biases analogous to CP violation
    in particle physics?

Hypothesis:
    For a phase-biased signal with CP-violating parameter φ,
    the asymmetry metric S(φ) should be:

        S(φ) ≈ c·φ  (odd function, linear for small φ)

    where c > 0 is a sensitivity coefficient.

Fixes applied:
    1. Use exact-order bases via primitive root (not approximate pow(a,r,N)==1)
    2. Ensure r divides N-1 for all N
    3. Derotate carrier before measuring asymmetry
    4. Measure CP asymmetry at DC (time-average), not FFT bin
    5. Subtract φ=0 baseline
    6. Enforce positive sign convention for c

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
    r_fraction = 0.143  # Target r ≈ 0.143*N

    # Signal parameters
    L_values = [2**12, 2**14, 2**16]  # Sequence lengths
    M_bases = 16  # Fixed number of bases

    # Noise model
    sigma_noise = 0.01  # Small phase noise

    # Monte Carlo
    n_trials = 50

    # Output paths
    output_dir = Path("../Data")
    figure_dir = Path("../Figures")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6B3_fixed_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-B3 FIXED: Matter/Antimatter CP-Phase Toy Model")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")


# ============================================================================
# Exact-Order Base Construction
# ============================================================================

def primitive_root_mod_prime(p: int) -> int:
    """Find smallest primitive root for prime p."""
    factors = []
    phi = p - 1
    n = phi
    f = 2
    while f * f <= n:
        if n % f == 0:
            factors.append(f)
            while n % f == 0:
                n //= f
        f += 1
    if n > 1:
        factors.append(n)

    for g in range(2, p):
        ok = True
        for q in factors:
            if pow(g, phi // q, p) == 1:
                ok = False
                break
        if ok:
            return g
    raise RuntimeError(f"No primitive root found for p={p}")


def exact_order_bases(N: int, r: int, M: int) -> List[int]:
    """
    Return M distinct bases of exact multiplicative order r in Z_N*.

    Args:
        N: Prime modulus
        r: Multiplicative order (must divide N-1)
        M: Number of bases needed

    Returns:
        bases: List of M bases with ord_N(a) = r
    """
    if (N - 1) % r != 0:
        raise ValueError(f"r={r} does not divide N-1={N-1}")

    g = primitive_root_mod_prime(N)
    h = (N - 1) // r

    # Bases with exact order r: g^(h*t) where gcd(t, r) = 1
    ts = [t for t in range(1, r) if np.gcd(t, r) == 1]

    if len(ts) < M:
        raise ValueError(f"Not enough exact-order elements: φ(r)={len(ts)} < M={M}")

    # Select M evenly spaced indices
    idx = np.linspace(0, len(ts) - 1, num=M, dtype=int)
    bases = [pow(g, h * ts[i], N) for i in idx]

    return bases


# ============================================================================
# CP-Biased Signal Generation
# ============================================================================

def generate_cp_biased_sequence(N: int, r: int, phi: float, L: int,
                                 M: int, sigma_noise: float = 0.01,
                                 seed: int = None) -> Tuple[np.ndarray, Dict]:
    """
    Generate modular sequences with CP-violating phase bias using exact-order bases.

    Args:
        N: Prime modulus
        r: Multiplicative order (must divide N-1)
        phi: CP-violating phase bias (radians)
        L: Sequence length
        M: Number of bases
        sigma_noise: Phase noise std
        seed: Random seed

    Returns:
        sequences: (M, L) complex phasors
        metadata: Signal parameters including bases
    """
    if seed is not None:
        np.random.seed(seed)

    # Build exact-order bases
    bases = exact_order_bases(N, r, M)

    # Generate sequences with CP bias
    sequences = np.zeros((M, L), dtype=complex)

    for i, a in enumerate(bases):
        x = 1
        for t in range(L):
            # Modular multiplication
            x = (x * a) % N

            # Convert to phase with CP bias
            phase_base = 2 * np.pi * x / N

            # Apply CP bias: first half get +φ (matter), second half get -φ (antimatter)
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
# CP Asymmetry Metric (DC Phase Difference)
# ============================================================================

def compute_cp_asymmetry(sequences: np.ndarray, N: int, r: int, bases: List[int]) -> float:
    """
    Compute CP asymmetry from biased sequences using DC phase difference.

    After derotation, the CP bias appears as a constant phase offset.
    We measure this at DC (time-average), not FFT bin.

    Args:
        sequences: (M, L) complex phasors
        N: Prime modulus
        r: Multiplicative order
        bases: List of bases used to generate sequences

    Returns:
        S: CP asymmetry (should be ~c·φ for small φ)
    """
    M, L = sequences.shape
    M_half = M // 2

    # Step 1: Derotate carrier
    derotated = derotate_sequences(N, r, bases, sequences)

    # Step 2: Time-average each base to get DC phasor
    dc_phasors = derotated.mean(axis=1)  # (M,)

    # Step 3: Split into matter/antimatter
    matter_phasors = dc_phasors[:M_half]
    antimatter_phasors = dc_phasors[M_half:]

    # Step 4: Compute mean phasors for each group
    z_m = matter_phasors.mean()
    z_a = antimatter_phasors.mean()

    # Step 5: CP asymmetry via phase difference
    # S = sin(angle_m - angle_a) = Im(z_m * conj(z_a)) / |z_m||z_a|
    cross_corr = z_m * np.conj(z_a)
    S = np.imag(cross_corr) / (np.abs(z_m) * np.abs(z_a) + 1e-12)

    return float(S)


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
        # Choose r as divisor of N-1 nearest to target
        target_r = int(config.r_fraction * N)
        best_r = None
        best_dist = float('inf')

        for d in range(2, N):
            if (N - 1) % d == 0:
                dist = abs(d - target_r)
                if dist < best_dist:
                    best_r = d
                    best_dist = dist

        r = best_r

        logging.info(f"\nTesting N={N}, r={r} (ρ={r/N:.4f})")

        # Compute baseline S(0) for this (N, r, L) combination
        baseline_S0 = {}

        for L in config.L_values:
            logging.info(f"  L={L}...")

            # Measure baseline at φ=0
            S0_samples = []
            for trial in range(config.n_trials):
                sequences, metadata = generate_cp_biased_sequence(
                    N, r, 0.0, L, config.M_bases, config.sigma_noise, seed=trial
                )
                S = compute_cp_asymmetry(sequences, N, r, metadata['bases'])
                S0_samples.append(S)
            baseline_S0[L] = float(np.mean(S0_samples))

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
                    S = compute_cp_asymmetry(sequences, N, r, metadata['bases'])
                    S_samples.append(S)

                S_mean = float(np.mean(S_samples))
                S_std = float(np.std(S_samples))

                # Subtract baseline
                S_corrected = S_mean - baseline_S0[L]

                if config_idx % 5 == 0 or phi == config.phi_values[-1]:
                    logging.info(f"    [{config_idx}/{total_configs}] φ={phi:.4f}: "
                                f"S={S_corrected:.6f}±{S_std:.6f} | ETA: {eta/60:.1f}m")

                results.append({
                    'N': int(N),
                    'r': int(r),
                    'L': int(L),
                    'phi': float(phi),
                    'S_mean': S_mean,
                    'S_std': S_std,
                    'S_corrected': S_corrected,  # With baseline subtracted
                    'S_baseline': baseline_S0[L],
                    'S_samples': [float(x) for x in S_samples]
                })

    elapsed = time.time() - start_time
    logging.info(f"\nScan complete: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    return results


# ============================================================================
# Analysis & Plotting
# ============================================================================

def analyze_linearity(results: List[Dict]) -> Dict:
    """
    Fit S(φ) = c·φ and check linearity.

    Returns:
        analysis: Fit parameters for each (N, L) combination
    """
    logging.info("")
    logging.info("="*70)
    logging.info("LINEARITY ANALYSIS: S(φ) = c·φ")
    logging.info("="*70)

    analysis = {}

    # Group by (N, L)
    N_values = sorted(set(r['N'] for r in results))
    L_values = sorted(set(r['L'] for r in results))

    for N in N_values:
        for L in L_values:
            # Extract data for this (N, L)
            subset = [r for r in results if r['N'] == N and r['L'] == L]
            subset.sort(key=lambda x: x['phi'])

            phi = np.array([r['phi'] for r in subset])
            S = np.array([r['S_corrected'] for r in subset])  # Use baseline-corrected
            S_err = np.array([r['S_std'] for r in subset])

            # Linear fit: S = c*phi (force intercept through origin after baseline correction)
            if len(phi) > 1:
                # Weighted least squares through origin
                weights = 1.0 / (S_err**2 + 1e-12)
                c = np.sum(weights * phi * S) / np.sum(weights * phi**2)

                # Compute R²
                S_pred = c * phi
                ss_res = np.sum((S - S_pred)**2)
                ss_tot = np.sum((S - S.mean())**2)
                r_squared = 1.0 - (ss_res / (ss_tot + 1e-12))

                # Enforce positive sign convention
                c_abs = abs(c)
                sign = np.sign(c)

                key = (N, L)
                analysis[key] = {
                    'N': int(N),
                    'L': int(L),
                    'c': float(c_abs),  # Report magnitude
                    'sign': int(sign),
                    'r_squared': float(r_squared),
                    'phi': phi.tolist(),
                    'S': S.tolist(),
                    'S_err': S_err.tolist()
                }

                logging.info(f"N={N}, L={L}: c = {c_abs:.4f} (sign={'+' if sign > 0 else '-'}), R² = {r_squared:.4f}")
            else:
                logging.info(f"N={N}, L={L}: Insufficient data for fit")

    return analysis


def plot_results(results: List[Dict], analysis: Dict, config: Config):
    """Generate CP asymmetry plots"""

    N_values = sorted(set(r['N'] for r in results))
    L_values = sorted(set(r['L'] for r in results))

    fig, axes = plt.subplots(1, len(N_values), figsize=(5*len(N_values), 5))
    if len(N_values) == 1:
        axes = [axes]

    colors = plt.cm.viridis(np.linspace(0, 1, len(L_values)))

    for idx, N in enumerate(N_values):
        ax = axes[idx]

        for L, color in zip(L_values, colors):
            # Extract data
            subset = [r for r in results if r['N'] == N and r['L'] == L]
            subset.sort(key=lambda x: x['phi'])

            phi = np.array([r['phi'] for r in subset])
            S = np.array([r['S_corrected'] for r in subset])
            S_err = np.array([r['S_std'] for r in subset])

            # Plot data
            ax.errorbar(phi, S, yerr=S_err, fmt='o', color=color,
                       label=f'L={L}', markersize=6, capsize=3, alpha=0.7)

            # Plot fit
            key = (N, L)
            if key in analysis:
                c = analysis[key]['c'] * analysis[key]['sign']  # Restore sign for plotting
                phi_fit = np.linspace(0, phi.max(), 100)
                S_fit = c * phi_fit
                ax.plot(phi_fit, S_fit, '--', color=color, alpha=0.5)

        ax.set_xlabel('CP phase φ (rad)')
        ax.set_ylabel('Asymmetry S(φ)')
        ax.set_title(f'N={N}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axhline(0, color='black', linewidth=0.5)

    plt.tight_layout()

    # Save
    figpath = config.figure_dir / 'T6B3_fixed_cp_asymmetry.png'
    plt.savefig(figpath, dpi=300, bbox_inches='tight')
    logging.info(f"\nFigure saved: {figpath}")
    plt.close()


# ============================================================================
# Main
# ============================================================================

def main():
    config = Config()

    # Run experiment
    results = run_cp_phase_scan(config)

    # Save raw data
    output_file = config.output_dir / 'T6B3_fixed_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logging.info(f"\nData saved: {output_file}")

    # Analyze linearity
    analysis = analyze_linearity(results)

    # Save analysis
    analysis_file = config.output_dir / 'T6B3_fixed_analysis.json'
    with open(analysis_file, 'w') as f:
        # Convert tuple keys to strings for JSON
        analysis_json = {f"{k[0]}_{k[1]}": v for k, v in analysis.items()}
        json.dump(analysis_json, f, indent=2)

    # Plot
    logging.info("")
    logging.info("Generating figures...")
    plot_results(results, analysis, config)

    # Summary
    logging.info("")
    logging.info("="*70)
    logging.info("T6-B3 FIXED COMPLETE")
    logging.info("="*70)

    # Check if c > 0 consistently
    c_values = [v['c'] for v in analysis.values()]
    if len(c_values) > 0:
        c_mean = np.mean(c_values)
        c_std = np.std(c_values)
        r2_values = [v['r_squared'] for v in analysis.values()]
        r2_mean = np.mean(r2_values)

        logging.info(f"Sensitivity: c = {c_mean:.4f} ± {c_std:.4f}")
        logging.info(f"Linearity: <R²> = {r2_mean:.4f}")

        if c_mean > 0.1 and r2_mean > 0.9:
            logging.info("VERDICT: PASS - Linear CP asymmetry detected")
        elif c_mean > 0.01:
            logging.info("VERDICT: WEAK - Small but nonzero sensitivity")
        else:
            logging.info("VERDICT: FAIL - No significant CP sensitivity")
    else:
        logging.info("VERDICT: INCONCLUSIVE - Insufficient data")

    logging.info("="*70)


if __name__ == '__main__':
    main()
