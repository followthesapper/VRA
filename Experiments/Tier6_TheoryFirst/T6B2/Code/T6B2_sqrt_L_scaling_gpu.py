#!/usr/bin/env python3
"""
T6-B2 — L² Scaling Law Verification (GPU-ACCELERATED)

Tests hypothesis: SNR_VRA ∝ L² (noise floor scaling)

Where L is the sequence length. VRA theory predicts +6.02 dB per doubling of L
due to noise power density ∝ 1/L².

CRITICAL: Requires GPU for efficient FFT computation across long sequences.

Runtime: 2-4 minutes (GPU-accelerated)
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
    # Modular system (same as T6-B1 for compatibility)
    N = 2003  # Prime modulus
    r_target = 182  # Target period (ρ ≈ 0.09)

    # L-scaling parameters
    L_values = [2048, 4096, 8192, 16384, 32768]  # Sequence lengths to test (start at 2048 for sufficient resolution)

    # Fixed parameters
    M = 16  # Fixed number of bases (smaller for reliability)
    n_trials = 40  # Trials per L value

    # Noise model
    noise_sigma = 0.03  # Low noise to see scaling clearly

    # Output
    output_dir = Path("../../Data/Experiments/Tier6/T6B2")
    figure_dir = Path("../../Figures/experiments/Tier6/T6B2")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6B2_gpu_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-B2: L² Scaling Law Verification (GPU) - SNR ∝ L²")
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
    max_attempts = N * 10

    while len(bases) < num_bases and attempts < max_attempts:
        a = np.random.randint(2, N)
        if np.gcd(a, N) != 1:
            attempts += 1
            continue

        # Check if order is r
        if pow_mod(a, r, N) == 1:
            # Check minimality
            is_minimal = True
            for d in [2, 3, 5, 7, 11]:
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
    if len(peak_indices) > 0:
        peak_powers = [float(power_gpu[idx].get()) for idx in peak_indices]
        peak_power = np.mean(peak_powers)
    else:
        peak_power = 0.0

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
    logging.info(f"  L values: {config.L_values}")
    logging.info(f"  M: {config.M} (fixed), trials: {config.n_trials}")
    logging.info(f"  Noise σ: {config.noise_sigma}")
    logging.info("")

    # Find bases
    logging.info(f"Finding {config.M} bases with order {config.r_target}...")
    bases = find_bases_with_order(config.N, config.r_target, config.M)
    logging.info(f"  Found {len(bases)} bases")

    if len(bases) < config.M:
        logging.error(f"Insufficient bases found ({len(bases)} < {config.M})")
        return []

    results = []
    total_trials = len(config.L_values) * config.n_trials
    trial_idx = 0
    start_time = time.time()

    for L in config.L_values:
        logging.info(f"\n{'='*60}")
        logging.info(f"Testing L = {L}")
        logging.info(f"{'='*60}")

        snr_samples = []

        for trial in range(config.n_trials):
            trial_idx += 1

            # Calculate ETA
            elapsed = time.time() - start_time
            rate = trial_idx / elapsed if elapsed > 0 else 0
            eta = (total_trials - trial_idx) / rate if rate > 0 else 0

            # Compute SNR with this L
            snr = compute_snr_at_peak_gpu(config.N, config.r_target, bases,
                                          L, config.noise_sigma)
            snr_samples.append(snr)

            # Log progress every 10 trials
            if (trial + 1) % 10 == 0 or trial == config.n_trials - 1:
                logging.info(f"  [{trial_idx}/{total_trials}] Trial {trial+1}/{config.n_trials} | "
                           f"SNR={np.mean(snr_samples):.2f} dB | "
                           f"Elapsed: {elapsed/60:.1f}m | ETA: {eta/60:.1f}m")

        snr_mean = np.mean(snr_samples)
        snr_std = np.std(snr_samples)

        logging.info(f"\n  L={L} → SNR = {snr_mean:.2f} ± {snr_std:.2f} dB")
        logging.info(f"  Theoretical L² gain vs L={config.L_values[0]}: "
                    f"{20*np.log10(L/config.L_values[0]):.2f} dB")

        results.append({
            'L': int(L),
            'snr_mean_db': float(snr_mean),
            'snr_std_db': float(snr_std),
            'snr_samples_db': [float(x) for x in snr_samples]
        })

    return results

# ============================================================================
# Analysis & Visualization
# ============================================================================

def analyze_scaling(results):
    """Fit L² scaling model (SNR ∝ L², +6dB per doubling)"""
    L_vals = np.array([r['L'] for r in results])
    snr_vals = np.array([r['snr_mean_db'] for r in results])

    # Convert dB to linear
    snr_linear = 10**(snr_vals / 10)

    # Fit: SNR = a * L²
    def quadratic_model(L, a):
        return a * L**2

    try:
        popt, _ = curve_fit(quadratic_model, L_vals, snr_linear)
        a_fit = popt[0]

        # Predicted values
        snr_pred_linear = quadratic_model(L_vals, a_fit)
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

    L_vals = np.array([r['L'] for r in results])
    snr_means = np.array([r['snr_mean_db'] for r in results])
    snr_stds = np.array([r['snr_std_db'] for r in results])

    # Get predictions
    snr_pred, r_squared, a_fit = analyze_scaling(results)

    # (A) SNR vs L (linear scale)
    ax = axes[0, 0]
    ax.errorbar(L_vals, snr_means, yerr=snr_stds, fmt='o', label='Measured', capsize=5)
    if snr_pred is not None:
        ax.plot(L_vals, snr_pred, 'r--', label=f'L² fit (R²={r_squared:.3f})', linewidth=2)
    # Theoretical gain (SNR ∝ L², +6dB per doubling)
    ref_snr = snr_means[0]
    ref_L = L_vals[0]
    theoretical = ref_snr + 20 * np.log10(L_vals / ref_L)
    ax.plot(L_vals, theoretical, 'g:', label='Theoretical L² (+6dB per 2×)', linewidth=2)
    ax.set_xlabel('Sequence Length (L)')
    ax.set_ylabel('SNR (dB)')
    ax.set_title('(A) SNR Scaling with L')
    ax.legend()
    ax.grid(alpha=0.3)

    # (B) Log-log plot
    ax = axes[0, 1]
    ax.loglog(L_vals, 10**(snr_means/10), 'o', label='Measured (linear SNR)')
    if snr_pred is not None:
        ax.loglog(L_vals, 10**(snr_pred/10), 'r--', label='L² fit', linewidth=2)
    # Add slope reference line (slope = 2 for SNR ∝ L²)
    ax.loglog(L_vals, L_vals**2 * (10**(snr_means[0]/10) / L_vals[0]**2),
             'g:', label='Slope = 2 (SNR∝L²)', linewidth=2)
    ax.set_xlabel('L (log scale)')
    ax.set_ylabel('Linear SNR (log scale)')
    ax.set_title('(B) Log-Log: Slope should be 2.0 (SNR∝L²)')
    ax.legend()
    ax.grid(alpha=0.3, which='both')

    # (C) Gain per doubling of L
    ax = axes[1, 0]
    if len(L_vals) > 1:
        gains = []
        L_ratios = []
        for i in range(1, len(L_vals)):
            gain_db = snr_means[i] - snr_means[i-1]
            L_ratio = L_vals[i] / L_vals[i-1]
            gains.append(gain_db)
            L_ratios.append(f"{L_vals[i-1]}→{L_vals[i]}")

        ax.bar(range(len(gains)), gains, alpha=0.6)
        ax.axhline(6.02, color='green', linestyle='--',
                  label='L² Theory: +6.02 dB per 2×')
        ax.set_xticks(range(len(gains)))
        ax.set_xticklabels(L_ratios, rotation=45)
        ax.set_ylabel('SNR Gain (dB)')
        ax.set_title('(C) Gain per Length Doubling')
        ax.legend()
        ax.grid(alpha=0.3)

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

    # Calculate actual gain per doubling
    if len(L_vals) > 1:
        total_gain = snr_means[-1] - snr_means[0]
        num_doublings = np.log2(L_vals[-1] / L_vals[0])
        gain_per_doubling = total_gain / num_doublings if num_doublings > 0 else 0
    else:
        gain_per_doubling = 0

    stats_text = f"""
    GPU-ACCELERATED L² SCALING
    (SNR ∝ L², not √L)

    Tested L: {config.L_values}
    Trials per L: {config.n_trials}
    Fixed M: {config.M}
    Noise σ: {config.noise_sigma}

    Fit Quality: R² = {r_squared:.4f}
    Fitted constant: a = {a_fit:.4e}

    SNR Range:
      L={L_vals[0]}: {snr_means[0]:.2f} dB
      L={L_vals[-1]}: {snr_means[-1]:.2f} dB

    Gain per 2× L: {gain_per_doubling:.2f} dB
    (Theoretical: 6.02 dB for L²)

    VERDICT: {verdict}
    """

    ax.text(0.1, 0.5, stats_text, fontsize=12, family='monospace',
            verticalalignment='center',
            bbox=dict(boxstyle='round', facecolor=color, alpha=0.2))

    fig.suptitle('T6-B2: GPU-Accelerated L² Scaling Law Verification (SNR ∝ L²)',
                fontsize=16, fontweight='bold')
    plt.tight_layout()

    output_path = config.figure_dir / 'T6B2_sqrt_L_gpu_summary.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"\nFigure: {output_path}")
    plt.close()

# ============================================================================
# Main
# ============================================================================

def main():
    config = Config()

    start = time.time()
    logging.info("Starting GPU-accelerated √L scaling experiment...")
    results = run_experiment(config)
    elapsed = time.time() - start

    if len(results) == 0:
        logging.error("No results collected. Exiting.")
        return

    logging.info(f"\nElapsed: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    # Save
    output_file = config.output_dir / 'T6B2_sqrt_L_gpu_results.json'
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
    logging.info("T6-B2 GPU COMPLETE!")
    logging.info("="*70)
    logging.info(f"L² Scaling R²: {r_squared:.4f}")
    logging.info(f"Verdict: {verdict}")
    logging.info("="*70)

if __name__ == '__main__':
    main()
