#!/usr/bin/env python3
"""
T6-B1 — √M Scaling Law Verification (GPU-ACCELERATED)

Tests hypothesis: SNR_VRA ∝ √M

Where M is the number of averaged bases and SNR is measured at the true
period peak in the averaged spectrum.

CRITICAL: Requires GPU for efficient FFT computation across many bases.

Runtime: 3-5 minutes (GPU-accelerated)
"""

import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path
import logging
import time
from datetime import datetime
from scipy.optimize import curve_fit

# GPU check
try:
    import cupy as cp
    test = cp.array([1.0])
    _ = cp.fft.fft(test)
    del test
    GPU_AVAILABLE = True
    device_name = cp.cuda.Device(0).compute_capability
    print(f"✅ GPU AVAILABLE: Compute Capability {device_name}")
except Exception as e:
    print(f"❌ GPU NOT AVAILABLE: {e}")
    print("This experiment requires GPU. Exiting.")
    exit(1)

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Experimental parameters - GPU-ACCELERATED"""
    # Modular system
    N = 2003  # Prime modulus
    r_target = 182  # Target period (ρ ≈ 0.09)

    # M-scaling parameters
    M_values = [4, 8, 16, 32, 64, 128]  # Number of bases to test

    # Sequence parameters
    L = 8192  # Longer sequence for better SNR measurement
    n_trials = 50  # Trials per M value

    # Noise model
    noise_sigma = 0.3  # Gaussian noise added to phases (increased to avoid saturation)

    # Output
    output_dir = Path("../Data")
    figure_dir = Path("../Figures")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6B1_gpu_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-B1: M Scaling Law Verification (GPU) - SNR ∝ M")
        logging.info("="*70)
        logging.info(f"Log: {self.log_file}")
        logging.info(f"GPU: Compute Capability {cp.cuda.Device(0).compute_capability}")

# ============================================================================
# Core Functions (GPU-Accelerated)
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

def find_bases_with_order(N, r, num_bases):
    """Find bases with specific multiplicative order"""
    bases = []
    attempts = 0
    max_attempts = N * 20

    while len(bases) < num_bases and attempts < max_attempts:
        a = np.random.randint(2, N)
        if np.gcd(a, N) != 1:
            attempts += 1
            continue

        # Check if order is r
        if pow_mod(a, r, N) == 1:
            # Check minimality
            is_minimal = True
            for d in [2, 3, 5, 7]:
                if r % d == 0 and pow_mod(a, r//d, N) == 1:
                    is_minimal = False
                    break
            if is_minimal:
                bases.append(a)

        attempts += 1

    return bases

def compute_snr_at_peak_gpu(N, r, bases, L, noise_sigma):
    """
    Compute SNR at true period peak using GPU-accelerated FFT.

    SNR = (peak power) / (median noise floor)
    """
    M = len(bases)

    # Generate all sequences on CPU, then batch transfer to GPU
    sequences = []
    for a in bases:
        seq = []
        x = 1
        for _ in range(L):
            x = (x * a) % N
            phase = 2 * np.pi * x / N
            # Add noise
            phase += np.random.normal(0, noise_sigma)
            seq.append(np.exp(1j * phase))
        sequences.append(seq)

    # Transfer to GPU as batch
    sequences_gpu = cp.array(sequences)  # Shape: (M, L)

    # Compute FFTs in batch on GPU
    spectra_gpu = cp.fft.fft(sequences_gpu, axis=1)  # Batch FFT

    # Average spectra
    avg_spectrum_gpu = cp.mean(spectra_gpu, axis=0)
    power_gpu = cp.abs(avg_spectrum_gpu)**2

    # Expected peak locations (harmonics of r)
    peak_indices = []
    for k in range(1, min(10, L//(2*r))):  # First 10 harmonics
        idx = int(k * L / r)
        if idx < L//2:
            peak_indices.append(idx)

    # Get peak power (average over harmonics)
    peak_powers = [float(power_gpu[idx].get()) for idx in peak_indices]
    peak_power = np.mean(peak_powers) if peak_powers else 0.0

    # Noise floor (median of non-peak bins)
    power_cpu = cp.asnumpy(power_gpu[:L//2])
    # Exclude peaks and DC
    mask = np.ones(len(power_cpu), dtype=bool)
    mask[0] = False  # DC
    for idx in peak_indices:
        if idx < len(mask):
            # Exclude peak and neighbors
            mask[max(0, idx-2):min(len(mask), idx+3)] = False

    noise_floor = np.median(power_cpu[mask]) if np.any(mask) else 1.0

    # SNR in dB
    snr_db = 10 * np.log10(peak_power / noise_floor) if noise_floor > 0 else 0.0

    # Clear GPU memory
    del sequences_gpu, spectra_gpu, avg_spectrum_gpu, power_gpu
    cp.get_default_memory_pool().free_all_blocks()

    return snr_db

# ============================================================================
# Main Experiment
# ============================================================================

def run_experiment(config):
    logging.info("")
    logging.info("Configuration:")
    logging.info(f"  N: {config.N}")
    logging.info(f"  r_target: {config.r_target}")
    logging.info(f"  M values: {config.M_values}")
    logging.info(f"  L: {config.L}, trials: {config.n_trials}")
    logging.info(f"  Noise σ: {config.noise_sigma}")
    logging.info("")

    # Find large pool of bases
    logging.info(f"Finding bases with order {config.r_target}...")
    max_M = max(config.M_values)
    base_pool = find_bases_with_order(config.N, config.r_target, max_M * 2)
    logging.info(f"  Found {len(base_pool)} bases")

    if len(base_pool) < max(config.M_values):
        logging.error(f"Insufficient bases found ({len(base_pool)} < {max(config.M_values)})")
        return []

    results = []
    total_trials = len(config.M_values) * config.n_trials
    trial_idx = 0
    start_time = time.time()

    for M in config.M_values:
        logging.info(f"\n{'='*60}")
        logging.info(f"Testing M = {M}")
        logging.info(f"{'='*60}")

        snr_samples = []

        for trial in range(config.n_trials):
            trial_idx += 1

            # Calculate ETA
            elapsed = time.time() - start_time
            rate = trial_idx / elapsed if elapsed > 0 else 0
            eta = (total_trials - trial_idx) / rate if rate > 0 else 0

            # Random sample of M bases
            bases = list(np.random.choice(base_pool, size=M, replace=False))

            # Compute SNR
            snr = compute_snr_at_peak_gpu(config.N, config.r_target, bases,
                                          config.L, config.noise_sigma)
            snr_samples.append(snr)

            # Log progress every 10 trials
            if (trial + 1) % 10 == 0 or trial == config.n_trials - 1:
                logging.info(f"  [{trial_idx}/{total_trials}] Trial {trial+1}/{config.n_trials} | "
                           f"SNR={np.mean(snr_samples):.2f} dB | "
                           f"Elapsed: {elapsed/60:.1f}m | ETA: {eta/60:.1f}m")

        snr_mean = np.mean(snr_samples)
        snr_std = np.std(snr_samples)

        logging.info(f"\n  M={M} → SNR = {snr_mean:.2f} ± {snr_std:.2f} dB")
        logging.info(f"  Theoretical √M gain: {10*np.log10(M):.2f} dB")

        results.append({
            'M': int(M),
            'snr_mean_db': float(snr_mean),
            'snr_std_db': float(snr_std),
            'snr_samples_db': [float(x) for x in snr_samples]
        })

    return results

# ============================================================================
# Analysis & Visualization
# ============================================================================

def analyze_scaling(results):
    """Fit M scaling model (SNR ∝ M in linear space, +3dB per doubling)"""
    M_vals = np.array([r['M'] for r in results])
    snr_vals = np.array([r['snr_mean_db'] for r in results])

    # Convert dB to linear
    snr_linear = 10**(snr_vals / 10)

    # Fit: SNR = a * M (linear in M)
    def linear_model(M, a):
        return a * M

    try:
        popt, _ = curve_fit(linear_model, M_vals, snr_linear)
        a_fit = popt[0]

        # Predicted values
        snr_pred_linear = linear_model(M_vals, a_fit)
        snr_pred_db = 10 * np.log10(snr_pred_linear)

        # R² goodness of fit (in dB space)
        ss_res = np.sum((snr_vals - snr_pred_db)**2)
        ss_tot = np.sum((snr_vals - np.mean(snr_vals))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return snr_pred_db, r_squared, a_fit
    except:
        return None, 0, 0

def plot_results(results, config):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    M_vals = np.array([r['M'] for r in results])
    snr_means = np.array([r['snr_mean_db'] for r in results])
    snr_stds = np.array([r['snr_std_db'] for r in results])

    # Get predictions
    snr_pred, r_squared, a_fit = analyze_scaling(results)

    # (A) SNR vs M (linear scale)
    ax = axes[0, 0]
    ax.errorbar(M_vals, snr_means, yerr=snr_stds, fmt='o', label='Measured', capsize=5)
    if snr_pred is not None:
        ax.plot(M_vals, snr_pred, 'r--', label=f'M fit (R²={r_squared:.3f})', linewidth=2)
    # Theoretical +3dB per doubling (SNR ∝ M)
    ref_snr = snr_means[0]
    ref_M = M_vals[0]
    theoretical = ref_snr + 10 * np.log10(M_vals / ref_M)  # Full M scaling
    ax.plot(M_vals, theoretical, 'g:', label='+3dB per doubling (SNR∝M)', linewidth=2)
    ax.set_xlabel('Number of Bases (M)')
    ax.set_ylabel('SNR (dB)')
    ax.set_title('(A) SNR Scaling with M')
    ax.legend()
    ax.grid(alpha=0.3)

    # (B) Log-log plot
    ax = axes[0, 1]
    ax.loglog(M_vals, 10**(snr_means/10), 'o', label='Measured (linear SNR)')
    if snr_pred is not None:
        ax.loglog(M_vals, 10**(snr_pred/10), 'r--', label='M fit', linewidth=2)
    # Add slope reference line (slope = 1 for SNR ∝ M)
    ax.loglog(M_vals, M_vals * (10**(snr_means[0]/10) / M_vals[0]),
             'g:', label='Slope = 1 (SNR∝M)', linewidth=2)
    ax.set_xlabel('M (log scale)')
    ax.set_ylabel('Linear SNR (log scale)')
    ax.set_title('(B) Log-Log: Slope should be 1.0 (SNR∝M)')
    ax.legend()
    ax.grid(alpha=0.3, which='both')

    # (C) Residuals from M fit
    ax = axes[1, 0]
    if snr_pred is not None:
        residuals = snr_means - snr_pred
        ax.bar(M_vals, residuals, alpha=0.6)
        ax.axhline(0, color='red', linestyle='--')
        ax.set_xlabel('M')
        ax.set_ylabel('Residual (dB)')
        ax.set_title('(C) Residuals from M Fit')
        ax.grid(alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'Fit failed', ha='center', va='center')

    # (D) Summary statistics
    ax = axes[1, 1]
    ax.axis('off')

    # Calculate verdict
    if r_squared is not None and r_squared > 0.95:
        verdict = "PASS"
        color = 'green'
    elif r_squared is not None and r_squared > 0.85:
        verdict = "PARTIAL"
        color = 'orange'
    else:
        verdict = "FAIL"
        color = 'red'

    stats_text = f"""
    GPU-ACCELERATED M SCALING
    (SNR ∝ M, not √M)

    Tested M: {config.M_values}
    Trials per M: {config.n_trials}
    Noise σ: {config.noise_sigma}

    Fit Quality: R² = {r_squared:.4f}
    Fitted constant: a = {a_fit:.4f}

    SNR Range:
      M={M_vals[0]}: {snr_means[0]:.2f} dB
      M={M_vals[-1]}: {snr_means[-1]:.2f} dB

    Gain per 2× M: {(snr_means[-1]-snr_means[0])/(np.log2(M_vals[-1]/M_vals[0])):.2f} dB
    (Theoretical: 3.0 dB)

    VERDICT: {verdict}
    """

    ax.text(0.1, 0.5, stats_text, fontsize=12, family='monospace',
            verticalalignment='center',
            bbox=dict(boxstyle='round', facecolor=color, alpha=0.2))

    fig.suptitle('T6-B1: GPU-Accelerated M Scaling Law Verification (SNR ∝ M)',
                fontsize=16, fontweight='bold')
    plt.tight_layout()

    output_path = config.figure_dir / 'T6B1_sqrt_M_gpu_summary.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"\nFigure: {output_path}")
    plt.close()

# ============================================================================
# Main
# ============================================================================

def main():
    config = Config()

    start = time.time()
    logging.info("Starting GPU-accelerated √M scaling experiment...")
    results = run_experiment(config)
    elapsed = time.time() - start

    if len(results) == 0:
        logging.error("No results collected. Exiting.")
        return

    logging.info(f"\nElapsed: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    # Save
    output_file = config.output_dir / 'T6B1_sqrt_M_gpu_results.json'
    with open(output_file, 'w') as f:
        json.dump({'results': results}, f, indent=2)
    logging.info(f"Data: {output_file}")

    # Analyze and plot
    _, r_squared, _ = analyze_scaling(results)
    plot_results(results, config)

    # Verdict
    if r_squared > 0.95:
        verdict = "PASS"
    elif r_squared > 0.85:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    logging.info("")
    logging.info("="*70)
    logging.info("T6-B1 GPU COMPLETE!")
    logging.info("="*70)
    logging.info(f"M Scaling R²: {r_squared:.4f}")
    logging.info(f"Verdict: {verdict}")
    logging.info("="*70)

if __name__ == '__main__':
    main()
