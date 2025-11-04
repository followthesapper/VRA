#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E7B — Information Feasibility Test (Fano Bound Analysis)
=========================================================

**Question**: Is shot reduction even information-theoretically possible?

**Hypothesis**: If mutual information I(Θ;R) is too low, NO prior (including VRA)
can reach 90% confidence with 10k shots → E7A's failure is fundamental.

**Method**:
1. Compute I(Θ;R) for uniform and VRA priors via GPU Monte Carlo
2. Apply Fano's inequality to bound minimal shots for P_error ≤ 0.10
3. Compare bounds: VRA vs. uniform

**Pass Criteria**:
- PASS: VRA's Fano bound < 0.7 × Uniform's bound
- FAIL: Both bounds ≫ 10k OR similar → E7A negative is fundamental

GPU ACCELERATED
"""

import argparse
import json
import time
import sys
from pathlib import Path
from typing import Dict, Tuple

import cupy as cp
import numpy as np
import matplotlib.pyplot as plt

# Add Tier3 directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from gpu_likelihood_kernel import (
    build_harmonic_lookup_gpu,
    compute_likelihood_vectorized_gpu,
    estimate_mutual_information_optimized_gpu
)


# ============================================================================
# GPU-Accelerated Information Theory Computations
# ============================================================================

def wrap01_gpu(x):
    """Wrap values to [0,1) on GPU."""
    y = cp.remainder(x, 1.0)
    y = cp.where(y < 0, y + 1.0, y)
    return y


def compute_log_likelihood_exact_gpu(theta_gpu, candidates_gpu, sigma: float):
    """
    Compute exact wrapped-Gaussian log-likelihood for all candidates.

    For each candidate r', sum over ALL harmonics m=0..r'-1:
    L(θ|r') = ∑_m exp(-0.5 * ((θ - m/r')/σ)²)

    Returns: (n_candidates,) array of log-likelihoods
    """
    n_cand = len(candidates_gpu)
    log_likes = cp.zeros(n_cand, dtype=cp.float32)

    for i, r_cand in enumerate(candidates_gpu):
        r_cand_int = int(r_cand)
        # Generate all harmonics m/r'
        m_vals = cp.arange(r_cand_int, dtype=cp.float32) / float(r_cand_int)

        # Compute circular distance to each harmonic
        dists = cp.abs(theta_gpu - m_vals)
        dists = cp.minimum(dists, 1.0 - dists)  # wrap

        # Sum likelihoods
        likes = cp.exp(-0.5 * (dists / sigma)**2)
        log_likes[i] = cp.log(likes.sum() + 1e-30)

    return log_likes


def estimate_mutual_information_gpu(
    r_true: int,
    r_min: int,
    r_max: int,
    sigma: float,
    prior_gpu,  # CuPy array
    n_samples: int = 100000,
    seed: int = 42
):
    """
    Estimate I(Θ;R) = E[log p(θ|r) / p(θ)] via Monte Carlo.

    Returns: I(Θ;R) in nats
    """
    cp.random.seed(seed)

    candidates_gpu = cp.arange(r_min, r_max + 1, dtype=cp.int32)
    n_cand = len(candidates_gpu)

    # Sample r values according to prior
    prior_np = cp.asnumpy(prior_gpu)
    r_samples = np.random.choice(candidates_gpu.get(), size=n_samples, p=prior_np)

    mi_sum = 0.0
    batch_size = 1000

    print(f"  Computing I(Θ;R) with {n_samples:,} Monte Carlo samples...")

    for batch_start in range(0, n_samples, batch_size):
        batch_end = min(batch_start + batch_size, n_samples)
        batch_r = r_samples[batch_start:batch_end]

        # Sample θ values
        batch_k = cp.random.randint(0, r_true, size=len(batch_r))
        batch_theta = wrap01_gpu(
            cp.array([r / float(r_true) for r in batch_k], dtype=cp.float32) +
            cp.random.normal(0.0, sigma, size=len(batch_r)).astype(cp.float32)
        )

        for i, (r_val, theta_val) in enumerate(zip(batch_r, cp.asnumpy(batch_theta))):
            theta_gpu_single = cp.array([theta_val], dtype=cp.float32)[0]

            # p(θ|r_val)
            log_p_theta_given_r = compute_log_likelihood_exact_gpu(
                theta_gpu_single, cp.array([r_val], dtype=cp.int32), sigma
            )[0]

            # p(θ) = ∑_r' p(θ|r') * p(r')
            log_likes_all = compute_log_likelihood_exact_gpu(
                theta_gpu_single, candidates_gpu, sigma
            )
            log_p_theta = cp.log(cp.sum(cp.exp(log_likes_all) * prior_gpu) + 1e-30)

            # I contribution: log(p(θ|r) / p(θ))
            mi_sum += float(log_p_theta_given_r - log_p_theta)

        if (batch_end // batch_size) % 10 == 0:
            print(f"    Progress: {batch_end:,}/{n_samples:,} ({100*batch_end/n_samples:.1f}%)")

    mi_nats = mi_sum / n_samples
    mi_bits = mi_nats / np.log(2)

    return mi_nats, mi_bits


def fano_bound(
    entropy_r: float,  # H(R) in bits
    mi_per_shot: float,  # I(Θ;R) in bits per shot
    p_error: float = 0.10
):
    """
    Apply Fano's inequality to bound minimum shots needed.

    Fano: H(R|Θ₁...Θₙ) ≤ H(P_error) + P_error·log(|R|-1)

    After n shots: H(R|Θ₁...Θₙ) ≤ H(R) - n·I(Θ;R)

    Solve for n: n ≥ (H(R) - H(P_error) - P_error·log(|R|-1)) / I(Θ;R)

    Returns: minimum shots needed
    """
    # Binary entropy of error
    if p_error == 0 or p_error == 1:
        h_pe = 0
    else:
        h_pe = -p_error * np.log2(p_error) - (1-p_error) * np.log2(1-p_error)

    # Number of candidates
    n_candidates = 2**entropy_r

    # Fano bound
    numerator = entropy_r - h_pe - p_error * np.log2(n_candidates - 1)

    if mi_per_shot <= 0:
        return np.inf

    n_min = numerator / mi_per_shot
    return max(1, int(np.ceil(n_min)))


# ============================================================================
# Experiment Runner
# ============================================================================

def run_experiment(args) -> Dict:
    print("=" * 70)
    print("E7B — Information Feasibility Test (Fano Bound)")
    print("=" * 70)
    print(f"GPU: CuPy {cp.__version__}")
    print(f"Device: {cp.cuda.Device()}")
    print(f"Parameters: r={args.r}, r∈[{args.r_min},{args.r_max}], σ={args.sigma}")
    print(f"Monte Carlo samples: {args.n_samples:,}")
    print("=" * 70)

    start_time = time.time()

    out_dir = Path("../Data")
    fig_dir = Path("../Figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    candidates = cp.arange(args.r_min, args.r_max + 1, dtype=cp.int32)
    n_candidates = len(candidates)
    entropy_r_bits = np.log2(n_candidates)

    print(f"\nCandidate set: {n_candidates} values")
    print(f"H(R) = {entropy_r_bits:.2f} bits")

    # ========================================================================
    # Compute I(Θ;R) for UNIFORM prior
    # ========================================================================
    print("\n" + "=" * 70)
    print("Computing I(Θ;R) for UNIFORM prior...")
    print("=" * 70)

    prior_uniform_gpu = cp.ones(n_candidates, dtype=cp.float32) / n_candidates
    mi_uniform_nats = estimate_mutual_information_optimized_gpu(
        r_true=args.r,
        r_min=args.r_min,
        r_max=args.r_max,
        sigma=args.sigma,
        prior_gpu=prior_uniform_gpu,
        n_samples=args.n_samples,
        seed=args.seed,
        use_mega=False
    )
    mi_uniform_bits = mi_uniform_nats / np.log(2)  # Convert nats to bits

    print(f"\n✅ I(Θ;R) | uniform = {mi_uniform_nats:.6f} nats = {mi_uniform_bits:.6f} bits/shot")

    # ========================================================================
    # Compute I(Θ;R) for VRA prior (synthetic)
    # ========================================================================
    print("\n" + "=" * 70)
    print("Computing I(Θ;R) for VRA prior (synthetic)...")
    print("=" * 70)

    # Build VRA-like prior (same as E7A)
    from E7_shot_reduction_study import make_vra_prior_gpu
    prior_vra_gpu = make_vra_prior_gpu(
        r_true=args.r,
        r_min=args.r_min,
        r_max=args.r_max,
        prior_hit=args.prior_hit,
        prior_k=args.prior_k,
        seed=args.seed
    )

    mi_vra_nats = estimate_mutual_information_optimized_gpu(
        r_true=args.r,
        r_min=args.r_min,
        r_max=args.r_max,
        sigma=args.sigma,
        prior_gpu=prior_vra_gpu,
        n_samples=args.n_samples,
        seed=args.seed + 1,
        use_mega=False
    )
    mi_vra_bits = mi_vra_nats / np.log(2)  # Convert nats to bits

    print(f"\n✅ I(Θ;R) | VRA = {mi_vra_nats:.6f} nats = {mi_vra_bits:.6f} bits/shot")

    # ========================================================================
    # Compute Fano Bounds
    # ========================================================================
    print("\n" + "=" * 70)
    print("Applying Fano's Inequality...")
    print("=" * 70)

    n_min_uniform = fano_bound(entropy_r_bits, mi_uniform_bits, args.p_error)
    n_min_vra = fano_bound(entropy_r_bits, mi_vra_bits, args.p_error)

    print(f"\nFano bounds (P_error ≤ {args.p_error}):")
    print(f"  Uniform prior: ≥ {n_min_uniform:,} shots")
    print(f"  VRA prior:     ≥ {n_min_vra:,} shots")

    ratio = n_min_vra / max(n_min_uniform, 1)
    print(f"\n  Ratio (VRA/Uniform): {ratio:.3f}")

    # ========================================================================
    # Verdict
    # ========================================================================
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    passed = (ratio < args.pass_ratio)

    if n_min_uniform > 100000 and n_min_vra > 100000:
        verdict_text = "❌ BOTH INFEASIBLE"
        interpretation = (
            f"Both bounds ≫ 10k shots → E7A's failure is FUNDAMENTAL.\n"
            f"This regime is information-theoretically impossible for Bayesian decoding.\n"
            f"No prior (including VRA) can help here."
        )
    elif passed:
        verdict_text = "✅ PASS"
        interpretation = (
            f"VRA prior reduces theoretical bound by {100*(1-ratio):.1f}%.\n"
            f"Shot reduction is theoretically possible — E7A failed due to parameters.\n"
            f"Proceed with E7C-E7G to find workable regimes."
        )
    else:
        verdict_text = "⚠️ MARGINAL"
        interpretation = (
            f"VRA provides modest theoretical advantage but ratio {ratio:.2f} > {args.pass_ratio}.\n"
            f"May not translate to practical shot reduction.\n"
            f"E7C-E7G should test easier regimes."
        )

    print(f"\n{verdict_text}")
    print(f"\n{interpretation}")

    runtime = time.time() - start_time

    # ========================================================================
    # Save Results
    # ========================================================================
    summary = {
        "r_true": args.r,
        "r_min": args.r_min,
        "r_max": args.r_max,
        "sigma": args.sigma,
        "n_candidates": int(n_candidates),
        "entropy_r_bits": float(entropy_r_bits),
        "n_samples": args.n_samples,
        "mutual_information": {
            "uniform_nats": float(mi_uniform_nats),
            "uniform_bits": float(mi_uniform_bits),
            "vra_nats": float(mi_vra_nats),
            "vra_bits": float(mi_vra_bits),
            "ratio_vra_over_uniform": float(mi_vra_bits / max(mi_uniform_bits, 1e-12))
        },
        "fano_bounds": {
            "p_error": args.p_error,
            "uniform_min_shots": int(n_min_uniform) if np.isfinite(n_min_uniform) else "inf",
            "vra_min_shots": int(n_min_vra) if np.isfinite(n_min_vra) else "inf",
            "ratio_vra_over_uniform": float(ratio) if np.isfinite(ratio) else "inf"
        },
        "verdict": {
            "passed": bool(passed),
            "verdict": verdict_text,
            "interpretation": interpretation
        },
        "runtime_seconds": float(runtime),
        "gpu_device": str(cp.cuda.Device())
    }

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_json = out_dir / f"{timestamp}_E7B_info_feasibility_r{args.r}_sig{args.sigma}.json"
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n💾 Saved: {out_json}")

    # ========================================================================
    # Generate Figures
    # ========================================================================
    print("\n📈 Generating figures...")

    # Figure 1: Mutual Information Comparison
    fig, ax = plt.subplots(figsize=(8, 6))
    priors = ['Uniform', 'VRA']
    mi_values = [mi_uniform_bits, mi_vra_bits]
    colors = ['steelblue', 'orange']

    bars = ax.bar(priors, mi_values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    ax.set_ylabel('Mutual Information I(Θ;R) [bits/shot]', fontsize=12)
    ax.set_title(f'E7B: Mutual Information per Shot (r={args.r}, σ={args.sigma})', fontsize=13)
    ax.grid(axis='y', alpha=0.3)

    # Annotate bars
    for bar, val in zip(bars, mi_values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height,
                f'{val:.4f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    fig1 = fig_dir / f"{timestamp}_E7B_mutual_information_r{args.r}_sig{args.sigma}.png"
    plt.tight_layout()
    plt.savefig(fig1, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   Saved {fig1}")

    # Figure 2: Fano Bounds Comparison
    fig, ax = plt.subplots(figsize=(8, 6))
    bound_values = [n_min_uniform, n_min_vra]

    bars = ax.bar(priors, bound_values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    ax.set_ylabel('Minimum Shots (Fano Bound)', fontsize=12)
    ax.set_title(f'E7B: Information-Theoretic Shot Bounds (P_error ≤ {args.p_error})', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    ax.set_yscale('log')

    # Reference line at 10k
    ax.axhline(10000, color='red', linestyle='--', linewidth=2, label='E7A max_shots=10k')
    ax.legend(fontsize=11)

    # Annotate bars
    for bar, val in zip(bars, bound_values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height,
                f'{val:,}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    fig2 = fig_dir / f"{timestamp}_E7B_fano_bounds_r{args.r}_sig{args.sigma}.png"
    plt.tight_layout()
    plt.savefig(fig2, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   Saved {fig2}")

    print("\n" + "=" * 70)
    print(f"E7B Complete — Runtime: {runtime:.1f}s")
    print("=" * 70)

    return summary


def parse_args():
    p = argparse.ArgumentParser(description="E7B — Information Feasibility Test (GPU)")
    p.add_argument("--r", type=int, default=168, help="True period")
    p.add_argument("--r-min", type=int, default=32, dest="r_min")
    p.add_argument("--r-max", type=int, default=1024, dest="r_max")
    p.add_argument("--sigma", type=float, default=0.02, help="Phase noise")
    p.add_argument("--prior-hit", type=float, default=0.55, dest="prior_hit")
    p.add_argument("--prior-k", type=int, default=12, dest="prior_k")
    p.add_argument("--n-samples", type=int, default=100000, dest="n_samples",
                   help="Monte Carlo samples for MI estimation")
    p.add_argument("--p-error", type=float, default=0.10, dest="p_error",
                   help="Target error probability for Fano bound")
    p.add_argument("--pass-ratio", type=float, default=0.70, dest="pass_ratio",
                   help="Pass if VRA/Uniform ratio < this")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_experiment(args)
