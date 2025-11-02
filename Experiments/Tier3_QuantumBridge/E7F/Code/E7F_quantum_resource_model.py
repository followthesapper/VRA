#!/usr/bin/env python3
"""
E7F: Quantum Resource Model Test

Tests whether VRA-derived priors reduce quantum circuit resources:
- Precision bits t (QPE register size)
- Controlled-U power range (max exponent j_max)
- T-gate depth (∑ 2^j for j ≤ j_max)

Even if shot counts don't improve, resource reduction is valuable for NISQ devices.

Method:
1. Compute prior entropy H(p) for uniform and VRA priors
2. Map entropy to required precision: t ~ log₂(|support|)
3. Estimate controlled-power range from prior concentration
4. Calculate T-depth from power range

Pass Criteria:
- ≥20% reduction in t OR T-depth OR qubit-time product
"""

import argparse
import json
import time
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

def build_uniform_prior(r_min: int, r_max: int):
    """Build flat uniform prior."""
    candidates = np.arange(r_min, r_max + 1)
    prior = np.ones(len(candidates)) / len(candidates)
    return candidates, prior

def build_vra_prior(r_true: int, r_min: int, r_max: int, hit_rate: float, k: int, seed: int = 42):
    """Build VRA-like sparse prior."""
    rng = np.random.default_rng(seed)
    candidates = np.arange(r_min, r_max + 1)

    # Decide if true r is in shortlist
    hit = rng.random() < hit_rate

    # Generate shortlist
    if hit:
        shortlist = [r_true]
        while len(shortlist) < k:
            r_cand = rng.choice(candidates)
            if r_cand not in shortlist:
                shortlist.append(r_cand)
    else:
        shortlist = rng.choice(candidates, size=k, replace=False).tolist()

    # Build sparse prior with softmax kernel
    prior = np.zeros(len(candidates))
    for r_s in shortlist:
        idx = r_s - r_min
        if 0 <= idx < len(candidates):
            prior[idx] = 1.0

    # Softmax with temperature
    tau = 0.1
    prior = np.exp(prior / tau)
    prior /= prior.sum()

    return candidates, prior

def entropy(p):
    """Compute Shannon entropy H(p) in bits."""
    p = p[p > 0]  # Remove zeros
    return -np.sum(p * np.log2(p))

def effective_support_size(p, threshold=0.95):
    """
    Count candidates needed to capture threshold probability mass.
    This is the "effective support" of the prior.
    """
    sorted_p = np.sort(p)[::-1]  # Sort descending
    cumsum = np.cumsum(sorted_p)
    idx = np.searchsorted(cumsum, threshold)
    return idx + 1

def precision_bits_from_entropy(H):
    """
    Map entropy to QPE precision bits.

    Heuristic: t ~ H + margin
    - Higher entropy = broader distribution = need more precision
    - Lower entropy = concentrated = can use fewer bits
    """
    margin = 2  # Safety margin
    return int(np.ceil(H + margin))

def precision_bits_from_support(support_size):
    """
    Map effective support size to precision bits.

    t = ceil(log₂(support_size)) + margin
    """
    margin = 2
    return int(np.ceil(np.log2(support_size) + margin))

def controlled_power_range(support_size):
    """
    Estimate max controlled-U exponent j_max.

    In QPE, we need j_max ~ log₂(r_max) to resolve periods.
    With a concentrated prior, we can reduce j_max.

    j_max ~ log₂(support_size)
    """
    return int(np.ceil(np.log2(support_size)))

def t_gate_depth(j_max):
    """
    Estimate T-gate depth from controlled-power range.

    QPE requires controlled-U^(2^j) for j = 0, 1, ..., j_max-1
    Each controlled operation costs O(2^j) T-gates

    Total T-depth ~ ∑_{j=0}^{j_max-1} 2^j = 2^j_max - 1
    """
    return 2**j_max - 1

def qubit_time_product(t, j_max, t_depth):
    """
    Quantum resource metric: qubit-time product.

    QTP = (ancilla qubits) × (circuit depth)
        = t × T_depth

    Lower is better for NISQ devices.
    """
    return t * t_depth

def main():
    parser = argparse.ArgumentParser(description="E7F: Quantum Resource Model Test")
    parser.add_argument('--r', type=int, default=168, help='True period')
    parser.add_argument('--r-min', type=int, default=32, help='Min search range')
    parser.add_argument('--r-max', type=int, default=1024, help='Max search range')
    parser.add_argument('--prior-hit', type=float, default=0.55, help='VRA hit rate')
    parser.add_argument('--prior-k', type=int, default=12, help='VRA shortlist size')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    print("=" * 70)
    print("E7F: Quantum Resource Model Test")
    print("=" * 70)
    print(f"True period r: {args.r}")
    print(f"Search range: [{args.r_min}, {args.r_max}] ({args.r_max - args.r_min + 1} candidates)")
    print(f"VRA prior: hit_rate={args.prior_hit}, shortlist_k={args.prior_k}")
    print()

    start_time = time.time()

    out_dir = Path("Data/Experiments/Tier3/E7F")
    fig_dir = Path("Figures/Experiments/Tier3/E7F")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Build priors
    print("Building priors...")
    cand_uniform, prior_uniform = build_uniform_prior(args.r_min, args.r_max)
    cand_vra, prior_vra = build_vra_prior(args.r, args.r_min, args.r_max,
                                           args.prior_hit, args.prior_k, args.seed)

    # Compute entropies
    H_uniform = entropy(prior_uniform)
    H_vra = entropy(prior_vra)

    print(f"Entropy:")
    print(f"  Uniform: {H_uniform:.2f} bits")
    print(f"  VRA:     {H_vra:.2f} bits")
    print(f"  Reduction: {H_uniform - H_vra:.2f} bits ({(1 - H_vra/H_uniform)*100:.1f}%)")
    print()

    # Effective support sizes
    support_uniform = effective_support_size(prior_uniform, threshold=0.95)
    support_vra = effective_support_size(prior_vra, threshold=0.95)

    print(f"Effective Support (95% mass):")
    print(f"  Uniform: {support_uniform} candidates")
    print(f"  VRA:     {support_vra} candidates")
    print(f"  Reduction: {support_uniform - support_vra} ({(1 - support_vra/support_uniform)*100:.1f}%)")
    print()

    # Precision bits (from entropy)
    t_uniform_H = precision_bits_from_entropy(H_uniform)
    t_vra_H = precision_bits_from_entropy(H_vra)

    # Precision bits (from support)
    t_uniform_S = precision_bits_from_support(support_uniform)
    t_vra_S = precision_bits_from_support(support_vra)

    # Use support-based estimate (more conservative)
    t_uniform = t_uniform_S
    t_vra = t_vra_S

    print(f"Precision Bits (QPE register size):")
    print(f"  Uniform: {t_uniform} qubits")
    print(f"  VRA:     {t_vra} qubits")
    print(f"  Reduction: {t_uniform - t_vra} qubits ({(1 - t_vra/t_uniform)*100:.1f}%)")
    print()

    # Controlled-power range
    j_max_uniform = controlled_power_range(support_uniform)
    j_max_vra = controlled_power_range(support_vra)

    print(f"Controlled-U Max Exponent (j_max):")
    print(f"  Uniform: {j_max_uniform}")
    print(f"  VRA:     {j_max_vra}")
    print(f"  Reduction: {j_max_uniform - j_max_vra} ({(1 - j_max_vra/j_max_uniform)*100:.1f}%)")
    print()

    # T-gate depth
    depth_uniform = t_gate_depth(j_max_uniform)
    depth_vra = t_gate_depth(j_max_vra)

    print(f"T-Gate Depth (∑ 2^j):")
    print(f"  Uniform: {depth_uniform:,}")
    print(f"  VRA:     {depth_vra:,}")
    print(f"  Reduction: {depth_uniform - depth_vra:,} ({(1 - depth_vra/depth_uniform)*100:.1f}%)")
    print()

    # Qubit-time product
    qtp_uniform = qubit_time_product(t_uniform, j_max_uniform, depth_uniform)
    qtp_vra = qubit_time_product(t_vra, j_max_vra, depth_vra)

    print(f"Qubit-Time Product (t × T_depth):")
    print(f"  Uniform: {qtp_uniform:,}")
    print(f"  VRA:     {qtp_vra:,}")
    print(f"  Reduction: {qtp_uniform - qtp_vra:,} ({(1 - qtp_vra/qtp_uniform)*100:.1f}%)")
    print()

    # Verdict
    t_reduction_pct = (1 - t_vra / t_uniform) * 100
    depth_reduction_pct = (1 - depth_vra / depth_uniform) * 100
    qtp_reduction_pct = (1 - qtp_vra / qtp_uniform) * 100

    threshold = 20.0  # 20% reduction

    pass_t = t_reduction_pct >= threshold
    pass_depth = depth_reduction_pct >= threshold
    pass_qtp = qtp_reduction_pct >= threshold

    passed = pass_t or pass_depth or pass_qtp

    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    print(f"Pass Criterion: ≥20% reduction in t OR T-depth OR QTP")
    print()
    print(f"  Precision bits (t):    {t_reduction_pct:5.1f}% reduction {'✓ PASS' if pass_t else '✗ FAIL'}")
    print(f"  T-gate depth:          {depth_reduction_pct:5.1f}% reduction {'✓ PASS' if pass_depth else '✗ FAIL'}")
    print(f"  Qubit-Time Product:    {qtp_reduction_pct:5.1f}% reduction {'✓ PASS' if pass_qtp else '✗ FAIL'}")
    print()

    if passed:
        print("🎉 E7F: ✓ PASS - VRA reduces quantum circuit resources")
    else:
        print("❌ E7F: ✗ FAIL - VRA provides no resource advantage")
    print("=" * 70)
    print()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "experiment": "E7F",
        "timestamp": timestamp,
        "parameters": {
            "r_true": args.r,
            "r_min": args.r_min,
            "r_max": args.r_max,
            "n_candidates": args.r_max - args.r_min + 1,
            "prior_hit": args.prior_hit,
            "prior_k": args.prior_k,
            "seed": args.seed
        },
        "entropy": {
            "uniform_bits": float(H_uniform),
            "vra_bits": float(H_vra),
            "reduction_bits": float(H_uniform - H_vra),
            "reduction_pct": float((1 - H_vra/H_uniform) * 100)
        },
        "support": {
            "uniform": int(support_uniform),
            "vra": int(support_vra),
            "reduction": int(support_uniform - support_vra),
            "reduction_pct": float((1 - support_vra/support_uniform) * 100)
        },
        "precision_bits": {
            "uniform": int(t_uniform),
            "vra": int(t_vra),
            "reduction": int(t_uniform - t_vra),
            "reduction_pct": float(t_reduction_pct)
        },
        "controlled_power": {
            "uniform_j_max": int(j_max_uniform),
            "vra_j_max": int(j_max_vra),
            "reduction": int(j_max_uniform - j_max_vra),
            "reduction_pct": float((1 - j_max_vra/j_max_uniform) * 100)
        },
        "t_gate_depth": {
            "uniform": int(depth_uniform),
            "vra": int(depth_vra),
            "reduction": int(depth_uniform - depth_vra),
            "reduction_pct": float(depth_reduction_pct)
        },
        "qubit_time_product": {
            "uniform": int(qtp_uniform),
            "vra": int(qtp_vra),
            "reduction": int(qtp_uniform - qtp_vra),
            "reduction_pct": float(qtp_reduction_pct)
        },
        "verdict": {
            "pass_threshold_pct": threshold,
            "precision_bits_pass": pass_t,
            "t_gate_depth_pass": pass_depth,
            "qubit_time_product_pass": pass_qtp,
            "overall_pass": passed
        },
        "runtime_seconds": time.time() - start_time
    }

    results_file = out_dir / f"{timestamp}_E7F_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved: {results_file}")

    # Generate comparison bar chart
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Precision bits
    ax = axes[0, 0]
    ax.bar(['Uniform', 'VRA'], [t_uniform, t_vra], color=['gray', 'green'])
    ax.set_ylabel('Precision Bits (t)')
    ax.set_title(f'QPE Register Size\n({t_reduction_pct:.1f}% reduction)')
    ax.grid(axis='y', alpha=0.3)

    # T-gate depth
    ax = axes[0, 1]
    ax.bar(['Uniform', 'VRA'], [depth_uniform, depth_vra], color=['gray', 'green'])
    ax.set_ylabel('T-Gate Depth')
    ax.set_title(f'Circuit Depth\n({depth_reduction_pct:.1f}% reduction)')
    ax.set_yscale('log')
    ax.grid(axis='y', alpha=0.3)

    # Qubit-Time Product
    ax = axes[1, 0]
    ax.bar(['Uniform', 'VRA'], [qtp_uniform, qtp_vra], color=['gray', 'green'])
    ax.set_ylabel('Qubit-Time Product')
    ax.set_title(f'Total Resource Cost\n({qtp_reduction_pct:.1f}% reduction)')
    ax.set_yscale('log')
    ax.grid(axis='y', alpha=0.3)

    # Summary table
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = f"""
E7F: Quantum Resource Model

Precision bits:  {t_reduction_pct:5.1f}% {'✓' if pass_t else '✗'}
T-gate depth:    {depth_reduction_pct:5.1f}% {'✓' if pass_depth else '✗'}
Qubit-Time:      {qtp_reduction_pct:5.1f}% {'✓' if pass_qtp else '✗'}

Verdict: {'PASS ✓' if passed else 'FAIL ✗'}

VRA prior entropy: {H_vra:.1f} bits
Uniform entropy:   {H_uniform:.1f} bits
Support reduction: {support_uniform - support_vra} candidates
    """
    ax.text(0.1, 0.5, summary_text, fontsize=11, family='monospace',
            verticalalignment='center')

    plt.tight_layout()
    fig_file = fig_dir / f"{timestamp}_E7F_resource_comparison.png"
    plt.savefig(fig_file, dpi=150, bbox_inches='tight')
    print(f"Figure saved: {fig_file}")
    plt.close()

    elapsed = time.time() - start_time
    print(f"\nTotal runtime: {elapsed:.1f}s")
    print("=" * 70)

if __name__ == "__main__":
    main()
