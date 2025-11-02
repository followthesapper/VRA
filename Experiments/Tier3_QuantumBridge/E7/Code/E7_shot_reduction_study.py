#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E7 — Shot Reduction Study (Pre-solver, QPE-like Post-Processing) — GPU ACCELERATED
==================================================================================
Goal
----
Show that conditioning phase-decoding on a VRA-derived prior over {k/r}
reduces the number of shots needed to confidently recover the true period r.

Claim to test (pass criterion):
    Required shots with VRA prior ≤ 0.7× baseline (paired test CI excludes 1.0).

What this script does
---------------------
• Simulates QPE-like shots: each shot yields a phase θ ≈ k/r (mod 1) with Gaussian
  phase noise σ (wrapped on the unit circle).
• Performs Bayesian period decoding over candidate r' ∈ [r_min, r_max] using a
  wrapped-Gaussian likelihood per shot.
• Compares two priors:
    (A) Uniform prior over r'  (Baseline)
    (B) VRA prior over r'      (Peaked over a sparse shortlist; parameterized by hit-rate)
• Stops the shot-accumulation loop as soon as posterior mass at MAP equals the true r
  AND posterior confidence ≥ target (e.g., 0.9). Records shots needed.
• Repeats over many trials; reports paired shot-count ratios, bootstrap CI, decision.

GPU ACCELERATION
----------------
This version is GPU-ONLY using CuPy. All computations run on NVIDIA GPU.
No CPU fallback. Requires CuPy and CUDA-capable GPU.

Outputs
-------
• JSON summary with median shot counts and 95% bootstrap CI for the paired ratio
• Two figures (PNG):
    - CDF of shots-to-confidence (baseline vs VRA prior)
    - Histogram of paired ratios (shots_VRA / shots_baseline)
• CSV of per-trial results (optional via --save-csv)

Usage
-----
python Experiments/Tier3_QuantumBridge/E7_shot_reduction_study.py \
    --r 168 --r-min 32 --r-max 1024 --sigma 0.02 --trials 500 \
    --target 0.9 --prior-hit 0.55 --prior-k 12

"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict, Tuple
import time

import cupy as cp
import numpy as np  # Only for CPU operations (plotting, JSON)
import matplotlib.pyplot as plt


# ----------------------------
# GPU Utilities: wrapped distances
# ----------------------------

def wrap01_gpu(x):
    """Wrap real values to [0,1) on GPU."""
    y = cp.remainder(x, 1.0)
    y = cp.where(y < 0, y + 1.0, y)
    return y


# ----------------------------------------------------
# Likelihood: θ ~ wrapped N(k/r, σ^2) for some integer
# ----------------------------------------------------

def log_likelihood_theta_given_r_gpu(theta_gpu, r_candidate: int, sigma: float) -> float:
    """
    Compute log-likelihood of observed phases θ under candidate r'.
    We model θ as a wrapped-Gaussian around the nearest multiple of 1/r'.
    For each θ, distance = min_m ||θ - m/r'||_circle, and likelihood ∝ exp(-0.5*(d/σ)^2).

    All operations on GPU.
    """
    phi = theta_gpu * r_candidate
    frac = cp.abs(phi - cp.round(phi))
    d = frac / r_candidate  # unit circle distance
    return float(cp.asnumpy(-0.5 * cp.sum((d / sigma)**2)))


# ------------------------------------------------------
# Priors over r: Uniform vs "VRA-derived" sparse prior
# ------------------------------------------------------

def make_uniform_prior_gpu(r_min: int, r_max: int):
    """Create uniform prior on GPU."""
    vals = cp.ones(r_max - r_min + 1, dtype=cp.float32)
    return vals / vals.sum()


def make_vra_prior_gpu(
    r_true: int,
    r_min: int,
    r_max: int,
    prior_hit: float = 0.55,
    prior_k: int = 12,
    seed: int = 42
):
    """
    Construct a *parameterized* sparse prior meant to emulate a shortlist produced by
    a lightweight classical VRA precomputation.

    Prior model:
      • With probability prior_hit, the shortlist contains the true r.
      • The shortlist size is prior_k. Remaining shortlist entries are distractors.
      • Mass is concentrated on the shortlist using a softmax kernel.

    Returns CuPy array on GPU.
    """
    # Use NumPy for random generation, then transfer to GPU
    rng = np.random.default_rng(seed)
    R = np.arange(r_min, r_max + 1)
    nR = len(R)

    # Pick shortlist indices
    shortlist = set()
    include_true = rng.random() < prior_hit

    # Structural hints
    structural = []
    for h in [2, 3, 4, 5, 6]:
        if r_true // h >= r_min and r_true // h <= r_max:
            structural.append(r_true // h)
        if r_true * h <= r_max:
            structural.append(r_true * h)

    rng.shuffle(structural)
    for v in structural:
        if len(shortlist) >= max(1, prior_k - 1):
            break
        if v != r_true and r_min <= v <= r_max:
            shortlist.add(int(v))

    # Ensure shortlist has prior_k elements
    pool = list(set(R.tolist()) - shortlist - {r_true})
    rng.shuffle(pool)
    while len(shortlist) < max(1, prior_k - (1 if include_true else 0)):
        shortlist.add(int(pool.pop()))

    if include_true:
        shortlist.add(r_true)

    # Build prior weights on GPU
    logits = np.full(nR, -5.0, dtype=np.float32)  # background floor
    for val in shortlist:
        idx = val - r_min
        logits[idx] = 2.0 if val == r_true else 1.0

    # Mild monotone bias
    bias = 0.5 * (1.0 - (R - r_min) / max(1, r_max - r_min))
    logits = logits + bias

    # Transfer to GPU and softmax
    logits_gpu = cp.asarray(logits, dtype=cp.float32)
    logits_gpu -= logits_gpu.max()
    w_gpu = cp.exp(logits_gpu)
    w_gpu /= w_gpu.sum()
    return w_gpu


# --------------------------------------------------------
# Bayesian decoder loop: accumulate shots until confidence
# --------------------------------------------------------

def run_decoder_once_gpu(
    r_true: int,
    r_min: int,
    r_max: int,
    sigma: float,
    target_conf: float,
    prior_gpu,  # CuPy array
    max_shots: int = 10000,
    seed: int | None = None,
) -> int:
    """
    Return shots needed to exceed target_conf on true r in posterior (MAP == r_true),
    or max_shots if not achieved.

    All operations on GPU.
    """
    # Use CuPy random for GPU operations
    if seed is not None:
        cp.random.seed(seed)

    candidates = cp.arange(r_min, r_max + 1, dtype=cp.int32)
    # posterior ∝ prior initially
    log_post = cp.log(prior_gpu + 1e-30)

    for shot in range(1, max_shots + 1):
        # Sample k ~ Uniform{0..r_true-1}
        k = int(cp.random.randint(0, r_true))
        theta = wrap01_gpu(k / r_true + float(cp.random.normal(0.0, sigma)))

        # Update log posterior for each candidate r' (vectorized on GPU)
        # Vectorize over candidates
        theta_expanded = cp.full(len(candidates), float(theta), dtype=cp.float32)

        # Compute log-likelihood for all candidates in parallel
        phi = theta_expanded * candidates.astype(cp.float32)
        frac = cp.abs(phi - cp.round(phi))
        d = frac / candidates.astype(cp.float32)
        ll = -0.5 * ((d / sigma)**2)

        log_post = log_post + ll

        # Normalize safely
        m = log_post.max()
        post = cp.exp(log_post - m)
        post /= post.sum()

        # Check stopping condition
        idx_true = r_true - r_min
        r_map_idx = int(cp.argmax(post))
        r_map = int(candidates[r_map_idx])
        conf = float(post[r_map_idx])

        if r_map == r_true and conf >= target_conf:
            return shot

    return max_shots


def paired_bootstrap_ci_gpu(x_gpu, y_gpu, B: int = 10000, seed: int = 123) -> Tuple[float, Tuple[float, float]]:
    """
    Bootstrap CI for ratio median(y/x) with paired resampling.
    Returns (median_ratio, (ci_lo, ci_hi)).

    All operations on GPU.
    """
    cp.random.seed(seed)
    n = len(x_gpu)
    ratios = y_gpu / cp.maximum(x_gpu, 1e-12)

    boot_medians = cp.empty(B, dtype=cp.float32)
    for b in range(B):
        idx = cp.random.randint(0, n, size=n)
        boot_medians[b] = cp.median(ratios[idx])

    ci_lo, ci_hi = cp.percentile(boot_medians, [2.5, 97.5])
    return float(cp.median(ratios)), (float(ci_lo), float(ci_hi))


# -------------------------
# Experiment runner (main)
# -------------------------

def run_experiment(args) -> Dict:
    print("=" * 70)
    print("E7 — Shot Reduction Study (GPU ACCELERATED)")
    print("=" * 70)
    print(f"GPU: CuPy {cp.__version__}")
    print(f"Device: {cp.cuda.Device()}")
    print(f"Trials: {args.trials}")
    print(f"r={args.r}, r_range=[{args.r_min}, {args.r_max}], σ={args.sigma}")
    print("=" * 70)

    start_time = time.time()

    # NumPy RNG for trial-level randomness
    rng = np.random.default_rng(args.seed)

    out_dir = Path("Data/Experiments/Tier3/E7")
    fig_dir = Path("Figures/Experiments/Tier3/E7")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Build uniform prior on GPU
    prior_uniform_gpu = make_uniform_prior_gpu(args.r_min, args.r_max)

    # For fairness, each trial gets an independent VRA prior draw
    def draw_vra_prior_gpu():
        return make_vra_prior_gpu(
            r_true=args.r,
            r_min=args.r_min,
            r_max=args.r_max,
            prior_hit=args.prior_hit,
            prior_k=args.prior_k,
            seed=int(rng.integers(0, 2**31 - 1))
        )

    # Allocate GPU arrays for results
    shots_base_gpu = cp.zeros(args.trials, dtype=cp.int32)
    shots_vra_gpu = cp.zeros(args.trials, dtype=cp.int32)

    print(f"\n🚀 Running {args.trials} trials on GPU...")
    print(f"Progress will be logged to /tmp/e7_progress.log")
    print("=" * 70)

    import sys
    trial_times = []

    for t in range(args.trials):
        trial_start = time.time()

        # Baseline (uniform prior)
        shots_base_gpu[t] = run_decoder_once_gpu(
            r_true=args.r,
            r_min=args.r_min,
            r_max=args.r_max,
            sigma=args.sigma,
            target_conf=args.target,
            prior_gpu=prior_uniform_gpu,
            max_shots=args.max_shots,
            seed=int(rng.integers(0, 2**31 - 1))
        )

        # VRA prior
        prior_vra_gpu = draw_vra_prior_gpu()
        shots_vra_gpu[t] = run_decoder_once_gpu(
            r_true=args.r,
            r_min=args.r_min,
            r_max=args.r_max,
            sigma=args.sigma,
            target_conf=args.target,
            prior_gpu=prior_vra_gpu,
            max_shots=args.max_shots,
            seed=int(rng.integers(0, 2**31 - 1))
        )

        # Log progress after each trial
        trial_elapsed = time.time() - trial_start
        trial_times.append(trial_elapsed)
        total_elapsed = time.time() - start_time

        avg_time_per_trial = total_elapsed / (t + 1)
        remaining_trials = args.trials - (t + 1)
        eta_seconds = avg_time_per_trial * remaining_trials
        eta_minutes = eta_seconds / 60

        progress_msg = (
            f"[{t+1:3d}/{args.trials}] "
            f"Trial: {trial_elapsed:5.2f}s | "
            f"Avg: {avg_time_per_trial:5.2f}s/trial | "
            f"Elapsed: {total_elapsed/60:6.1f}min | "
            f"ETA: {eta_minutes:6.1f}min | "
            f"Baseline: {int(shots_base_gpu[t]):4d} shots | "
            f"VRA: {int(shots_vra_gpu[t]):4d} shots"
        )

        print(progress_msg)
        sys.stdout.flush()  # Force output to display immediately

        # Also write to progress file
        with open("/tmp/e7_progress.log", "a") as pf:
            pf.write(progress_msg + "\n")
            pf.flush()

        # Aggressive GPU memory cleanup every trial
        cp.get_default_memory_pool().free_all_blocks()
        cp.get_default_pinned_memory_pool().free_all_blocks()

    total_time = time.time() - start_time
    print(f"\n✅ All trials complete in {total_time:.1f}s ({total_time/args.trials:.2f}s/trial)")

    # Compute paired ratio CI on GPU
    print("\n📊 Computing bootstrap confidence intervals on GPU...")
    median_ratio, (ci_lo, ci_hi) = paired_bootstrap_ci_gpu(
        shots_base_gpu.astype(cp.float32),
        shots_vra_gpu.astype(cp.float32),
        B=args.bootstraps,
        seed=args.seed + 1
    )

    # Transfer results to CPU for analysis
    shots_base = cp.asnumpy(shots_base_gpu).astype(int)
    shots_vra = cp.asnumpy(shots_vra_gpu).astype(int)

    passed = (median_ratio <= args.pass_ratio) and (ci_hi < 1.0)

    summary = {
        "r_true": args.r,
        "r_min": args.r_min,
        "r_max": args.r_max,
        "sigma": args.sigma,
        "target_conf": args.target,
        "trials": args.trials,
        "max_shots": args.max_shots,
        "prior_hit": args.prior_hit,
        "prior_k": args.prior_k,
        "median_shots_baseline": float(np.median(shots_base)),
        "median_shots_vra": float(np.median(shots_vra)),
        "median_ratio_vra_over_base": float(median_ratio),
        "ratio_ci_95": [float(ci_lo), float(ci_hi)],
        "pass_ratio_threshold": args.pass_ratio,
        "passed": bool(passed),
        "runtime_seconds": float(total_time),
        "gpu_device": str(cp.cuda.Device()),
    }

    # Save JSON
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_json = out_dir / f"{timestamp}_E7_results_r{args.r}_sig{args.sigma}_T{args.target}_n{args.trials}.json"
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"💾 Wrote summary: {out_json}")

    # Optional CSV
    if args.save_csv:
        out_csv = out_dir / f"{timestamp}_E7_per_trial_r{args.r}_sig{args.sigma}_n{args.trials}.csv"
        with open(out_csv, "w") as f:
            f.write("trial,shots_baseline,shots_vra,ratio\n")
            for i in range(args.trials):
                r = shots_vra[i] / max(shots_base[i], 1e-12)
                f.write(f"{i+1},{shots_base[i]},{shots_vra[i]},{r:.6f}\n")
        print(f"💾 Wrote per-trial CSV: {out_csv}")

    # Figures
    print("\n📈 Generating figures...")

    # 1) CDF of shots
    def ecdf(x: np.ndarray):
        xs = np.sort(x)
        ys = np.arange(1, len(x) + 1) / len(x)
        return xs, ys

    xs_b, ys_b = ecdf(shots_base)
    xs_v, ys_v = ecdf(shots_vra)

    plt.figure(figsize=(7.5, 5.0))
    plt.plot(xs_b, ys_b, label="Baseline (uniform prior)", linewidth=2)
    plt.plot(xs_v, ys_v, label="VRA prior", linewidth=2)
    plt.xlabel("Shots to reach target confidence", fontsize=12)
    plt.ylabel("Empirical CDF", fontsize=12)
    plt.title(f"E7: Shots-to-Confidence CDF (r={args.r}, σ={args.sigma}, target={args.target})", fontsize=13)
    plt.grid(alpha=0.3)
    plt.legend(fontsize=11)
    fig1 = fig_dir / f"{timestamp}_E7_shots_cdf_r{args.r}_sig{args.sigma}_T{args.target}.png"
    plt.tight_layout()
    plt.savefig(fig1, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"   Saved {fig1}")

    # 2) Histogram of ratios
    ratios = shots_vra / np.maximum(shots_base, 1e-12)
    plt.figure(figsize=(7.5, 5.0))
    plt.hist(ratios, bins=40, alpha=0.8, edgecolor="black", color="steelblue")
    plt.axvline(1.0, color="red", linestyle="--", linewidth=2, label="Parity (1.0)")
    plt.axvline(args.pass_ratio, color="orange", linestyle=":", linewidth=2, label=f"Pass threshold ({args.pass_ratio:.2f})")
    plt.xlabel("Shots ratio (VRA / Baseline)", fontsize=12)
    plt.ylabel("Frequency", fontsize=12)
    plt.title(f"E7: Paired Ratios (r={args.r}) — median={median_ratio:.3f}, CI=[{ci_lo:.3f},{ci_hi:.3f}]", fontsize=13)
    plt.legend(fontsize=11)
    plt.grid(alpha=0.3)
    fig2 = fig_dir / f"{timestamp}_E7_ratio_hist_r{args.r}_sig{args.sigma}.png"
    plt.tight_layout()
    plt.savefig(fig2, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"   Saved {fig2}")

    # Console verdict
    verdict = "✅ PASS" if passed else "❌ FAIL"
    print("\n" + "=" * 70)
    print("E7 — Shot Reduction Study (Pre-solver) — SUMMARY")
    print("=" * 70)
    print(f"Runtime                 : {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"Median shots (baseline) : {summary['median_shots_baseline']:.1f}")
    print(f"Median shots (VRA prior): {summary['median_shots_vra']:.1f}")
    print(f"Median ratio (VRA/base) : {summary['median_ratio_vra_over_base']:.3f}")
    print(f"95% CI (ratio)          : [{ci_lo:.3f}, {ci_hi:.3f}]")
    print(f"Pass threshold (ratio)  : ≤ {args.pass_ratio:.2f} and CI_hi < 1.0")
    print(f"VERDICT                 : {verdict}")
    print("=" * 70)

    return summary


def parse_args():
    p = argparse.ArgumentParser(description="E7 — Shot Reduction Study (GPU Accelerated)")
    p.add_argument("--r", type=int, default=168, help="True period r")
    p.add_argument("--r-min", type=int, default=32, dest="r_min", help="Minimum r' in candidate grid")
    p.add_argument("--r-max", type=int, default=1024, dest="r_max", help="Maximum r' in candidate grid")
    p.add_argument("--sigma", type=float, default=0.02, help="Phase noise σ (wrapped Gaussian)")
    p.add_argument("--target", type=float, default=0.90, help="Posterior confidence threshold")
    p.add_argument("--trials", type=int, default=500, help="Number of Monte Carlo trials")
    p.add_argument("--max-shots", type=int, default=10000, dest="max_shots", help="Safety cap on shots per trial")
    p.add_argument("--prior-hit", type=float, default=0.55, dest="prior_hit", help="VRA prior: shortlist includes true r with this probability")
    p.add_argument("--prior-k", type=int, default=12, dest="prior_k", help="VRA prior shortlist size")
    p.add_argument("--bootstraps", type=int, default=10000, help="Bootstrap resamples for ratio CI")
    p.add_argument("--pass-ratio", type=float, default=0.70, dest="pass_ratio", help="Pass threshold for median ratio (VRA/base)")
    p.add_argument("--seed", type=int, default=42, help="RNG seed")
    p.add_argument("--save-csv", action="store_true", help="Also save per-trial CSV")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_experiment(args)
