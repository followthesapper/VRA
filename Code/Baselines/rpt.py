#!/usr/bin/env python3
"""
Ramanujan Periodicity Transform (RPT) Baseline
===============================================

Implementation of Ramanujan-sum-based period detection for comparison
with VRA. This represents the closest prior-art spectral approach to
integer period discovery.

References:
- Vaidyanathan et al., "Ramanujan Sums in Signal Processing"
-Planat et al., "Ramanujan Periodic Transform"

Author: Dylan Vaca
Date: October 2025
"""

import numpy as np
from math import gcd
from typing import Dict, List, Tuple


def ramanujan_sum(q: int, n: np.ndarray) -> np.ndarray:
    """
    Compute Ramanujan sum c_q(n).

    The Ramanujan sum is defined as:
        c_q(n) = sum_{1<=k<=q, gcd(k,q)=1} exp(2πi k n / q)

    This is a periodic function with period q that captures
    arithmetic structure related to divisibility and coprimality.

    Parameters
    ----------
    q : int
        Period parameter
    n : np.ndarray
        Sample indices (integer array)

    Returns
    -------
    np.ndarray
        Complex-valued Ramanujan sum c_q(n)
    """
    # Find all k coprime to q
    ks = np.array([k for k in range(1, q + 1) if gcd(k, q) == 1])

    # Compute exp(2πi k n / q) for all coprime k
    # Shape: (len(ks), len(n))
    angles = 2j * np.pi * np.outer(ks, n) / q

    # Sum over coprime k values
    result = np.exp(angles).sum(axis=0).astype(np.complex64)

    return result


def build_rpt_dictionary(Nsamples: int, q_max: int) -> Dict[int, np.ndarray]:
    """
    Build dictionary of Ramanujan atoms for period detection.

    Precomputes normalized Ramanujan sums c_q(n) for all periods
    q from 1 to q_max. These form an overcomplete basis for
    representing periodic signals.

    Parameters
    ----------
    Nsamples : int
        Number of samples in signal
    q_max : int
        Maximum period to include in dictionary

    Returns
    -------
    Dict[int, np.ndarray]
        Dictionary mapping period q to normalized Ramanujan atom
    """
    n = np.arange(Nsamples, dtype=np.int64)
    atoms = {}

    for q in range(1, q_max + 1):
        atom = ramanujan_sum(q, n)
        # Normalize to unit energy for fair comparison
        norm = np.linalg.norm(atom)
        if norm > 1e-12:
            atoms[q] = atom / norm
        else:
            atoms[q] = atom

    return atoms


def rpt_periodogram(signal: np.ndarray, atoms: Dict[int, np.ndarray]) -> Dict[int, float]:
    """
    Compute Ramanujan Periodicity Transform (RPT) periodogram.

    For each period q, computes the energy captured:
        P[q] = |<signal, c_q>|^2

    where c_q is the normalized Ramanujan atom for period q.

    Parameters
    ----------
    signal : np.ndarray
        Input signal (real or complex)
    atoms : Dict[int, np.ndarray]
        Dictionary of Ramanujan atoms from build_rpt_dictionary

    Returns
    -------
    Dict[int, float]
        Periodogram mapping period q to power
    """
    P = {}
    x = signal.astype(np.complex64)

    for q, atom in atoms.items():
        # Inner product: <atom, signal>
        inner = np.vdot(atom, x)
        # Power: |inner product|^2
        P[q] = float(np.abs(inner) ** 2)

    return P


def detect_period_rpt(
    signal: np.ndarray,
    q_max: int = 1024,
    topk: int = 11
) -> Dict:
    """
    Detect periods in signal using Ramanujan Periodicity Transform.

    Main entry point for RPT-based period detection. Builds dictionary,
    computes periodogram, and returns top-k detected periods.

    Parameters
    ----------
    signal : np.ndarray
        Input signal (real or complex)
    q_max : int, optional
        Maximum period to search (default: 1024)
    topk : int, optional
        Number of top periods to return (default: 11)

    Returns
    -------
    Dict
        Results containing:
        - 'P': full periodogram (period -> power)
        - 'top_periods': list of top-k detected periods
        - 'argmax_q': period with highest power
        - 'power_top': power values for top-k periods
    """
    # Build Ramanujan dictionary
    atoms = build_rpt_dictionary(len(signal), q_max)

    # Compute periodogram
    P = rpt_periodogram(signal, atoms)

    # Rank periods by power
    ranked = sorted(P.items(), key=lambda kv: kv[1], reverse=True)

    # Extract top-k
    top_periods = [q for q, _ in ranked[:topk]]
    top_powers = [pwr for _, pwr in ranked[:topk]]

    return {
        "P": P,
        "top_periods": top_periods,
        "argmax_q": top_periods[0] if top_periods else None,
        "power_top": top_powers,
    }


def rpt_precision_recall(
    signal: np.ndarray,
    true_period: int,
    expected_harmonics: List[int],
    q_max: int = 1024,
    topk: int = 11,
    harmonic_tolerance: int = 2
) -> Tuple[float, float, Dict]:
    """
    Evaluate RPT detection using precision and recall.

    Compares RPT's top-k detected periods against ground truth,
    checking both for exact period match and harmonic alignment.

    Parameters
    ----------
    signal : np.ndarray
        Input signal
    true_period : int
        Ground-truth period r
    expected_harmonics : List[int]
        Expected harmonic bin locations
    q_max : int
        Maximum period to search
    topk : int
        Number of detections to evaluate
    harmonic_tolerance : int
        Tolerance for harmonic bin matching

    Returns
    -------
    Tuple[float, float, Dict]
        (precision, recall, detailed_results)
    """
    # Run RPT detection
    rpt_result = detect_period_rpt(signal, q_max=q_max, topk=topk)
    detected_periods = rpt_result["top_periods"]

    # Check if true period is in top-k
    exact_hit = (true_period in detected_periods)

    # For harmonic matching, check if detected periods are divisors/multiples
    # of true period (common in periodic signals with harmonic structure)
    harmonic_hits = 0
    for q in detected_periods:
        if q == true_period:
            harmonic_hits += 1
        elif true_period % q == 0 or q % true_period == 0:
            # q is a harmonic of true period
            harmonic_hits += 1

    # Precision: fraction of detections that are harmonically related
    precision = harmonic_hits / len(detected_periods) if detected_periods else 0.0

    # Recall: did we detect the fundamental period?
    recall = 1.0 if exact_hit else 0.0

    details = {
        "detected_periods": detected_periods,
        "true_period": true_period,
        "exact_hit": exact_hit,
        "harmonic_hits": harmonic_hits,
        "precision": precision,
        "recall": recall,
    }

    return precision, recall, details


if __name__ == "__main__":
    # Simple test case
    print("Testing Ramanujan Periodicity Transform...")

    # Create synthetic periodic signal with period r=7
    r = 7
    N = 100
    t = np.arange(N)
    signal = np.sin(2 * np.pi * t / r)

    # Detect period
    result = detect_period_rpt(signal, q_max=50, topk=5)

    print(f"\nTrue period: {r}")
    print(f"Detected top-5 periods: {result['top_periods']}")
    print(f"Top period powers: {[f'{p:.3f}' for p in result['power_top']]}")

    if result['argmax_q'] == r:
        print(f"✅ Correct detection: period {r}")
    else:
        print(f"❌ Incorrect: detected {result['argmax_q']} instead of {r}")
