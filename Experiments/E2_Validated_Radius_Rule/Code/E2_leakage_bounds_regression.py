#!/usr/bin/env python3
"""
E2 — Leakage Bound Regression (radius rule)
-------------------------------------------
Goal: Fit/log-sweep across L to confirm R ≈ 0.5*log2(L) minimizes FP without harming recall.

Outputs
  • JSON summary:  E2_results.json
  • CSV table:     E2_fp_recall_table.csv
  • PNG figures:   E2_fp_vs_radius.png, E2_recall_vs_radius.png, E2_opt_radius_vs_L.png

Assumptions
  • Imports VRA core from ../../Code/Core (adjust sys.path if needed).
  • compute_averaged_spectrum, compute_precision_recall, validated_radius exist.

Run (from Code/ directory)
  python3 E2_leakage_bounds_regression.py --out ../Data
"""
import argparse, json, csv
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import sys

# Adjust for your repo layout
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Code" / "VRA"))

from core import (
    multiplicative_order,
    compute_averaged_spectrum,
    compute_precision_recall,
    validated_radius,
    classify_regime,
)

WINDOWS = ["hann", "hamming", "blackman"]
L_LIST = [2**16, 2**17, 2**18]
M = 16
MODULI = [997, 1009, 1013, 2017, 3001]


def expected_bins(r: int, Lzp: int):
    """Generate all expected harmonic bin locations for order r.

    Returns list of FFT bin indices corresponding to harmonics k*Lzp/r
    for k = 1, 2, ..., r-1.
    """
    return [int(round(k * Lzp / r)) for k in range(1, r)]


def find_orders(N: int, cap: int = 300):
    seen = set()
    for a in range(2, min(N, cap)):
        if np.gcd(a, N) == 1:
            try:
                r = multiplicative_order(a, N)
                if r not in seen:
                    seen.add(r)
                    yield r
            except Exception:
                pass


def pick_bases_with_order(N: int, r: int, M: int):
    bases = []
    a = 2
    while len(bases) < M and a < N:
        if np.gcd(a, N) == 1:
            try:
                if multiplicative_order(a, N) == r:
                    bases.append(a)
            except Exception:
                pass
        a += 1
    return bases


def sweep_radius(mag2, r, Lzp, R_grid):
    hb = expected_bins(r, Lzp)
    out = []
    for R in R_grid:
        metrics = compute_precision_recall(mag2, hb, int(R))
        out.append({"R": float(R), **{k: float(v) for k, v in metrics.items()}})
    return out


def fit_opt_radius(records):
    # Choose R* that minimizes FP with recall >= 0.95 of best recall
    if not records:
        return None
    best_recall = max(r["recall"] for r in records)
    candidates = [r for r in records if r["recall"] >= 0.95 * best_recall]
    if not candidates:
        candidates = records
    # Among candidates, select minimal FP; tie-breaker: higher precision
    candidates.sort(key=lambda d: (d["FP"], -d["precision"]))
    return candidates[0]


def main(out_dir: str):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    table_rows = []
    json_rows = []

    for N in MODULI:
        # collect a few orders spanning regimes
        orders = list(find_orders(N, cap=400))
        if not orders:
            continue
        # pick 3 representative orders ~ HIGH/TRANS/LOW via rho=r/N
        orders.sort(key=lambda r: r / N)
        picks = []
        for rho_lo, rho_hi in [(0.0, 0.146), (0.146, 0.263), (0.263, 1.0)]:
            cands = [r for r in orders if rho_lo <= (r / N) < rho_hi]
            if cands:
                picks.append(cands[len(cands) // 2])
        for r in picks:
            rho = r / N
            for L in L_LIST:
                Lzp = L * 4
                R0 = validated_radius(Lzp)
                # radius sweep: 0.25..1.25 times log2 L / 2
                base = 0.5 * np.log2(L)
                R_grid = np.unique(np.clip(np.round(np.linspace(0.25, 1.25, 17) * base), 1, None)).astype(int)
                bases = pick_bases_with_order(N, r, M)
                if len(bases) < max(1, M // 2):
                    continue
                for win in WINDOWS:
                    mag2 = compute_averaged_spectrum(N, bases, x0=1, length=L, zp=4, window=win)
                    records = sweep_radius(mag2, r, Lzp, R_grid)
                    opt = fit_opt_radius(records)
                    regime, _ = classify_regime(N, r)
                    json_rows.append({
                        "N": N, "r": r, "rho": float(rho), "regime": regime,
                        "L": int(L), "window": win, "validated_R": int(R0),
                        "records": records, "opt": opt,
                    })
                    for rec in records:
                        table_rows.append([
                            N, r, rho, regime, L, win, R0,
                            int(rec["R"]), rec["precision"], rec["recall"], rec["FP"], rec["FN"], rec["TP"]
                        ])

    # write CSV
    csv_path = out_path / "E2_fp_recall_table.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["N","r","rho","regime","L","window","validated_R","R","precision","recall","FP","FN","TP"])
        w.writerows(table_rows)

    # write JSON
    (out_path / "E2_results.json").write_text(json.dumps(json_rows, indent=2))

    # Figures: aggregate FP/Recall vs normalized radius
    def plot_metric(metric, fname):
        xs, ys = [], []
        for row in json_rows:
            L = row["L"]
            base = 0.5 * np.log2(L)
            for rec in row["records"]:
                xs.append(rec["R"] / base)
                ys.append(rec[metric])
        if xs:
            plt.figure(figsize=(7,4))
            plt.scatter(xs, ys, s=10, alpha=0.5)
            plt.xlabel("R / (0.5 log2 L)")
            plt.ylabel(metric.capitalize())
            plt.title(f"E2: {metric.capitalize()} vs normalized radius")
            plt.grid(alpha=0.3)
            plt.savefig(out_path / fname, dpi=200, bbox_inches="tight")
            plt.close()
    plot_metric("FP", "E2_fp_vs_radius.png")
    plot_metric("recall", "E2_recall_vs_radius.png")

    # Plot optimal R* vs L
    Rstars = []
    for row in json_rows:
        L = row["L"]; base = 0.5*np.log2(L)
        if row["opt"]:
            Rstars.append((L, row["opt"]["R"] / base))
    if Rstars:
        xs, ys = zip(*Rstars)
        plt.figure(figsize=(6,4))
        plt.scatter(xs, ys, s=12, alpha=0.6)
        plt.xscale("log", base=2)
        plt.axhline(1.0, linestyle=":")
        plt.xlabel("L")
        plt.ylabel("R* / (0.5 log2 L)")
        plt.title("E2: Optimal radius vs L (normalized)")
        plt.grid(alpha=0.3)
        plt.savefig(out_path / "E2_opt_radius_vs_L.png", dpi=200, bbox_inches="tight")
        plt.close()

    print(f"[ok] Wrote {csv_path} and E2_results.json + figures")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../Data")
    args = ap.parse_args()
    main(args.out)