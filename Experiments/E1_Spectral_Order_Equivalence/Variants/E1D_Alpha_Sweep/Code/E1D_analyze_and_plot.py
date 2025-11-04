#!/usr/bin/env python3
"""
E1D Analysis & Plots
====================

Answers:
  1) For which α do we hit good precision/recall per regime?
  2) For those α where recall < 1.0, does recall increase with √M?
  3) Does within-(N,r) harmonic SNR increase with √M?

Outputs:
  ../Figures/E1D_*.png
  ../Data/E1D_verdict.json
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

def linreg(x, y):
    x, y = np.array(x, float), np.array(y, float)
    xm, ym = x.mean(), y.mean()
    num = ((x-xm)*(y-ym)).sum()
    den = ((x-xm)**2).sum()
    if den == 0: return 0.0, ym, 0.0
    slope = num/den
    intercept = ym - slope*xm
    yhat = slope*x + intercept
    ss_res = ((y - yhat)**2).sum()
    ss_tot = ((y - ym)**2).sum()
    r2 = 1 - (ss_res/ss_tot) if ss_tot > 0 else 0.0
    return slope, intercept, r2

def load(path):
    with open(path, "r") as f:
        return json.load(f)

def by_alpha(results):
    d = defaultdict(list)
    for r in results:
        d[r["alpha"]].append(r)
    return dict(sorted(d.items()))

def by_regime_M(rows):
    out = defaultdict(lambda: defaultdict(list))
    for r in rows:
        out[r["regime"]][r["M"]].append(r)
    return out

def mean_metric(rows, key):
    vals = [r[key] for r in rows]
    return float(np.mean(vals)) if vals else None

def analyze_pr_curves(results, out_dir):
    """PR vs alpha per regime (at M=64 by default)."""
    target_M = 64
    regimes = ["HIGH_SNR", "TRANSITION", "LOW_SNR"]
    plt.figure(figsize=(10,6))
    for reg, mkr in zip(regimes, ["o-","s-","^-"]):
        xs, precs, recs = [], [], []
        for alpha, rows in by_alpha(results).items():
            rows_m = [r for r in rows if r["M"]==target_M and r["regime"]==reg]
            if not rows_m: continue
            xs.append(alpha)
            precs.append(mean_metric(rows_m, "cfar_precision"))
            recs.append(mean_metric(rows_m, "cfar_recall"))
        if xs:
            plt.plot(xs, precs, mkr, label=f"{reg} — Precision")
            plt.plot(xs, recs, mkr.replace('-','--'), label=f"{reg} — Recall")
    plt.axhline(0.85, linestyle=":", label="Precision target (85%)")
    plt.axhline(0.60, linestyle=":", label="Recall target (60%)")
    plt.xlabel("CFAR α"); plt.ylabel("Metric"); plt.title(f"E1D: Precision/Recall vs α (M={target_M})")
    plt.grid(alpha=0.3); plt.legend(fontsize=9)
    p = Path(out_dir)/"E1D_pr_vs_alpha_M64.png"
    plt.tight_layout(); plt.savefig(p, dpi=300); plt.close()
    print(f"Saved {p}")

def analyze_sqrtM_scaling_unsaturated(results, out_dir):
    """Where recall<1.0 across M, fit recall vs √M and report best α per regime."""
    regimes = ["HIGH_SNR", "TRANSITION", "LOW_SNR"]
    summary = {}
    for alpha, rows in by_alpha(results).items():
        M_values = sorted(set(r["M"] for r in rows))
        sqrtM = [np.sqrt(M) for M in M_values]
        reg_stats = {}
        for reg in regimes:
            means = []
            for M in M_values:
                vals = [r["cfar_recall"] for r in rows if r["regime"]==reg and r["M"]==M]
                means.append(np.mean(vals) if vals else np.nan)
            means = np.array(means, float)
            # use only if any means < 1.0 (unsaturated)
            if np.all(np.isnan(means)) or np.nanmin(means) >= 1.0:
                reg_stats[reg] = {"slope":0.0,"r2":0.0,"status":"saturated"}
                continue
            # drop NaNs for regression
            x = [x for x, y in zip(sqrtM, means) if not np.isnan(y)]
            y = [y for y in means if not np.isnan(y)]
            slope, _, r2 = linreg(x, y)
            reg_stats[reg] = {"slope":float(slope), "r2":float(r2), "status":"fit"}
        summary[alpha] = reg_stats

    # plot: for LOW_SNR show recall vs √M for each α (E4-style with fits)
    plt.figure(figsize=(10,6))
    for alpha, rows in by_alpha(results).items():
        M_values = sorted(set(r["M"] for r in rows))
        sqrtM = [np.sqrt(M) for M in M_values]
        means = []
        for M in M_values:
            vals = [r["cfar_recall"] for r in rows if r["regime"]=="LOW_SNR" and r["M"]==M]
            means.append(np.mean(vals) if vals else np.nan)
        if np.all(np.isnan(means)):
            continue

        plt.plot(sqrtM, means, "o-", label=f"α={alpha}")

        # Add linear fit if not saturated (E4-style)
        valid_x = [x for x, y in zip(sqrtM, means) if not np.isnan(y)]
        valid_y = [y for y in means if not np.isnan(y)]
        if len(valid_x) >= 3 and min(valid_y) < 0.95:
            slope, intercept, r2 = linreg(valid_x, valid_y)
            x_fit = np.linspace(min(valid_x), max(valid_x), 50)
            y_fit = slope * x_fit + intercept
            plt.plot(x_fit, y_fit, '--', alpha=0.5, label=f'α={alpha} fit (R²={r2:.3f})')

    plt.axhline(0.60, linestyle=":", color='gray', label="Target recall (60%)")
    plt.ylim(0,1.05)
    plt.xlabel("√M")
    plt.ylabel("LOW_SNR Recall")
    plt.title("E1D: LOW_SNR Recall vs √M across α")
    plt.grid(alpha=0.3)
    plt.legend(ncol=2, fontsize=9)
    p = Path(out_dir)/"E1D_low_snr_recall_vs_sqrtM_by_alpha.png"
    plt.tight_layout(); plt.savefig(p, dpi=300); plt.close()
    print(f"Saved {p}")
    return summary

def analyze_precision_vs_sqrtM(results, out_dir):
    """Plot precision vs √M for each α (E4-style)"""
    plt.figure(figsize=(10,6))
    for alpha, rows in by_alpha(results).items():
        M_values = sorted(set(r["M"] for r in rows))
        sqrtM = [np.sqrt(M) for M in M_values]
        means = []
        for M in M_values:
            vals = [r["cfar_precision"] for r in rows if r["regime"]=="LOW_SNR" and r["M"]==M]
            means.append(np.mean(vals) if vals else np.nan)
        if np.all(np.isnan(means)):
            continue
        plt.plot(sqrtM, means, "s-", label=f"α={alpha}")

    plt.axhline(0.85, linestyle=":", color='gray', label="Target precision (85%)")
    plt.ylim(0,1.05)
    plt.xlabel("√M")
    plt.ylabel("LOW_SNR Precision")
    plt.title("E1D: LOW_SNR Precision vs √M across α")
    plt.grid(alpha=0.3)
    plt.legend(ncol=2, fontsize=9)
    p = Path(out_dir)/"E1D_low_snr_precision_vs_sqrtM_by_alpha.png"
    plt.tight_layout(); plt.savefig(p, dpi=300); plt.close()
    print(f"Saved {p}")

def analyze_within_case_snr(results, out_dir):
    """Per (N,r,alpha): slope of SNR vs √M, then aggregate slopes."""
    # group by (N,r,alpha)
    groups = defaultdict(list)
    for r in results:
        key = (r["N"], r["r"], r["alpha"])
        groups[key].append(r)

    slopes = []
    for (N, r, alpha), rows in groups.items():
        rows = sorted(rows, key=lambda x: x["M"])
        x = [np.sqrt(rr["M"]) for rr in rows]
        y = [rr["harmonic_snr_db"] for rr in rows]
        if len(set(x)) < 2: 
            continue
        slope, _, _ = linreg(x, y)
        slopes.append(slope)

    if slopes:
        mean_slope = float(np.mean(slopes))
        med_slope  = float(np.median(slopes))
    else:
        mean_slope = med_slope = 0.0

    plt.figure(figsize=(8,5))
    plt.hist(slopes, bins=30)
    plt.axvline(0, color="k", linestyle=":")
    plt.xlabel("SNR slope (dB per √M)"); plt.ylabel("Count")
    plt.title("E1D: Within-(N,r,α) SNR slopes vs √M")
    p = Path(out_dir)/"E1D_within_case_snr_slopes.png"
    plt.tight_layout(); plt.savefig(p, dpi=300); plt.close()
    print(f"Saved {p}")
    return {"mean_slope_db_per_sqrtM": mean_slope, "median_slope_db_per_sqrtM": med_slope, "num_groups": len(slopes)}

def choose_operating_points(pr_plot_source, results):
    """
    Simple heuristic picks:
      HIGH_SNR: α with precision≥0.90 & recall≥0.85 at M=64
      TRANSITION: precision≥0.85 & recall≥0.75
      LOW_SNR: precision≥0.80 & recall≥0.60
    Returns dict by regime.
    """
    target_M = 64
    targets = {
        "HIGH_SNR": (0.90, 0.85),
        "TRANSITION": (0.85, 0.75),
        "LOW_SNR": (0.80, 0.60),
    }
    picks = {}
    grouped = by_alpha(results)
    for reg, (pmin, rmin) in targets.items():
        best = None
        for alpha, rows in grouped.items():
            rows_m = [r for r in rows if r["M"]==target_M and r["regime"]==reg]
            if not rows_m: continue
            p = mean_metric(rows_m, "cfar_precision")
            r = mean_metric(rows_m, "cfar_recall")
            f1 = (2*p*r/(p+r)) if (p+r)>0 else 0.0
            if p>=pmin and r>=rmin:
                if best is None or f1 > best["f1"]:
                    best = {"alpha":alpha, "precision":p, "recall":r, "f1":f1}
        if best: picks[reg] = best
    return picks

def main():
    res_file = Path("../Data/E1D_results.json")
    out_dir = Path("../Figures")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = load(res_file)
    print(f"Loaded {len(results)} rows from {res_file}")

    analyze_pr_curves(results, out_dir)
    unsat = analyze_sqrtM_scaling_unsaturated(results, out_dir)
    analyze_precision_vs_sqrtM(results, out_dir)  # E4-style precision plot
    snr_summary = analyze_within_case_snr(results, out_dir)
    picks = choose_operating_points(None, results)

    verdict = {
        "recommended_alphas": picks,                # per-regime candidates
        "unsaturated_scaling_summary": unsat,       # slope/r2 per alpha per regime
        "within_case_snr_summary": snr_summary,     # mean/median slope
    }

    out_json = res_file.parent / "E1D_verdict.json"
    with open(out_json, "w") as f:
        json.dump(verdict, f, indent=2)
    print(f"Saved verdict to {out_json}")

if __name__ == "__main__":
    main()
