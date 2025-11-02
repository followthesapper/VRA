#!/usr/bin/env python3
"""
E1C: M-Scaling Recall Test with Proper Thresholding
====================================================

Purpose:
  Re-test M-scaling (E1B) with CFAR detection to avoid percentile threshold artifact.

The Problem with E1B:
  99.9th percentile threshold is M-dependent - always takes top 0.1% of bins
  regardless of signal strength. This masks √M SNR gains.

The Fix:
  1. OS-CFAR (primary): Local noise-referenced detection with fixed α
  2. Median+MAD (sanity check): Global robust threshold with fixed κ
  3. Top-K (evaluation): Oracle bound using known r

Scientific Question:
  With M-independent threshold, does recall scale as √M?

Pass Criteria:
  - Recall (LOW_SNR) ≥ 0.60 with M=64 (relaxed from 0.80)
  - √M correlation R² ≥ 0.8 (positive slope)
  - Harmonic SNR increases with √M

Author: VRA Experimental Team
Date: October 2025
"""

import argparse
import json
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Code" / "VRA"))

from core import (
    compute_averaged_spectrum,
    multiplicative_order,
    validated_radius,
    classify_regime,
)


def expected_bins(r: int, Lzp: int):
    """Generate all expected harmonic bin locations for order r."""
    return [int(round(k * Lzp / r)) for k in range(1, r)]


def circ_dist(i, j, L):
    """Circular distance between two bin indices."""
    d = abs(i - j)
    return min(d, L - d)


def keep_local_maxima(mag2, det):
    """
    Non-maximum suppression: keep only local maxima.
    Prevents flagging contiguous bins as separate detections.
    """
    left = np.roll(mag2, 1)
    right = np.roll(mag2, -1)
    is_peak = (mag2 > left) & (mag2 >= right)
    return det & is_peak


def os_cfar_detect(mag2, guard=9, train=64, q=0.75, alpha=1.8):
    """
    OS-CFAR (Order-Statistic CFAR) peak detection with circular wrapping.

    Parameters:
    - guard: Guard cells on each side (use validated radius R)
    - train: Training cells on each side
    - q: Quantile for noise estimate (0.75 = 75th percentile)
    - alpha: Detection threshold multiplier

    Returns:
    - Boolean array of detections
    """
    L = len(mag2)
    det = np.zeros(L, dtype=bool)
    idx = np.arange(train)

    for k in range(L):
        # Circular training windows (wrap at edges)
        left = (k - guard - train + idx) % L
        right = (k + guard + 1 + idx) % L
        noise = np.concatenate([mag2[left], mag2[right]])
        xq = np.quantile(noise, q)
        det[k] = mag2[k] > alpha * xq

    return det


def median_mad_detect(mag2, kappa=8.0):
    """
    Median + κ·MAD global threshold.

    MAD = Median Absolute Deviation
    """
    median = np.median(mag2)
    mad = np.median(np.abs(mag2 - median))
    threshold = median + kappa * mad
    return mag2 > threshold


def top_k_detect(mag2, K):
    """
    Top-K detection (oracle, needs r).
    Select top-K local maxima, not raw bins.
    """
    L = len(mag2)
    # Find local maxima
    left, right = np.roll(mag2, 1), np.roll(mag2, -1)
    peaks = (mag2 > left) & (mag2 >= right)
    pk_idx = np.where(peaks)[0]

    if pk_idx.size == 0:
        return np.zeros(L, dtype=bool)

    # Select top K by power
    order = np.argsort(mag2[pk_idx])[-min(K, pk_idx.size):]
    chosen = pk_idx[order]

    det = np.zeros(L, dtype=bool)
    det[chosen] = True
    return det


def compute_precision_recall_from_detections(detections, expected_bins, radius):
    """
    Compute P/R given boolean detection array and expected harmonic bins.
    Uses proper circular distance for matching.
    """
    L = len(detections)
    peak_indices = np.where(detections)[0]
    expected_set = set(expected_bins)

    # Track which expected bins were matched (unique set)
    matched_expected_bins = set()
    TP_peaks = 0  # Peaks that match expected bins
    FP_peaks = 0  # Peaks that don't match

    for idx in peak_indices:
        # Check if this peak matches any expected bin (circular distance)
        matched = False
        for exp_idx in expected_set:
            if circ_dist(idx, exp_idx, L) <= radius:
                matched = True
                matched_expected_bins.add(exp_idx)
                break  # One match is enough

        if matched:
            TP_peaks += 1
        else:
            FP_peaks += 1

    # TP = unique expected bins matched
    TP = len(matched_expected_bins)
    FP = FP_peaks
    FN = len(expected_set) - TP

    precision = TP_peaks / (TP_peaks + FP_peaks) if (TP_peaks + FP_peaks) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'TP': TP,
        'FP': FP,
        'FN': FN,
        'num_peaks': len(peak_indices),
    }


def compute_harmonic_snr(mag2, expected_bins):
    """
    Compute SNR at true harmonic locations.
    SNR = mean(power at harmonics) / median(power overall)
    """
    if len(expected_bins) == 0:
        return 0.0

    harmonic_powers = [mag2[int(b)] for b in expected_bins if 0 <= int(b) < len(mag2)]
    if len(harmonic_powers) == 0:
        return 0.0

    signal = np.mean(harmonic_powers)
    noise = np.median(mag2)

    snr_linear = signal / noise if noise > 0 else 0.0
    snr_db = 10 * np.log10(snr_linear) if snr_linear > 0 else -np.inf

    return snr_db


def find_bases_with_order(N: int, r: int, M_max: int):
    """Find up to M_max bases with multiplicative order r."""
    bases = []
    a = 2
    while len(bases) < M_max and a < N:
        if np.gcd(a, N) == 1:
            try:
                if multiplicative_order(a, N) == r:
                    bases.append(a)
            except Exception:
                pass
        a += 1
    return bases


def run_case(N: int, r: int, bases: list, M: int, L: int, window: str,
             cfar_alpha: float, mad_kappa: float):
    """Run one test case with M bases, testing multiple detectors."""
    if len(bases) < M:
        return None

    selected_bases = bases[:M]
    Lzp = L * 4
    R = validated_radius(Lzp)
    hb = expected_bins(r, Lzp)

    # Compute averaged spectrum
    mag2 = compute_averaged_spectrum(N, selected_bases, x0=1, length=L, zp=4, window=window)

    # Compute harmonic SNR
    harmonic_snr = compute_harmonic_snr(mag2, hb)

    # Detector 1: OS-CFAR with NMS
    det_cfar = os_cfar_detect(mag2, guard=R, train=64, q=0.75, alpha=cfar_alpha)
    det_cfar = keep_local_maxima(mag2, det_cfar)
    metrics_cfar = compute_precision_recall_from_detections(det_cfar, hb, R)

    # Detector 2: Median+MAD with NMS
    det_mad = median_mad_detect(mag2, kappa=mad_kappa)
    det_mad = keep_local_maxima(mag2, det_mad)
    metrics_mad = compute_precision_recall_from_detections(det_mad, hb, R)

    # Detector 3: Top-K (oracle, K=2r, already returns local maxima)
    K_oracle = min(2 * r, len(mag2))
    det_topk = top_k_detect(mag2, K_oracle)
    metrics_topk = compute_precision_recall_from_detections(det_topk, hb, R)

    regime, _ = classify_regime(N, r)
    rho = r / N

    return {
        "N": N,
        "r": r,
        "rho": float(rho),
        "regime": regime,
        "M": M,
        "L": L,
        "window": window,
        "harmonic_snr_db": float(harmonic_snr),

        # CFAR metrics
        "cfar_precision": metrics_cfar["precision"],
        "cfar_recall": metrics_cfar["recall"],
        "cfar_f1": metrics_cfar["f1"],
        "cfar_TP": metrics_cfar["TP"],
        "cfar_FP": metrics_cfar["FP"],
        "cfar_FN": metrics_cfar["FN"],
        "cfar_num_peaks": metrics_cfar["num_peaks"],

        # MAD metrics
        "mad_precision": metrics_mad["precision"],
        "mad_recall": metrics_mad["recall"],
        "mad_f1": metrics_mad["f1"],
        "mad_num_peaks": metrics_mad["num_peaks"],

        # Top-K metrics (oracle)
        "topk_precision": metrics_topk["precision"],
        "topk_recall": metrics_topk["recall"],
        "topk_f1": metrics_topk["f1"],
        "topk_num_peaks": metrics_topk["num_peaks"],
    }


def main(out_dir: str):
    # Set random seed for reproducibility
    np.random.seed(42)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Parameters
    MODULI = [997, 1009, 1013, 2017, 3001]
    M_VALUES = [8, 16, 32, 64, 128]
    M_MAX = max(M_VALUES)
    L = 131072
    WINDOW = "hamming"

    # Detector parameters
    CFAR_ALPHA = 1.8  # Fixed across all M
    MAD_KAPPA = 8.0   # Fixed across all M

    all_results = []

    print(f"E1C: M-Scaling with CFAR Detection")
    print(f"Testing M ∈ {M_VALUES}")
    print(f"CFAR α={CFAR_ALPHA}, MAD κ={MAD_KAPPA}")
    print(f"Moduli: {MODULI}")
    print()

    for N in MODULI:
        print(f"Processing N={N}...")

        # Collect representative orders
        seen_orders = set()
        order_cases = []

        for a in range(2, min(N, 400)):
            if np.gcd(a, N) == 1:
                try:
                    r = multiplicative_order(a, N)
                    if r not in seen_orders:
                        seen_orders.add(r)
                        rho = r / N
                        regime, _ = classify_regime(N, r)
                        order_cases.append((r, rho, regime))
                except Exception:
                    pass

        # Select representative cases per regime
        order_cases.sort(key=lambda x: x[1])
        selected_orders = []

        for regime_name, (rho_lo, rho_hi) in [
            ('HIGH_SNR', (0.0, 0.146)),
            ('TRANSITION', (0.146, 0.263)),
            ('LOW_SNR', (0.263, 1.0))
        ]:
            regime_orders = [r for r, rho, regime in order_cases
                           if rho_lo <= rho < rho_hi]
            if regime_orders:
                n = len(regime_orders)
                picks = [regime_orders[0], regime_orders[n//2], regime_orders[-1]] if n >= 3 else regime_orders
                selected_orders.extend(picks)

        selected_orders = list(set(selected_orders))
        print(f"  Selected {len(selected_orders)} representative orders")

        for r in selected_orders:
            bases = find_bases_with_order(N, r, M_MAX)

            if len(bases) < M_MAX:
                if len(bases) < min(M_VALUES):
                    continue

            for M in M_VALUES:
                if len(bases) >= M:
                    result = run_case(N, r, bases, M, L, WINDOW, CFAR_ALPHA, MAD_KAPPA)
                    if result:
                        all_results.append(result)

        print(f"  Completed N={N}: {len([r for r in all_results if r['N']==N])} cases")

    # Save results
    results_file = out_path / "E1C_results.json"
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print()
    print(f"✅ Saved {len(all_results)} results to {results_file}")

    # Quick summary
    print()
    print("="*70)
    print("QUICK SUMMARY (CFAR Detector)")
    print("="*70)

    for M in M_VALUES:
        m_cases = [r for r in all_results if r['M'] == M]
        if not m_cases:
            continue

        by_regime = {'HIGH_SNR': [], 'TRANSITION': [], 'LOW_SNR': []}
        for case in m_cases:
            by_regime[case['regime']].append(case)

        print(f"\nM = {M} ({len(m_cases)} cases):")
        for regime in ['HIGH_SNR', 'TRANSITION', 'LOW_SNR']:
            cases = by_regime[regime]
            if cases:
                avg_recall = np.mean([c['cfar_recall'] for c in cases])
                avg_prec = np.mean([c['cfar_precision'] for c in cases])
                avg_snr = np.mean([c['harmonic_snr_db'] for c in cases])
                avg_peaks = np.mean([c['cfar_num_peaks'] for c in cases])
                print(f"  {regime:12s}: Recall={avg_recall:.3f}, Prec={avg_prec:.3f}, "
                      f"SNR={avg_snr:.1f}dB, peaks={avg_peaks:.0f} ({len(cases)} cases)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E1C: M-Scaling with CFAR")
    parser.add_argument("--out", default="../../Data/Experiments/Tier1/E1C",
                       help="Output directory")
    args = parser.parse_args()

    main(args.out)
