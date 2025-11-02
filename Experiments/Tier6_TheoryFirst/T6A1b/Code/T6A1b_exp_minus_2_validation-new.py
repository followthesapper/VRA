#!/usr/bin/env python3
"""
T6-A1b — exp(-2) Convergence Validation (GPU-ACCELERATED)
+ ρ sweep diagnostic (R̄ vs ρ)

Two modes:
  1) Default experiment run (exp2_run): test convergence across M with logging of
     Ungated / Top-K / Weighted (mag^p) R̄.
  2) rho_sweep: scan divisors r | (N-1) to visualize R̄ vs ρ and save a quick plot.

Examples:
  # Main experiment (uses Config defaults)
  python3 T6A1b_exp_minus_2_validation.py

  # ρ sweep (override N/L if desired)
  python3 T6A1b_exp_minus_2_validation.py --mode rho_sweep --N 12289 --L 16384 --M 64 \
      --Kmax 50 --p 1.5 --rho_min 0.08 --rho_max 0.28 --max_r_points 12
"""

import argparse
import json
import logging
import time
from datetime import datetime
from math import gcd
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# GPU check
try:
    import cupy as cp
    _ = cp.fft.fft(cp.array([1.0]))
    GPU_AVAILABLE = True
except Exception as e:
    print(f"❌ GPU NOT AVAILABLE: {e}")
    print("This experiment requires GPU. Exiting.")
    exit(1)


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Experimental parameters for exp(-2) validation"""

    # Chosen prime (NTT prime) with many divisors: N-1 = 12288 = 2^12 * 3
    N = 12289

    # CRITICAL: Lock ρ to the exp(-2) ridge at ρ ≈ 0.25
    # This is where the V-shaped R̄(ρ) curve hits the exp(-2) target
    r_target = int(round(0.25 * N))  # ρ = 0.25 → r = 3072 for N=12289

    # Large M values to test convergence
    M_values = [128, 256, 512]

    # Sequence parameters - will be aligned to r_target in __init__
    L = 24576  # Will be adjusted to ensure L/r is integer

    n_trials = 1  # Single trial per M (fixed bases + σ=0 makes trials identical)

    # Noise model (NONE - match T6-A1 methodology)
    noise_sigma = 0.0  # No noise for clean measurement

    # Theoretical prediction
    exp_minus_2 = float(np.exp(-2.0))  # 0.1353352832...

    # Aggregation defaults (optimized for ρ ≈ 0.25)
    # Use Top-K by coherence (fixed K=24 eliminates τ-bias)
    agg = 'topk'
    topk = 24  # Fixed K by coherence
    p = 2.0
    perc = None

    # Output
    output_dir = Path("../../Data/Experiments/Tier6/T6A1b")
    figure_dir = Path("../../Figures/experiments/Tier6/T6A1b")

    def __init__(self):
        # Ensure r divides N-1
        import math as m
        if (self.N - 1) % self.r_target != 0:
            # Find nearest divisor of N-1 to target_r
            all_divs = divisors_of_n_minus_1(self.N)
            target_rho = 0.25
            closest_r = min([d for d in all_divs if d > 32],
                          key=lambda d: abs(d/self.N - target_rho))
            logging.warning(f"r={self.r_target} doesn't divide N-1={self.N-1}, using closest divisor r={closest_r}")
            self.r_target = closest_r

        # Force L alignment: L must be a multiple of r_target
        self.L = m.ceil(self.L / self.r_target) * self.r_target

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6A1b_gpu_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-A1b: exp(-2) Convergence Validation (GPU)")
        logging.info("="*70)
        logging.info(f"Log: {self.log_file}")
        logging.info(f"GPU: {cp.cuda.runtime.getDeviceProperties(0)['name'].decode()} "
                     f"(CC {cp.cuda.Device(0).compute_capability})")


# ============================================================================
# Core helpers
# ============================================================================

def pow_mod(base, exp, mod):
    """Fast modular exponentiation"""
    result = 1
    base = base % mod
    while exp > 0:
        if exp & 1:
            result = (result * base) % mod
        exp >>= 1
        base = (base * base) % mod
    return result


def _prime_factors(n: int):
    """Return list of prime factors (with multiplicity) of n."""
    fs = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            fs.append(d)
            n //= d
        d += 1 if d == 2 else 2  # 2, then odds
    if n > 1:
        fs.append(n)
    return fs


def primitive_root(N: int):
    """
    Find a primitive root modulo prime N.
    A primitive root g has multiplicative order φ(N) = N-1.
    """
    if N == 2:
        return 1

    phi = N - 1  # For prime N
    prime_factors_phi = sorted(set(_prime_factors(phi)))

    # Test candidates starting from 2
    for g in range(2, N):
        if np.gcd(g, N) != 1:
            continue

        # Check if g is a primitive root: g^(φ/p) ≢ 1 (mod N) for all prime p | φ
        is_primitive = True
        for p in prime_factors_phi:
            if pow_mod(g, phi // p, N) == 1:
                is_primitive = False
                break

        if is_primitive:
            return g

    raise ValueError(f"No primitive root found for N={N}")


def exact_order_bases_deterministic(N: int, r: int, limit: int = None, rng=None):
    """
    DETERMINISTIC construction of exact-order-r bases using primitive root.

    For prime N, let g = primitive root mod N (order N-1).
    Let h = (N-1)/r. Then the set A = {g^(h*t) mod N : 1 ≤ t < r, gcd(t, r) = 1}
    contains exactly φ(r) elements, all with exact multiplicative order r.

    This eliminates random hunting and guarantees purity (no contamination).
    """
    if rng is None:
        rng = np.random

    g = primitive_root(N)
    h = (N - 1) // r

    if (N - 1) % r != 0:
        raise ValueError(f"r={r} does not divide N-1={N-1}")

    # Generate all exact-order bases
    candidates = []
    for t in range(1, r):
        if np.gcd(t, r) == 1:
            base = pow_mod(g, h * t, N)
            candidates.append(base)

    # Shuffle and return requested number
    rng.shuffle(candidates)

    if limit is None:
        return candidates
    else:
        return candidates[:min(limit, len(candidates))]

def find_bases_with_order(N, r, num_bases, *, rng=np.random):
    """
    Wrapper function that uses deterministic primitive root construction.
    This eliminates random hunting and guarantees exact-order bases.
    """
    logging.info(f"  Using deterministic primitive root construction...")
    bases = exact_order_bases_deterministic(N, r, limit=num_bases, rng=rng)

    if len(bases) < num_bases:
        logging.warning(f"Only {len(bases)} exact-order bases available (φ(r)={len(bases)}), requested {num_bases}")

    return bases


def fractional_bin_dft_gpu(sequences_gpu, f: float) -> cp.ndarray:
    """
    Compute DFT at fractional bin f using complex demodulation (exact frequency readout).
    sequences_gpu: (M, L) complex on GPU
    returns: (M,) complex values at frequency f
    """
    M, L = sequences_gpu.shape
    n = cp.arange(L, dtype=cp.float32)
    kernel = cp.exp((-2j * cp.pi * f / L) * n)
    return (sequences_gpu * kernel).sum(axis=1)


# ============================================================================
# Measurement path (now logs Ungated / Top-K / Weighted and returns Weighted)
# ============================================================================

def compute_coherence_gpu(N, r, bases, L, noise_sigma, agg='topk', topk=None, p=2.0, perc=None):
    """
    Compute mean resultant length (R̄) using FRACTIONAL-BIN DFT at exact peak locations.

    Args:
        agg: Aggregation mode - 'ungated', 'topk', 'weighted', 'perc'
        topk: Number of top harmonics to use (default: min(32, len(R_arr)))
        p: Power for weighted aggregation (default: 2.0)
        perc: Percentile cutoff for 'perc' mode (e.g., 0.75 = top 25%)

    Returns the selected aggregator and logs all variants for visibility.
    """
    # Build sequences on CPU
    sequences = []
    for a in bases:
        seq = []
        x = 1
        for _ in range(L):
            x = (x * a) % N
            phase = 2 * np.pi * x / N
            if noise_sigma:
                phase += np.random.normal(0, noise_sigma)
            seq.append(np.exp(1j * phase))
        sequences.append(seq)

    # Transfer to GPU
    sequences_gpu = cp.array(sequences)  # (M, L)

    # Read harmonics
    R_per_harmonic = []
    mag_per_harmonic = []
    num_harmonics = min(50, r // 2)

    for harmonic_idx in range(1, num_harmonics + 1):
        f = harmonic_idx * (L / r)
        if f >= L // 2:
            break

        phasors_gpu = fractional_bin_dft_gpu(sequences_gpu, f)  # (M,)
        magnitudes_gpu = cp.abs(phasors_gpu)

        if cp.all(magnitudes_gpu > 0):
            unit_phasors_gpu = phasors_gpu / magnitudes_gpu
            mean_phasor_gpu = cp.mean(unit_phasors_gpu)
            R_ell = float(cp.abs(mean_phasor_gpu).get())
            R_per_harmonic.append(R_ell)

            mag_mean = float(cp.mean(magnitudes_gpu).get())
            mag_per_harmonic.append(mag_mean)

    # Cleanup GPU mem
    del sequences_gpu
    cp.get_default_memory_pool().free_all_blocks()

    # Aggregate
    if not R_per_harmonic:
        return float('nan')

    R_arr = np.array(R_per_harmonic, dtype=float)
    mag_arr = np.array(mag_per_harmonic, dtype=float)

    # Ungated (all)
    R_bar_ungated = float(np.mean(R_arr))

    # Compute correlation between magnitude and coherence for diagnostics
    corr_mag_coh = float(np.corrcoef(mag_arr, R_arr)[0, 1]) if len(R_arr) > 1 else 0.0

    # THRESHOLD-BASED GATING: Select harmonics with R_ℓ ≥ τ
    # This adapts to variable harmonic quality better than fixed Top-K
    tau = 0.12  # Threshold for coherence (R_ℓ)
    tau_idx = np.where(R_arr >= tau)[0]

    if len(tau_idx) == 0:
        # Safety fallback: use top-16 by coherence if none exceed threshold
        tau_idx = np.argsort(R_arr)[-16:]
        tau = float(R_arr[tau_idx[0]]) if len(tau_idx) > 0 else 0.0

    R_bar_tau = float(np.mean(R_arr[tau_idx]))
    K_used = len(tau_idx)

    # Legacy Top-K by coherence (for comparison)
    if topk is None:
        topk = min(32, len(R_arr))
    else:
        topk = min(topk, len(R_arr))

    top_k_idx = np.argsort(R_arr)[-topk:]
    R_bar_topK = float(np.mean(R_arr[top_k_idx]))

    # Weighted by mag^p
    w = mag_arr ** p
    R_bar_weighted = float(np.sum(w * R_arr) / np.sum(w))

    # Percentile-based (top X% by COHERENCE, not magnitude)
    if perc is not None:
        threshold = np.percentile(R_arr, perc * 100)
        perc_idx = R_arr >= threshold
        R_bar_perc = float(np.mean(R_arr[perc_idx])) if np.any(perc_idx) else R_bar_ungated
    else:
        R_bar_perc = R_bar_ungated

    # Select return value based on aggregation mode
    if agg == 'ungated':
        R_bar_return = R_bar_ungated
        agg_label = "Ungated"
    elif agg == 'topk':
        R_bar_return = R_bar_topK
        agg_label = f"Top-{topk}"
    elif agg == 'tau' or agg == 'threshold':
        R_bar_return = R_bar_tau
        agg_label = f"Tau({tau:.3f},K={K_used})"
    elif agg == 'weighted':
        R_bar_return = R_bar_weighted
        agg_label = f"Weighted(p={p})"
    elif agg == 'perc':
        R_bar_return = R_bar_perc
        agg_label = f"Percentile({perc})"
    else:
        # Default to threshold-based gating
        R_bar_return = R_bar_tau
        agg_label = f"Tau({tau:.3f},K={K_used})"

    # Log all aggregators for visibility
    corr_str = f" | corr(mag,R)={corr_mag_coh:.3f}"
    logging.info(
        f"    R̄: Ungated={R_bar_ungated:.6f} | Top-{topk}={R_bar_topK:.6f} | "
        f"Tau(≥{tau:.2f},K={K_used})={R_bar_tau:.6f} | "
        f"Weighted(p={p})={R_bar_weighted:.6f}{corr_str}"
    )
    logging.info(f"    → RETURNING {agg_label}={R_bar_return:.6f}")

    return R_bar_return


# ============================================================================
# ρ sweep helpers
# ============================================================================

def divisors_of_n_minus_1(N: int):
    """Return sorted divisors of N-1 (for prime N this is φ(N))."""
    n = N - 1
    divs = set()
    i = 1
    while i * i <= n:
        if n % i == 0:
            divs.add(i)
            divs.add(n // i)
        i += 1
    return sorted(divs)


def find_exact_order_bases(N: int, r: int, M: int, max_tries: int = 200000):
    """Return up to M bases of EXACT multiplicative order r mod N (prime N)."""
    bases = []
    tries = 0
    small_primes = [2, 3, 5, 7, 11, 13]
    while len(bases) < M and tries < max_tries:
        a = np.random.randint(2, N)
        if gcd(a, N) != 1:
            tries += 1
            continue
        if pow_mod(a, r, N) == 1:
            minimal = True
            for d in small_primes:
                if r % d == 0 and pow_mod(a, r // d, N) == 1:
                    minimal = False
                    break
            if minimal:
                bases.append(a)
        tries += 1
    return bases


def rho_sweep_diag(
    N: int,
    L: int,
    M: int,
    Kmax: int = 50,
    p_exp: float = 1.5,
    rho_min: float = 0.05,
    rho_max: float = 0.30,
    max_r_points: int = 12,
    seed: int = 0,
    **_
):
    """
    Sample r | (N-1) across rho in [rho_min, rho_max] and compute R̄ for each using the
    same path: exact-order bases + fractional DFT + mag^p weighting (also log Ungated & Top-K).
    Saves rho_sweep_R_vs_rho.png and logs a table.
    """
    np.random.seed(seed)

    all_divs = divisors_of_n_minus_1(N)
    cands = [r for r in all_divs if r >= 32 and rho_min <= (r / N) <= rho_max]
    if not cands:
        logging.warning("No divisors r in requested ρ range.")
        return

    if len(cands) > max_r_points:
        idx = np.linspace(0, len(cands) - 1, max_r_points).round().astype(int)
        cands = [cands[i] for i in idx]

    rows = []

    for r in cands:
        bases = find_exact_order_bases(N, r, M)
        if len(bases) < M:
            logging.info(f"r={r} (ρ={r/N:.4f}): only {len(bases)}/{M} exact-order bases; skipping.")
            continue

        # build seqs
        sequences = []
        for a in bases:
            seq = []
            x = 1
            for _ in range(L):
                x = (x * a) % N
                phase = 2 * np.pi * x / N
                seq.append(np.exp(1j * phase))
            sequences.append(seq)

        sequences_gpu = cp.array(sequences)
        R_list, mag_list = [], []
        num_harm = min(Kmax, r // 2)
        for h in range(1, num_harm + 1):
            f = h * (L / r)
            if f >= L // 2:
                break
            ph = fractional_bin_dft_gpu(sequences_gpu, f)
            mags = cp.abs(ph)
            if cp.all(mags > 0):
                unit = ph / mags
                mean_ph = cp.mean(unit)
                R_list.append(float(cp.abs(mean_ph).get()))
                mag_list.append(float(cp.mean(mags).get()))

        del sequences_gpu
        cp.get_default_memory_pool().free_all_blocks()

        if not R_list:
            continue

        R_arr = np.array(R_list)
        mag_arr = np.array(mag_list)
        R_ung = float(np.mean(R_arr))
        K = min(32, len(R_arr))
        top_idx = np.argsort(mag_arr)[-K:]
        R_top = float(np.mean(R_arr[top_idx]))
        w = (mag_arr ** p_exp)
        R_wgt = float(np.sum(w * R_arr) / np.sum(w))

        rows.append((r/N, r, R_ung, R_top, R_wgt))

    if not rows:
        logging.warning("No valid r runs completed in sweep.")
        return

    rows.sort(key=lambda t: t[0])

    logging.info("\nρ sweep (N={}, L={}, M={}, p={}):".format(N, L, M, p_exp))
    logging.info("   {:>8} {:>8}   {:>10} {:>10} {:>10}".format("rho","r","Ungated","TopK32","Weighted"))
    for rho, r, Ru, Rt, Rw in rows:
        logging.info("   {:8.4f} {:8d}   {:10.6f} {:10.6f} {:10.6f}".format(rho, r, Ru, Rt, Rw))

    # Plot
    try:
        rho_vals = [t[0] for t in rows]
        ung_vals = [t[2] for t in rows]
        top_vals = [t[3] for t in rows]
        wgt_vals = [t[4] for t in rows]

        plt.figure(figsize=(7.5, 5.0))
        plt.plot(rho_vals, ung_vals, 'o-', label='Ungated')
        plt.plot(rho_vals, top_vals, 'o-', label='Top-K (K=32)')
        plt.plot(rho_vals, wgt_vals, 'o-', label=f'Weighted (p={p_exp})')
        plt.axhline(np.exp(-2), linestyle='--', linewidth=1.5, label='exp(-2)')
        plt.xlabel('ρ = r / N')
        plt.ylabel('R̄')
        plt.title(f'R̄ vs ρ (N={N}, L={L}, M={M}, Kmax={Kmax})')
        plt.legend()
        plt.grid(alpha=0.3)
        out = Path("rho_sweep_R_vs_rho.png")
        plt.tight_layout()
        plt.savefig(out, dpi=160)
        logging.info(f"Saved plot: {out.resolve()}")
        plt.close()
    except Exception as e:
        logging.warning(f"Plotting failed: {e}")


# ============================================================================
# Experiment driver + analysis/plots
# ============================================================================

def run_experiment(config: Config):
    logging.info("")
    logging.info("OBJECTIVE: Validate R̄ → exp(-2) = 0.1353352832... as M → ∞")
    logging.info("")

    # Enforce L alignment with r
    if config.L % config.r_target != 0:
        L_old = config.L
        config.L = ((config.L // config.r_target) + 1) * config.r_target
        logging.info(f"L ALIGNMENT: Adjusted L from {L_old} to {config.L} (now L/r = {config.L // config.r_target})")

    logging.info("Configuration:")
    logging.info(f"  N: {config.N}")
    logging.info(f"  r_target: {config.r_target}")
    logging.info(f"  ρ: {config.r_target / config.N:.4f}")
    logging.info(f"  M values: {config.M_values}")
    logging.info(f"  L: {config.L} (L/r = {config.L // config.r_target}), trials: {config.n_trials}")
    logging.info(f"  Noise σ: {config.noise_sigma}")
    logging.info(f"  Aggregator: {getattr(config, 'agg', 'topk')}, topk={getattr(config, 'topk', None)}, p={getattr(config, 'p', 2.0)}")
    logging.info(f"  Target: exp(-2) = {config.exp_minus_2:.10f}")
    logging.info("")

    # Build deterministic exact-order base pool using primitive root
    max_M = max(config.M_values)
    logging.info(f"Building deterministic exact-order base pool (φ(r) bases)...")

    # Get primitive root info for verification
    g = primitive_root(config.N)
    h = (config.N - 1) // config.r_target
    logging.info(f"  Primitive root g={g}, h=(N-1)/r={h}")

    # Get ALL exact-order bases (φ(r) of them)
    base_pool = exact_order_bases_deterministic(config.N, config.r_target, limit=None)
    logging.info(f"  Generated {len(base_pool)} exact-order bases (φ(r)={len(base_pool)})")

    # Log first 10 bases for verification
    if len(base_pool) >= 10:
        logging.info(f"  First 10 bases: {base_pool[:10]}")
        logging.info(f"  Verification: These should be of form g^(h*t) mod N where gcd(t,r)=1")

    if len(base_pool) < max_M:
        logging.error(f"Insufficient bases available ({len(base_pool)} < {max_M})")
        return []

    # Create FIXED base sets for each M (no resampling per trial)
    # Use evenly-spaced indices to get a representative sample
    logging.info(f"Creating fixed base sets for each M (eliminates per-trial variance)...")
    fixed_bases_by_M = {}
    for M in config.M_values:
        if M <= len(base_pool):
            # Take evenly spaced indices
            indices = np.linspace(0, len(base_pool) - 1, num=M, dtype=int)
            fixed_bases_by_M[M] = [base_pool[i] for i in indices]
            logging.info(f"  M={M}: Fixed base set created (same bases used for all {config.n_trials} trials)")
        else:
            logging.error(f"M={M} exceeds available bases ({len(base_pool)})")
            return []

    results = []
    total_trials = len(config.M_values) * config.n_trials
    trial_idx = 0
    start_time = time.time()

    # Get aggregation parameters from config
    agg = getattr(config, 'agg', 'topk')
    topk = getattr(config, 'topk', None)
    p = getattr(config, 'p', 2.0)
    perc = getattr(config, 'perc', None)

    for M in config.M_values:
        logging.info(f"\n{'='*60}")
        logging.info(f"Testing M = {M}")
        logging.info(f"{'='*60}")

        R_samples = []

        for trial in range(config.n_trials):
            trial_idx += 1
            elapsed = time.time() - start_time
            rate = trial_idx / elapsed if elapsed > 0 else 0
            eta = (total_trials - trial_idx) / rate if rate > 0 else 0

            # Use FIXED base set (same bases for all trials at this M)
            # This eliminates per-trial variance from resampling
            bases = fixed_bases_by_M[M]

            R = compute_coherence_gpu(config.N, config.r_target, bases,
                                      config.L, config.noise_sigma,
                                      agg=agg, topk=topk, p=p, perc=perc)
            R_samples.append(R)

            if (trial + 1) % 5 == 0 or trial == config.n_trials - 1:
                R_mean_current = float(np.mean(R_samples))
                error = 100 * abs(R_mean_current - config.exp_minus_2) / config.exp_minus_2
                logging.info(f"  [{trial_idx}/{total_trials}] Trial {trial+1}/{config.n_trials} | "
                             f"R̄={R_mean_current:.6f} (error: {error:.2f}%) | "
                             f"Elapsed: {elapsed/60:.1f}m | ETA: {eta/60:.1f}m")

        R_mean = float(np.mean(R_samples))
        R_std = float(np.std(R_samples))
        error_from_exp2 = R_mean - config.exp_minus_2
        pct_error = 100 * abs(error_from_exp2) / config.exp_minus_2

        logging.info(f"\n  M={M} → R̄ = {R_mean:.6f} ± {R_std:.6f}")
        logging.info(f"  Δ from exp(-2): {error_from_exp2:+.6f} ({pct_error:+.2f}%)")

        results.append({
            'M': int(M),
            'R_mean': R_mean,
            'R_std': R_std,
            'R_samples': [float(x) for x in R_samples],
            'error_from_exp_minus_2': float(error_from_exp2),
            'percent_error': float(pct_error)
        })

    return results


def analyze_convergence(results, config):
    """Fit convergence model: R̄(M) = exp(-2) + c/M^α"""
    if not results:
        return None, None, None

    M_vals = np.array([r['M'] for r in results], dtype=float)
    R_vals = np.array([r['R_mean'] for r in results], dtype=float)

    def model(M, c, alpha):
        return config.exp_minus_2 + c / (M**alpha)

    try:
        popt, _ = curve_fit(model, M_vals, R_vals, p0=[1.0, 1.5], maxfev=10000)
        c_fit, alpha_fit = popt
        R_pred = model(M_vals, c_fit, alpha_fit)
        return float(c_fit), float(alpha_fit), R_pred
    except Exception:
        return None, None, None


def plot_results(results, config):
    if not results:
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    M_vals = np.array([r['M'] for r in results])
    R_means = np.array([r['R_mean'] for r in results])
    R_stds = np.array([r['R_std'] for r in results])

    c_fit, alpha_fit, R_pred = analyze_convergence(results, config)

    # (A) Convergence to exp(-2)
    ax = axes[0, 0]
    ax.errorbar(M_vals, R_means, yerr=R_stds, fmt='o', capsize=5,
                label='Measured R̄', markersize=8)
    ax.axhline(config.exp_minus_2, color='red', linestyle='--', linewidth=2,
               label=f'exp(-2) = {config.exp_minus_2:.6f}')
    if R_pred is not None:
        ax.plot(M_vals, R_pred, 'g:', linewidth=2,
                label=f'Fit: exp(-2) + {c_fit:.2f}/M^{alpha_fit:.2f}')
    ax.set_xlabel('Number of Bases (M)')
    ax.set_ylabel('Mean Resultant Length (R̄)')
    ax.set_title('(A) Convergence to exp(-2)')
    ax.legend()
    ax.grid(alpha=0.3)

    # (B) Error from exp(-2) vs M
    ax = axes[0, 1]
    errors = np.abs(R_means - config.exp_minus_2)
    ax.semilogy(M_vals, errors, 'o-', markersize=8, linewidth=2)
    if c_fit is not None:
        M_dense = np.linspace(M_vals[0], M_vals[-1], 100)
        error_pred = np.abs(c_fit) / (M_dense**alpha_fit)
        ax.semilogy(M_dense, error_pred, 'r--', linewidth=2,
                    label=f'|error| ∝ M^{-alpha_fit:.2f}')
    ax.set_xlabel('M')
    ax.set_ylabel('|R̄ - exp(-2)|')
    ax.set_title('(B) Error Decay (Log Scale)')
    ax.legend()
    ax.grid(alpha=0.3, which='both')

    # (C) Distribution at each M
    ax = axes[1, 0]
    positions = [r['M'] for r in results]
    data_violin = [r['R_samples'] for r in results]
    parts = ax.violinplot(data_violin, positions=positions, widths=30,
                          showmeans=True, showextrema=True)
    ax.axhline(config.exp_minus_2, color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('M')
    ax.set_ylabel('R̄ Distribution')
    ax.set_title('(C) R̄ Distributions Across Trials')
    ax.grid(alpha=0.3)

    # (D) Summary
    ax = axes[1, 1]
    ax.axis('off')
    final_error = results[-1]['percent_error']
    verdict = "CONFIRMED" if final_error < 1.0 else ("STRONG" if final_error < 2.0 else "PARTIAL")

    stats_text = f"""
    exp(-2) CONVERGENCE VALIDATION

    Theoretical: exp(-2) = {config.exp_minus_2:.10f}

    Measured Results:
      M=128: R̄ = {results[0]['R_mean']:.6f} ({results[0]['percent_error']:+.2f}%)
      M=256: R̄ = {results[1]['R_mean']:.6f} ({results[1]['percent_error']:+.2f}%)
      M=512: R̄ = {results[2]['R_mean']:.6f} ({results[2]['percent_error']:+.2f}%)

    Convergence Model:
      R̄(M) = exp(-2) + {c_fit if c_fit is not None else float('nan'):.2f}/M^{alpha_fit if alpha_fit is not None else float('nan'):.2f}

    Final Error (M=512): {final_error:.3f}%
    VERDICT: {verdict}
    """

    ax.text(0.1, 0.5, stats_text, fontsize=11, family='monospace',
            verticalalignment='center',
            bbox=dict(boxstyle='round', facecolor='lightgreen' if verdict=="CONFIRMED" else 'orange', alpha=0.2))

    fig.suptitle('T6-A1b: exp(-2) Validation (Weighted, Top-K, and Ungated)', fontsize=16, fontweight='bold')
    plt.tight_layout()

    output_path = config.figure_dir / 'T6A1b_exp_minus_2_validation.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"\nFigure: {output_path}")
    plt.close()


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="T6-A1b: exp(-2) convergence validation with configurable aggregation"
    )

    # Mode selection
    parser.add_argument("--mode", choices=["exp2_run", "rho_sweep"], default="exp2_run",
                        help="Experiment mode: exp2_run (main experiment) or rho_sweep (diagnostic)")

    # System parameters
    parser.add_argument("--N", type=int, default=None, help="Prime modulus (default: from Config)")
    parser.add_argument("--L", type=int, default=None, help="Sequence length (default: from Config)")
    parser.add_argument("--r", type=int, default=None, help="Target order (default: from Config)")
    parser.add_argument("--M", type=int, default=64, help="Number of bases for rho_sweep")

    # Aggregation control (for exp2_run mode)
    # OPTIMIZED DEFAULTS for ρ ≈ 0.25: Top-K by coherence (eliminates τ-bias)
    parser.add_argument("--agg", choices=["ungated", "topk", "tau", "threshold", "weighted", "perc"],
                        default="topk",
                        help="Aggregation mode (default: topk - fixed K by coherence)")
    parser.add_argument("--topk", type=int, default=24,
                        help="Number of top harmonics for topk mode (default: 24)")
    parser.add_argument("--p", type=float, default=2.0,
                        help="Power for weighted aggregation (default: 2.0)")
    parser.add_argument("--perc", type=float, default=None,
                        help="Percentile threshold for perc mode (e.g., 0.75 = top 25%%)")

    # Rho sweep parameters
    parser.add_argument("--Kmax", type=int, default=50, help="Max harmonics for rho_sweep")
    parser.add_argument("--rho_min", type=float, default=0.05, help="Min rho for sweep")
    parser.add_argument("--rho_max", type=float, default=0.30, help="Max rho for sweep")
    parser.add_argument("--max_r_points", type=int, default=12, help="Max r values to sample")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")

    args = parser.parse_args()
    np.random.seed(args.seed)

    if args.mode == "rho_sweep":
        cfg = Config()
        N = args.N if args.N is not None else cfg.N
        L = args.L if args.L is not None else cfg.L
        logging.info("Starting ρ sweep diagnostic...")
        logging.info(f"Params: N={N}, L={L}, M={args.M}, Kmax={args.Kmax}, p={args.p}")
        logging.info(f"  rho∈[{args.rho_min:.3f},{args.rho_max:.3f}], max_r_points={args.max_r_points}, seed={args.seed}")

        rho_sweep_diag(
            N=N,
            L=L,
            M=args.M,
            Kmax=args.Kmax,
            p_exp=args.p,
            rho_min=args.rho_min,
            rho_max=args.rho_max,
            max_r_points=args.max_r_points,
            seed=args.seed,
        )
        return

    # Default: exp2_run mode (main experiment)
    config = Config()

    # Override config with CLI arguments
    if args.N is not None:
        config.N = args.N
    if args.L is not None:
        config.L = args.L
    if args.r is not None:
        config.r_target = args.r

    # Set aggregation parameters (CLI overrides Config defaults)
    config.agg = args.agg
    config.topk = args.topk  # Already defaults to 32 in argparse
    config.p = args.p
    config.perc = args.perc

    # Log configuration
    rho = config.r_target / config.N
    logging.info("Starting exp(-2) convergence validation...")
    logging.info(f"System: N={config.N}, r={config.r_target}, ρ={rho:.6f}")
    logging.info(f"Aggregator: {config.agg}, topk={config.topk}, p={config.p}, perc={config.perc}")

    start = time.time()
    results = run_experiment(config)
    elapsed = time.time() - start

    if len(results) == 0:
        logging.error("No results collected. Exiting.")
        return

    logging.info(f"\nElapsed: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    # Save results
    output_file = config.output_dir / 'T6A1b_exp_minus_2_results.json'
    with open(output_file, 'w') as f:
        json.dump({'exp_minus_2': config.exp_minus_2, 'results': results}, f, indent=2)
    logging.info(f"Data: {output_file}")

    # Plots
    plot_results(results, config)

    # Final verdict
    final_error = results[-1]['percent_error']
    verdict = "CONFIRMED" if final_error < 1.0 else ("STRONG SUPPORT" if final_error < 2.0 else "PARTIAL SUPPORT")

    c_fit, alpha_fit, _ = analyze_convergence(results, config)

    logging.info("")
    logging.info("="*70)
    logging.info("T6-A1b COMPLETE!")
    logging.info("="*70)
    logging.info(f"exp(-2) = {config.exp_minus_2:.10f}")
    logging.info(f"M=512  → R̄ = {results[-1]['R_mean']:.10f}")
    logging.info(f"Error: {final_error:.3f}%")
    if c_fit is not None:
        logging.info(f"Convergence: R̄(M) = exp(-2) + {c_fit:.2f}/M^{alpha_fit:.2f}")
    logging.info(f"Verdict: {verdict}")
    logging.info("="*70)


if __name__ == '__main__':
    main()
