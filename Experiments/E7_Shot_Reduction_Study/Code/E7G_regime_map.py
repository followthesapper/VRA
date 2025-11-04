#!/usr/bin/env python3
"""
E7G: Regime Map - Where (if anywhere) does VRA help?

Tests VRA advantage across multiple parameter regimes:
- Search space size (candidates)
- VRA shortlist size (k)
- VRA hit rate
- Phase noise (sigma)

Uses fixed-budget approach (like E7D) to avoid timeouts.

Pass Criteria:
- Find at least ONE regime where median(shots_vra) < 0.9 * median(shots_uniform)
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

def run_fixed_budget_trial(r_true, candidates_gpu, prior_gpu, sigma, max_shots, seed, target_conf=0.9):
    """
    Run Bayesian decoder with fixed max budget.
    Returns shots_used (max_shots if timeout, else actual shots to reach target_conf).

    Uses E7's fast vectorized likelihood.
    """
    rng = np.random.default_rng(seed)

    log_post = cp.log(prior_gpu + 1e-30)
    r_idx = int(r_true - candidates_gpu[0])

    for shot in range(max_shots):
        k = rng.integers(0, r_true)
        theta = (k / r_true + rng.normal(0, sigma)) % 1.0

        # E7's vectorized likelihood
        theta_expanded = cp.full(len(candidates_gpu), float(theta), dtype=cp.float32)
        phi = theta_expanded * candidates_gpu.astype(cp.float32)
        frac = cp.abs(phi - cp.round(phi))
        d = frac / candidates_gpu.astype(cp.float32)
        ll = -0.5 * ((d / sigma)**2)

        log_post = log_post + ll
        m = log_post.max()
        posterior_gpu = cp.exp(log_post - m)
        posterior_gpu /= posterior_gpu.sum()
        log_post = cp.log(posterior_gpu + 1e-30)

        # Check convergence
        if float(posterior_gpu[r_idx]) >= target_conf:
            return shot + 1  # Converged

    return max_shots  # Timeout

def main():
    parser = argparse.ArgumentParser(description="E7G: Regime Map")
    parser.add_argument('--r', type=int, default=168, help='True period')
    parser.add_argument('--trials', type=int, default=50, help='Trials per regime')
    parser.add_argument('--max-shots', type=int, default=5000, help='Max shots per trial')
    parser.add_argument('--target', type=float, default=0.9, help='Target confidence')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    print("=" * 70)
    print("E7G: Regime Map - Where Does VRA Help?")
    print("=" * 70)
    print(f"True period r: {args.r}")
    print(f"Max shots: {args.max_shots}")
    print(f"Trials per regime: {args.trials}")
    print(f"Target confidence: {args.target}")
    print()

    start_time = time.time()

    out_dir = Path("../Data")
    fig_dir = Path("../Figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Define parameter sweep
    regimes = [
        # Small search space (VRA best chance)
        {"name": "tiny_optimal", "r_min": 150, "r_max": 200, "sigma": 0.01, "k": 30, "hit": 0.90},
        {"name": "tiny_good", "r_min": 150, "r_max": 200, "sigma": 0.01, "k": 20, "hit": 0.70},
        {"name": "tiny_medium", "r_min": 150, "r_max": 200, "sigma": 0.02, "k": 20, "hit": 0.70},

        # Small search space
        {"name": "small_optimal", "r_min": 100, "r_max": 250, "sigma": 0.01, "k": 50, "hit": 0.85},
        {"name": "small_good", "r_min": 100, "r_max": 250, "sigma": 0.02, "k": 30, "hit": 0.70},
        {"name": "small_medium", "r_min": 100, "r_max": 250, "sigma": 0.02, "k": 20, "hit": 0.55},

        # Medium search space (like E7C "easy")
        {"name": "medium_optimal", "r_min": 32, "r_max": 256, "sigma": 0.01, "k": 50, "hit": 0.85},
        {"name": "medium_good", "r_min": 32, "r_max": 256, "sigma": 0.01, "k": 30, "hit": 0.70},
        {"name": "medium_baseline", "r_min": 32, "r_max": 256, "sigma": 0.01, "k": 12, "hit": 0.55},

        # Large search space (like E7A baseline - expected to fail)
        {"name": "large_baseline", "r_min": 32, "r_max": 1024, "sigma": 0.02, "k": 12, "hit": 0.55},
    ]

    results = {}

    for regime in regimes:
        print(f"\nRegime: {regime['name']}")
        print(f"  r ∈ [{regime['r_min']}, {regime['r_max']}] ({regime['r_max'] - regime['r_min'] + 1} candidates)")
        print(f"  σ = {regime['sigma']}, VRA k={regime['k']}, hit={regime['hit']}")

        # Build candidates
        candidates_gpu = cp.arange(regime['r_min'], regime['r_max'] + 1, dtype=cp.int32)
        n_candidates = len(candidates_gpu)

        # Uniform prior
        prior_uniform_gpu = cp.ones(n_candidates, dtype=cp.float64) / n_candidates

        # VRA prior
        rng = np.random.default_rng(args.seed + abs(hash(regime['name'])))
        hit = rng.random() < regime['hit']
        if hit:
            shortlist = [args.r]
            while len(shortlist) < regime['k']:
                r_cand = rng.choice(np.arange(regime['r_min'], regime['r_max'] + 1))
                if r_cand not in shortlist:
                    shortlist.append(r_cand)
        else:
            shortlist = rng.choice(np.arange(regime['r_min'], regime['r_max'] + 1),
                                   size=regime['k'], replace=False).tolist()

        prior_vra = np.zeros(n_candidates)
        for r_s in shortlist:
            idx = r_s - regime['r_min']
            if 0 <= idx < n_candidates:
                prior_vra[idx] = 1.0
        tau = 0.1
        prior_vra = np.exp(prior_vra / tau)
        prior_vra /= prior_vra.sum()
        prior_vra_gpu = cp.array(prior_vra, dtype=cp.float64)

        print(f"  True r in shortlist: {'YES' if args.r in shortlist else 'NO'}")
        print(f"  Running trials (early stop if all timeout)...")

        shots_uniform = []
        shots_vra = []

        trial_start = time.time()

        # Adaptive trials: start with 10, if all timeout in first 10, skip rest
        min_trials = 10
        for t in range(args.trials):
            seed_t = args.seed + abs(hash(regime['name'])) * 1000 + t

            su = run_fixed_budget_trial(
                args.r, candidates_gpu, prior_uniform_gpu, regime['sigma'],
                args.max_shots, seed_t, args.target
            )
            sv = run_fixed_budget_trial(
                args.r, candidates_gpu, prior_vra_gpu, regime['sigma'],
                args.max_shots, seed_t, args.target
            )

            shots_uniform.append(su)
            shots_vra.append(sv)

            elapsed = time.time() - trial_start
            avg_time = elapsed / (t + 1)
            remaining = args.trials - t - 1
            eta = avg_time * remaining
            print(f"    [{t+1:3d}/{args.trials}] ({(t+1)*100//args.trials:3d}%) | "
                  f"U:{su:5d} V:{sv:5d} | "
                  f"Avg: {avg_time:.2f}s/trial | ETA: {eta:.1f}s")
            sys.stdout.flush()

            # Early stopping: if first min_trials all timeout, skip rest
            if t+1 >= min_trials:
                all_timeout = all(s == args.max_shots for s in shots_uniform[:min_trials]) and \
                              all(s == args.max_shots for s in shots_vra[:min_trials])
                if all_timeout:
                    print(f"    Early stop: All first {min_trials} trials hit timeout. Skipping remaining trials.")
                    break

        # Compute statistics
        shots_uniform = np.array(shots_uniform)
        shots_vra = np.array(shots_vra)
        n_trials_run = len(shots_uniform)

        median_u = np.median(shots_uniform)
        median_v = np.median(shots_vra)
        ratio = median_v / median_u if median_u > 0 else 1.0

        timeout_rate_u = np.sum(shots_uniform == args.max_shots) / n_trials_run
        timeout_rate_v = np.sum(shots_vra == args.max_shots) / n_trials_run

        success_rate_u = 1.0 - timeout_rate_u
        success_rate_v = 1.0 - timeout_rate_v

        print(f"  Trials run: {n_trials_run}/{args.trials}")
        print(f"  Median shots: Uniform={median_u:.0f}, VRA={median_v:.0f}, Ratio={ratio:.3f}")
        print(f"  Success rate: Uniform={success_rate_u:.2%}, VRA={success_rate_v:.2%}")

        results[regime['name']] = {
            "parameters": regime,
            "shots_uniform": shots_uniform.tolist(),
            "shots_vra": shots_vra.tolist(),
            "median_uniform": float(median_u),
            "median_vra": float(median_v),
            "ratio": float(ratio),
            "success_rate_uniform": float(success_rate_u),
            "success_rate_vra": float(success_rate_v),
            "vra_in_shortlist": args.r in shortlist
        }

        cp.get_default_memory_pool().free_all_blocks()

    # Verdict
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    print("Pass Criterion: Find ≥1 regime where median(shots_vra) < 0.9 * median(shots_uniform)")
    print()

    passed_regimes = []
    for name, res in results.items():
        if res['ratio'] < 0.9:
            passed_regimes.append(name)
            print(f"  ✓ {name:20s}: Ratio={res['ratio']:.3f} (VRA advantage!)")
        else:
            print(f"  ✗ {name:20s}: Ratio={res['ratio']:.3f}")

    print()
    if len(passed_regimes) > 0:
        print(f"🎉 E7G: ✓ PASS - VRA helps in {len(passed_regimes)} regime(s): {passed_regimes}")
    else:
        print("❌ E7G: ✗ FAIL - VRA provides no advantage in any regime")
    print("=" * 70)
    print()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "experiment": "E7G",
        "timestamp": timestamp,
        "parameters": {
            "r_true": args.r,
            "max_shots": args.max_shots,
            "trials": args.trials,
            "target_conf": args.target
        },
        "regimes": results,
        "verdict": {
            "pass_criterion": "ratio < 0.9 in >=1 regime",
            "passed_regimes": passed_regimes,
            "overall_pass": len(passed_regimes) > 0
        },
        "runtime_seconds": time.time() - start_time
    }

    results_file = out_dir / f"{timestamp}_E7G_results.json"
    with open(results_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Results saved: {results_file}")

    # Generate figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Shot ratio by regime
    ax = axes[0, 0]
    regime_names = list(results.keys())
    ratios = [results[r]['ratio'] for r in regime_names]
    colors = ['green' if ratio < 0.9 else 'red' for ratio in ratios]
    ax.barh(regime_names, ratios, color=colors, alpha=0.7)
    ax.axvline(0.9, color='orange', linestyle='--', label='0.9× threshold (10% speedup)')
    ax.axvline(1.0, color='gray', linestyle='-', alpha=0.5, label='1.0× (no advantage)')
    ax.set_xlabel('Shot Ratio (VRA / Uniform)')
    ax.set_title('VRA Advantage by Regime')
    ax.legend()
    ax.grid(axis='x', alpha=0.3)

    # Success rates
    ax = axes[0, 1]
    x = np.arange(len(regime_names))
    width = 0.35
    ax.bar(x - width/2, [results[r]['success_rate_uniform'] for r in regime_names],
           width, label='Uniform', color='gray', alpha=0.7)
    ax.bar(x + width/2, [results[r]['success_rate_vra'] for r in regime_names],
           width, label='VRA', color='green', alpha=0.7)
    ax.set_ylabel('Success Rate (converged within budget)')
    ax.set_title('Convergence Success Rate')
    ax.set_xticks(x)
    ax.set_xticklabels(regime_names, rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Shot distribution for best regime (if any)
    ax = axes[1, 0]
    if len(passed_regimes) > 0:
        best_regime = min(regime_names, key=lambda r: results[r]['ratio'])
        shots_u = results[best_regime]['shots_uniform']
        shots_v = results[best_regime]['shots_vra']
        ax.hist(shots_u, bins=30, alpha=0.5, label=f'Uniform (median={np.median(shots_u):.0f})',
                color='gray')
        ax.hist(shots_v, bins=30, alpha=0.5, label=f'VRA (median={np.median(shots_v):.0f})',
                color='green')
        ax.set_xlabel('Shots to Convergence')
        ax.set_ylabel('Count')
        ax.set_title(f'Shot Distribution - Best Regime: {best_regime}')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'No regime with VRA advantage found',
                ha='center', va='center', fontsize=12)
        ax.axis('off')

    # Summary table
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = f"""
E7G: Regime Map

Pass Criterion:
  Ratio < 0.9 in ≥1 regime

Tested {len(regime_names)} regimes:
"""
    for name in regime_names:
        ratio = results[name]['ratio']
        mark = '✓' if ratio < 0.9 else '✗'
        summary_text += f"  {mark} {name[:15]:15s} {ratio:5.3f}×\n"

    summary_text += f"\nVerdict: {'PASS ✓' if len(passed_regimes) > 0 else 'FAIL ✗'}"
    if len(passed_regimes) > 0:
        summary_text += f"\n\nVRA helps in:\n  " + "\n  ".join(passed_regimes)

    ax.text(0.1, 0.5, summary_text, fontsize=9, family='monospace',
            verticalalignment='center')

    plt.tight_layout()
    fig_file = fig_dir / f"{timestamp}_E7G_regime_map.png"
    plt.savefig(fig_file, dpi=150, bbox_inches='tight')
    print(f"Figure saved: {fig_file}")
    plt.close()

    elapsed = time.time() - start_time
    print(f"\nTotal runtime: {elapsed/60:.1f} min")
    print("=" * 70)

if __name__ == "__main__":
    main()
