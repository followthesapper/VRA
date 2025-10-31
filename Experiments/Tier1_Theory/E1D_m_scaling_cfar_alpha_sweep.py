#!/usr/bin/env python3
"""
E1D: CFAR Alpha Sweep for M-Scaling
===================================

Goal:
  Find an operating point with strong precision/recall and verify √M scaling
  in the unsaturated regime (recall < 1.0).

Key Idea:
  Sweep CFAR alpha (α) while holding everything else fixed. For each α:
    - Run M ∈ {8,16,32,64,128}
    - Compute CFAR, MAD, and Top-K metrics (reuse E1C helpers)
    - Save all per-case results

Outputs:
  Data/Experiments/Tier1/E1D/E1D_results.json
  (same record schema as E1C, plus "alpha")
"""

import argparse
import json
import numpy as np
from pathlib import Path
import sys

# --- repo wiring -------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Code" / "VRA"))
from core import (
    compute_averaged_spectrum,
    multiplicative_order,
    validated_radius,
    classify_regime,
)

# --- helpers (copied from E1C, trimmed to essentials) -----------------------
def expected_bins(r: int, Lzp: int):
    return [int(round(k * Lzp / r)) for k in range(1, r)]

def circ_dist(i, j, L):
    d = abs(i - j)
    return min(d, L - d)

def keep_local_maxima(mag2, det):
    left = np.roll(mag2, 1)
    right = np.roll(mag2, -1)
    is_peak = (mag2 > left) & (mag2 >= right)
    return det & is_peak

def os_cfar_detect(mag2, guard=9, train=64, q=0.80, alpha=2.5):
    """Circular OS-CFAR (slightly tougher default: q=0.80)."""
    L = len(mag2)
    det = np.zeros(L, dtype=bool)
    idx = np.arange(train)
    for k in range(L):
        left = (k - guard - train + idx) % L
        right = (k + guard + 1 + idx) % L
        noise = np.concatenate([mag2[left], mag2[right]])
        xq = np.quantile(noise, q)
        det[k] = mag2[k] > alpha * xq
    return det

def median_mad_detect(mag2, kappa=8.0):
    median = np.median(mag2)
    mad = np.median(np.abs(mag2 - median))
    thr = median + kappa * mad
    return mag2 > thr

def top_k_detect(mag2, K):
    L = len(mag2)
    left, right = np.roll(mag2, 1), np.roll(mag2, -1)
    peaks = (mag2 > left) & (mag2 >= right)
    pk_idx = np.where(peaks)[0]
    if pk_idx.size == 0:
        return np.zeros(L, dtype=bool)
    order = np.argsort(mag2[pk_idx])[-min(K, pk_idx.size):]
    chosen = pk_idx[order]
    det = np.zeros(L, dtype=bool)
    det[chosen] = True
    return det

def compute_precision_recall_from_detections(detections, expected_bins, radius):
    L = len(detections)
    peak_indices = np.where(detections)[0]
    expected_set = set(expected_bins)
    matched_expected_bins = set()
    TP_peaks = 0
    FP_peaks = 0
    for idx in peak_indices:
        matched = False
        for exp_idx in expected_set:
            if circ_dist(idx, exp_idx, L) <= radius:
                matched = True
                matched_expected_bins.add(exp_idx)
                break
        if matched: TP_peaks += 1
        else: FP_peaks += 1
    TP = len(matched_expected_bins)
    FP = FP_peaks
    FN = len(expected_set) - TP
    precision = TP_peaks / (TP_peaks + FP_peaks) if (TP_peaks + FP_peaks) else 0.0
    recall = TP / (TP + FN) if (TP + FN) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return dict(precision=precision, recall=recall, f1=f1, TP=TP, FP=FP, FN=FN, num_peaks=len(peak_indices))

def compute_harmonic_snr(mag2, expected):
    if not expected: return 0.0
    vals = [mag2[int(b)] for b in expected if 0 <= int(b) < len(mag2)]
    if not vals: return 0.0
    signal = np.mean(vals)
    noise = np.median(mag2)
    lin = (signal / noise) if noise > 0 else 0.0
    return (10 * np.log10(lin)) if lin > 0 else -np.inf

def find_bases_with_order(N: int, r: int, M_max: int):
    bases, a = [], 2
    while len(bases) < M_max and a < N:
        if np.gcd(a, N) == 1:
            try:
                if multiplicative_order(a, N) == r:
                    bases.append(a)
            except Exception:
                pass
        a += 1
    return bases

def main(out_dir: str, quick: bool = False):
    np.random.seed(42)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Quick mode: trim parameters for ~30% runtime (exploratory)
    if quick:
        MODULI = [997, 2017, 3001]  # 3 instead of 5
        ALPHAS = [2.0, 2.5, 3.0]    # 3 instead of 7
        print("⚡ QUICK MODE: 3 moduli, 3 alphas (~30% of full sweep)")
    else:
        MODULI = [997, 1009, 1013, 2017, 3001]
        ALPHAS = [2.0, 2.2, 2.5, 2.8, 3.0, 3.5, 4.0]

    M_VALUES = [8, 16, 32, 64, 128]
    L = 131072
    WINDOW = "hamming"
    MAD_KAPPA = 8.0
    Q = 0.80
    TRAIN = 64

    all_results = []

    print("E1D: CFAR α sweep for M-scaling\n")
    print(f"Alphas: {ALPHAS}")
    print(f"M values: {M_VALUES}")
    print(f"Moduli: {MODULI}\n")

    for N in MODULI:
        print(f"Processing N={N} ...")
        # Enumerate representative orders (as in E1C)
        seen_orders, cases = set(), []
        for a in range(2, min(N, 400)):
            if np.gcd(a, N) == 1:
                try:
                    r = multiplicative_order(a, N)
                    if r not in seen_orders:
                        seen_orders.add(r)
                        rho = r / N
                        regime, _ = classify_regime(N, r)
                        cases.append((r, rho, regime))
                except Exception:
                    pass
        cases.sort(key=lambda x: x[1])

        # pick per-regime representatives
        reps = []
        for _, (lo, hi) in [('HIGH_SNR',(0.0,0.146)), ('TRANSITION',(0.146,0.263)), ('LOW_SNR',(0.263,1.0))]:
            opts = [r for r, rho, _ in cases if lo <= rho < hi]
            if opts:
                reps.extend([opts[0], opts[len(opts)//2], opts[-1]] if len(opts) >= 3 else opts)
        reps = sorted(set(reps))

        for r in reps:
            bases = find_bases_with_order(N, r, max(M_VALUES))
            if len(bases) < min(M_VALUES):  # skip if too few
                continue

            # OPTIMIZATION: Compute spectrum once per (N,r,M), test all alphas on it
            for M in M_VALUES:
                if len(bases) < M:
                    continue

                # Compute spectrum once (expensive FFT)
                selected_bases = bases[:M]
                Lzp = L * 4
                R = validated_radius(Lzp)
                hb = expected_bins(r, Lzp)
                mag2 = compute_averaged_spectrum(N, selected_bases, x0=1, length=L, zp=4, window=WINDOW)
                snr_db = float(compute_harmonic_snr(mag2, hb))

                regime, _ = classify_regime(N, r)
                rho = r / N

                # Test all alphas on same spectrum (cheap thresholding)
                for alpha in ALPHAS:
                    det_cfar = os_cfar_detect(mag2, guard=R, train=TRAIN, q=Q, alpha=alpha)
                    det_cfar = keep_local_maxima(mag2, det_cfar)
                    m_cfar = compute_precision_recall_from_detections(det_cfar, hb, R)

                    det_mad = median_mad_detect(mag2, kappa=MAD_KAPPA)
                    det_mad = keep_local_maxima(mag2, det_mad)
                    m_mad = compute_precision_recall_from_detections(det_mad, hb, R)

                    K = min(2 * r, len(mag2))
                    det_topk = top_k_detect(mag2, K)
                    m_topk = compute_precision_recall_from_detections(det_topk, hb, R)

                    rec = {
                        "alpha": float(alpha),
                        "N": int(N),
                        "r": int(r),
                        "rho": float(rho),
                        "regime": regime,
                        "M": int(M),
                        "L": int(L),
                        "window": WINDOW,
                        "harmonic_snr_db": snr_db,
                        "cfar_precision": m_cfar["precision"],
                        "cfar_recall": m_cfar["recall"],
                        "cfar_f1": m_cfar["f1"],
                        "cfar_TP": m_cfar["TP"],
                        "cfar_FP": m_cfar["FP"],
                        "cfar_FN": m_cfar["FN"],
                        "cfar_num_peaks": m_cfar["num_peaks"],
                        "mad_precision": m_mad["precision"],
                        "mad_recall": m_mad["recall"],
                        "mad_f1": m_mad["f1"],
                        "mad_num_peaks": m_mad["num_peaks"],
                        "topk_precision": m_topk["precision"],
                        "topk_recall": m_topk["recall"],
                        "topk_f1": m_topk["f1"],
                        "topk_num_peaks": m_topk["num_peaks"],
                    }
                    all_results.append(rec)

        done = len([r for r in all_results if r["N"] == N])
        print(f"  Completed N={N}: {done} rows")

    out_file = out / "E1D_results.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n✅ Saved {len(all_results)} rows to {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E1D: CFAR α sweep for M-scaling")
    parser.add_argument("--out", default="../../Data/Experiments/Tier1/E1D", help="Output directory")
    parser.add_argument("--quick", action="store_true", help="Quick mode: 3 moduli, 3 alphas (~30%% runtime)")
    args = parser.parse_args()
    main(args.out, quick=args.quick)
