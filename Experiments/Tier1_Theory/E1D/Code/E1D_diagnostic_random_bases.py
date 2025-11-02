#!/usr/bin/env python3
"""
E1D Diagnostic: Random Coprime Bases Test
==========================================

Test M RANDOM coprime bases (not consecutive powers) to check M scaling.
This is closer to how E4/E5 work with character embeddings.
"""

import sys
import numpy as np
from pathlib import Path

# Add VRA core to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Code" / "VRA"))
from core import compute_averaged_spectrum, multiplicative_order

def harmonic_snr_db(mag2, N, r, Lzp):
    """Compute harmonic SNR in dB."""
    expected_bins = [int(round(k * Lzp / r)) for k in range(1, r)]
    signal_power = np.array([mag2[b] for b in expected_bins])
    noise_mask = np.ones(len(mag2), dtype=bool)
    noise_mask[expected_bins] = False
    noise_power = mag2[noise_mask]
    snr_db = 10 * np.log10(np.mean(signal_power) / np.mean(noise_power))
    return snr_db

def find_coprime_bases(N, target_r, max_bases=200):
    """Find bases with the target multiplicative order."""
    bases = []
    for a in range(2, N):
        if np.gcd(a, N) != 1:
            continue
        r = multiplicative_order(a, N)
        if r == target_r:
            bases.append(a)
            if len(bases) >= max_bases:
                break
    return bases

def main():
    # Test parameters
    N = 997

    # Find a base with small order
    a_ref = None
    r = None
    for test_a in range(2, 20):
        test_r = multiplicative_order(test_a, N)
        if test_r < 100:
            a_ref = test_a
            r = test_r
            break

    if a_ref is None:
        print("Could not find suitable base with r < 100")
        return

    print(f"Finding all bases with order r={r} for N={N}...")
    all_bases = find_coprime_bases(N, r, max_bases=200)
    print(f"Found {len(all_bases)} bases with order {r}")
    print(f"First 20: {all_bases[:20]}")

    if len(all_bases) < 64:
        print(f"ERROR: Only {len(all_bases)} bases available, need at least 64")
        return

    L = 131072
    window = "hamming"
    M_values = [4, 8, 16, 32, 64]

    print(f"\nE1D Diagnostic: Random Coprime Bases Test")
    print(f"=" * 60)
    print(f"N={N}, r={r}, ρ={r/N:.4f} (HIGH_SNR regime)")
    print(f"Testing RANDOM coprime bases (not consecutive powers)")
    print(f"")

    results = []

    # Shuffle bases for randomness
    rng = np.random.default_rng(42)
    shuffled_bases = rng.choice(all_bases, size=len(all_bases), replace=False)

    for M in M_values:
        # Use first M shuffled bases
        bases = [int(a) for a in shuffled_bases[:M]]

        # Compute averaged spectrum
        x0 = 1
        mag2 = compute_averaged_spectrum(N, bases, x0, L, 1, window)
        Lzp = len(mag2)

        # Compute SNR
        snr_db = harmonic_snr_db(mag2, N, r, Lzp)

        results.append({
            "M": M,
            "snr_db": snr_db
        })

        print(f"M={M:3d}: SNR = {snr_db:.2f} dB (bases: {bases[:5]}...)")

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

    # Total gain M=4 → M=64
    total_gain = results[-1]["snr_db"] - results[0]["snr_db"]
    M_final = M_values[-1]
    M_initial = M_values[0]
    theoretical_total = 10 * np.log10(M_final / M_initial)

    print(f"")
    print(f"Total M={M_initial}→{M_final} gain: {total_gain:.2f} dB")
    print(f"Theoretical gain:    {theoretical_total:.2f} dB")
    print(f"Ratio: {total_gain / theoretical_total * 100:.1f}% of theoretical")

    print(f"")
    print(f"Verdict:")
    print(f"-" * 60)

    if total_gain >= 0.8 * theoretical_total:
        print(f"✅ M scaling VALIDATED: Observed {total_gain:.2f} dB ≈ {theoretical_total:.2f} dB expected")
        print(f"   → Random coprime bases DO average coherently!")
    elif total_gain >= 0.5 * theoretical_total:
        print(f"⚠️  Partial M scaling: Observed {total_gain:.2f} dB vs. {theoretical_total:.2f} dB expected")
        print(f"   → Some scaling present but weaker than theory predicts")
    else:
        print(f"❌ M scaling FAILED: Observed {total_gain:.2f} dB << {theoretical_total:.2f} dB expected")
        print(f"   → Random coprime bases do NOT average coherently")

    print(f"")

if __name__ == "__main__":
    main()
