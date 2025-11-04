#!/usr/bin/env python3
"""
E1D Diagnostic: Single-Case M Scaling Test
===========================================

Test ONE (N, r) pair across all M values to check if M scaling works.
This isolates measurement artifacts from real scaling behavior.

Expected: +3 dB per 2× increase in M (SNR ∝ M in dB scale)
"""

import sys
import numpy as np
from pathlib import Path

# Add VRA core to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Code" / "VRA"))
from core import compute_averaged_spectrum, multiplicative_order

def harmonic_snr_db(mag2, N, r, Lzp):
    """Compute harmonic SNR in dB."""
    # Expected harmonic bins
    expected_bins = [int(round(k * Lzp / r)) for k in range(1, r)]

    # Signal power at harmonic bins
    signal_power = np.array([mag2[b] for b in expected_bins])

    # Noise power (all other bins, excluding harmonics)
    noise_mask = np.ones(len(mag2), dtype=bool)
    noise_mask[expected_bins] = False
    noise_power = mag2[noise_mask]

    # SNR in dB
    snr_db = 10 * np.log10(np.mean(signal_power) / np.mean(noise_power))
    return snr_db

def main():
    # Test parameters
    N = 997

    # Find a base with small order (HIGH_SNR regime)
    # Try small bases until we find one with r < 100
    a = None
    r = None
    for test_a in range(2, 20):
        test_r = multiplicative_order(test_a, N)
        if test_r < 100:
            a = test_a
            r = test_r
            break

    if a is None:
        print("Could not find suitable (a, r) pair with r < 100")
        return

    L = 131072  # Same as E1D
    window = "hamming"

    M_values = [4, 8, 16, 32, 64, 128]

    print(f"E1D Diagnostic: Single-Case M Scaling Test")
    print(f"=" * 60)
    print(f"Testing N={N}, a={a}, r={r}, ρ={r/N:.4f} (HIGH_SNR regime)")
    print(f"M values: {M_values}")
    print(f"")

    results = []

    for M in M_values:
        # Generate M bases (skip i=0 which is identity!)
        bases = [pow(a, i, N) for i in range(1, M+1)]

        # Compute averaged spectrum
        # Signature: compute_averaged_spectrum(N, bases, x0, length, zp, window)
        x0 = 1  # Starting point
        mag2 = compute_averaged_spectrum(N, bases, x0, L, 1, window)
        Lzp = len(mag2)

        # Compute SNR
        snr_db = harmonic_snr_db(mag2, N, r, Lzp)

        results.append({
            "M": M,
            "snr_db": snr_db
        })

        print(f"M={M:3d}: SNR = {snr_db:.2f} dB")

    print(f"")
    print(f"SNR Gains (relative to M=4):")
    print(f"-" * 60)

    baseline_snr = results[0]["snr_db"]

    for i, res in enumerate(results):
        M = res["M"]
        snr = res["snr_db"]
        gain = snr - baseline_snr

        # Theoretical gain from M scaling
        M_ratio = M / M_values[0]
        theoretical_gain = 10 * np.log10(M_ratio)

        print(f"M={M:3d}: Gain = {gain:+.2f} dB (theoretical: {theoretical_gain:+.2f} dB)")

    print(f"")
    print(f"Analysis:")
    print(f"-" * 60)

    # Compute per-doubling gains
    doublings = []
    for i in range(len(results) - 1):
        if results[i+1]["M"] == 2 * results[i]["M"]:
            gain = results[i+1]["snr_db"] - results[i]["snr_db"]
            doublings.append(gain)
            M1, M2 = results[i]["M"], results[i+1]["M"]
            print(f"M={M1}→{M2}: {gain:.2f} dB gain (expected: +3.0 dB)")

    avg_doubling = np.mean(doublings)
    print(f"")
    print(f"Average per-doubling gain: {avg_doubling:.2f} dB")
    print(f"Expected per-doubling gain: +3.00 dB")
    print(f"Ratio: {avg_doubling / 3.0 * 100:.1f}% of theoretical")

    # Total gain M=4 → M=128
    total_gain = results[-1]["snr_db"] - results[0]["snr_db"]
    theoretical_total = 10 * np.log10(128 / 4)

    print(f"")
    print(f"Total M=4→128 gain: {total_gain:.2f} dB")
    print(f"Theoretical gain:    {theoretical_total:.2f} dB")
    print(f"Ratio: {total_gain / theoretical_total * 100:.1f}% of theoretical")

    print(f"")
    print(f"Verdict:")
    print(f"-" * 60)

    if total_gain >= 0.8 * theoretical_total:
        print(f"✅ M scaling VALIDATED: Observed {total_gain:.2f} dB ≈ {theoretical_total:.2f} dB expected")
        print(f"   → E1D's weak within-case result (+1.6 dB) was a measurement artifact")
    elif total_gain >= 0.5 * theoretical_total:
        print(f"⚠️  Partial M scaling: Observed {total_gain:.2f} dB vs. {theoretical_total:.2f} dB expected")
        print(f"   → Some saturation or interference effects present")
    else:
        print(f"❌ M scaling FAILED: Observed {total_gain:.2f} dB << {theoretical_total:.2f} dB expected")
        print(f"   → Real issue with algorithm or implementation")

    print(f"")

if __name__ == "__main__":
    main()
