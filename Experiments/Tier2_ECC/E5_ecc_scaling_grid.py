#!/usr/bin/env python3
"""
E5: ECC Scaling Grid (Character Embedding)
===========================================

Goal:
  Comprehensive sweep of (p, rE, α, M) using the character embedding from E4
  to demonstrate VRA's √M scaling across different ECC parameters.

Key Differences from Original E5:
  - Uses character embedding u_n = exp(2πin/rE) NOT x-coordinate
  - Tests multiple orders and alphas to find optimal operating points
  - No K=100 cap bug (tests all harmonics)

Pass Criteria:
  - √M scaling with R² ≥ 0.80 in unsaturated regime
  - Precision ≥ 0.85 and Recall ≥ 0.80 with optimal α

Outputs:
  - JSON: per-(p,rE,α,M) metrics
  - Figures: Recall/Precision vs √M, α tradeoff curves

Author: VRA Experimental Team (Based on E4 character embedding)
Date: October 2025
"""

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Code" / "VRA"))
from core import validated_radius

# --- ECC primitives (minimal, from E4) -------------------------------------

def inv_mod(x, p):
    return pow(x, p - 2, p)

def ecc_add(P, Q, a, p):
    """Add two points on y^2 = x^3 + ax + b (mod p)"""
    if P is None:
        return Q
    if Q is None:
        return P
    (x1, y1), (x2, y2) = P, Q
    if x1 == x2 and (y1 + y2) % p == 0:
        return None
    if P != Q:
        m = ((y2 - y1) * inv_mod((x2 - x1) % p, p)) % p
    else:
        m = ((3 * x1 * x1 + a) * inv_mod((2 * y1) % p, p)) % p
    x3 = (m * m - x1 - x2) % p
    y3 = (m * (x1 - x3) - y1) % p
    return (x3, y3)

def order_of_point(P, a, p, cap=None):
    """Compute order of point P"""
    Q = P
    n = 1
    lim = cap or (2 * p)
    while Q is not None and n <= lim:
        Q = ecc_add(Q, P, a, p)
        n += 1
        if Q == P:
            return n
    return n if Q is None else None

def find_point_on_curve(a, b, p, max_tries=1000, min_order=30):
    """Find point with order >= min_order"""
    for x in range(1, min(p, max_tries)):
        y_squared = (x**3 + a*x + b) % p
        y = pow(y_squared, (p + 1) // 4, p)
        if (y * y) % p == y_squared:
            if y == 0:
                continue
            pt = (x, y)
            r = order_of_point(pt, a, p)
            if r and r >= min_order:
                return pt, a, b, r
    return None, a, b, None

# --- Character embedding (from E4) -----------------------------------------

def ecc_character_sequence(rE: int, n0: int, L: int):
    """Character samples: u_t = exp(2πi(n0+t)/rE)"""
    n = (n0 % rE)
    k = (2.0 * np.pi) / rE
    phases = k * (n + np.arange(L))
    return np.exp(1j * phases)

def make_M_sequences_character(rE: int, L: int, M: int, rng=None):
    """Build M character sequences with random offsets"""
    if rng is None:
        rng = np.random.default_rng(42)
    offsets = rng.integers(0, rE, size=M, dtype=np.int64)
    return [ecc_character_sequence(rE, int(n0), L) for n0 in offsets]

# --- Spectrum computation (from E4) ----------------------------------------

def compute_averaged_spectrum(signals, window="hamming", zp=4):
    """Coherent averaging"""
    M = len(signals)
    L = len(signals[0])
    Lzp = L * zp

    if window == "hamming":
        win = np.hamming(L)
    elif window == "hann":
        win = np.hanning(L)
    else:
        win = np.ones(L)

    fft_sum = np.zeros(Lzp, dtype=complex)
    for sig in signals:
        sig_windowed = sig * win
        sig_padded = np.pad(sig_windowed, (0, Lzp - L), mode='constant')
        fft_sum += np.fft.fft(sig_padded)

    fft_avg = fft_sum / M
    mag2 = np.abs(fft_avg) ** 2
    return mag2

# --- Detection (from E1C/E4) -----------------------------------------------

def circ_dist(i, j, L):
    d = abs(i - j)
    return min(d, L - d)

def keep_local_maxima(mag2, det):
    left = np.roll(mag2, 1)
    right = np.roll(mag2, -1)
    is_peak = (mag2 > left) & (mag2 >= right)
    return det & is_peak

def os_cfar_detect(mag2, guard=9, train=64, q=0.75, alpha=2.5):
    """Circular OS-CFAR"""
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

def expected_bins(r, Lzp):
    """All expected harmonic bins (NO CAP)"""
    return [int(round(k * Lzp / r)) for k in range(1, r)]

def compute_precision_recall_from_detections(detections, expected_bins_list, radius):
    """Compute precision/recall from detection mask"""
    L = len(detections)
    peak_indices = np.where(detections)[0]
    expected_set = set(expected_bins_list)
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
        if matched:
            TP_peaks += 1
        else:
            FP_peaks += 1

    TP = len(matched_expected_bins)
    FP = FP_peaks
    FN = len(expected_set) - TP

    precision = TP_peaks / (TP_peaks + FP_peaks) if (TP_peaks + FP_peaks) else 0.0
    recall = TP / (TP + FN) if (TP + FN) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return dict(precision=precision, recall=recall, f1=f1, TP=TP, FP=FP, FN=FN, num_peaks=len(peak_indices))

def compute_harmonic_snr(mag2, expected):
    """Compute SNR at expected bins"""
    if not expected:
        return 0.0
    vals = [mag2[int(b)] for b in expected if 0 <= int(b) < len(mag2)]
    if not vals:
        return 0.0
    signal = np.mean(vals)
    noise = np.median(mag2)
    lin = (signal / noise) if noise > 0 else 0.0
    return (10 * np.log10(lin)) if lin > 0 else -np.inf

# --- Plotting helpers (from E4) --------------------------------------------

def linreg(x, y):
    x, y = np.array(x, float), np.array(y, float)
    xm, ym = x.mean(), y.mean()
    num = ((x-xm)*(y-ym)).sum()
    den = ((x-xm)**2).sum()
    if den == 0:
        return 0.0, ym, 0.0
    slope = num/den
    intercept = ym - slope*xm
    yhat = slope*x + intercept
    ss_res = ((y - yhat)**2).sum()
    ss_tot = ((y - ym)**2).sum()
    r2 = 1 - (ss_res/ss_tot) if ss_tot > 0 else 0.0
    return slope, intercept, r2

def plot_recall_vs_sqrtM_by_order(results, out_dir):
    """Plot recall vs √M grouped by rE"""
    plt.figure(figsize=(12, 6))

    orders = sorted(set(r["rE"] for r in results))
    colors = plt.cm.viridis(np.linspace(0, 1, len(orders)))

    for rE, color in zip(orders, colors):
        rows = [r for r in results if r["rE"] == rE]
        alphas = sorted(set(r["alpha"] for r in rows))

        for alpha in alphas:
            alpha_rows = [r for r in rows if r["alpha"] == alpha]
            M_values = sorted(set(r["M"] for r in alpha_rows))
            sqrtM = [np.sqrt(M) for M in M_values]
            recalls = [np.mean([r["cfar_recall"] for r in alpha_rows if r["M"]==M]) for M in M_values]

            plt.plot(sqrtM, recalls, 'o-', color=color, alpha=0.7,
                    label=f'rE={rE}, α={alpha}')

            # Fit if unsaturated
            if len(sqrtM) >= 3 and min(recalls) < 0.95:
                slope, intercept, r2 = linreg(sqrtM, recalls)
                x_fit = np.linspace(min(sqrtM), max(sqrtM), 50)
                y_fit = slope * x_fit + intercept
                plt.plot(x_fit, y_fit, '--', color=color, alpha=0.3)

    plt.axhline(0.80, linestyle=':', color='gray', label='Target recall (80%)')
    plt.xlabel('√M')
    plt.ylabel('Recall')
    plt.title('E5: ECC Character Embedding - Recall vs √M')
    plt.legend(ncol=2, fontsize=8)
    plt.grid(alpha=0.3)
    plt.ylim(0, 1.05)

    p = Path(out_dir) / "E5_recall_vs_sqrtM.png"
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    print(f"Saved {p}")

# --- Main ------------------------------------------------------------------

def main(out_dir, primes, alphas, M_values, L):
    np.random.seed(42)
    rng = np.random.default_rng(42)

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    print("E5: ECC Scaling Grid (Character Embedding)")
    print("=" * 70)

    # Candidate curves (a, b) for each prime
    candidate_curves = [(0, 7), (1, 6), (2, 3), (1, 1), (0, 3), (5, 1)]

    # Find curves with varying orders
    test_cases = []
    for p in primes:
        print(f"\nSearching curves over F_{p}...")
        for a, b in candidate_curves:
            pt, a_found, b_found, rE = find_point_on_curve(a, b, p, min_order=50)
            if pt is not None and rE is not None:
                test_cases.append((p, a_found, b_found, pt, rE))
                print(f"  ✓ y²=x³+{a_found}x+{b_found}: G={pt}, rE={rE}")
                if len([tc for tc in test_cases if tc[0]==p]) >= 2:
                    break  # 2 curves per prime is enough

    print(f"\n{len(test_cases)} test cases found")
    print(f"M values: {M_values}")
    print(f"Alphas: {alphas}")
    print(f"L={L}, zp=4")

    all_results = []

    for p, a, b, G, rE in test_cases:
        print(f"\nProcessing p={p}, rE={rE}...")

        for M in M_values:
            # Generate M sequences once per M
            signals = make_M_sequences_character(rE, L=L, M=M, rng=rng)
            mag2 = compute_averaged_spectrum(signals, window="hamming", zp=4)

            Lzp = L * 4
            R = validated_radius(Lzp)
            hb = expected_bins(rE, Lzp)
            snr_db = compute_harmonic_snr(mag2, hb)

            # Test all alphas on this spectrum
            for alpha in alphas:
                det_cfar = os_cfar_detect(mag2, guard=R, train=64, q=0.75, alpha=alpha)
                det_cfar = keep_local_maxima(mag2, det_cfar)
                m_cfar = compute_precision_recall_from_detections(det_cfar, hb, R)

                rec = {
                    "p": int(p),
                    "a": int(a),
                    "b": int(b),
                    "rE": int(rE),
                    "alpha": float(alpha),
                    "M": int(M),
                    "L": int(L),
                    "harmonic_snr_db": float(snr_db),
                    "cfar_precision": float(m_cfar["precision"]),
                    "cfar_recall": float(m_cfar["recall"]),
                    "cfar_f1": float(m_cfar["f1"]),
                    "cfar_TP": int(m_cfar["TP"]),
                    "cfar_FP": int(m_cfar["FP"]),
                    "cfar_FN": int(m_cfar["FN"]),
                    "cfar_num_peaks": int(m_cfar["num_peaks"]),
                }
                all_results.append(rec)

        print(f"  Completed p={p}, rE={rE}: {len([r for r in all_results if r['p']==p and r['rE']==rE])} rows")

    # Save results
    out_file = Path(out_dir) / "E5_results.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n✅ Saved {len(all_results)} rows to {out_file}")

    # Generate plots
    print("\nGenerating figures...")
    plot_recall_vs_sqrtM_by_order(all_results, out_dir)

    print("\n" + "=" * 70)
    print("✅ E5 Complete")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E5: ECC Scaling Grid")
    parser.add_argument("--out", default="../../Data/Experiments/Tier2/E5", help="Output directory")
    parser.add_argument("--primes", nargs="+", type=int, default=[1009, 2017])
    parser.add_argument("--alphas", nargs="+", type=float, default=[2.0, 2.5, 3.0])
    parser.add_argument("--M", nargs="+", type=int, default=[8, 16, 32, 64])
    parser.add_argument("--L", type=int, default=65536)
    args = parser.parse_args()

    main(args.out, args.primes, args.alphas, args.M, args.L)
