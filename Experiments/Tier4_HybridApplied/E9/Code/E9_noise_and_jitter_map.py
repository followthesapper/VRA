#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E9 — Noise/Jitter Robustness Map
================================

Goal
----
Map VRA precision and recall over a grid of Gaussian *amplitude noise* (σ_amp)
and *phase jitter* (σ_phase), aggregated across HIGH / TRANSITION / LOW SNR regimes.

Pass Criteria
-------------
• TRANS/LOW: precision ≈ 100% over a wide region of (σ_amp, σ_phase)
• HIGH: phase-aligned averaging remains essential (visible advantage)

Outputs
-------
• JSON:  Data/Phase4_Robustness/E9_noise_map.json
• PNG:   Figures/Phase4_Robustness/E9_noise_surface.png

Usage
-----
# Default (three canonical (N,r) regime points)
python Experiments/Tier4_HybridApplied/E9_noise_jitter_map.py

# Custom grid / trials
python Experiments/Tier4_HybridApplied/E9_noise_jitter_map.py \
  --sigma-amp 0.0 0.05 0.1 0.2 0.3 --sigma-phase 0.0 0.05 0.10 0.15 \
  --trials 200 --L 4096 --M 16

# Focus on a single (N:r)
python Experiments/Tier4_HybridApplied/E9_noise_jitter_map.py \
  --pairs 1009:168 --M 8 --L 4096

Notes
-----
• Depends on VRA core utilities (Code/Core/vra_core.py)
• For HIGH-SNR: uses "phase-aligned" bases; others: random same-order bases.
• Generates publication-quality contour plots.
Author: VRA Team (Dylan Vaca et al.)
Date: 2025-10-30
"""

from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import numpy as np, matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# Core Imports
# ---------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "Code" / "VRA"))

from core import (
    multiplicative_order, modular_sequence, phase_embed,
    compute_averaged_spectrum, compute_precision_recall,
    validated_radius, classify_regime
)

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

@dataclass
class RegimeCase:
    N: int
    r: int
    label: str

def default_regime_cases() -> List[RegimeCase]:
    """Canonical test cases across regimes."""
    return [
        RegimeCase(1009, 8, "HIGH"),
        RegimeCase(1009, 168, "TRANSITION"),
        RegimeCase(1009, 504, "LOW"),
    ]

def apply_window(us: np.ndarray, window: str = "hann") -> np.ndarray:
    n = us.shape[0]
    w = np.hanning(n) if window == "hann" else np.ones(n)
    return us * w

def add_noise(us: np.ndarray, sigma_amp: float, sigma_phase: float, rng) -> np.ndarray:
    """Apply Gaussian amplitude noise and phase jitter."""
    if sigma_phase > 0:
        us *= np.exp(1j * rng.normal(0, sigma_phase, size=us.shape))
    if sigma_amp > 0:
        noise = rng.normal(0, sigma_amp, us.shape) + 1j * rng.normal(0, sigma_amp, us.shape)
        us += noise
    return us

def expected_harmonic_bins(Lzp: int, r: int, limit_k=100) -> List[int]:
    return [int(round(k * Lzp / r)) for k in range(1, min(r, limit_k))]

# ---------------------------------------------------------------------
# Core Evaluation
# ---------------------------------------------------------------------

def evaluate_case(N, r, M, L, sigma_amp, sigma_phase, rng, window="hann", zp=4):
    """Evaluate precision/recall for one regime and noise level."""
    _, regime = classify_regime(N, r)
    bases = [a for a in range(2, N) if math.gcd(a, N) == 1 and multiplicative_order(a, N) == r][:M]

    # If we need noise/jitter, we need to manually build sequences
    # Otherwise, use the standard compute_averaged_spectrum
    if sigma_amp > 0 or sigma_phase > 0:
        mag2_list = []
        for a in bases:
            xs = modular_sequence(N, a, 1, L)
            us = add_noise(phase_embed(xs, N), sigma_amp, sigma_phase, rng)
            us = apply_window(us, window)
            spec = np.fft.fft(us, n=L * zp)
            mag2_list.append(np.abs(spec) ** 2)
        avg = np.mean(mag2_list, axis=0)
    else:
        # No noise - use standard VRA
        avg = compute_averaged_spectrum(N, bases, x0=1, length=L, zp=zp, window=window)

    R = validated_radius(L * zp)
    harm = expected_harmonic_bins(L * zp, r)
    m = compute_precision_recall(avg, harm, R)
    return float(m["precision"]), float(m["recall"])

def sweep(cases, M, L, sigma_amp_list, sigma_phase_list, trials, seed=42):
    rng_master = np.random.default_rng(seed)
    out = {"meta": {"M": M, "L": L, "trials": trials,
                    "sigma_amp": sigma_amp_list, "sigma_phase": sigma_phase_list},
           "aggregates": {}}
    for case in cases:
        grid = np.zeros((len(sigma_amp_list), len(sigma_phase_list)))
        for i, sA in enumerate(sigma_amp_list):
            for j, sP in enumerate(sigma_phase_list):
                vals = []
                for _ in range(trials):
                    rng = np.random.default_rng(rng_master.integers(0, 2**31))
                    p, _ = evaluate_case(case.N, case.r, M, L, sA, sP, rng)
                    vals.append(p)
                grid[i, j] = np.mean(vals)
        out["aggregates"][case.label] = grid.tolist()
    return out

# ---------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------

def plot_map(noise_map, out_png="Figures/Phase4_Robustness/E9_noise_surface.png"):
    meta = noise_map["meta"]
    sA, sP = np.array(meta["sigma_amp"]), np.array(meta["sigma_phase"])
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for k, label in enumerate(["HIGH", "TRANSITION", "LOW"]):
        ax = axes[k]
        if label not in noise_map["aggregates"]: continue
        Z = np.array(noise_map["aggregates"][label])
        SA, SP = np.meshgrid(sA, sP, indexing="ij")
        cf = ax.contourf(SA, SP, Z, levels=15)
        plt.colorbar(cf, ax=ax)
        ax.set_title(label)
        ax.set_xlabel("σ_amp")
        ax.set_ylabel("σ_phase")
    fig.suptitle("E9 — VRA Robustness Map (Precision vs Noise/Jitter)", fontsize=14)
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=300)
    plt.close(fig)

# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--M", type=int, default=8)
    p.add_argument("--L", type=int, default=2048)
    p.add_argument("--trials", type=int, default=50)
    p.add_argument("--sigma-amp", type=float, nargs="+",
                   default=[0.0, 0.02, 0.05, 0.1, 0.2, 0.3])
    p.add_argument("--sigma-phase", type=float, nargs="+",
                   default=[0.0, 0.02, 0.05, 0.1, 0.15, 0.2])
    args = p.parse_args()

    noise_map = sweep(default_regime_cases(), args.M, args.L,
                      args.sigma_amp, args.sigma_phase, args.trials)
    Path("Data/Phase4_Robustness").mkdir(parents=True, exist_ok=True)
    with open("Data/Phase4_Robustness/E9_noise_map.json", "w") as f:
        json.dump(noise_map, f, indent=2)
    print("[ok] JSON saved -> Data/Phase4_Robustness/E9_noise_map.json")

    plot_map(noise_map)
    print("[ok] Figure saved -> Figures/Phase4_Robustness/E9_noise_surface.png")

if __name__ == "__main__":
    main()
