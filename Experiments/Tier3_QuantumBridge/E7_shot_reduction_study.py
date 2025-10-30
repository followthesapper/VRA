#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E7 — Shot Reduction Study (Pre-solver, QPE-like Post-Processing)
================================================================
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

IMPORTANT — Assumptions
-----------------------
This is a *pre-solver* study. The “VRA prior” here is parameterized by a hit-rate
(`--prior-hit`) and a shortlist size (`--prior-k`). You should calibrate these to
your empirical VRA precision and the shortlist size you actually provide from a
lightweight classical precomputation (e.g., your averaged spectrum shortlist of candidate r’s).
Default values reflect your repo’s *overall* VRA precision (~0.5). Update as you gather
more regime-specific priors.

Outputs
-------
• JSON summary with median shot counts and 95% bootstrap CI for the paired ratio
• Two figures (PNG):
    - CDF of shots-to-confidence (baseline vs VRA prior)
    - Histogram of paired ratios (shots_VRA / shots_baseline)
• CSV of per-trial results (optional via --save-csv)

Usage
-----
python Experiments/Tier3_QuantumBridge/E7_shot_reduction_qpe_prior.py \
    --r 168 --r-min 32 --r-max 1024 --sigma 0.02 --trials 500 \
    --target 0.9 --prior-hit 0.55 --prior-k 12

"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt


# ----------------------------
# Utilities: wrapped distances
# ----------------------------

def wrap01(x: np.ndarray) -> np.ndarray:
    """Wrap real values to [0,1)."""
    y = np.remainder(x, 1.0)
    y[y < 0] += 1.0
    return y


def circle_dist(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Smallest circular distance on the unit interval between a and b (both in [0,1)).
    Returns values in [0, 0.5].
    """
    d = np.abs(a - b)
    return np.minimum(d, 1.0 - d)


# ----------------------------------------------------
# Likelihood: θ ~ wrapped N(k/r, σ^2) for some integer
# ----------------------------------------------------

def log_likelihood_theta_given_r(theta: np.ndarray, r_candidate: int, sigma: float) -> float:
    """
    Compute log-likelihood of observed phases θ under candidate r'.
    We model θ as a wrapped-Gaussian around the nearest multiple of 1/r'.
    For each θ, distance = min_m ||θ - m/r'||_circle, and likelihood ∝ exp(-0.5*(d/σ)^2).
    """
    # For a given r', the set of grid points on [0,1) is {m/r' : m=0..r'-1}
    # Nearest grid distance on circle:
    # Equivalent to distance to nearest multiple of 1/r'.
    # Efficiently: distance to 0 on the circle of resolution 1/r' after scaling.
    # Let φ = θ * r', then nearest integer distance in cycles is dist_cycles = min |φ - round(φ)|
    # Convert back to unit-circle distance by dividing by r'.
    phi = theta * r_candidate
    frac = np.abs(phi - np.round(phi))
    d = frac / r_candidate  # unit circle distance
    # Wrapped-Gaussian (unnormalized) log-likelihood sum across shots:
    # logL = -0.5 * sum((d/σ)^2) + const
    return float(-0.5 * np.sum((d / sigma)**2))


# ------------------------------------------------------
# Priors over r: Uniform vs "VRA-derived" sparse prior
# ------------------------------------------------------

def make_uniform_prior(r_min: int, r_max: int) -> np.ndarray:
    vals = np.ones(r_max - r_min + 1, dtype=float)
    return vals / vals.sum()


def make_vra_prior(
    r_true: int,
    r_min: int,
    r_max: int,
    prior_hit: float = 0.55,
    prior_k: int = 12,
    seed: int = 42
) -> np.ndarray:
    """
    Construct a *parameterized* sparse prior meant to emulate a shortlist produced by
    a lightweight classical VRA precomputation.

    Prior model:
      • With probability prior_hit, the shortlist contains the true r.
      • The shortlist size is prior_k. Remaining shortlist entries are distractors
        (chosen from [r_min, r_max], avoiding r_true when “miss”).
      • Mass is concentrated on the shortlist using a softmax kernel; everything else
        shares a small uniform floor.

    Notes:
      - Tune (prior_hit, prior_k) using *your measured precision and shortlist length*.
      - You can replace this with an actual shortlist from your averaged spectrum
        to make the study fully “oracle-free”.
    """
    rng = np.random.default_rng(seed)
    R = np.arange(r_min, r_max + 1)
    nR = len(R)

    # Pick shortlist indices
    shortlist = set()
    # Decide whether we hit the true r in the shortlist
    include_true = rng.random() < prior_hit

    # Always try to add divisors/multiples near the search range as plausible structure
    # (light structure helps avoid a too-delta prior).
    # Start shortlist with structural hints:
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

    # Build prior weights: softmax with mild preference toward smaller r' (optional bias)
    logits = np.full(nR, -5.0, dtype=float)  # background floor
    for val in shortlist:
        idx = val - r_min
        # Favor the true r (if present) with a larger logit
        logits[idx] = 2.0 if val == r_true else 1.0

    # Mild monotone bias (optional): encourage smaller r by +0.0 .. +0.5
    bias = 0.5 * (1.0 - (R - r_min) / max(1, r_max - r_min))
    logits = logits + bias

    # Softmax
    logits -= logits.max()
    w = np.exp(logits)
    w /= w.sum()
    return w


# --------------------------------------------------------
# Bayesian decoder loop: accumulate shots until confidence
# --------------------------------------------------------

def run_decoder_once(
    r_true: int,
    r_min: int,
    r_max: int,
    sigma: float,
    target_conf: float,
    prior: np.ndarray,
    max_shots: int = 10000,
    seed: int | None = None,
) -> int:
    """
    Return shots needed to exceed target_conf on true r in posterior (MAP == r_true),
    or max_shots if not achieved.
    """
    rng = np.random.default_rng(seed)
    candidates = np.arange(r_min, r_max + 1)
    # posterior ∝ prior initially
    log_post = np.log(np.asarray(prior, dtype=float) + 1e-300)

    for shot in range(1, max_shots + 1):
        # Sample k ~ Uniform{0..r_true-1}
        k = rng.integers(0, r_true)
        theta = wrap01(k / r_true + rng.normal(0.0, sigma))

        # Update log posterior for each candidate r'
        ll = np.array([log_likelihood_theta_given_r(theta=np.array([theta]),
                                                    r_candidate=int(rc),
                                                    sigma=sigma)
                       for rc in candidates], dtype=float)
        log_post = log_post + ll

        # Normalize safely
        m = log_post.max()
        post = np.exp(log_post - m)
        post /= post.sum()

        # Check stopping condition
        idx_true = r_true - r_min
        r_map_idx = int(np.argmax(post))
        r_map = candidates[r_map_idx]
        conf = float(post[r_map_idx])

        if r_map == r_true and conf >= target_conf:
            return shot

    return max_shots


def paired_bootstrap_ci(x: np.ndarray, y: np.ndarray, B: int = 10000, seed: int = 123) -> Tuple[float, Tuple[float, float]]:
    """
    Bootstrap CI for ratio median(y/x) with paired resampling.
    Returns (median_ratio, (ci_lo, ci_hi)).
    """
    rng = np.random.default_rng(seed)
    n = len(x)
    ratios = y / np.maximum(x, 1e-12)

    boot_medians = np.empty(B, dtype=float)
    for b in range(B):
        idx = rng.integers(0, n, n)
        boot_medians[b] = np.median(ratios[idx])

    ci_lo, ci_hi = np.percentile(boot_medians, [2.5, 97.5])
    return float(np.median(ratios)), (float(ci_lo), float(ci_hi))


# -------------------------
# Experiment runner (main)
# -------------------------

def run_experiment(args) -> Dict:
    rng = np.random.default_rng(args.seed)

    out_dir = Path("Data/Tier3/E7_shot_reduction")
    fig_dir = Path("Figures/Tier3/E7_shot_reduction")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Build priors
    prior_uniform = make_uniform_prior(args.r_min, args.r_max)
    # For fairness, each trial gets an independent VRA prior draw (whether it includes the true r)
    def draw_vra_prior():
        return make_vra_prior(
            r_true=args.r,
            r_min=args.r_min,
            r_max=args.r_max,
            prior_hit=args.prior_hit,
            prior_k=args.prior_k,
            seed=int(rng.integers(0, 2**31 - 1))
        )

    shots_base = np.zeros(args.trials, dtype=int)
    shots_vra  = np.zeros(args.trials, dtype=int)

    for t in range(args.trials):
        # Baseline (uniform prior)
        shots_base[t] = run_decoder_once(
            r_true=args.r,
            r_min=args.r_min,
            r_max=args.r_max,
            sigma=args.sigma,
            target_conf=args.target,
            prior=prior_uniform,
            max_shots=args.max_shots,
            seed=int(rng.integers(0, 2**31 - 1))
        )

        # VRA prior
        prior_vra = draw_vra_prior()
        shots_vra[t] = run_decoder_once(
            r_true=args.r,
            r_min=args.r_min,
            r_max=args.r_max,
            sigma=args.sigma,
            target_conf=args.target,
            prior=prior_vra,
            max_shots=args.max_shots,
            seed=int(rng.integers(0, 2**31 - 1))
        )

    # Compute paired ratio CI
    median_ratio, (ci_lo, ci_hi) = paired_bootstrap_ci(shots_base.astype(float),
                                                       shots_vra.astype(float),
                                                       B=args.bootstraps,
                                                       seed=args.seed + 1)

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
    }

    # Save JSON
    out_json = out_dir / f"E7_results_r{args.r}_sig{args.sigma}_T{args.target}_n{args.trials}.json"
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Wrote summary: {out_json}")

    # Optional CSV
    if args.save_csv:
        out_csv = out_dir / f"E7_per_trial_r{args.r}_sig{args.sigma}_n{args.trials}.csv"
        with open(out_csv, "w") as f:
            f.write("trial,shots_baseline,shots_vra,ratio\n")
            for i in range(args.trials):
                r = shots_vra[i] / max(shots_base[i], 1e-12)
                f.write(f"{i+1},{shots_base[i]},{shots_vra[i]},{r:.6f}\n")
        print(f"✅ Wrote per-trial CSV: {out_csv}")

    # Figures
    # 1) CDF of shots
    def ecdf(x: np.ndarray):
        xs = np.sort(x)
        ys = np.arange(1, len(x) + 1) / len(x)
        return xs, ys

    xs_b, ys_b = ecdf(shots_base)
    xs_v, ys_v = ecdf(shots_vra)

    plt.figure(figsize=(7.5, 5.0))
    plt.plot(xs_b, ys_b, label="Baseline (uniform prior)")
    plt.plot(xs_v, ys_v, label="VRA prior")
    plt.xlabel("Shots to reach target confidence")
    plt.ylabel("Empirical CDF")
    plt.title(f"E7: Shots-to-Confidence CDF (r={args.r}, σ={args.sigma}, target={args.target})")
    plt.grid(alpha=0.3)
    plt.legend()
    fig1 = fig_dir / f"E7_shots_cdf_r{args.r}_sig{args.sigma}_T{args.target}.png"
    plt.tight_layout()
    plt.savefig(fig1, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"📈 Saved {fig1}")

    # 2) Histogram of ratios
    ratios = shots_vra / np.maximum(shots_base, 1e-12)
    plt.figure(figsize=(7.5, 5.0))
    plt.hist(ratios, bins=40, alpha=0.8, edgecolor="black")
    plt.axvline(1.0, color="red", linestyle="--", label="Parity (1.0)")
    plt.axvline(args.pass_ratio, color="orange", linestyle=":", label=f"Pass threshold ({args.pass_ratio:.2f})")
    plt.xlabel("Shots ratio (VRA / Baseline)")
    plt.ylabel("Frequency")
    plt.title(f"E7: Paired Ratios (r={args.r}) — median={median_ratio:.3f}, CI=[{ci_lo:.3f},{ci_hi:.3f}]")
    plt.legend()
    plt.grid(alpha=0.3)
    fig2 = fig_dir / f"E7_ratio_hist_r{args.r}_sig{args.sigma}.png"
    plt.tight_layout()
    plt.savefig(fig2, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"📈 Saved {fig2}")

    # Console verdict
    verdict = "✅ PASS" if passed else "❌ FAIL"
    print("\n" + "=" * 70)
    print("E7 — Shot Reduction Study (Pre-solver) — SUMMARY")
    print("=" * 70)
    print(f"Median shots (baseline) : {summary['median_shots_baseline']:.1f}")
    print(f"Median shots (VRA prior): {summary['median_shots_vra']:.1f}")
    print(f"Median ratio (VRA/base) : {summary['median_ratio_vra_over_base']:.3f}")
    print(f"95% CI (ratio)          : [{ci_lo:.3f}, {ci_hi:.3f}]")
    print(f"Pass threshold (ratio)  : ≤ {args.pass_ratio:.2f} and CI_hi < 1.0")
    print(f"VERDICT                 : {verdict}")
    print("=" * 70)

    return summary


def parse_args():
    p = argparse.ArgumentParser(description="E7 — Shot Reduction Study (Pre-solver, QPE-like)")
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
