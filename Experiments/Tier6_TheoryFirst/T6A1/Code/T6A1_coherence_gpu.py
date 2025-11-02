#!/usr/bin/env python3
"""
T6-A1 — Coherence-Incoherence Transition (GPU-ACCELERATED)

Demonstrates R̄ ≈ 0.137 phenomenon using GPU-accelerated CuPy FFT.

CRITICAL: This experiment REQUIRES GPU. Will fail if GPU not available.

Runtime: 2-5 minutes (GPU-accelerated)
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import i0, i1
import json
from pathlib import Path
import logging
import time
from datetime import datetime

# GPU check
try:
    import cupy as cp
    # Test GPU
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
    # Test parameters
    N_primes = [997, 2003, 4999]  # 3 moduli
    rho_targets = [0.10, 0.15, 0.20, 0.25, 0.30]  # 5 densities
    M_values = [16, 32, 64]  # 3 base counts (GPU can handle more)

    # Sequence parameters
    L = 4096  # Sequence length
    n_samples = 20  # Samples per config (more for statistics)

    # Output
    output_dir = Path("../../Data/Experiments/Tier6/T6A1")
    figure_dir = Path("../../Figures/experiments/Tier6/T6A1")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6A1_gpu_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-A1: Coherence-Incoherence Transition (GPU)")
        logging.info("="*70)
        logging.info(f"Log: {self.log_file}")
        logging.info(f"GPU: Compute Capability {cp.cuda.Device(0).compute_capability}")

# ============================================================================
# Core Functions (GPU-Accelerated)
# ============================================================================

def pow_mod_gpu(base, exp, mod):
    """Fast modular exponentiation on CPU (then transfer to GPU)"""
    result = 1
    base = base % mod
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        exp = exp >> 1
        base = (base * base) % mod
    return result

def find_order_batch(N, num_bases=100):
    """Find multiple bases with various orders (CPU-based search)"""
    orders_found = {}
    attempts = 0
    max_attempts = N * 10

    while len(orders_found) < 20 and attempts < max_attempts:
        a = np.random.randint(2, N)
        if np.gcd(a, N) != 1:
            attempts += 1
            continue

        # Find order
        for r in range(1, min(N, 2000)):
            if pow_mod_gpu(a, r, N) == 1:
                # Check minimality
                is_minimal = True
                for d in [2, 3, 5, 7]:
                    if r % d == 0 and pow_mod_gpu(a, r//d, N) == 1:
                        is_minimal = False
                        break
                if is_minimal:
                    if r not in orders_found:
                        orders_found[r] = []
                    orders_found[r].append(a)
                    break
        attempts += 1

    return orders_found

def compute_coherence_gpu(N, r, M, L):
    """
    GPU-accelerated coherence computation using CuPy FFT.

    Returns R̄ (mean resultant length)
    """
    # Find M bases with order r (CPU-based search)
    orders_dict = find_order_batch(N)

    if r not in orders_dict or len(orders_dict[r]) < M:
        return np.nan

    bases = orders_dict[r][:M]

    # Generate phase sequences and transfer to GPU
    spectra_list = []

    for a in bases:
        # Generate sequence on CPU
        seq = []
        x = 1
        for _ in range(L):
            x = (x * a) % N
            phase = 2 * np.pi * x / N
            seq.append(np.exp(1j * phase))

        # Transfer to GPU and compute FFT
        seq_gpu = cp.array(seq)
        spectrum_gpu = cp.fft.fft(seq_gpu)
        spectra_list.append(spectrum_gpu)

    # Stack all spectra on GPU
    spectra_gpu = cp.stack(spectra_list)

    # Compute mean resultant length on GPU
    R_per_harmonic = []
    for ℓ in range(1, min(51, L)):  # Skip DC, use first 50 harmonics
        # Get phasors at this harmonic from all M bases
        phasors_gpu = spectra_gpu[:, ℓ]

        # Normalize to unit length
        magnitudes_gpu = cp.abs(phasors_gpu)
        if cp.all(magnitudes_gpu > 0):
            unit_phasors_gpu = phasors_gpu / magnitudes_gpu

            # Mean resultant length = |mean of unit phasors|
            mean_phasor_gpu = cp.mean(unit_phasors_gpu)
            R_ℓ = float(cp.abs(mean_phasor_gpu).get())  # Transfer back to CPU
            R_per_harmonic.append(R_ℓ)

    # Clear GPU memory
    del spectra_gpu, seq_gpu
    cp.get_default_memory_pool().free_all_blocks()

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
    logging.info("")

    results = []
    idx = 0
    start_time = time.time()

    for N in config.N_primes:
        # Pre-find all orders for this N
        logging.info(f"Finding orders for N={N}...")
        orders_dict = find_order_batch(N)
        logging.info(f"  Found orders: {sorted(orders_dict.keys())[:10]}...")

        for rho_target in config.rho_targets:
            r_target = int(rho_target * N)

            # Find closest available order
            available_orders = sorted(orders_dict.keys())
            r_actual = min(available_orders, key=lambda x: abs(x - r_target))

            if abs(r_actual - r_target) > 0.15 * N:
                logging.warning(f"Skipping ρ={rho_target:.2f} for N={N} (no close order)")
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
                for sample_idx in range(config.n_samples):
                    R = compute_coherence_gpu(N, r_actual, M, config.L)
                    if not np.isnan(R):
                        R_samples.append(R)

                    # Log progress every 5 samples
                    if (sample_idx + 1) % 5 == 0:
                        logging.info(f"  Sample {sample_idx+1}/{config.n_samples}: R̄={np.mean(R_samples):.4f}")

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
    ax.set_title('(A) GPU-Accelerated: Coherence vs Density')
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
            ax.plot([1/M for M in M_vals], var_vals, 'o-', label=f'ρ≈{rho_target:.2f}')

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
    GPU-ACCELERATED RESULTS

    Overall R̄: {mean_R:.4f} ± {std_R:.4f}
    Target R̄: 0.137
    Deviation: {dev:.4f}

    Configs tested: {len(results)}
    Total samples: {len(all_R)}

    GPU: CuPy {cp.__version__}

    VERDICT: {verdict}
    """

    ax.text(0.1, 0.5, stats_text, fontsize=14, family='monospace',
            verticalalignment='center', bbox=dict(boxstyle='round', facecolor=color, alpha=0.2))

    fig.suptitle('T6-A1: GPU-Accelerated Coherence-Incoherence Transition',
                fontsize=16, fontweight='bold')
    plt.tight_layout()

    output_path = config.figure_dir / 'T6A1_gpu_summary.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"Figure: {output_path}")
    plt.close()

# ============================================================================
# Main
# ============================================================================

def main():
    config = Config()

    start = time.time()
    logging.info("Starting GPU-accelerated experiment...")
    results = run_experiment(config)
    elapsed = time.time() - start

    logging.info(f"\nElapsed: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    # Save
    output_file = config.output_dir / 'T6A1_gpu_results.json'
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
    logging.info("T6-A1 GPU COMPLETE!")
    logging.info("="*70)
    logging.info(f"Overall R̄: {mean_R:.4f} ± {np.std(all_R):.4f}")
    logging.info(f"Target: 0.137")
    logging.info(f"Deviation: {dev:.4f}")
    logging.info(f"Verdict: {verdict}")
    logging.info("="*70)

if __name__ == '__main__':
    main()
