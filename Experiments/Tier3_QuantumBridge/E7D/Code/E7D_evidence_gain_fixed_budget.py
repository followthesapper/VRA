#!/usr/bin/env python3
"""
E7D: Evidence Gain at Fixed Budget

Even if 90% confidence isn't reached, does VRA prior increase posterior evidence
within the same shot budget?

Tests whether VRA provides better evidence accumulation at fixed shot counts,
measured by:
- Posterior mass p(r_true|data)
- Bayes factor BF = p(r_true|data) / p(r_true)
- KL divergence from uniform

Pass Criteria:
- Median BF ≥ 2× (+3 dB evidence) AND posterior mass ≥ 10× in ≥1 regime
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

# No harmonic lookup needed - using E7's fast vectorized approach

def run_fixed_budget_trial(r_true, candidates_gpu, prior_gpu, sigma, n_shots, seed):
    """
    Run Bayesian inference for exactly n_shots (no early stopping).
    Uses E7's fast vectorized likelihood (no harmonic lookup needed).

    Returns:
    - posterior_mass: p(r_true | data)
    - bayes_factor: posterior_mass / prior_mass
    - kl_divergence: KL(posterior || uniform)
    """
    rng = np.random.default_rng(seed)

    # Initialize log-posterior = log-prior
    log_post = cp.log(prior_gpu + 1e-30)

    # Get prior mass on true r
    r_idx = int(r_true - candidates_gpu[0])
    if r_idx < 0 or r_idx >= len(candidates_gpu):
        raise ValueError(f"r_true={r_true} not in candidate range")

    prior_mass = float(prior_gpu[r_idx])

    # Generate n_shots and update posterior
    for _ in range(n_shots):
        # Sample k uniformly from [0, r_true)
        k = rng.integers(0, r_true)
        # Sample phase with noise
        theta = (k / r_true + rng.normal(0, sigma)) % 1.0

        # E7's vectorized likelihood (all candidates in parallel, no loops)
        theta_expanded = cp.full(len(candidates_gpu), float(theta), dtype=cp.float32)
        phi = theta_expanded * candidates_gpu.astype(cp.float32)
        frac = cp.abs(phi - cp.round(phi))
        d = frac / candidates_gpu.astype(cp.float32)
        ll = -0.5 * ((d / sigma)**2)

        # Bayesian update in log-space
        log_post = log_post + ll
        m = log_post.max()
        posterior_gpu = cp.exp(log_post - m)
        posterior_gpu /= posterior_gpu.sum()
        log_post = cp.log(posterior_gpu + 1e-30)

    # Compute metrics
    posterior_mass = float(posterior_gpu[r_idx])
    bayes_factor = posterior_mass / prior_mass if prior_mass > 0 else 0.0

    # KL divergence from uniform
    uniform_gpu = cp.ones_like(posterior_gpu) / len(posterior_gpu)
    kl_div = float(cp.sum(posterior_gpu * cp.log(posterior_gpu / uniform_gpu + 1e-10)))

    return posterior_mass, bayes_factor, kl_div

def main():
    parser = argparse.ArgumentParser(description="E7D: Evidence Gain at Fixed Budget")
    parser.add_argument('--r', type=int, default=168, help='True period')
    parser.add_argument('--r-min', type=int, default=32, help='Min search range')
    parser.add_argument('--r-max', type=int, default=1024, help='Max search range')
    parser.add_argument('--sigma', type=float, default=0.02, help='Phase noise std')
    parser.add_argument('--budgets', type=int, nargs='+', default=[500, 1000, 2000, 5000],
                        help='Shot budgets to test')
    parser.add_argument('--trials', type=int, default=100, help='Trials per budget')
    parser.add_argument('--prior-hit', type=float, default=0.55, help='VRA hit rate')
    parser.add_argument('--prior-k', type=int, default=12, help='VRA shortlist size')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    print("=" * 70)
    print("E7D: Evidence Gain at Fixed Budget")
    print("=" * 70)
    print(f"True period r: {args.r}")
    print(f"Search range: [{args.r_min}, {args.r_max}] ({args.r_max - args.r_min + 1} candidates)")
    print(f"Phase noise σ: {args.sigma}")
    print(f"Shot budgets: {args.budgets}")
    print(f"Trials per budget: {args.trials}")
    print(f"VRA prior: hit_rate={args.prior_hit}, shortlist_k={args.prior_k}")
    print()

    start_time = time.time()

    out_dir = Path("Data/Experiments/Tier3/E7D")
    fig_dir = Path("Figures/Experiments/Tier3/E7D")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Build candidates on GPU
    candidates_gpu = cp.arange(args.r_min, args.r_max + 1, dtype=cp.int32)
    n_candidates = len(candidates_gpu)

    # Build uniform prior
    prior_uniform_gpu = cp.ones(n_candidates, dtype=cp.float64) / n_candidates

    # Build VRA prior
    rng = np.random.default_rng(args.seed)
    hit = rng.random() < args.prior_hit
    if hit:
        shortlist = [args.r]
        while len(shortlist) < args.prior_k:
            r_cand = rng.choice(np.arange(args.r_min, args.r_max + 1))
            if r_cand not in shortlist:
                shortlist.append(r_cand)
    else:
        shortlist = rng.choice(np.arange(args.r_min, args.r_max + 1),
                               size=args.prior_k, replace=False).tolist()

    prior_vra = np.zeros(n_candidates)
    for r_s in shortlist:
        idx = r_s - args.r_min
        if 0 <= idx < n_candidates:
            prior_vra[idx] = 1.0
    tau = 0.1
    prior_vra = np.exp(prior_vra / tau)
    prior_vra /= prior_vra.sum()
    prior_vra_gpu = cp.array(prior_vra, dtype=cp.float64)

    print(f"VRA shortlist: {sorted(shortlist)}")
    print(f"True r in shortlist: {'YES' if args.r in shortlist else 'NO'}")
    print(f"Using E7's fast vectorized likelihood (no harmonic lookup needed)")
    print()

    # Run trials for each budget
    results = {}

    for budget in args.budgets:
        print(f"Budget: {budget} shots")
        print(f"Running {args.trials} trials...")

        pm_uniform = np.zeros(args.trials)
        bf_uniform = np.zeros(args.trials)
        kl_uniform = np.zeros(args.trials)

        pm_vra = np.zeros(args.trials)
        bf_vra = np.zeros(args.trials)
        kl_vra = np.zeros(args.trials)

        trial_start = time.time()

        for t in range(args.trials):
            seed_t = args.seed + budget * 1000 + t

            # Uniform prior
            pm, bf, kl = run_fixed_budget_trial(
                args.r, candidates_gpu, prior_uniform_gpu, args.sigma, budget, seed_t
            )
            pm_uniform[t] = pm
            bf_uniform[t] = bf
            kl_uniform[t] = kl

            # VRA prior
            pm, bf, kl = run_fixed_budget_trial(
                args.r, candidates_gpu, prior_vra_gpu, args.sigma, budget, seed_t
            )
            pm_vra[t] = pm
            bf_vra[t] = bf
            kl_vra[t] = kl

            # Per-trial progress update
            elapsed = time.time() - trial_start
            avg_time = elapsed / (t + 1)
            eta = avg_time * (args.trials - t - 1)
            print(f"  [{t+1:3d}/{args.trials}] ({(t+1)*100//args.trials:3d}%) | "
                  f"BF U:{bf_uniform[t]:.2f} V:{bf_vra[t]:.2f} | "
                  f"Avg: {avg_time:.2f}s/trial | ETA: {eta:.1f}s")
            sys.stdout.flush()

        # Compute statistics
        median_bf_uniform = np.median(bf_uniform)
        median_bf_vra = np.median(bf_vra)
        bf_ratio = median_bf_vra / median_bf_uniform if median_bf_uniform > 0 else 0

        median_pm_uniform = np.median(pm_uniform)
        median_pm_vra = np.median(pm_vra)
        pm_ratio = median_pm_vra / median_pm_uniform if median_pm_uniform > 0 else 0

        print(f"  Median BF:  Uniform={median_bf_uniform:.2f}, VRA={median_bf_vra:.2f}, "
              f"Ratio={bf_ratio:.2f}×")
        print(f"  Median PM:  Uniform={median_pm_uniform:.4f}, VRA={median_pm_vra:.4f}, "
              f"Ratio={pm_ratio:.2f}×")
        print()

        results[budget] = {
            "posterior_mass": {
                "uniform": pm_uniform.tolist(),
                "vra": pm_vra.tolist(),
                "median_uniform": float(median_pm_uniform),
                "median_vra": float(median_pm_vra),
                "ratio": float(pm_ratio)
            },
            "bayes_factor": {
                "uniform": bf_uniform.tolist(),
                "vra": bf_vra.tolist(),
                "median_uniform": float(median_bf_uniform),
                "median_vra": float(median_bf_vra),
                "ratio": float(bf_ratio)
            },
            "kl_divergence": {
                "uniform": kl_uniform.tolist(),
                "vra": kl_vra.tolist(),
                "median_uniform": float(np.median(kl_uniform)),
                "median_vra": float(np.median(kl_vra))
            }
        }

        # GPU cleanup
        cp.get_default_memory_pool().free_all_blocks()

    # Verdict
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    print("Pass Criterion: Median BF ≥ 2× (+3 dB) AND Posterior Mass ≥ 10× in ≥1 budget")
    print()

    passed = False
    for budget in args.budgets:
        bf_ratio = results[budget]["bayes_factor"]["ratio"]
        pm_ratio = results[budget]["posterior_mass"]["ratio"]
        budget_pass = (bf_ratio >= 2.0) and (pm_ratio >= 10.0)
        passed = passed or budget_pass

        print(f"  Budget {budget:4d}: BF={bf_ratio:5.2f}×, PM={pm_ratio:6.2f}× "
              f"{'✓ PASS' if budget_pass else '✗ FAIL'}")

    print()
    if passed:
        print("🎉 E7D: ✓ PASS - VRA increases evidence accumulation")
    else:
        print("❌ E7D: ✗ FAIL - VRA provides no evidence advantage")
    print("=" * 70)
    print()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "experiment": "E7D",
        "timestamp": timestamp,
        "parameters": {
            "r_true": args.r,
            "r_min": args.r_min,
            "r_max": args.r_max,
            "sigma": args.sigma,
            "budgets": args.budgets,
            "trials": args.trials,
            "prior_hit": args.prior_hit,
            "prior_k": args.prior_k,
            "vra_shortlist": shortlist,
            "true_r_in_shortlist": args.r in shortlist
        },
        "results": results,
        "verdict": {
            "pass_criterion": "BF >= 2x AND PM >= 10x in >=1 budget",
            "overall_pass": passed
        },
        "runtime_seconds": time.time() - start_time
    }

    results_file = out_dir / f"{timestamp}_E7D_results.json"
    with open(results_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Results saved: {results_file}")

    # Generate figures
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Bayes Factor vs Budget
    ax = axes[0, 0]
    bf_medians_uniform = [results[b]["bayes_factor"]["median_uniform"] for b in args.budgets]
    bf_medians_vra = [results[b]["bayes_factor"]["median_vra"] for b in args.budgets]
    ax.plot(args.budgets, bf_medians_uniform, 'o-', label='Uniform', color='gray', linewidth=2)
    ax.plot(args.budgets, bf_medians_vra, 's-', label='VRA', color='green', linewidth=2)
    ax.axhline(2.0, color='red', linestyle='--', label='2× threshold', alpha=0.5)
    ax.set_xlabel('Shot Budget')
    ax.set_ylabel('Median Bayes Factor')
    ax.set_title('Bayes Factor vs Shot Budget')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.legend()
    ax.grid(alpha=0.3)

    # Posterior Mass vs Budget
    ax = axes[0, 1]
    pm_medians_uniform = [results[b]["posterior_mass"]["median_uniform"] for b in args.budgets]
    pm_medians_vra = [results[b]["posterior_mass"]["median_vra"] for b in args.budgets]
    ax.plot(args.budgets, pm_medians_uniform, 'o-', label='Uniform', color='gray', linewidth=2)
    ax.plot(args.budgets, pm_medians_vra, 's-', label='VRA', color='green', linewidth=2)
    ax.set_xlabel('Shot Budget')
    ax.set_ylabel('Median Posterior Mass p(r_true|data)')
    ax.set_title('Posterior Concentration vs Shot Budget')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.legend()
    ax.grid(alpha=0.3)

    # BF Distribution (largest budget)
    ax = axes[1, 0]
    max_budget = max(args.budgets)
    bf_u = results[max_budget]["bayes_factor"]["uniform"]
    bf_v = results[max_budget]["bayes_factor"]["vra"]
    ax.hist(bf_u, bins=30, alpha=0.5, label=f'Uniform (median={np.median(bf_u):.1f})', color='gray')
    ax.hist(bf_v, bins=30, alpha=0.5, label=f'VRA (median={np.median(bf_v):.1f})', color='green')
    ax.axvline(2.0, color='red', linestyle='--', label='2× threshold')
    ax.set_xlabel('Bayes Factor')
    ax.set_ylabel('Count')
    ax.set_title(f'Bayes Factor Distribution (Budget={max_budget})')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Summary table
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = f"""
E7D: Evidence Gain at Fixed Budget

Pass Criterion:
  BF ≥ 2× AND PM ≥ 10× in ≥1 budget

Results:
"""
    for budget in args.budgets:
        bf_ratio = results[budget]["bayes_factor"]["ratio"]
        pm_ratio = results[budget]["posterior_mass"]["ratio"]
        budget_pass = (bf_ratio >= 2.0) and (pm_ratio >= 10.0)
        summary_text += f"  {budget:4d}: BF={bf_ratio:4.1f}× PM={pm_ratio:5.1f}× {'✓' if budget_pass else '✗'}\n"

    summary_text += f"\nVerdict: {'PASS ✓' if passed else 'FAIL ✗'}"

    ax.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
            verticalalignment='center')

    plt.tight_layout()
    fig_file = fig_dir / f"{timestamp}_E7D_evidence_gain.png"
    plt.savefig(fig_file, dpi=150, bbox_inches='tight')
    print(f"Figure saved: {fig_file}")
    plt.close()

    elapsed = time.time() - start_time
    print(f"\nTotal runtime: {elapsed/60:.1f} min")
    print("=" * 70)

if __name__ == "__main__":
    main()
