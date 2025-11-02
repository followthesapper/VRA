#!/usr/bin/env python3
"""
E1D Diagnostic: Visual Spectrum Analysis
========================================

Plot the actual power spectra for different M values to see WHY SNR decreases.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
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
    return snr_db, expected_bins

def main():
    # Test parameters
    N = 997

    # Find a base with small order (HIGH_SNR regime)
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

    L = 131072
    window = "hamming"
    M_values = [4, 8, 16, 32, 64, 128]

    print(f"Visual Diagnostic: Spectrum Analysis")
    print(f"=" * 60)
    print(f"Testing N={N}, a={a}, r={r}, ρ={r/N:.4f} (HIGH_SNR regime)")
    print(f"")

    # Compute spectra for all M values
    spectra = {}
    snrs = {}
    harmonic_bins = None

    for M in M_values:
        bases = [pow(a, i, N) for i in range(M)]
        x0 = 1
        mag2 = compute_averaged_spectrum(N, bases, x0, L, 1, window)
        snr_db, expected_bins = harmonic_snr_db(mag2, N, r, len(mag2))

        spectra[M] = mag2
        snrs[M] = snr_db
        if harmonic_bins is None:
            harmonic_bins = expected_bins

        print(f"M={M:3d}: SNR = {snr_db:.2f} dB, Max power = {np.max(mag2):.2e}, Mean power = {np.mean(mag2):.2e}")

    print(f"")
    print(f"Analysis:")
    print(f"-" * 60)

    # Check if max power is increasing or decreasing
    max_powers = [np.max(spectra[M]) for M in M_values]
    print(f"Max power trend:")
    for i, M in enumerate(M_values):
        ratio = max_powers[i] / max_powers[0] if max_powers[0] > 0 else 0
        print(f"  M={M:3d}: {max_powers[i]:.2e} ({ratio:.2f}× relative to M=4)")

    # Check mean noise floor
    mean_powers = [np.mean(spectra[M]) for M in M_values]
    print(f"")
    print(f"Mean noise floor trend:")
    for i, M in enumerate(M_values):
        ratio = mean_powers[i] / mean_powers[0] if mean_powers[0] > 0 else 0
        print(f"  M={M:3d}: {mean_powers[i]:.2e} ({ratio:.2f}× relative to M=4)")

    # Plot spectra
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    axes = axes.flatten()

    for idx, M in enumerate(M_values):
        ax = axes[idx]
        mag2 = spectra[M]
        Lzp = len(mag2)

        # Plot spectrum in dB
        mag2_db = 10 * np.log10(mag2 + 1e-20)
        ax.plot(mag2_db, alpha=0.7, linewidth=0.5)

        # Mark harmonic bins
        for hbin in harmonic_bins:
            ax.axvline(hbin, color='red', alpha=0.3, linewidth=0.5)

        ax.set_title(f"M={M}, SNR={snrs[M]:.2f} dB")
        ax.set_xlabel("Bin")
        ax.set_ylabel("Power (dB)")
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, min(2000, Lzp))  # Zoom to first 2000 bins

        # Add text with statistics
        max_db = np.max(mag2_db[mag2_db > -100])
        noise_mask = np.ones(len(mag2), dtype=bool)
        noise_mask[harmonic_bins] = False
        mean_noise_db = 10 * np.log10(np.mean(mag2[noise_mask]) + 1e-20)
        ax.text(0.02, 0.98, f"Peak: {max_db:.1f} dB\nNoise: {mean_noise_db:.1f} dB",
                transform=ax.transAxes, va='top', fontsize=8,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    out_path = Path(__file__).parent.parent.parent / "Figures" / "Experiments" / "Tier1"
    out_path.mkdir(parents=True, exist_ok=True)
    fig_path = out_path / "E1D_diagnostic_spectra.png"
    plt.savefig(fig_path, dpi=150)
    print(f"")
    print(f"Figure saved: {fig_path}")

    # Plot zoomed-in view of first few harmonics
    fig2, axes2 = plt.subplots(2, 3, figsize=(15, 8))
    axes2 = axes2.flatten()

    for idx, M in enumerate(M_values):
        ax = axes2[idx]
        mag2 = spectra[M]

        # Zoom to first 5 harmonics
        zoom_start = max(0, harmonic_bins[0] - 100)
        zoom_end = harmonic_bins[4] + 100 if len(harmonic_bins) > 4 else harmonic_bins[-1] + 100

        mag2_db = 10 * np.log10(mag2[zoom_start:zoom_end] + 1e-20)
        ax.plot(range(zoom_start, zoom_end), mag2_db, alpha=0.7, linewidth=0.8)

        # Mark harmonic bins
        for hbin in harmonic_bins[:5]:
            if zoom_start <= hbin < zoom_end:
                ax.axvline(hbin, color='red', alpha=0.5, linewidth=1.5, label='Harmonic')

        ax.set_title(f"M={M}, SNR={snrs[M]:.2f} dB")
        ax.set_xlabel("Bin")
        ax.set_ylabel("Power (dB)")
        ax.grid(True, alpha=0.3)

    axes2[0].legend(loc='upper right')
    plt.tight_layout()

    fig2_path = out_path / "E1D_diagnostic_harmonics_zoom.png"
    plt.savefig(fig2_path, dpi=150)
    print(f"Figure saved: {fig2_path}")

    print(f"")

if __name__ == "__main__":
    main()
