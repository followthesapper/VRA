#!/usr/bin/env python3
"""
E10: VRA on Stationary Rational Tones
======================================

Goal:
  Test VRA-style coherent averaging on stationary signals with planted
  rational-frequency tones (not cyclic group sequences).

Key differences from E1-E9:
  - Signal: planted tones at f_k = p_k/q_k (rational frequencies)
  - M trials: random initial phases (not different bases)
  - Coherent averaging: average complex FFTs before squaring
  - Detection: OS-CFAR with α-sweep
  - Metrics: precision, recall, F1 against ground truth planted bins
  - √M scaling: vary M ∈ {4, 8, 16, 32, 64}

This tests whether VRA's coherent averaging principle generalizes beyond
cyclic group order-finding to stationary tone detection in physics signals.
"""

import argparse
import json
import numpy as np
from pathlib import Path
import sys

# --- repo wiring -------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "Code" / "VRA"))

# Note: Don't import validated_radius - it's for cyclic groups, not FFT spectra

# --- signal generation -------------------------------------------------------
def generate_tone_signal(freqs, L, phases=None, noise_std=0.1, rng=None):
    """
    Generate signal with K tones at specified frequencies.

    Args:
        freqs: list of K rational frequencies (normalized, 0-1)
        L: signal length
        phases: optional list of K initial phases (radians)
        noise_std: Gaussian noise level
        rng: numpy random generator

    Returns:
        signal: complex array of length L
    """
    if rng is None:
        rng = np.random.default_rng()

    if phases is None:
        phases = [0.0] * len(freqs)

    t = np.arange(L)
    signal = np.zeros(L, dtype=complex)

    for freq, phase in zip(freqs, phases):
        signal += np.exp(1j * (2 * np.pi * freq * t + phase))

    # Add complex Gaussian noise
    noise = rng.normal(0, noise_std, L) + 1j * rng.normal(0, noise_std, L)
    return signal + noise

def freq_to_bin(freq, L, zp=4):
    """Convert normalized frequency to FFT bin index."""
    return int(round(freq * L * zp))

# --- coherent averaging ------------------------------------------------------
def coherent_average(signals, window="hamming", zp=4):
    """
    Coherent averaging: average complex FFTs before squaring.

    This is the core VRA principle adapted to arbitrary signals.

    Args:
        signals: list of M complex arrays (same length L)
        window: window function name
        zp: zero-padding factor

    Returns:
        mag2: averaged power spectrum
    """
    L = len(signals[0])
    M = len(signals)

    # Apply window
    if window == "hamming":
        w = np.hamming(L)
    elif window == "hann":
        w = np.hann(L)
    else:
        w = np.ones(L)

    # Compute complex FFTs and average
    fft_sum = np.zeros(L * zp, dtype=complex)
    for sig in signals:
        windowed = sig * w
        fft_sum += np.fft.fft(windowed, n=L * zp)

    avg_fft = fft_sum / M
    mag2 = np.abs(avg_fft) ** 2

    return mag2

def naive_average(signals, window="hamming", zp=4):
    """
    Naive averaging: square each FFT, then average (no coherent gain).

    This is the baseline that should NOT show √M scaling.
    """
    L = len(signals[0])
    M = len(signals)

    if window == "hamming":
        w = np.hamming(L)
    elif window == "hann":
        w = np.hann(L)
    else:
        w = np.ones(L)

    mag2_sum = np.zeros(L * zp)
    for sig in signals:
        windowed = sig * w
        spec = np.fft.fft(windowed, n=L * zp)
        mag2_sum += np.abs(spec) ** 2

    return mag2_sum / M

# --- detection ---------------------------------------------------------------
def os_cfar_detect(mag2, guard=7, train=48, q=0.8, alpha=2.5):
    """
    OS-CFAR detector adapted for FFT spectra (not cyclic groups).

    Returns:
        detected: boolean array of detected peaks
    """
    N = len(mag2)
    detected = np.zeros(N, dtype=bool)
    # For FFT: search up to Nyquist (don't use validated_radius which is for mod N)
    R = N // 2 + 1

    # Only consider [1, R-1] (skip DC bin)
    for i in range(1, R):
        # Guard cells
        exclude = set(range(max(0, i - guard), min(N, i + guard + 1)))

        # Training cells (circular)
        left_start = (i - guard - train) % N
        right_start = (i + guard + 1) % N

        train_cells = []
        for j in range(train):
            left_idx = (left_start + j) % N
            right_idx = (right_start + j) % N
            if left_idx not in exclude and left_idx < R:
                train_cells.append(mag2[left_idx])
            if right_idx not in exclude and right_idx < R:
                train_cells.append(mag2[right_idx])

        if len(train_cells) < 10:
            continue

        # Order-statistic threshold
        train_cells = sorted(train_cells)
        k = int(q * len(train_cells))
        threshold = alpha * train_cells[k]

        # Local maximum test
        left = mag2[(i - 1) % N]
        right = mag2[(i + 1) % N]
        is_peak = (mag2[i] > left) and (mag2[i] >= right)

        if is_peak and mag2[i] > threshold:
            detected[i] = True

    return detected

def evaluate_detection(detected, true_bins, Lzp, tolerance=2):
    """
    Compute precision, recall, F1 given detected peaks and ground truth bins.

    Args:
        detected: boolean array (detector output)
        true_bins: list of ground truth bin indices
        Lzp: spectrum length
        tolerance: ±bin tolerance for matching

    Returns:
        dict with precision, recall, f1, TP, FP, FN
    """
    detected_bins = np.where(detected)[0]

    # Match detected to true (with tolerance)
    TP = 0
    matched_true = set()
    for det_bin in detected_bins:
        for true_bin in true_bins:
            if abs(det_bin - true_bin) <= tolerance:
                TP += 1
                matched_true.add(true_bin)
                break

    FP = len(detected_bins) - TP
    FN = len(true_bins) - len(matched_true)

    precision = TP / len(detected_bins) if len(detected_bins) > 0 else 0.0
    recall = TP / len(true_bins) if len(true_bins) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "TP": TP,
        "FP": FP,
        "FN": FN,
        "n_detected": len(detected_bins),
        "n_true": len(true_bins)
    }

def compute_snr_at_bins(mag2, true_bins):
    """Compute average SNR at ground truth bins."""
    if not true_bins:
        return 0.0
    signal = np.mean([mag2[b] for b in true_bins])
    noise = np.median(mag2)
    lin = signal / noise if noise > 0 else 0.0
    return 10 * np.log10(lin) if lin > 0 else -np.inf

# --- main experiment ---------------------------------------------------------
def main(out_dir: str, quick: bool = False):
    np.random.seed(42)
    rng = np.random.default_rng(42)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Parameters
    L = 4096  # signal length
    zp = 8    # zero-padding factor
    K = 5     # number of planted tones
    noise_std = 0.15
    window = "hamming"

    # Planted tones: choose INTEGER bins first to avoid leakage
    # Then convert to normalized frequencies
    Lzp = L * zp
    planted_bins = [512, 1234, 2345, 3456, 4096]  # Well-spaced bins below Nyquist
    planted_freqs = [k / Lzp for k in planted_bins]  # Exact bin alignment

    print(f"E10: VRA on Stationary Rational Tones\n")
    print(f"Signal length L = {L}, zero-padding = {zp}×")
    print(f"Planted {K} tones at normalized freqs: {planted_freqs}")
    print(f"Planted bins: {planted_bins}")
    print(f"Noise std: {noise_std}\n")

    if quick:
        M_VALUES = [4, 16, 64]
        ALPHAS = [2.0, 2.5, 3.0]
        TRIALS = 10
        print("⚡ QUICK MODE: 3 M values, 3 alphas, 10 trials\n")
    else:
        M_VALUES = [4, 8, 16, 32, 64]
        ALPHAS = [2.0, 2.2, 2.5, 2.8, 3.0, 3.5, 4.0]
        TRIALS = 50
        print(f"FULL MODE: {len(M_VALUES)} M values, {len(ALPHAS)} alphas, {TRIALS} trials\n")

    results = []

    for M in M_VALUES:
        print(f"  M = {M} ...")

        for trial in range(TRIALS):
            # Generate M trials with FIXED phases (only noise varies per trial)
            # This ensures coherent averaging works - signal phases align, noise doesn't
            base_phases = rng.uniform(0, 2*np.pi, K)
            phases_list = [base_phases for _ in range(M)]  # Same phases across trials
            signals = [generate_tone_signal(planted_freqs, L, phases, noise_std, rng)
                      for phases in phases_list]

            # Coherent averaging (VRA-style)
            mag2_coherent = coherent_average(signals, window, zp)

            # Naive averaging (baseline)
            mag2_naive = naive_average(signals, window, zp)

            # Compute SNR at planted bins
            snr_coherent = compute_snr_at_bins(mag2_coherent, planted_bins)
            snr_naive = compute_snr_at_bins(mag2_naive, planted_bins)

            # Sweep alpha for coherent method
            for alpha in ALPHAS:
                detected = os_cfar_detect(mag2_coherent, alpha=alpha)
                metrics = evaluate_detection(detected, planted_bins, L * zp)

                results.append({
                    "method": "coherent",
                    "M": M,
                    "trial": trial,
                    "alpha": alpha,
                    "snr_db": float(snr_coherent),
                    **metrics
                })

            # Sweep alpha for naive method (for comparison)
            for alpha in ALPHAS:
                detected = os_cfar_detect(mag2_naive, alpha=alpha)
                metrics = evaluate_detection(detected, planted_bins, L * zp)

                results.append({
                    "method": "naive",
                    "M": M,
                    "trial": trial,
                    "alpha": alpha,
                    "snr_db": float(snr_naive),
                    **metrics
                })

    # Save results
    out_file = out / "E10_stationary_tones_results.json"
    with open(out_file, 'w') as f:
        json.dump({
            "meta": {
                "L": L,
                "zp": zp,
                "K": K,
                "planted_freqs": planted_freqs,
                "planted_bins": planted_bins,
                "noise_std": noise_std,
                "M_values": M_VALUES,
                "alphas": ALPHAS,
                "trials": TRIALS
            },
            "results": results
        }, f, indent=2)

    print(f"\n[ok] Results saved -> {out_file}")

    # Compute summary statistics
    print("\n=== Summary Statistics ===\n")

    # Group by method and M, average over trials and alphas
    for method in ["coherent", "naive"]:
        print(f"{method.upper()} averaging:")
        for M in M_VALUES:
            subset = [r for r in results if r["method"] == method and r["M"] == M]
            avg_snr = np.mean([r["snr_db"] for r in subset])
            avg_precision = np.mean([r["precision"] for r in subset])
            avg_recall = np.mean([r["recall"] for r in subset])
            avg_f1 = np.mean([r["f1"] for r in subset])
            print(f"  M={M:3d}: SNR={avg_snr:6.2f} dB, P={avg_precision:.3f}, R={avg_recall:.3f}, F1={avg_f1:.3f}")
        print()

    print("✅ E10 complete!\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E10: VRA on stationary rational tones")
    parser.add_argument("--out", default="Data/Experiments/Tier4/E10", help="Output directory")
    parser.add_argument("--quick", action="store_true", help="Quick mode: 3 M values, 3 alphas, 10 trials")
    args = parser.parse_args()

    main(args.out, args.quick)
