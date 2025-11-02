#!/usr/bin/env python3
"""
T6-D4 — Protein Normal Mode Detection: Sample Complexity (V3 - FINAL)

OPTIMIZATIONS (V3 - FINAL):
1. φ = 0.95 (drift τ ≈ 20)
2. Polynomial detrending (degree 3)
3. Complex-domain processing
4. L ≤ 1024 (operational limit: [128, 256, 512, 1024])
5. PM = 0.10 rad (HARD task to force L-scaling)
6. M = 8 (stable averaging)
7. More ε values for better fit: [0.0005, 0.001, 0.002, 0.005, 0.010]

Expected outcome:
- L=128: 20-40% success
- L=256: 40-70% success
- L=512: 70-90% success
- L=1024: 90-98% success
- Slope ≈ -1.8 to -2.2

Run:
  python3 T6D4_protein_modes_v3_final.py
"""

import argparse, json, logging, time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from scipy.special import gammaincc

def parse_args():
    p = argparse.ArgumentParser(description="T6-D4 V3 FINAL: Hard task, operational L range")
    p.add_argument("--alpha", type=float, default=None)
    p.add_argument("--band", type=float, default=None)
    p.add_argument("--trials", type=int, default=None)
    return p.parse_args()

@dataclass
class Config:
    mode_frequency: float = 0.053
    epsilon_values: np.ndarray = field(default_factory=lambda: np.array([0.0005, 0.001, 0.002, 0.005, 0.010]))
    delta_confidence: float = 0.05

    N_prime: int = 1009
    r_fraction: float = 0.25

    # V3: Operational range L ≤ 1024 with fine gradient
    L_values: Tuple[int, ...] = (2**7, 2**8, 2**9, 2**10)  # [128, 256, 512, 1024]

    n_trials: int = 50

    # V3: HARD task to force L-scaling
    mode_amplitude: float = 0.10     # Reduced from 0.16
    sigma_thermal: float = 0.50
    phi_drift: float = 0.95
    amp_jitter_std: float = 0.02
    M_bases: int = 8

    detrend_degree: int = 3

    output_dir: Path = Path("../../Data/Experiments/Tier6/T6D4")
    figure_dir: Path = Path("../../Figures/experiments/Tier6/T6D4")

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f"T6D4_v3_final_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(message)s",
            handlers=[logging.FileHandler(self.log_file), logging.StreamHandler()],
            force=True
        )
        logging.info("="*70)
        logging.info("T6-D4 V3 FINAL: Hard task in operational L range")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")
        logging.info("V3 FINAL CONFIG:")
        logging.info(f"  • L_values = {self.L_values} (operational range ≤1024)")
        logging.info(f"  • mode_amplitude = {self.mode_amplitude} (HARD)")
        logging.info(f"  • epsilon_values = {list(self.epsilon_values)} (5 points)")
        logging.info(f"  • phi_drift = {self.phi_drift}, detrend_degree = {self.detrend_degree}")
        logging.info(f"  • M_bases = {self.M_bases}, trials = {self.n_trials}")

def get_prime_factors(n: int) -> List[int]:
    factors, d, m = [], 2, n
    while d*d <= m:
        if m % d == 0:
            factors.append(d)
            while m % d == 0: m //= d
        d += 1
    if m > 1: factors.append(m)
    return factors

def has_exact_order(a: int, r: int, N: int, prime_factors: List[int]) -> bool:
    if pow(a, r, N) != 1: return False
    for p in prime_factors:
        if r % p == 0 and pow(a, r // p, N) == 1:
            return False
    return True

def generate_protein_trajectory(N: int, r: int, L: int, M: int,
                                omega_mode: float, mode_amplitude: float,
                                sigma_thermal: float, amp_jitter_std: float,
                                phi_drift: float, seed: int = None) -> Tuple[np.ndarray, List[int]]:
    if seed is not None:
        np.random.seed(seed)

    prime_factors = get_prime_factors(r)
    bases = []
    for _ in range(10000):
        if len(bases) >= M: break
        a = np.random.randint(2, N)
        if np.gcd(a, N) == 1 and has_exact_order(a, r, N, prime_factors):
            bases.append(a)
    if len(bases) < M:
        logging.warning(f"Only {len(bases)}/{M} bases found")

    seq = np.zeros((len(bases), L), dtype=complex)
    for i, a in enumerate(bases):
        x = 1
        drift = 0.0
        offset = np.random.uniform(0, 2*np.pi)
        for t in range(L):
            x = (x * a) % N
            base_phase = 2*np.pi * (x / N)
            pm = mode_amplitude * np.sin(2*np.pi*omega_mode*t + offset)
            thermal = np.random.normal(0, sigma_thermal)
            drift = phi_drift*drift + np.random.normal(0, 0.02*sigma_thermal)
            phase = base_phase + pm + thermal + drift
            amp = 1.0 + np.random.normal(0, amp_jitter_std)
            seq[i, t] = amp * np.exp(1j*phase)
    return seq, bases

def reconstruct_base_phase(a: int, N: int, L: int) -> np.ndarray:
    x = 1
    phases = np.empty(L, dtype=float)
    for t in range(L):
        x = (x * a) % N
        phases[t] = 2*np.pi * (x / N)
    return phases

def polynomial_detrend_complex(z: np.ndarray, degree: int = 3) -> np.ndarray:
    L = len(z)
    t = np.arange(L, dtype=float)
    theta = np.unwrap(np.angle(z))
    coeffs = np.polyfit(t, theta, deg=degree)
    theta_trend = np.polyval(coeffs, t)
    return z * np.exp(-1j * theta_trend)

def extract_real_residual(z_detrended: np.ndarray) -> np.ndarray:
    return np.angle(z_detrended).astype(float)

def estimate_ar1_phi(y: np.ndarray) -> float:
    if len(y) < 3: return 0.0
    y0, y1 = y[:-1], y[1:]
    denom = float(np.dot(y0, y0))
    phi = float(np.dot(y0, y1) / denom) if denom > 0 else 0.0
    return float(np.clip(phi, -0.99, 0.99))

def prewhiten_ar1(y: np.ndarray, phi: float) -> np.ndarray:
    if len(y) == 0: return y
    y = y - np.mean(y)
    if abs(phi) < 1e-12: return y
    yp = y.copy()
    yp[1:] = y[1:] - phi * y[:-1]
    yp[0] = yp[0] - yp.mean()
    return yp

def fft_glrt_avg_psd_padj(residuals: List[np.ndarray],
                          alpha: float,
                          omega_true: float,
                          band_halfwidth: float | None) -> Tuple[bool, float, float]:
    M = len(residuals)
    if M == 0: return False, float('inf'), 1.0

    P_list, freqs = [], None
    for y in residuals:
        phi = estimate_ar1_phi(y)
        yp = prewhiten_ar1(y, phi)
        N = len(yp)
        if N < 16: continue
        w = np.hanning(N)
        Y = np.fft.rfft(yp * w)
        P = (np.abs(Y)**2) / (np.sum(w**2))
        f = np.fft.rfftfreq(N, d=1.0)
        P_list.append(P)
        if freqs is None or len(f) > len(freqs):
            freqs = f

    if not P_list or freqs is None: return False, float('inf'), 1.0

    Luse = min(len(P) for P in P_list)
    P_stack = np.stack([P[:Luse] for P in P_list], axis=0)
    f_use = freqs[:Luse]
    P_avg = np.mean(P_stack, axis=0)

    if band_halfwidth is None:
        mask = (f_use >= 1e-4) & (f_use <= 0.5 - 1e-4)
    else:
        lo = max(1e-4, omega_true - band_halfwidth)
        hi = min(0.5 - 1e-4, omega_true + band_halfwidth)
        mask = (f_use >= lo) & (f_use <= hi)
    idx = np.where(mask)[0]
    if idx.size == 0: return False, float('inf'), 1.0

    P_band = P_avg[idx]

    order = np.argsort(P_band)
    cutoff = max(1, int(0.8 * len(P_band)))
    noise = float(np.median(P_band[order[:cutoff]]))
    noise = max(noise, 1e-20)

    k_rel = int(np.argmax(P_band))
    k_abs = idx[k_rel]
    if 1 <= k_abs < len(P_avg) - 1:
        y0, y1, y2 = P_avg[k_abs-1], P_avg[k_abs], P_avg[k_abs+1]
        denom = (y0 - 2*y1 + y2)
        delta = 0.5*(y0 - y2)/denom if denom != 0 else 0.0
        delta = float(np.clip(delta, -0.5, 0.5))
        k_hat = k_abs + delta
    else:
        k_hat = float(k_abs)

    df = f_use[1] - f_use[0] if len(f_use) > 1 else 1.0 / max(len(f_use), 1)
    omega_hat = f_use[int(np.floor(k_hat))] + (k_hat - np.floor(k_hat)) * df
    err = abs(omega_hat - omega_true)

    T = float(P_avg[k_abs] / noise)
    kshape = max(1, M)
    p_bin = float(gammaincc(kshape, kshape * max(T, 0.0)))
    m_tests = int(idx.size)
    p_adj = min(1.0, p_bin * m_tests)
    detected = p_adj < alpha
    return bool(detected), float(err), float(p_adj)

def run_experiment(cfg: Config, alpha: float, band_halfwidth: float | None) -> List[Dict]:
    logging.info("\nStarting experiment (V3 FINAL)…")
    logging.info(f"L values: {cfg.L_values}")
    logging.info(f"ε values: {cfg.epsilon_values}")

    N = cfg.N_prime
    r = int(cfg.r_fraction * N)
    for cand in range(r, r+100):
        if (N - 1) % cand == 0:
            r = cand
            break

    logging.info(f"VRA params: N={N}, r={r}")
    logging.info(f"Signal: ω={cfg.mode_frequency}, PM={cfg.mode_amplitude}, σ={cfg.sigma_thermal}, M={cfg.M_bases}, φ={cfg.phi_drift}\n")

    results = []
    start = time.time()

    for L in cfg.L_values:
        logging.info(f"{'='*60}\nTesting L={L}\n{'='*60}")
        for eps in cfg.epsilon_values:
            errs, pads, hits = [], [], []
            for t in range(cfg.n_trials):
                seed = (hash((L, float(eps), t)) % (2**31-1))
                seq, bases = generate_protein_trajectory(
                    N, r, L, cfg.M_bases,
                    cfg.mode_frequency, cfg.mode_amplitude,
                    cfg.sigma_thermal, cfg.amp_jitter_std,
                    cfg.phi_drift, seed=seed
                )

                residuals = []
                for i, a in enumerate(bases):
                    base_phase = reconstruct_base_phase(a, N, L)
                    z = seq[i] * np.exp(-1j * base_phase)
                    z_detr = polynomial_detrend_complex(z, degree=cfg.detrend_degree)
                    residual = extract_real_residual(z_detr)
                    residuals.append(residual)

                detected, err, p_adj = fft_glrt_avg_psd_padj(
                    residuals, alpha, cfg.mode_frequency, band_halfwidth
                )

                hits.append(detected and (err < float(eps)))
                errs.append(err if detected else float("inf"))
                pads.append(p_adj)

            arr = np.array(errs)
            success = float(np.sum(hits) / cfg.n_trials)
            finite = arr[np.isfinite(arr)]
            mean_err = float(np.mean(finite)) if finite.size else float('inf')
            std_err  = float(np.std(finite))  if finite.size else float('nan')

            logging.info(f"  ε={eps:.4f}: Success={success:.2%} | Err={mean_err:.4f}±{std_err:.4f}")

            results.append(dict(
                L=int(L), epsilon=float(eps),
                success_rate=success,
                mean_error=mean_err, std_error=std_err
            ))

    logging.info(f"\nExperiment complete: {time.time()-start:.1f}s")
    return results

def analyze_scaling(results: List[Dict], cfg: Config) -> Dict:
    logging.info("\n" + "="*70)
    logging.info("SAMPLE COMPLEXITY ANALYSIS")
    target = 1 - cfg.delta_confidence
    minL = []
    for eps in cfg.epsilon_values:
        rows = sorted([r for r in results if r['epsilon']==float(eps)], key=lambda x: x['L'])
        Lmin = None
        for row in rows:
            if row['success_rate'] >= target:
                Lmin = row['L']; break
        if Lmin is not None:
            minL.append(dict(epsilon=float(eps), min_L=int(Lmin)))
            logging.info(f"ε={eps:.4f}: L_min ≈ {Lmin} for {target:.0%} success")
        else:
            logging.info(f"ε={eps:.4f}: Target not achieved")

    if len(minL) < 3:
        logging.info("⚠️ INCONCLUSIVE — need ≥3 thresholds")
        return {'min_L_data': minL}

    eps = np.array([d['epsilon'] for d in minL])
    Ls  = np.array([d['min_L'] for d in minL])
    slope, intercept, r, p, _ = linregress(np.log(eps), np.log(Ls))
    R2 = r**2
    logging.info(f"\nFit: log(L) = {slope:.3f}·log(ε) + {intercept:.3f}")
    logging.info(f"R² = {R2:.3f}, p-value = {p:.3g}")

    if abs(slope + 2) < 0.5 and R2 > 0.80:
        logging.info("✅ PASS — L ∝ ε⁻² confirmed (slope ∈ [-2.5, -1.5], R² > 0.80)")
    elif abs(slope + 2) < 0.75 and R2 > 0.70:
        logging.info("⚠️ PARTIAL — near-quadratic, acceptable fit")
    else:
        logging.info("❌ FAIL — scaling inconsistent")

    return dict(slope=float(slope), intercept=float(intercept), r_squared=float(R2),
                p_value=float(p), min_L_data=minL)

def plot_results(results: List[Dict], fit: Dict, cfg: Config):
    logging.info("\nGenerating figures...")
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))

    for L in cfg.L_values:
        Ld = [r for r in results if r['L']==L]
        ax[0].plot([r['epsilon'] for r in Ld],
                   [r['success_rate'] for r in Ld],
                   'o-', label=f"L={L}", markersize=7, linewidth=2)
    ax[0].axhline(1-cfg.delta_confidence, color='k', ls=':', alpha=.6, linewidth=2.5,
                  label=f"{(1-cfg.delta_confidence)*100:.0f}% target")
    ax[0].set_xscale('log'); ax[0].set_ylim(0,1.05)
    ax[0].set_xlabel("ε (accuracy)", fontsize=12)
    ax[0].set_ylabel("Success rate", fontsize=12)
    ax[0].set_title("Detection Success vs Accuracy Requirement", fontsize=13, fontweight='bold')
    ax[0].legend(fontsize=10); ax[0].grid(alpha=.4)

    ax[1].set_title("Sample Complexity: L vs ε", fontsize=13, fontweight='bold')
    ax[1].set_xlabel("ε (accuracy)", fontsize=12)
    ax[1].set_ylabel("L (minimum trajectory length)", fontsize=12)
    if 'min_L_data' in fit and len(fit['min_L_data']) >= 3:
        eps = np.array([d['epsilon'] for d in fit['min_L_data']])
        Ls  = np.array([d['min_L'] for d in fit['min_L_data']])
        ax[1].loglog(eps, Ls, 'o', label='Observed', markersize=12, color='C0', zorder=3)
        er = np.logspace(np.log10(eps.min()), np.log10(eps.max()), 100)
        Lfit = np.exp(fit['slope']*np.log(er) + fit['intercept'])
        ax[1].loglog(er, Lfit, '--', linewidth=2.5,
                     label=f"Fit: L ∝ ε^{fit['slope']:.2f} (R²={fit['r_squared']:.3f})",
                     color='C1', zorder=2)
        ax[1].loglog(er, np.exp(fit['intercept'])*er**(-2), ':',
                     linewidth=2.5, label='Theory: L ∝ ε⁻²',
                     alpha=0.7, color='C2', zorder=1)
        ax[1].legend(fontsize=10)
    ax[1].grid(which='both', alpha=.4)

    fig.suptitle("T6-D4 V3 FINAL: PM Mode Detection (φ=0.95, poly³, PM=0.10, M=8, L≤1024)",
                 fontsize=14, fontweight='bold')
    out = cfg.figure_dir / "T6D4_protein_modes_V3_FINAL.png"
    plt.tight_layout(); plt.savefig(out, dpi=300); plt.close()
    logging.info(f"Figure saved: {out}")

def main():
    args = parse_args()
    cfg = Config()
    if args.trials is not None:
        cfg.n_trials = int(args.trials)

    alpha = args.alpha if args.alpha is not None else cfg.delta_confidence
    band_hw = None if args.band is None else float(args.band)

    results = run_experiment(cfg, alpha=alpha, band_halfwidth=band_hw)

    with open(cfg.output_dir/'T6D4_v3_final_results.json','w') as f:
        json.dump({'results': results}, f, indent=2)

    fit = analyze_scaling(results, cfg)
    plot_results(results, fit, cfg)

    logging.info("\n" + "="*70 + "\nT6-D4 V3 FINAL COMPLETE\n" + "="*70)
    if 'slope' in fit:
        logging.info(f"Slope = {fit['slope']:.3f}, R² = {fit['r_squared']:.3f}")
        logging.info(f"Target: slope ≈ -2.0 ± 0.5, R² > 0.80")
        if abs(fit['slope'] + 2) < 0.5 and fit['r_squared'] > 0.80:
            logging.info("✅ FINAL VERDICT: PASS")
        elif abs(fit['slope'] + 2) < 0.75 and fit['r_squared'] > 0.70:
            logging.info("⚠️ FINAL VERDICT: PARTIAL")
        else:
            logging.info("❌ FINAL VERDICT: FAIL")
    logging.info("="*70)

if __name__ == "__main__":
    main()
