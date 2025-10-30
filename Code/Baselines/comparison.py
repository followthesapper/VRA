#!/usr/bin/env python3
"""
VRA vs. RPT Comparison Framework
==================================

Head-to-head comparison between VRA (Vaca Resonance Analysis) and
RPT (Ramanujan Periodicity Transform) to establish novelty.

This module runs systematic experiments to answer:
    E1: Does VRA achieve better accuracy than RPT?
    E2: Does phase-alignment matter?
    E3: Is VRA more robust?
    E4: Is VRA faster?

Author: Dylan Vaca
Date: October 2025
"""

import json
import time
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Callable
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "Core"))
sys.path.insert(0, str(Path(__file__).parent.parent / "Robustness"))

from vra_core import (
    multiplicative_order,
    modular_sequence,
    phase_embed,
    compute_averaged_spectrum,
    compute_concentration,
    compute_precision_recall,
    validated_radius,
    classify_regime,
)
from ramanujan_baseline import detect_period_rpt


def find_bases_with_order(N: int, target_r: int, M: int, strategy: str = "random") -> List[int]:
    """
    Find M bases with multiplicative order target_r.

    Parameters
    ----------
    N : int
        Modulus
    target_r : int
        Target multiplicative order
    M : int
        Number of bases to find
    strategy : str
        Base selection strategy:
        - "random": random sampling
        - "aligned": phase-aligned (coprime to r)
        - "adversarial": maximum phase spread

    Returns
    -------
    List[int]
        List of M bases with order target_r
    """
    candidates = []

    # Find all bases with order target_r
    for a in range(2, N):
        if np.gcd(a, N) == 1:
            if multiplicative_order(a, N) == target_r:
                candidates.append(a)
                if len(candidates) >= M * 5:  # Get plenty of options
                    break

    if len(candidates) < M:
        raise ValueError(f"Could not find {M} bases with order {target_r} in Z_{N}")

    # Apply selection strategy
    if strategy == "random":
        np.random.shuffle(candidates)
        return candidates[:M]

    elif strategy == "aligned":
        # Phase-aligned: prefer bases whose initial phase is coprime to r
        # This maximizes coherent averaging in HIGH-SNR regime
        aligned = []
        for a in candidates:
            # Check if a is "well-distributed" (coprime to r ideally)
            if np.gcd(a, target_r) == 1:
                aligned.append(a)
        if len(aligned) >= M:
            return aligned[:M]
        else:
            # Fall back to first M
            return candidates[:M]

    elif strategy == "adversarial":
        # Maximum phase spread: choose bases with maximally different phases
        # This tests worst-case for coherent averaging
        if M <= len(candidates):
            # Simple strategy: space them out evenly in candidate list
            indices = np.linspace(0, len(candidates) - 1, M, dtype=int)
            return [candidates[i] for i in indices]
        else:
            return candidates[:M]

    else:
        return candidates[:M]


def generate_vra_signal(N: int, r: int, bases: List[int], L: int, x0: int = 1) -> Tuple[np.ndarray, float]:
    """
    Generate VRA signal (averaged spectrum) from given bases.

    Parameters
    ----------
    N : int
        Modulus
    r : int
        Multiplicative order
    bases : List[int]
        Bases to average
    L : int
        Sequence length
    x0 : int
        Initial condition

    Returns
    -------
    Tuple[np.ndarray, float]
        (power spectrum, concentration)
    """
    # Use VRA's coherent averaging
    mag2 = compute_averaged_spectrum(N, bases, x0=x0, length=L, zp=4, window="hann")
    C = compute_concentration(mag2)
    return mag2, C


def generate_rpt_signal(N: int, r: int, bases: List[int], L: int, x0: int = 1) -> np.ndarray:
    """
    Generate time-domain signal for RPT from modular sequence.

    RPT expects a time-domain signal, so we create one from the
    first base (or average multiple if desired).

    Parameters
    ----------
    N : int
        Modulus
    r : int
        Multiplicative order
    bases : List[int]
        Bases (typically use first one for RPT)
    L : int
        Sequence length
    x0 : int
        Initial condition

    Returns
    -------
    np.ndarray
        Real-valued time-domain signal
    """
    # Use first base for RPT (single-base approach)
    # Or average multiple sequences in time domain
    signals = []
    for a in bases:
        xs = modular_sequence(N, a, x0=x0, length=L)
        # Normalize to [-1, 1]
        signal = (xs.astype(float) / N) * 2 - 1
        signals.append(signal)

    # Average in time domain
    avg_signal = np.mean(signals, axis=0)
    return avg_signal


def evaluate_vra_vs_rpt_single(
    N: int,
    r: int,
    M: int,
    L: int,
    base_strategy: str = "random",
    x0: int = 1,
    q_max: int = None,
    topk: int = 11,
) -> Dict:
    """
    Run single VRA vs. RPT comparison.

    Parameters
    ----------
    N : int
        Modulus
    r : int
        True multiplicative order
    M : int
        Number of bases
    L : int
        Sequence length
    base_strategy : str
        "random", "aligned", or "adversarial"
    x0 : int
        Initial condition
    q_max : int, optional
        Max period for RPT (default: min(2*r, L//2))
    topk : int
        Number of top detections to consider

    Returns
    -------
    Dict
        Comparison results
    """
    if q_max is None:
        q_max = min(2 * r, L // 2)

    # Find bases
    bases = find_bases_with_order(N, r, M, strategy=base_strategy)

    # === VRA Evaluation ===
    t0_vra = time.perf_counter()

    mag2_vra, C_vra = generate_vra_signal(N, r, bases, L, x0)

    # Expected harmonic bins for order r
    Lzp = L * 4  # VRA uses zp=4
    harmonic_bins = [int(round(k * Lzp / r)) for k in range(1, min(r, 100))]

    # Precision/Recall with validated radius
    R = validated_radius(Lzp)
    metrics_vra = compute_precision_recall(mag2_vra, harmonic_bins, R)

    time_vra = time.perf_counter() - t0_vra

    # === RPT Evaluation ===
    t0_rpt = time.perf_counter()

    signal_rpt = generate_rpt_signal(N, r, bases, L, x0)
    rpt_result = detect_period_rpt(signal_rpt, q_max=q_max, topk=topk)

    time_rpt = time.perf_counter() - t0_rpt

    # Check if RPT detected the correct period
    detected_periods = rpt_result["top_periods"]
    rpt_hit = (r in detected_periods)

    # Precision: fraction of top-k that are harmonically related to r
    harmonic_hits = sum(1 for q in detected_periods if (r % q == 0 or q % r == 0))
    prec_rpt = harmonic_hits / len(detected_periods) if detected_periods else 0.0
    rec_rpt = 1.0 if rpt_hit else 0.0

    # Regime classification
    regime, base_req = classify_regime(N, r)
    rho = r / N

    return {
        "N": N,
        "r": r,
        "rho": float(rho),
        "regime": regime,
        "M": M,
        "L": L,
        "base_strategy": base_strategy,
        "bases_used": bases,
        # VRA results
        "precision_vra": float(metrics_vra["precision"]),
        "recall_vra": float(metrics_vra["recall"]),
        "concentration_vra": float(C_vra),
        "TP_vra": int(metrics_vra["TP"]),
        "FP_vra": int(metrics_vra["FP"]),
        "FN_vra": int(metrics_vra["FN"]),
        "time_vra": float(time_vra),
        # RPT results
        "precision_rpt": float(prec_rpt),
        "recall_rpt": float(rec_rpt),
        "detected_periods_rpt": detected_periods[:5],  # Top 5
        "exact_hit_rpt": bool(rpt_hit),
        "time_rpt": float(time_rpt),
        # Comparison
        "delta_precision": float(metrics_vra["precision"] - prec_rpt),
        "delta_recall": float(metrics_vra["recall"] - rec_rpt),
        "speedup": float(time_rpt / time_vra) if time_vra > 0 else None,
    }


def sweep_grid(
    test_cases: List[Dict],
    base_strategy: str = "random",
    out_json: str = "Data/Novelty/vra_vs_rpt_results.json",
    verbose: bool = True,
) -> Dict:
    """
    Sweep grid of test cases for VRA vs. RPT comparison.

    Parameters
    ----------
    test_cases : List[Dict]
        List of test case dicts with keys: N, r, M, L
    base_strategy : str
        Base selection strategy
    out_json : str
        Output JSON path
    verbose : bool
        Print progress

    Returns
    -------
    Dict
        Summary statistics
    """
    results = []
    t0 = time.time()

    if verbose:
        print(f"\nRunning {len(test_cases)} VRA vs. RPT comparisons...")
        print(f"Base selection strategy: {base_strategy}")

    for i, case in enumerate(test_cases):
        if verbose and i % 10 == 0:
            print(f"  [{i+1}/{len(test_cases)}] N={case['N']}, r={case['r']}, M={case['M']}")

        try:
            result = evaluate_vra_vs_rpt_single(
                N=case["N"],
                r=case["r"],
                M=case["M"],
                L=case.get("L", 500),
                base_strategy=base_strategy,
            )
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"    ⚠️  Error: {e}")
            continue

    # Save results
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)

    elapsed = time.time() - t0

    if verbose:
        print(f"\n✅ Completed {len(results)} comparisons in {elapsed:.1f}s")
        print(f"   Results saved to: {out_json}")

    return {
        "n_cases": len(results),
        "elapsed_sec": elapsed,
        "output_file": out_json,
        "base_strategy": base_strategy,
    }


def generate_test_grid() -> List[Dict]:
    """
    Generate comprehensive test grid for novelty evaluation.

    Covers:
    - Multiple moduli (N ~ 1000, 2000, 3000)
    - All three regimes (HIGH, TRANSITION, LOW SNR)
    - Different M values (1, 4, 8, 16, 32)

    Returns
    -------
    List[Dict]
        Test case grid
    """
    test_cases = []

    # Moduli to test
    moduli = [997, 1009, 1013, 2003, 2017, 3001]

    # Fixed sequence length
    L = 500

    for N in moduli:
        # Find actual orders that exist for this modulus
        # Categorize by regime
        orders_by_regime = {"HIGH": [], "TRANSITION": [], "LOW": []}

        # Sample many bases to find their orders
        for a in range(2, min(N, 200)):
            if np.gcd(a, N) == 1:
                try:
                    r = multiplicative_order(a, N)
                    rho = r / N

                    if rho < 0.146:
                        regime = "HIGH"
                    elif rho < 0.263:
                        regime = "TRANSITION"
                    else:
                        regime = "LOW"

                    if r not in orders_by_regime[regime]:
                        orders_by_regime[regime].append(r)

                except:
                    continue

        # Select one order from each regime (prefer diverse orders)
        selected_orders = []
        for regime in ["HIGH", "TRANSITION", "LOW"]:
            if orders_by_regime[regime]:
                # Pick an order from middle of the list
                idx = len(orders_by_regime[regime]) // 2
                selected_orders.append(orders_by_regime[regime][idx])

        # Generate test cases with these valid orders
        for r in selected_orders:
            # Test different M values
            for M in [1, 4, 8, 16]:
                test_cases.append({"N": N, "r": r, "M": M, "L": L})

    return test_cases


if __name__ == "__main__":
    print("=" * 60)
    print("VRA vs. RPT Novelty Comparison")
    print("=" * 60)

    # Generate test grid
    test_grid = generate_test_grid()
    print(f"\nGenerated test grid: {len(test_grid)} cases")

    # Run comparison
    summary = sweep_grid(
        test_grid,
        base_strategy="random",
        out_json="Data/Novelty/vra_vs_rpt_results.json",
        verbose=True,
    )

    print("\n" + "=" * 60)
    print(f"Comparison complete!")
    print(f"Total cases: {summary['n_cases']}")
    print(f"Time: {summary['elapsed_sec']:.1f}s")
    print(f"Output: {summary['output_file']}")
    print("=" * 60)
