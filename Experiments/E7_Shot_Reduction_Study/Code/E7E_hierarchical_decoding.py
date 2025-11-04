#!/usr/bin/env python3
"""
E7E: Hierarchical Coarse-to-Fine Decoding

Tests whether VRA can accelerate inference via adaptive two-stage decoding:
- Stage 1: VRA on coarse grid (steps of 4) → identify top 10% mass
- Stage 2: Refine only those candidates to full resolution

Pass Criteria:
- Total shots (S_c + S_f) ≥ 20% fewer at equal confidence
"""

import argparse
import json
import time
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import cupy as cp
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

# No imports needed - using E7's inline vectorized approach

def run_baseline_decoder(r_true, candidates_gpu, prior_gpu, sigma, target, max_shots, seed):
    """
    Standard one-shot decoder on full grid using E7's fast vectorized likelihood.
    Returns shots needed to reach target confidence.
    """
    rng = np.random.default_rng(seed)
    log_post = cp.log(prior_gpu + 1e-30)
    r_idx = int(r_true - candidates_gpu[0])

    for shot in range(1, max_shots + 1):
        k = rng.integers(0, r_true)
        theta = (k / r_true + rng.normal(0, sigma)) % 1.0

        # E7's vectorized likelihood (all candidates in parallel, no loops)
        theta_expanded = cp.full(len(candidates_gpu), float(theta), dtype=cp.float32)
        phi = theta_expanded * candidates_gpu.astype(cp.float32)
        frac = cp.abs(phi - cp.round(phi))
        d = frac / candidates_gpu.astype(cp.float32)
        ll = -0.5 * ((d / sigma)**2)

        # Bayesian update
        log_post = log_post + ll
        m = log_post.max()
        post = cp.exp(log_post - m)
        post /= post.sum()

        # Check convergence
        map_idx = int(cp.argmax(post))
        map_r = int(candidates_gpu[map_idx])
        confidence = float(post[map_idx])

        if map_r == r_true and confidence >= target:
            return shot

    return max_shots

def run_hierarchical_decoder(r_true, r_min, r_max, sigma, target, max_shots, coarse_step, seed):
    """
    Two-stage hierarchical decoder:
    1. Coarse stage: Decode on grid with step=coarse_step, accumulate top 10% mass
    2. Fine stage: Refine within top bins to full resolution

    Returns (total_shots, coarse_shots, fine_shots).
    """
    rng = np.random.default_rng(seed)

    # Stage 1: Coarse grid
    coarse_candidates = np.arange(r_min, r_max + 1, coarse_step)
    coarse_candidates_gpu = cp.array(coarse_candidates, dtype=cp.int32)
    coarse_prior_gpu = cp.ones(len(coarse_candidates_gpu), dtype=cp.float64) / len(coarse_candidates_gpu)
    log_coarse_post = cp.log(coarse_prior_gpu + 1e-30)

    coarse_shots = 0
    max_coarse_shots = max_shots // 2  # Allocate half budget to coarse

    for shot in range(1, max_coarse_shots + 1):
        k = rng.integers(0, r_true)
        theta = (k / r_true + rng.normal(0, sigma)) % 1.0

        # E7's vectorized likelihood (coarse grid, no harmonic lookup)
        theta_expanded = cp.full(len(coarse_candidates_gpu), float(theta), dtype=cp.float32)
        phi = theta_expanded * coarse_candidates_gpu.astype(cp.float32)
        frac = cp.abs(phi - cp.round(phi))
        d = frac / coarse_candidates_gpu.astype(cp.float32)
        ll = -0.5 * ((d / sigma)**2)

        # Bayesian update
        log_coarse_post = log_coarse_post + ll
        m = log_coarse_post.max()
        coarse_posterior_gpu = cp.exp(log_coarse_post - m)
        coarse_posterior_gpu /= coarse_posterior_gpu.sum()

        coarse_shots = shot

        # Check if we have reasonable concentration (top candidate > 10%)
        if cp.max(coarse_posterior_gpu) > 0.1:
            break

    # Identify top 10% mass bins
    coarse_posterior = cp.asnumpy(coarse_posterior_gpu)
    sorted_indices = np.argsort(coarse_posterior)[::-1]
    cumsum = np.cumsum(coarse_posterior[sorted_indices])
    n_top = np.searchsorted(cumsum, 0.10) + 1  # Top bins covering 10% mass
    top_indices = sorted_indices[:max(n_top, 1)]

    # Build fine-resolution candidates within top bins
    fine_candidates = []
    for idx in top_indices:
        r_coarse = coarse_candidates[idx]
        # Expand around this coarse candidate
        for r_fine in range(max(r_min, r_coarse - coarse_step + 1),
                           min(r_max + 1, r_coarse + coarse_step)):
            if r_fine not in fine_candidates:
                fine_candidates.append(r_fine)

    fine_candidates = sorted(fine_candidates)
    fine_candidates_gpu = cp.array(fine_candidates, dtype=cp.int32)

    # Check if true r is in fine candidates
    if r_true not in fine_candidates:
        # Failed to capture true r - return max_shots
        return max_shots, coarse_shots, max_shots - coarse_shots

    # Stage 2: Fine refinement
    fine_prior_gpu = cp.ones(len(fine_candidates_gpu), dtype=cp.float64) / len(fine_candidates_gpu)
    log_fine_post = cp.log(fine_prior_gpu + 1e-30)

    r_idx_fine = fine_candidates.index(r_true)
    fine_shots = 0
    max_fine_shots = max_shots - coarse_shots

    for shot in range(1, max_fine_shots + 1):
        k = rng.integers(0, r_true)
        theta = (k / r_true + rng.normal(0, sigma)) % 1.0

        # E7's vectorized likelihood (fine grid, no harmonic lookup)
        theta_expanded = cp.full(len(fine_candidates_gpu), float(theta), dtype=cp.float32)
        phi = theta_expanded * fine_candidates_gpu.astype(cp.float32)
        frac = cp.abs(phi - cp.round(phi))
        d = frac / fine_candidates_gpu.astype(cp.float32)
        ll = -0.5 * ((d / sigma)**2)

        # Bayesian update
        log_fine_post = log_fine_post + ll
        m = log_fine_post.max()
        fine_posterior_gpu = cp.exp(log_fine_post - m)
        fine_posterior_gpu /= fine_posterior_gpu.sum()

        fine_shots = shot

        # Check convergence
        map_idx = int(cp.argmax(fine_posterior_gpu))
        map_r = fine_candidates[map_idx]
        confidence = float(fine_posterior_gpu[map_idx])

        if map_r == r_true and confidence >= target:
            total_shots = coarse_shots + fine_shots
            return total_shots, coarse_shots, fine_shots

    return max_shots, coarse_shots, fine_shots

def main():
    parser = argparse.ArgumentParser(description="E7E: Hierarchical Coarse-to-Fine Decoding")
    parser.add_argument('--r', type=int, default=168, help='True period')
    parser.add_argument('--r-min', type=int, default=32, help='Min search range')
    parser.add_argument('--r-max', type=int, default=1024, help='Max search range')
    parser.add_argument('--sigma', type=float, default=0.02, help='Phase noise std')
    parser.add_argument('--target', type=float, default=0.9, help='Target confidence')
    parser.add_argument('--max-shots', type=int, default=50000, help='Max shots')
    parser.add_argument('--coarse-step', type=int, default=4, help='Coarse grid step')
    parser.add_argument('--trials', type=int, default=100, help='Number of trials')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    print("=" * 70)
    print("E7E: Hierarchical Coarse-to-Fine Decoding")
    print("=" * 70)
    print(f"True period r: {args.r}")
    print(f"Search range: [{args.r_min}, {args.r_max}] ({args.r_max - args.r_min + 1} candidates)")
    print(f"Phase noise σ: {args.sigma}")
    print(f"Target confidence: {args.target}")
    print(f"Coarse grid step: {args.coarse_step}")
    print(f"Trials: {args.trials}")
    print()

    start_time = time.time()

    out_dir = Path("../Data")
    fig_dir = Path("../Figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Run trials
    print("Running baseline decoder (full grid, one-shot)...")
    candidates_full = np.arange(args.r_min, args.r_max + 1)
    candidates_full_gpu = cp.array(candidates_full, dtype=cp.int32)
    prior_uniform_gpu = cp.ones(len(candidates_full_gpu), dtype=cp.float64) / len(candidates_full_gpu)
    print("  Using E7's fast vectorized likelihood (no harmonic lookup needed)")

    shots_baseline = np.zeros(args.trials, dtype=np.int32)
    baseline_start = time.time()

    for t in range(args.trials):
        seed_t = args.seed + t
        shots_baseline[t] = run_baseline_decoder(
            args.r, candidates_full_gpu, prior_uniform_gpu,
            args.sigma, args.target, args.max_shots, seed_t
        )

        # Progress update every trial
        elapsed = time.time() - baseline_start
        avg_time = elapsed / (t + 1)
        eta = avg_time * (args.trials - t - 1)
        median_b = np.median(shots_baseline[:t+1])
        print(f"  [{t+1:3d}/{args.trials}] ({(t+1)*100//args.trials:3d}%) | "
              f"Med:{median_b:.0f} | Avg: {avg_time:.2f}s/trial | ETA: {eta:.1f}s")
        sys.stdout.flush()

        # GPU cleanup
        if (t + 1) % 10 == 0:
            cp.get_default_memory_pool().free_all_blocks()

    print()
    print("Running hierarchical decoder (coarse → fine)...")
    shots_hierarchical = np.zeros(args.trials, dtype=np.int32)
    shots_coarse = np.zeros(args.trials, dtype=np.int32)
    shots_fine = np.zeros(args.trials, dtype=np.int32)

    hierarchical_start = time.time()

    for t in range(args.trials):
        seed_t = args.seed + 10000 + t
        total, coarse, fine = run_hierarchical_decoder(
            args.r, args.r_min, args.r_max, args.sigma,
            args.target, args.max_shots, args.coarse_step, seed_t
        )
        shots_hierarchical[t] = total
        shots_coarse[t] = coarse
        shots_fine[t] = fine

        # Progress update every trial
        elapsed = time.time() - hierarchical_start
        avg_time = elapsed / (t + 1)
        eta = avg_time * (args.trials - t - 1)
        median_h = np.median(shots_hierarchical[:t+1])
        print(f"  [{t+1:3d}/{args.trials}] ({(t+1)*100//args.trials:3d}%) | "
              f"Med:{median_h:.0f} | Avg: {avg_time:.2f}s/trial | ETA: {eta:.1f}s")
        sys.stdout.flush()

        # GPU cleanup
        if (t + 1) % 10 == 0:
            cp.get_default_memory_pool().free_all_blocks()

    # Statistics
    median_baseline = np.median(shots_baseline)
    median_hierarchical = np.median(shots_hierarchical)
    ratio = median_hierarchical / median_baseline if median_baseline > 0 else 1.0
    reduction_pct = (1 - ratio) * 100

    # Bootstrap CI
    n_boot = 1000
    ratios_boot = []
    rng_boot = np.random.default_rng(args.seed)
    for _ in range(n_boot):
        idx = rng_boot.choice(args.trials, size=args.trials, replace=True)
        r = np.median(shots_hierarchical[idx]) / np.median(shots_baseline[idx])
        ratios_boot.append(r)
    ci_lower, ci_upper = np.percentile(ratios_boot, [2.5, 97.5])

    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Median shots (Baseline):     {median_baseline:.0f}")
    print(f"Median shots (Hierarchical): {median_hierarchical:.0f}")
    print(f"  (Coarse: {np.median(shots_coarse):.0f}, Fine: {np.median(shots_fine):.0f})")
    print(f"Ratio:                       {ratio:.3f} ({reduction_pct:+.1f}% change)")
    print(f"95% CI:                      [{ci_lower:.3f}, {ci_upper:.3f}]")
    print()

    # Verdict
    passed = reduction_pct >= 20.0

    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    print("Pass Criterion: ≥20% reduction in total shots")
    print()
    print(f"  Reduction: {reduction_pct:.1f}%")
    print()

    if passed:
        print("🎉 E7E: ✓ PASS - Hierarchical decoding reduces shots by ≥20%")
    else:
        print("❌ E7E: ✗ FAIL - Hierarchical decoding provides no advantage")
    print("=" * 70)
    print()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "experiment": "E7E",
        "timestamp": timestamp,
        "parameters": {
            "r_true": args.r,
            "r_min": args.r_min,
            "r_max": args.r_max,
            "sigma": args.sigma,
            "target": args.target,
            "max_shots": args.max_shots,
            "coarse_step": args.coarse_step,
            "trials": args.trials
        },
        "results": {
            "shots_baseline": shots_baseline.tolist(),
            "shots_hierarchical": shots_hierarchical.tolist(),
            "shots_coarse": shots_coarse.tolist(),
            "shots_fine": shots_fine.tolist(),
            "median_baseline": float(median_baseline),
            "median_hierarchical": float(median_hierarchical),
            "median_coarse": float(np.median(shots_coarse)),
            "median_fine": float(np.median(shots_fine)),
            "ratio": float(ratio),
            "reduction_pct": float(reduction_pct),
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper)
        },
        "verdict": {
            "pass_criterion": "reduction >= 20%",
            "reduction_pct": float(reduction_pct),
            "pass": bool(passed)
        },
        "runtime_seconds": time.time() - start_time
    }

    results_file = out_dir / f"{timestamp}_E7E_results.json"
    with open(results_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Results saved: {results_file}")

    # Generate figures
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Shot distribution comparison
    ax = axes[0]
    ax.hist(shots_baseline, bins=30, alpha=0.5,
            label=f'Baseline (med={median_baseline:.0f})', color='gray')
    ax.hist(shots_hierarchical, bins=30, alpha=0.5,
            label=f'Hierarchical (med={median_hierarchical:.0f})', color='green')
    ax.set_xlabel('Total Shots')
    ax.set_ylabel('Count')
    ax.set_title(f'Shot Distribution\nReduction: {reduction_pct:+.1f}%')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # CDF comparison
    ax = axes[1]
    sorted_base = np.sort(shots_baseline)
    sorted_hier = np.sort(shots_hierarchical)
    cdf = np.arange(1, len(shots_baseline) + 1) / len(shots_baseline)

    ax.plot(sorted_base, cdf, label='Baseline', color='gray', linewidth=2)
    ax.plot(sorted_hier, cdf, label='Hierarchical', color='green', linewidth=2)
    ax.set_xlabel('Shots')
    ax.set_ylabel('CDF')
    ax.set_title('Cumulative Distribution')
    ax.legend()
    ax.grid(alpha=0.3)

    # Coarse vs Fine breakdown
    ax = axes[2]
    ax.scatter(shots_coarse, shots_fine, alpha=0.5, s=20)
    ax.set_xlabel('Coarse Stage Shots')
    ax.set_ylabel('Fine Stage Shots')
    ax.set_title(f'Hierarchical Breakdown\n'
                 f'Median: {np.median(shots_coarse):.0f} + {np.median(shots_fine):.0f} = '
                 f'{median_hierarchical:.0f}')
    ax.grid(alpha=0.3)

    plt.tight_layout()
    fig_file = fig_dir / f"{timestamp}_E7E_hierarchical_comparison.png"
    plt.savefig(fig_file, dpi=150, bbox_inches='tight')
    print(f"Figure saved: {fig_file}")
    plt.close()

    elapsed = time.time() - start_time
    print(f"\nTotal runtime: {elapsed/60:.1f} min")
    print("=" * 70)

if __name__ == "__main__":
    main()
