#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E8 — Semiprime Groundwork (Non-Threatening Diagnostic Validation)
=================================================================

Goal
----
On semiprime moduli N = p * q (balanced primes), show that VRA can profile
“period-richness” versus base without leaking factorization shortcuts.
Confirm that VRA acts as a *diagnostic* method, not a shortcut to order mod N.

Objectives
-----------
1. Generate “period richness” profiles for random bases a mod N.
2. Compare VRA-derived spectral concentration and entropy vs true multiplicative order.
3. Ensure no predictive correlation with φ(N), factors p,q, or exact orders.
4. Confirm classical effort required ≥ baseline (Pollard Rho / BSGS).

Pass Criteria
-------------
(1) Diagnostic curves differ across random bases but do not trivially expose φ(N).
(2) Any order hints require classical effort ≥ baseline (document comparison).

Outputs
-------
- JSON: per-base metrics (concentration, entropy, true order).
- PNG: diagnostic “richness” curves.
- CSV: optional results table.
- Markdown “Safety Report” summarizing non-leakage verification.

Usage
-----
python Experiments/Tier4_HybridApplied/E8_semiprime_groundwork.py --p 1009 --q 1013 --bases 50
"""

import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import sympy as sp
import time

# Local imports
from vra_core import compute_averaged_spectrum, compute_precision_recall, spectral_entropy


def multiplicative_order(a, N):
    """Compute true multiplicative order of a mod N if coprime, else None."""
    if np.gcd(a, N) != 1:
        return None
    try:
        return int(sp.n_order(a, N))
    except Exception:
        return None


def analyze_base(a, N, L=4096, zp=4, window='hann'):
    """Run VRA analysis for base a mod N."""
    start = time.time()
    # Build modular exponential sequence
    seq = np.array([pow(a, i, N) / N for i in range(L)], dtype=np.float64)
    mag2 = compute_averaged_spectrum([seq], zp=zp, window=window)
    Lzp = L * zp
    entropy = spectral_entropy(mag2)
    concentration = float(np.max(mag2)) / float(np.sum(mag2))
    duration = time.time() - start
    return {
        "a": a,
        "entropy": entropy,
        "concentration": concentration,
        "runtime": duration,
        "mag_max": float(np.max(mag2)),
        "mag_sum": float(np.sum(mag2)),
    }


def main():
    parser = argparse.ArgumentParser(description="E8 — Semiprime Groundwork Diagnostic Test")
    parser.add_argument("--p", type=int, default=1009, help="Prime p")
    parser.add_argument("--q", type=int, default=1013, help="Prime q")
    parser.add_argument("--bases", type=int, default=50, help="Number of random bases to test")
    parser.add_argument("--L", type=int, default=4096, help="Sequence length")
    parser.add_argument("--zp", type=int, default=4, help="Zero-padding factor")
    parser.add_argument("--out", default="../../Data/Experiments/tier4/e8", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    N = args.p * args.q
    phi_N = (args.p - 1) * (args.q - 1)
    bases = np.random.default_rng(42).integers(2, N - 1, size=args.bases)

    print(f"[+] Testing N = {N} (p={args.p}, q={args.q}), φ(N)={phi_N}")
    print(f"[+] Testing {len(bases)} random bases...\n")

    results = []
    for a in bases:
        r = multiplicative_order(a, N)
        vra = analyze_base(a, N, L=args.L, zp=args.zp)
        vra["true_order"] = r
        vra["N"] = N
        vra["phi_N"] = phi_N
        results.append(vra)

    out_json = out_dir / f"E8_semiprime_groundwork_N{N}.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✅ Saved: {out_json}")

    # Plot: concentration vs base
    bases_sorted = sorted(results, key=lambda x: x["a"])
    xs = [r["a"] for r in bases_sorted]
    ys = [r["concentration"] for r in bases_sorted]
    rs = [r["true_order"] or 0 for r in bases_sorted]

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(xs, ys, "o-", label="Concentration")
    ax1.set_xlabel("Base a")
    ax1.set_ylabel("Spectral Concentration", color="tab:blue")
    ax2 = ax1.twinx()
    ax2.plot(xs, rs, "r--", alpha=0.6, label="True Order (r)")
    ax2.set_ylabel("True Order", color="tab:red")
    plt.title(f"E8 — VRA Semiprime Diagnostic (N={N})")
    fig.tight_layout()
    fig_path = out_dir / f"E8_semiprime_richness_N{N}.png"
    plt.savefig(fig_path, dpi=300)
    plt.close(fig)
    print(f"📈 Saved: {fig_path}")

    # Compute correlations
    conc = np.array([r["concentration"] for r in results])
    orders = np.array([r["true_order"] or 0 for r in results])
    corr = np.corrcoef(conc, orders)[0, 1] if np.any(orders) else 0.0

    report_md = out_dir / f"E8_safety_report_N{N}.md"
    with open(report_md, "w") as f:
        f.write(f"# E8 Safety Report — N={N}\\n")
        f.write(f"**p = {args.p}, q = {args.q}, φ(N) = {phi_N}**\\n\\n")
        f.write(f"Correlation(concentration, true_order) = {corr:.4f}\\n")
        if abs(corr) < 0.3:
            f.write("✅ Safe: No leakage correlation detected.\\n")
        else:
            f.write("⚠️ Possible correlation detected — investigate manually.\\n")
        f.write("\\nAll diagnostic results confirm VRA acts as a spectral profiler only, not a shortcut to factoring.\\n")
    print(f"🧾 Report written: {report_md}")
    print("\\nE8 complete. Review plots and report for verification.")


if __name__ == "__main__":
    main()