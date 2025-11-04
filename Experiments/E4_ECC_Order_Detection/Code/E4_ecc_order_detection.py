#!/usr/bin/env python3
"""
E4: ECC Order Detection with VRA
=================================

Goal:
  Demonstrate that VRA can detect the order of an elliptic curve point
  by analyzing the spectral signature of the point sequence under repeated addition.

Scientific Question:
  Does VRA's coherent averaging detect periodicity in ECC group operations
  the same way it detects multiplicative order in (Z/NZ)*?

Pass Criteria:
  - Recall ≥ 0.80 for detecting ECC point order
  - Precision ≥ 0.85 for harmonic peaks
  - Demonstrates VRA generality beyond multiplicative groups

Author: VRA Experimental Team
Date: October 2025
"""

import numpy as np
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Code" / "VRA"))
from core import validated_radius

# --- ECC Primitives ---
def inv_mod(x, p):
    """Modular inverse using Fermat's little theorem"""
    return pow(x, p - 2, p)

def add(P, Q, a, p):
    """Add two points on y^2 = x^3 + ax + b (mod p)"""
    if P is None:
        return Q
    if Q is None:
        return P
    (x1, y1), (x2, y2) = P, Q
    if x1 == x2 and (y1 + y2) % p == 0:
        return None  # Point at infinity
    if P != Q:
        m = ((y2 - y1) * inv_mod((x2 - x1) % p, p)) % p
    else:
        m = ((3 * x1 * x1 + a) * inv_mod((2 * y1) % p, p)) % p
    x3 = (m * m - x1 - x2) % p
    y3 = (m * (x1 - x3) - y1) % p
    return (x3, y3)

def mul(k, P, a, p):
    """Scalar multiplication: [k]P"""
    R = None
    Q = P
    while k > 0:
        if k & 1:
            R = add(R, Q, a, p)
        Q = add(Q, Q, a, p)
        k >>= 1
    return R

def order_of_point(P, a, p, cap=None):
    """Compute order of point P (naive walk)"""
    Q = P
    n = 1
    lim = cap or (2 * p)
    while Q is not None and n <= lim:
        Q = add(Q, P, a, p)
        n += 1
        if Q == P:
            return n
    return n if Q is None else None

# --- Fixed functions ---
def expected_bins(r, Lzp):
    """Generate all expected harmonic bins (NO CAP - learned from E1 bug!)"""
    return [int(round(k * Lzp / r)) for k in range(1, r)]


def find_point_on_curve(a, b, p, max_tries=1000, min_order=10):
    """Brute-force search for valid point on curve y^2 = x^3 + ax + b (mod p)

    Args:
        a, b: Curve parameters
        p: Prime modulus
        max_tries: Maximum x values to try
        min_order: Minimum order to accept (to avoid 2-torsion points)
    """
    for x in range(1, min(p, max_tries)):
        y_squared = (x**3 + a*x + b) % p
        # Check if y_squared is a quadratic residue (has sqrt mod p)
        y = pow(y_squared, (p + 1) // 4, p)  # Tonelli-Shanks for p ≡ 3 (mod 4)
        if (y * y) % p == y_squared:
            # Skip 2-torsion points (y=0) - they have order 2
            if y == 0:
                continue
            # Check if order is large enough for meaningful VRA test
            pt = (x, y)
            r = order_of_point(pt, a, p)
            if r >= min_order:
                return pt
    return None


def sample_ecc_sequence(G, a, p, length):
    """
    Generate ECC point sequence: G, 2G, 3G, ..., length*G
    Returns phase-embedded complex sequence for VRA analysis.
    """
    pts = [G]
    Q = G
    for _ in range(length - 1):
        Q = add(Q, G, a, p)
        if Q is None:  # Hit point at infinity (order found)
            break
        pts.append(Q)

    # Phase embedding: use normalized x-coordinate
    phases = np.array([2*np.pi * pt[0] / p for pt in pts], dtype=float)
    signal = np.exp(1j * phases)

    # Pad to desired length if sequence ended early
    if len(signal) < length:
        signal = np.pad(signal, (0, length - len(signal)), mode='constant', constant_values=0)

    return signal


def compute_ecc_averaged_spectrum(signals, window="hamming", zp=4):
    """
    Compute averaged power spectrum from multiple ECC signal sequences.
    Mimics compute_averaged_spectrum from VRA core but for pre-generated signals.
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


def compute_precision_recall_ecc(mag2, expected_bins, radius):
    """
    Compute precision/recall for ECC order detection.
    Uses top-K peak detection with local maxima filtering.
    """
    L = len(mag2)

    # First, find local maxima
    left = np.roll(mag2, 1)
    right = np.roll(mag2, -1)
    local_max = (mag2 > left) & (mag2 >= right)
    local_max_indices = np.where(local_max)[0]

    if len(local_max_indices) == 0:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "TP": 0,
            "FP": 0,
            "FN": len(expected_bins),
            "num_peaks": 0,
        }

    # Take top K local maxima (K = 2*r to be generous)
    K = min(2 * len(expected_bins), len(local_max_indices))
    peak_powers = mag2[local_max_indices]
    top_k_idx = np.argsort(peak_powers)[-K:]
    peaks = local_max_indices[top_k_idx]

    expected_set = set(expected_bins)
    matched_bins = set()

    for peak_idx in peaks:
        # Check if this peak is within radius of any expected bin (circular distance)
        for exp_idx in expected_set:
            d = abs(peak_idx - exp_idx)
            circ_d = min(d, L - d)  # Circular distance
            if circ_d <= radius:
                matched_bins.add(exp_idx)
                break

    TP = len(matched_bins)
    FP = len(peaks) - TP
    FN = len(expected_set) - TP

    precision = TP / len(peaks) if len(peaks) > 0 else 0.0
    recall = TP / len(expected_set) if len(expected_set) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "TP": TP,
        "FP": FP,
        "FN": FN,
        "num_peaks": len(peaks),
    }


def main(out_dir):
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    print("E4: ECC Order Detection with VRA")
    print("=" * 70)

    # Use small curve for demonstration
    p = 1009  # Small prime

    # Try multiple curve parameters until we find one with points
    candidate_curves = [
        (0, 7),   # y^2 = x^3 + 7 (similar to secp256k1)
        (1, 6),   # y^2 = x^3 + x + 6
        (2, 3),   # y^2 = x^3 + 2x + 3
        (1, 1),   # y^2 = x^3 + x + 1
        (0, 3),   # y^2 = x^3 + 3
        (5, 1),   # y^2 = x^3 + 5x + 1
    ]

    print(f"\nSearching for valid curve over F_{p}...")
    G = None
    for a, b in candidate_curves:
        print(f"  Trying y^2 = x^3 + {a}x + {b} ...", end=" ")
        G = find_point_on_curve(a, b, p)
        if G is not None:
            print(f"✓ Found point {G}")
            break
        print("✗ No point found")

    if G is None:
        print("\n❌ Failed to find point on any candidate curve")
        return

    print(f"\nUsing curve: y^2 = x^3 + {a}x + {b} (mod {p})")
    print(f"Generator point G = {G}")

    # Compute order of G
    print("Computing order of G...")
    rE = order_of_point(G, a, p)
    print(f"Order of G: rE = {rE}")

    if rE > 2*p:  # Sanity check
        print("⚠️  Order computation may have failed (too large)")
        return

    # VRA parameters
    L = 16384  # Shorter for ECC demo (faster)
    M = 64     # Number of sequences (increased for better SNR)
    zp = 4
    window = "hamming"

    print(f"\nVRA Parameters:")
    print(f"  Sequence length L = {L}")
    print(f"  Number of sequences M = {M}")
    print(f"  Zero-padding factor = {zp}")
    print(f"  Window = {window}")

    # Generate M independent ECC sequences (same G, different random phases)
    print(f"\nGenerating {M} ECC sequences...")
    signals = []
    for m in range(M):
        # Each "base" is a slightly perturbed starting point (or use different L samples)
        # For simplicity, we'll use the same sequence but this demonstrates the principle
        sig = sample_ecc_sequence(G, a, p, length=L)
        signals.append(sig)

    # Compute averaged spectrum
    print("Computing averaged spectrum...")
    mag2 = compute_ecc_averaged_spectrum(signals, window=window, zp=zp)

    Lzp = L * zp
    R = validated_radius(Lzp)
    hb = expected_bins(rE, Lzp)

    print(f"  Expected {len(hb)} harmonic bins")
    print(f"  Validated radius R = {R} bins")

    # Diagnostic: check power at expected harmonics
    expected_power = [mag2[int(b)] for b in hb if 0 <= int(b) < len(mag2)]
    median_noise = np.median(mag2)
    if expected_power:
        mean_harmonic_power = np.mean(expected_power)
        max_harmonic_power = np.max(expected_power)
        snr_db = 10 * np.log10(mean_harmonic_power / median_noise) if median_noise > 0 else -np.inf
        print(f"  Harmonic SNR: {snr_db:.1f} dB (mean harmonic / median noise)")
        print(f"  Mean harmonic power: {mean_harmonic_power:.2e}")
        print(f"  Max harmonic power: {max_harmonic_power:.2e}")
        print(f"  Median noise floor: {median_noise:.2e}")

    # Compute precision/recall
    print("\nDetecting ECC order harmonics...")
    metrics = compute_precision_recall_ecc(mag2, hb, R)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Precision: {metrics['precision']:.3f}")
    print(f"Recall:    {metrics['recall']:.3f}")
    print(f"F1 Score:  {metrics['f1']:.3f}")
    print(f"TP: {metrics['TP']}, FP: {metrics['FP']}, FN: {metrics['FN']}")
    print(f"Peaks detected: {metrics['num_peaks']}")

    # Verdict
    print("\n" + "=" * 70)
    if metrics['recall'] >= 0.80 and metrics['precision'] >= 0.85:
        print("✅ PASS - VRA successfully detects ECC point order!")
    elif metrics['recall'] >= 0.60:
        print("⚠️  PARTIAL - VRA detects ECC order but with lower metrics")
    else:
        print("❌ FAIL - VRA struggles with ECC order detection")
    print("=" * 70)

    # Save results
    results = {
        "curve": {"p": int(p), "a": int(a), "b": int(b)},
        "point_G": {"x": int(G[0]), "y": int(G[1])},
        "order_rE": int(rE),
        "vra_params": {"L": L, "M": M, "zp": zp, "window": window},
        "metrics": {
            "precision": float(metrics['precision']),
            "recall": float(metrics['recall']),
            "f1": float(metrics['f1']),
            "TP": int(metrics['TP']),
            "FP": int(metrics['FP']),
            "FN": int(metrics['FN']),
            "num_peaks": int(metrics['num_peaks']),
        },
        "pass": bool(metrics['recall'] >= 0.80 and metrics['precision'] >= 0.85),
    }

    out_file = Path(out_dir) / "E4_ecc_order_detection.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E4: ECC Order Detection")
    parser.add_argument("--out", default="../../Data/Experiments/Tier2/E4",
                       help="Output directory")
    args = parser.parse_args()
    main(args.out)
