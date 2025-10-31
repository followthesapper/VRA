#!/usr/bin/env python3
"""
VRA Core Functions
==================

Shared mathematical and signal processing functions for VRA analysis.

Author: Dylan Vaca
Date: October 2025
"""

import numpy as np

# =============================================================================
# Modular Arithmetic
# =============================================================================

def modular_sequence(N, a, x0, length):
    """Generate modular iteration sequence.

    Parameters:
        N (int): Modulus
        a (int): Base
        x0 (int): Starting seed
        length (int): Sequence length

    Returns:
        numpy.ndarray: Sequence x_i where x_{i+1} = a*x_i mod N
    """
    xs = np.zeros(length, dtype=np.int64)
    xs[0] = x0
    for i in range(1, length):
        xs[i] = (a * xs[i-1]) % N
    return xs


def multiplicative_order(a, N, max_iter=10000):
    """Compute multiplicative order of a modulo N.

    Parameters:
        a (int): Base
        N (int): Modulus
        max_iter (int): Maximum iterations

    Returns:
        int or None: Order r where a^r ≡ 1 (mod N), or None if gcd(a,N) != 1
    """
    if np.gcd(a, N) != 1:
        return None
    x = a
    for r in range(1, min(max_iter, N)):
        if x == 1:
            return r
        x = (x * a) % N
    return None


# =============================================================================
# Phase Embedding
# =============================================================================

def phase_embed(xs, N):
    """Phase embedding into complex unit circle.

    Parameters:
        xs (numpy.ndarray): Modular sequence
        N (int): Modulus

    Returns:
        numpy.ndarray: Complex signal u_i = exp(2πj * x_i / N)
    """
    phases = 2.0 * np.pi * xs / N
    return np.exp(1j * phases)


# =============================================================================
# Windowing
# =============================================================================

def apply_window(signal, kind="hann"):
    """Apply window function to signal.

    Parameters:
        signal (numpy.ndarray): Input signal
        kind (str): Window type ('hann', 'hamming', 'blackman', 'none')

    Returns:
        numpy.ndarray: Windowed signal
    """
    length = len(signal)

    if kind == "hann":
        window = np.hanning(length)
    elif kind == "hamming":
        window = np.hamming(length)
    elif kind == "blackman":
        window = np.blackman(length)
    elif kind == "none":
        window = np.ones(length)
    else:
        raise ValueError(f"Unknown window type: {kind}")

    return signal * window


# =============================================================================
# Spectrum Analysis
# =============================================================================

def compute_spectrum(N, a, x0, length, zp, window="hann"):
    """Compute single-base power spectrum.

    Parameters:
        N (int): Modulus
        a (int): Base
        x0 (int): Starting seed
        length (int): Sequence length before zero-padding
        zp (int): Zero-padding factor
        window (str): Window function type

    Returns:
        numpy.ndarray: Power spectrum |S[k]|^2
    """
    # Generate sequence
    xs = modular_sequence(N, a, x0, length)

    # Phase embed
    us = phase_embed(xs, N)

    # Window
    us_windowed = apply_window(us, window)

    # Zero-pad
    L = length * zp
    us_padded = np.zeros(L, dtype=np.complex128)
    us_padded[:length] = us_windowed

    # FFT
    spectrum = np.fft.fft(us_padded)
    mag2 = np.abs(spectrum) ** 2

    return mag2


def compute_averaged_spectrum(N, bases, x0, length, zp, window="hann"):
    """Compute M-base COHERENTLY averaged power spectrum.

    CRITICAL: This performs coherent averaging by summing complex FFTs
    before squaring, NOT by averaging power spectra. This preserves
    phase relationships and enables √M SNR scaling.

    Coherent: |Σ U_m / M|² → SNR scales as √M
    Incoherent: Σ|U_m|²/M → No SNR gain

    Parameters:
        N (int): Modulus
        bases (list): List of M bases
        x0 (int): Starting seed
        length (int): Sequence length before zero-padding
        zp (int): Zero-padding factor
        window (str): Window function type

    Returns:
        numpy.ndarray: Coherently averaged power spectrum
    """
    M = len(bases)
    L = length * zp
    U_sum = None

    for a in bases:
        # Generate sequence
        xs = modular_sequence(N, a, x0, length)

        # Phase embed
        us = phase_embed(xs, N)

        # Window
        us_windowed = apply_window(us, window)

        # Zero-pad
        us_padded = np.zeros(L, dtype=np.complex128)
        us_padded[:length] = us_windowed

        # FFT (keep complex!)
        U = np.fft.fft(us_padded)

        # Sum complex FFTs
        if U_sum is None:
            U_sum = np.zeros_like(U, dtype=np.complex128)
        U_sum += U

    # Average THEN square (coherent)
    U_mean = U_sum / M
    mag2_avg = np.abs(U_mean) ** 2

    return mag2_avg


# =============================================================================
# Metrics
# =============================================================================

def compute_concentration(mag2):
    """Compute concentration ratio.

    Parameters:
        mag2 (numpy.ndarray): Power spectrum

    Returns:
        float: C = max(|S|^2) / sum(|S|^2)
    """
    return np.max(mag2) / np.sum(mag2)


def compute_precision_recall(mag2, expected_bins, radius):
    """Compute precision and recall metrics.

    Precision = (# detected peaks matching expected bins) / (# total detected peaks)
    Recall = (# expected bins with matching peaks) / (# total expected bins)

    Parameters:
        mag2 (numpy.ndarray): Power spectrum
        expected_bins (list): Expected harmonic bin locations
        radius (int): Validated radius in bins

    Returns:
        dict: {'precision', 'recall', 'f1', 'TP', 'FP', 'FN', 'num_peaks'}
    """
    L = len(mag2)

    # Threshold at 99.9th percentile
    threshold = np.percentile(mag2, 99.9)

    # Find peaks above threshold
    peak_indices = np.where(mag2 > threshold)[0]

    # Expected peak set
    expected_set = set(expected_bins)

    # Track which expected bins were matched and which peaks are TP
    matched_expected_bins = set()
    TP_peaks = 0
    FP_peaks = 0

    for idx in peak_indices:
        # Check if within radius of any expected peak
        matched_bins = [
            exp_idx for exp_idx in expected_set
            if (abs(idx - exp_idx) <= radius or
                abs(idx - (L - exp_idx)) <= radius or
                abs((L - idx) - exp_idx) <= radius)
        ]

        if matched_bins:
            TP_peaks += 1
            # Add all matched bins to the set of matched expected bins
            matched_expected_bins.update(matched_bins)
        else:
            FP_peaks += 1

    # TP = number of expected bins that were successfully detected
    TP = len(matched_expected_bins)
    # FP = number of detected peaks that don't match expected bins
    FP = FP_peaks
    # FN = number of expected bins that were not detected
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
        'num_peaks': len(peak_indices)
    }


# =============================================================================
# Validated Radius Calculation
# =============================================================================

def validated_radius(L):
    """Compute validated radius from FFT length.

    Parameters:
        L (int): FFT length (power of 2)

    Returns:
        int: R = floor(0.5 * log2(L))
    """
    return int(0.5 * np.log2(L))


# =============================================================================
# Regime Classification
# =============================================================================

def classify_regime(N, r):
    """Classify VRA regime based on r/N ratio.

    Parameters:
        N (int): Modulus
        r (int): Multiplicative order

    Returns:
        tuple: (regime_name, base_requirement)
            regime_name: 'HIGH_SNR', 'TRANSITION', or 'LOW_SNR'
            base_requirement: 'phase_aligned' or 'any_same_order'
    """
    rho = r / N

    if rho < 0.15:
        return 'HIGH_SNR', 'phase_aligned'
    elif rho < 0.26:
        return 'TRANSITION', 'any_same_order'
    else:
        return 'LOW_SNR', 'any_same_order'
