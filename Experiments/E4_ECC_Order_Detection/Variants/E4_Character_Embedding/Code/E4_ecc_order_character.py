#!/usr/bin/env python3
"""
E4 (ECC) — Character-Embedding Variant with √M Plots
=====================================================

Purpose
-------
Provide a *clean* ECC experiment where VRA conditions for coherent averaging
are satisfied by using a valid character on the cyclic subgroup <G> of order rE:
    [n]G  ->  exp(2πi n / rE)

We *still* compute an ECC point and its order rE to keep the experiment in the ECC
context, but we embed sequences via the character so each sequence differs only by a
global phase (random starting offset). This guarantees √M SNR scaling.

Outputs
-------
- JSON with per-M, per-α metrics
- Figures:
  * E4_char_recall_vs_sqrtM.png
  * E4_char_precision_vs_sqrtM.png
  * E4_char_pr_tradeoff_alpha.png

Run
---
python E4_ecc_order_character.py \
  --out ../Data \
  --alphas 2.0 2.2 2.5 2.8 3.0 \
  --M 8 16 32 64 128 \
  --L 131072 --zp 4 --window hamming

Notes
-----
- Uses the small ECC toy curve search from your existing E4 to find any decent-order point G.
- Builds M sequences using the group character (random offsets) → coherent FFT averaging works.
- Uses OS-CFAR with local-max (NMS) and circular matching.
"""

import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Code" / "VRA"))
from core import validated_radius

# --- Minimal ECC primitives --------------------------------------------------

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

def ecc_mul(k, P, a, p):
    """Scalar multiplication: [k]P"""
    R = None
    Q = P
    while k > 0:
        if k & 1:
            R = ecc_add(R, Q, a, p)
        Q = ecc_add(Q, Q, a, p)
        k >>= 1
    return R

def order_of_point(P, a, p, cap=None):
    """Compute order of point P (naive walk)"""
    Q = P
    n = 1
    lim = cap or (2 * p)
    while Q is not None and n <= lim:
        Q = ecc_add(Q, P, a, p)
        n += 1
        if Q == P:
            return n
    return n if Q is None else None

def find_point_on_curve(a, b, p, max_tries=1000, min_order=10):
    """Brute-force search for valid point with order >= min_order"""
    for x in range(1, min(p, max_tries)):
        y_squared = (x**3 + a*x + b) % p
        y = pow(y_squared, (p + 1) // 4, p)  # Tonelli-Shanks for p ≡ 3 (mod 4)
        if (y * y) % p == y_squared:
            if y == 0:  # Skip 2-torsion
                continue
            pt = (x, y)
            r = order_of_point(pt, a, p)
            if r and r >= min_order:
                return pt, a, b
    return None, a, b

# --- Character embedding for ECC ---------------------------------------------

def ecc_character_sequence(rE: int, n0: int, L: int):
    """
    Character samples for the cyclic subgroup <G> of order rE:
        u_t = exp(2πi (n0 + t) / rE),  t = 0..L-1
    n0 is a starting offset (sequence-specific phase).
    """
    n = (n0 % rE)
    k = (2.0 * np.pi) / rE
    phases = k * (n + np.arange(L))
    return np.exp(1j * phases)

def make_M_sequences_character(rE: int, L: int, M: int, rng=None):
    """
    Build M independent character sequences with random offsets (pure phase shifts).
    These *do* average coherently and should yield √M scaling.
    """
    if rng is None:
        rng = np.random.default_rng(42)
    offsets = rng.integers(0, rE, size=M, dtype=np.int64)
    return [ecc_character_sequence(rE, int(n0), L) for n0 in offsets]

# --- Spectrum computation ----------------------------------------------------

def compute_averaged_spectrum(signals, window="hamming", zp=4):
    """
    Compute averaged power spectrum from multiple signal sequences.
    Coherent averaging: average complex FFTs then take magnitude.
    """
    M = len(signals)
    L = len(signals[0])
    Lzp = L * zp

    # Apply window
    if window == "hamming":
        win = np.hamming(L)
    elif window == "hann":
        win = np.hanning(L)
    else:
        win = np.ones(L)

    # Coherent averaging: average complex FFTs then take magnitude
    fft_sum = np.zeros(Lzp, dtype=complex)

    for sig in signals:
        sig_windowed = sig * win
        sig_padded = np.pad(sig_windowed, (0, Lzp - L), mode='constant')
        fft_sum += np.fft.fft(sig_padded)

    fft_avg = fft_sum / M
    mag2 = np.abs(fft_avg) ** 2

    return mag2

# --- Detection (from E1C) ----------------------------------------------------

def circ_dist(i, j, L):
    """Circular distance between two bin indices."""
    d = abs(i - j)
    return min(d, L - d)

def keep_local_maxima(mag2, det):
    """Non-maximum suppression: keep only local maxima."""
    left = np.roll(mag2, 1)
    right = np.roll(mag2, -1)
    is_peak = (mag2 > left) & (mag2 >= right)
    return det & is_peak

def os_cfar_detect(mag2, guard=9, train=64, q=0.75, alpha=2.5):
    """Circular OS-CFAR detection"""
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
    """Median + MAD threshold"""
    median = np.median(mag2)
    mad = np.median(np.abs(mag2 - median))
    thr = median + kappa * mad
    return mag2 > thr

def compute_precision_recall_from_detections(detections, expected_bins, radius):
    """Compute precision/recall from detection mask"""
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

def expected_bins(r, Lzp):
    """Generate all expected harmonic bins"""
    return [int(round(k * Lzp / r)) for k in range(1, r)]

def compute_harmonic_snr(mag2, expected):
    """Compute SNR at expected harmonic bins"""
    if not expected:
        return 0.0
    vals = [mag2[int(b)] for b in expected if 0 <= int(b) < len(mag2)]
    if not vals:
        return 0.0
    signal = np.mean(vals)
    noise = np.median(mag2)
    lin = (signal / noise) if noise > 0 else 0.0
    return (10 * np.log10(lin)) if lin > 0 else -np.inf

# --- Plotting ----------------------------------------------------------------

def linreg(x, y):
    """Simple linear regression"""
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

def plot_recall_vs_sqrtM(results, alphas, M_values, out_dir):
    """Plot recall vs √M for each alpha"""
    plt.figure(figsize=(10, 6))

    for alpha in alphas:
        rows = [r for r in results if r["alpha"] == alpha]
        sqrtM = [np.sqrt(r["M"]) for r in rows]
        recalls = [r["cfar_recall"] for r in rows]

        plt.plot(sqrtM, recalls, 'o-', label=f'α={alpha}')

        # Fit line if not saturated
        if len(sqrtM) >= 3 and min(recalls) < 0.95:
            slope, intercept, r2 = linreg(sqrtM, recalls)
            x_fit = np.linspace(min(sqrtM), max(sqrtM), 50)
            y_fit = slope * x_fit + intercept
            plt.plot(x_fit, y_fit, '--', alpha=0.5, label=f'α={alpha} fit (R²={r2:.3f})')

    plt.xlabel('√M')
    plt.ylabel('Recall')
    plt.title('E4 Character: Recall vs √M (ECC order detection)')
    plt.legend(ncol=2, fontsize=9)
    plt.grid(alpha=0.3)
    plt.ylim(0, 1.05)

    p = Path(out_dir) / "E4_char_recall_vs_sqrtM.png"
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    print(f"Saved {p}")

def plot_precision_vs_sqrtM(results, alphas, M_values, out_dir):
    """Plot precision vs √M for each alpha"""
    plt.figure(figsize=(10, 6))

    for alpha in alphas:
        rows = [r for r in results if r["alpha"] == alpha]
        sqrtM = [np.sqrt(r["M"]) for r in rows]
        precisions = [r["cfar_precision"] for r in rows]

        plt.plot(sqrtM, precisions, 's-', label=f'α={alpha}')

    plt.xlabel('√M')
    plt.ylabel('Precision')
    plt.title('E4 Character: Precision vs √M (ECC order detection)')
    plt.legend(ncol=2, fontsize=9)
    plt.grid(alpha=0.3)
    plt.ylim(0, 1.05)

    p = Path(out_dir) / "E4_char_precision_vs_sqrtM.png"
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    print(f"Saved {p}")

def plot_pr_tradeoff(results, M_values, alphas, out_dir):
    """Plot precision/recall vs alpha at fixed M"""
    target_M = M_values[len(M_values)//2]  # Use middle M value

    plt.figure(figsize=(10, 6))

    rows = [r for r in results if r["M"] == target_M]
    alphas_sorted = sorted(set(r["alpha"] for r in rows))
    precisions = [np.mean([r["cfar_precision"] for r in rows if r["alpha"]==a]) for a in alphas_sorted]
    recalls = [np.mean([r["cfar_recall"] for r in rows if r["alpha"]==a]) for a in alphas_sorted]

    plt.plot(alphas_sorted, precisions, 'o-', label='Precision')
    plt.plot(alphas_sorted, recalls, 's-', label='Recall')
    plt.axhline(0.85, linestyle=':', color='gray', label='Target precision (85%)')
    plt.axhline(0.80, linestyle=':', color='gray', label='Target recall (80%)')

    plt.xlabel('CFAR α')
    plt.ylabel('Metric')
    plt.title(f'E4 Character: Precision/Recall vs α (M={target_M})')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.ylim(0, 1.05)

    p = Path(out_dir) / "E4_char_pr_tradeoff_alpha.png"
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    print(f"Saved {p}")

# --- Main --------------------------------------------------------------------

def main(out_dir, alphas, M_values, L, zp, window):
    np.random.seed(42)
    rng = np.random.default_rng(42)

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    print("E4 (ECC Character Embedding): √M Scaling Test")
    print("=" * 70)

    # Find ECC point
    p = 1009
    candidate_curves = [(0, 7), (1, 6), (2, 3), (1, 1), (0, 3), (5, 1)]

    print(f"\nSearching for valid curve over F_{p}...")
    G, a, b = None, None, None
    for a_try, b_try in candidate_curves:
        print(f"  Trying y^2 = x^3 + {a_try}x + {b_try} ...", end=" ")
        pt, a_found, b_found = find_point_on_curve(a_try, b_try, p, min_order=30)
        if pt is not None:
            G, a, b = pt, a_found, b_found
            print(f"✓ Found point {G}")
            break
        print("✗")

    if G is None:
        print("\n❌ Failed to find suitable ECC point")
        return

    print(f"\nCurve: y^2 = x^3 + {a}x + {b} (mod {p})")
    print(f"Point G = {G}")

    # Compute order
    rE = order_of_point(G, a, p)
    print(f"Order rE = {rE}")

    if rE is None or rE < 10:
        print("❌ Order too small or computation failed")
        return

    print(f"\nParameters: L={L}, zp={zp}, window={window}")
    print(f"M values: {M_values}")
    print(f"Alphas: {alphas}")

    # Run sweep
    all_results = []

    for M in M_values:
        print(f"\nProcessing M={M}...")

        # Generate M character sequences (once per M)
        signals = make_M_sequences_character(rE, L=L, M=M, rng=rng)

        # Compute spectrum (once per M)
        mag2 = compute_averaged_spectrum(signals, window=window, zp=zp)

        Lzp = L * zp
        R = validated_radius(Lzp)
        hb = expected_bins(rE, Lzp)
        snr_db = compute_harmonic_snr(mag2, hb)

        # Test all alphas on this spectrum
        for alpha in alphas:
            det_cfar = os_cfar_detect(mag2, guard=R, train=64, q=0.75, alpha=alpha)
            det_cfar = keep_local_maxima(mag2, det_cfar)
            m_cfar = compute_precision_recall_from_detections(det_cfar, hb, R)

            det_mad = median_mad_detect(mag2, kappa=8.0)
            det_mad = keep_local_maxima(mag2, det_mad)
            m_mad = compute_precision_recall_from_detections(det_mad, hb, R)

            rec = {
                "alpha": float(alpha),
                "M": int(M),
                "L": int(L),
                "rE": int(rE),
                "harmonic_snr_db": float(snr_db),
                "cfar_precision": float(m_cfar["precision"]),
                "cfar_recall": float(m_cfar["recall"]),
                "cfar_f1": float(m_cfar["f1"]),
                "cfar_TP": int(m_cfar["TP"]),
                "cfar_FP": int(m_cfar["FP"]),
                "cfar_FN": int(m_cfar["FN"]),
                "cfar_num_peaks": int(m_cfar["num_peaks"]),
                "mad_precision": float(m_mad["precision"]),
                "mad_recall": float(m_mad["recall"]),
                "mad_f1": float(m_mad["f1"]),
            }
            all_results.append(rec)

        print(f"  M={M}: SNR={snr_db:.1f} dB")

    # Save results
    out_file = Path(out_dir) / "E4_char_results.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n✅ Saved {len(all_results)} rows to {out_file}")

    # Generate plots
    print("\nGenerating figures...")
    plot_recall_vs_sqrtM(all_results, alphas, M_values, out_dir)
    plot_precision_vs_sqrtM(all_results, alphas, M_values, out_dir)
    plot_pr_tradeoff(all_results, M_values, alphas, out_dir)

    print("\n" + "=" * 70)
    print("✅ E4 Character Embedding Complete")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E4: ECC Character Embedding √M Test")
    parser.add_argument("--out", default="../Data", help="Output directory")
    parser.add_argument("--alphas", nargs="+", type=float, default=[2.0, 2.2, 2.5, 2.8, 3.0])
    parser.add_argument("--M", nargs="+", type=int, default=[8, 16, 32, 64, 128])
    parser.add_argument("--L", type=int, default=131072)
    parser.add_argument("--zp", type=int, default=4)
    parser.add_argument("--window", default="hamming")
    args = parser.parse_args()

    main(args.out, args.alphas, args.M, args.L, args.zp, args.window)
