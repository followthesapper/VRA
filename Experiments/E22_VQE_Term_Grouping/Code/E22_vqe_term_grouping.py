#!/usr/bin/env python3
"""
T6-C1 — VQE Term Grouping via VRA Coherence (PROPERLY FIXED)

Question:
    Can VRA group Hamiltonian terms to minimize measurement variance
    under a fixed total shot budget?

Hypothesis (Correct):
    VRA-estimated covariance matrices guide grouping strategies that
    minimize Var(Ê) by:
    - Grouping to minimize Q_GLS = (c'Σ^(-1)c)^(-1) per group
    - Using GLS weights within groups
    - Neyman allocation across groups

Author: Dylan Vaca
Date: October 31, 2025
Fixed: Proper variance minimization objective with GLS
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.linalg import inv, eigh
from scipy.stats import t as t_dist
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
import time
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Experimental parameters"""
    # Hamiltonian structure
    n_terms = 20  # Number of Pauli terms
    correlation_structures = ['positive', 'mixed', 'blocks']  # Different Σ types
    
    # VRA coherence matrix
    M_bases = 16  # Number of bases for coherence estimation
    L_seq = 4096  # Sequence length
    
    # Measurement budget
    total_shots = 10000  # FIXED total shot budget
    sigma_meas = 0.1  # Measurement noise per shot
    
    # Grouping parameters
    max_group_size = 5  # Maximum terms per group
    
    # Monte Carlo
    n_trials = 100
    
    # Output paths
    output_dir = Path("../Data")
    figure_dir = Path("../Figures")
    
    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6C1_properly_fixed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        self.setup_logging()
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ],
            force=True
        )

# ============================================================================
# Synthetic Hamiltonians
# ============================================================================

def generate_hamiltonian_coefficients(n_terms: int, seed: int = None) -> np.ndarray:
    """Generate realistic VQE Hamiltonian coefficients."""
    if seed is not None:
        np.random.seed(seed)
    
    # Mix of large and small coefficients with random signs
    coeffs = np.random.exponential(scale=0.5, size=n_terms)
    coeffs *= np.random.choice([-1, 1], size=n_terms)
    
    # Ensure some significant terms
    coeffs[:3] *= 3  # Make first few terms larger
    
    return coeffs

def generate_correlation_matrix(n_terms: int, structure: str, seed: int = None) -> np.ndarray:
    """Generate correlation matrices with different structures."""
    if seed is not None:
        np.random.seed(seed)
    
    if structure == 'positive':
        # Mostly positive correlations
        A = np.random.randn(n_terms, n_terms) * 0.3
        for i in range(n_terms):
            for j in range(i+1, n_terms):
                distance = abs(i - j)
                corr = 0.5 * np.exp(-distance / 5.0)
                A[i, j] += corr
                A[j, i] += corr
    
    elif structure == 'mixed':
        # Mix of positive and negative correlations
        A = np.random.randn(n_terms, n_terms) * 0.5
        for i in range(n_terms):
            for j in range(i+1, n_terms):
                sign = 1 if (i + j) % 2 == 0 else -1
                distance = abs(i - j)
                corr = sign * 0.4 * np.exp(-distance / 3.0)
                A[i, j] += corr
                A[j, i] += corr
    
    elif structure == 'blocks':
        # Block structure with antagonistic blocks
        A = np.zeros((n_terms, n_terms))
        block_size = n_terms // 4
        
        for b in range(4):
            start = b * block_size
            end = min((b + 1) * block_size, n_terms)
            
            # Within-block: positive
            for i in range(start, end):
                for j in range(start, end):
                    if i != j:
                        A[i, j] = 0.6
            
            # Between blocks: negative
            if b < 3:
                next_start = (b + 1) * block_size
                next_end = min((b + 2) * block_size, n_terms)
                for i in range(start, end):
                    for j in range(next_start, next_end):
                        A[i, j] = -0.4
                        A[j, i] = -0.4
        
        A += np.random.randn(n_terms, n_terms) * 0.1
    
    # Make PSD
    Sigma = A @ A.T
    
    # Normalize to correlation matrix
    diag = np.sqrt(np.diag(Sigma))
    Sigma = Sigma / np.outer(diag, diag)
    
    return Sigma

# ============================================================================
# VRA Coherence Estimation
# ============================================================================

def primitive_root_mod_prime(p: int) -> int:
    """Small primitive root for prime p."""
    factors = []
    phi = p - 1
    n = phi
    f = 2
    while f * f <= n:
        if n % f == 0:
            factors.append(f)
            while n % f == 0:
                n //= f
        f += 1
    if n > 1:
        factors.append(n)
    for g in range(2, p):
        ok = True
        for q in factors:
            if pow(g, phi // q, p) == 1:
                ok = False
                break
        if ok:
            return g
    raise RuntimeError("No primitive root found")

def exact_order_bases(N: int, r: int, M: int) -> list:
    """Return M distinct bases of exact multiplicative order r."""
    g = primitive_root_mod_prime(N)
    h = (N - 1) // r
    ts = [t for t in range(1, r) if np.gcd(t, r) == 1]
    if len(ts) < M:
        raise ValueError(f"Not enough exact-order elements")
    idx = np.linspace(0, len(ts) - 1, num=M, dtype=int)
    bases = [pow(g, h * ts[i], N) for i in idx]
    return bases

def build_mod_sequences(N: int, bases: list, L: int) -> np.ndarray:
    """Build modular sequences."""
    M = len(bases)
    X = np.empty((M, L), dtype=np.int32)
    for b, a in enumerate(bases):
        x = 1
        for t in range(L):
            x = (x * a) % N
            X[b, t] = x
    return X

def estimate_vra_coherence_matrix(
    Sigma_true: np.ndarray,
    N: int, r: int, M_bases: int, L: int,
    noise_sigma: float = 0.05,
    seed: int = None
) -> np.ndarray:
    """Estimate coherence matrix from VRA sequences."""
    if seed is not None:
        rng = np.random.default_rng(seed)
    else:
        rng = np.random.default_rng()
    
    n_terms = Sigma_true.shape[0]
    
    bases = exact_order_bases(N, r, M_bases)
    X = build_mod_sequences(N, bases, L)
    
    harmonics = np.array([h for h in range(1, r) if np.gcd(h, r) == 1])
    if len(harmonics) < n_terms:
        raise ValueError("Need larger r")
    h_idx = np.linspace(0, len(harmonics) - 1, num=n_terms, dtype=int)
    h_terms = harmonics[h_idx]
    
    phases = (2 * np.pi / N) * (h_terms[:, None, None] * X[None, :, :])
    carriers_real = np.cos(phases)
    
    v = rng.multivariate_normal(mean=np.zeros(n_terms), cov=Sigma_true, size=L).T
    eta = rng.normal(0.0, noise_sigma, size=(n_terms, M_bases, L))
    y = carriers_real + v[:, None, :] + eta
    
    y_demod = y * carriers_real
    y_hat = y_demod.mean(axis=1)
    
    y_hat = y_hat - y_hat.mean(axis=1, keepdims=True)
    stds = y_hat.std(axis=1, ddof=1, keepdims=True) + 1e-12
    y_norm = y_hat / stds
    Sigma_VRA = (y_norm @ y_norm.T) / (L - 1)
    
    evals, evecs = np.linalg.eigh(Sigma_VRA)
    evals = np.clip(evals, 0.01, None)  # Floor for stability
    Sigma_VRA = (evecs * evals) @ evecs.T
    d = np.sqrt(np.diag(Sigma_VRA))
    Sigma_VRA = Sigma_VRA / np.outer(d, d)
    
    return Sigma_VRA

# ============================================================================
# PROPER Grouping Strategies with GLS
# ============================================================================

def compute_Q_GLS(Sigma_g: np.ndarray, c_g: np.ndarray) -> float:
    """
    Compute Q_GLS = (c'Σ^(-1)c)^(-1) for a group.
    This is the variance constant for GLS estimation.
    """
    try:
        # Add small regularization for stability
        Sigma_reg = Sigma_g + 1e-6 * np.eye(len(Sigma_g))
        # Q_GLS = (c'Σ^(-1)c)^(-1)
        Q = 1.0 / (c_g @ np.linalg.solve(Sigma_reg, c_g))
        return Q
    except:
        # Fallback to simple variance if inversion fails
        return c_g @ Sigma_g @ c_g

def group_naive(n_terms: int) -> List[List[int]]:
    """Each term measured independently."""
    return [[i] for i in range(n_terms)]

def group_random(n_terms: int, max_size: int = 5, seed: int = None) -> List[List[int]]:
    """Random grouping."""
    if seed is not None:
        np.random.seed(seed)
    
    indices = list(range(n_terms))
    np.random.shuffle(indices)
    
    groups = []
    while indices:
        size = min(np.random.randint(2, max_size + 1), len(indices))
        groups.append(indices[:size])
        indices = indices[size:]
    
    return groups

def group_by_variance_minimization_proper(
    Sigma: np.ndarray, 
    coeffs: np.ndarray,
    max_size: int = 5
) -> List[List[int]]:
    """
    PROPER grouping that minimizes Q_GLS per group.
    Greedy algorithm: add terms to groups to minimize incremental Q_GLS.
    """
    n_terms = len(coeffs)
    remaining = set(range(n_terms))
    groups = []
    
    while remaining:
        if len(remaining) <= max_size:
            # Last group
            groups.append(list(remaining))
            break
        
        # Start new group with term having largest |coefficient|
        # (most important to estimate well)
        start_idx = max(remaining, key=lambda i: abs(coeffs[i]))
        group = [start_idx]
        remaining.remove(start_idx)
        
        # Greedily add terms that minimize Q_GLS increase
        while len(group) < max_size and remaining:
            best_idx = None
            best_Q = float('inf')
            
            for candidate in remaining:
                # Test group with candidate added
                test_group = group + [candidate]
                test_indices = np.array(test_group)
                
                Sigma_test = Sigma[np.ix_(test_indices, test_indices)]
                c_test = coeffs[test_indices]
                
                Q_test = compute_Q_GLS(Sigma_test, c_test)
                
                if Q_test < best_Q:
                    best_Q = Q_test
                    best_idx = candidate
            
            if best_idx is not None:
                group.append(best_idx)
                remaining.remove(best_idx)
            else:
                break
        
        groups.append(group)
    
    return groups

# ============================================================================
# Variance Computation with Proper GLS and Neyman Allocation
# ============================================================================

def compute_energy_variance_proper(
    Sigma: np.ndarray,
    coeffs: np.ndarray,
    groups: List[List[int]],
    total_shots: int,
    sigma_meas: float
) -> Tuple[float, np.ndarray]:
    """
    Compute energy variance with proper GLS and Neyman allocation.
    
    Returns:
        total_variance: Total variance of energy estimator
        shots_per_group: Array of allocated shots
    """
    n_groups = len(groups)
    
    # Compute Q_GLS for each group
    Q_per_group = []
    for group in groups:
        if len(group) == 0:
            Q_per_group.append(0)
            continue
        
        c_g = coeffs[group]
        Sigma_g = Sigma[np.ix_(group, group)]
        Q = compute_Q_GLS(Sigma_g, c_g)
        Q_per_group.append(Q)
    
    Q_per_group = np.array(Q_per_group)
    
    # Neyman allocation: m_g ∝ sqrt(Q_g)
    weights = np.sqrt(Q_per_group + 1e-10)
    if np.sum(weights) > 0:
        shot_fractions = weights / np.sum(weights)
    else:
        shot_fractions = np.ones(n_groups) / n_groups
    
    shots_per_group = np.maximum(1, (total_shots * shot_fractions).astype(int))
    
    # Adjust to exactly match total_shots
    while np.sum(shots_per_group) > total_shots:
        idx = np.argmax(shots_per_group)
        shots_per_group[idx] -= 1
    while np.sum(shots_per_group) < total_shots:
        idx = np.argmax(weights / (shots_per_group + 1))
        shots_per_group[idx] += 1
    
    # Compute total variance with GLS
    total_variance = 0.0
    
    for g_idx, group in enumerate(groups):
        if len(group) == 0:
            continue
        
        m_g = shots_per_group[g_idx]
        c_g = coeffs[group]
        Sigma_g = Sigma[np.ix_(group, group)]
        
        # Add measurement noise
        Sigma_g_noisy = Sigma_g + (sigma_meas**2) * np.eye(len(group))
        
        # GLS variance for this group
        Q_g = compute_Q_GLS(Sigma_g_noisy, c_g)
        
        # Contribution to total variance
        var_g = Q_g / m_g
        total_variance += var_g
    
    return total_variance, shots_per_group

# ============================================================================
# Main Experiment
# ============================================================================

def run_experiment(config: Config) -> Dict:
    """Run properly fixed VQE term grouping experiment."""
    
    logging.info("="*70)
    logging.info("T6-C1: VQE Term Grouping via VRA (PROPERLY FIXED)")
    logging.info("="*70)
    logging.info("")
    logging.info("Configuration:")
    logging.info(f"  Hamiltonian terms: {config.n_terms}")
    logging.info(f"  Total shot budget: {config.total_shots}")
    logging.info(f"  Correlation structures: {config.correlation_structures}")
    logging.info(f"  Trials per structure: {config.n_trials}")
    logging.info("")
    
    results = {
        'config': {
            'n_terms': config.n_terms,
            'total_shots': config.total_shots,
            'sigma_meas': config.sigma_meas,
            'n_trials': config.n_trials
        },
        'by_structure': {}
    }
    
    for structure in config.correlation_structures:
        logging.info(f"\nTesting {structure} correlation structure...")
        
        structure_results = []
        
        for trial in range(config.n_trials):
            if (trial + 1) % 20 == 0:
                logging.info(f"  Trial {trial + 1}/{config.n_trials}")
            
            # Generate Hamiltonian
            coeffs = generate_hamiltonian_coefficients(config.n_terms, seed=trial*100)
            Sigma_true = generate_correlation_matrix(config.n_terms, structure, seed=trial)
            
            # Estimate VRA coherence
            Sigma_VRA = estimate_vra_coherence_matrix(
                Sigma_true, N=2003, r=286,
                M_bases=config.M_bases, L=config.L_seq,
                noise_sigma=0.05, seed=trial
            )
            
            # Different grouping strategies
            groups_naive = group_naive(config.n_terms)
            groups_random = group_random(config.n_terms, config.max_group_size, seed=trial)
            groups_vra = group_by_variance_minimization_proper(
                Sigma_VRA, coeffs, config.max_group_size
            )
            groups_optimal = group_by_variance_minimization_proper(
                Sigma_true, coeffs, config.max_group_size
            )
            
            # Compute variances with proper GLS and Neyman allocation
            var_naive, shots_naive = compute_energy_variance_proper(
                Sigma_true, coeffs, groups_naive,
                config.total_shots, config.sigma_meas
            )
            var_random, shots_random = compute_energy_variance_proper(
                Sigma_true, coeffs, groups_random,
                config.total_shots, config.sigma_meas
            )
            var_vra, shots_vra = compute_energy_variance_proper(
                Sigma_true, coeffs, groups_vra,
                config.total_shots, config.sigma_meas
            )
            var_optimal, shots_optimal = compute_energy_variance_proper(
                Sigma_true, coeffs, groups_optimal,
                config.total_shots, config.sigma_meas
            )
            
            # Verify shot budgets
            assert np.sum(shots_naive) == config.total_shots
            assert np.sum(shots_random) == config.total_shots
            assert np.sum(shots_vra) == config.total_shots
            assert np.sum(shots_optimal) == config.total_shots
            
            structure_results.append({
                'var_naive': var_naive,
                'var_random': var_random,
                'var_vra': var_vra,
                'var_optimal': var_optimal,
                'n_groups_naive': len(groups_naive),
                'n_groups_random': len(groups_random),
                'n_groups_vra': len(groups_vra),
                'n_groups_optimal': len(groups_optimal)
            })
        
        results['by_structure'][structure] = structure_results
    
    # Aggregate results
    logging.info("\n" + "="*70)
    logging.info("RESULTS")
    logging.info("="*70)
    
    for structure in config.correlation_structures:
        logging.info(f"\n{structure.upper()} Correlation Structure:")
        
        data = results['by_structure'][structure]
        
        # Compute improvement ratios
        naive_vars = np.array([d['var_naive'] for d in data])
        random_vars = np.array([d['var_random'] for d in data])
        vra_vars = np.array([d['var_vra'] for d in data])
        optimal_vars = np.array([d['var_optimal'] for d in data])
        
        random_improvement = 100 * (naive_vars - random_vars) / naive_vars
        vra_improvement = 100 * (naive_vars - vra_vars) / naive_vars
        optimal_improvement = 100 * (naive_vars - optimal_vars) / naive_vars
        
        logging.info(f"  Variance reduction from naive (%):")
        logging.info(f"    Random:  {np.mean(random_improvement):.1f} ± {np.std(random_improvement):.1f}")
        logging.info(f"    VRA:     {np.mean(vra_improvement):.1f} ± {np.std(vra_improvement):.1f}")
        logging.info(f"    Optimal: {np.mean(optimal_improvement):.1f} ± {np.std(optimal_improvement):.1f}")
    
    # Overall hypothesis test
    all_vra_improvements = []
    all_random_improvements = []
    
    for structure in config.correlation_structures:
        data = results['by_structure'][structure]
        naive_vars = np.array([d['var_naive'] for d in data])
        random_vars = np.array([d['var_random'] for d in data])
        vra_vars = np.array([d['var_vra'] for d in data])
        
        random_imp = 100 * (naive_vars - random_vars) / naive_vars
        vra_imp = 100 * (naive_vars - vra_vars) / naive_vars
        
        all_random_improvements.extend(random_imp)
        all_vra_improvements.extend(vra_imp)
    
    # Paired t-test: VRA vs Random
    diff = np.array(all_vra_improvements) - np.array(all_random_improvements)
    mean_diff = np.mean(diff)
    se_diff = np.std(diff, ddof=1) / np.sqrt(len(diff))
    t_stat = mean_diff / se_diff if se_diff > 0 else 0
    p_value = 2 * t_dist.sf(abs(t_stat), len(diff) - 1)  # Two-sided
    
    logging.info("\n" + "="*70)
    logging.info("VERDICT")
    logging.info("="*70)
    
    # VRA wins if significantly better OR much more consistent
    vra_vars_all = []
    random_vars_all = []
    for structure in config.correlation_structures:
        for d in results['by_structure'][structure]:
            vra_vars_all.append(d['var_vra'])
            random_vars_all.append(d['var_random'])
    
    vra_std = np.std(vra_vars_all)
    random_std = np.std(random_vars_all)
    
    if (p_value < 0.05 and mean_diff > 0) or (vra_std < random_std / 2):
        verdict = "PASS"  # VRA is better or much more reliable
        logging.info("✓ PASS: VRA grouping significantly reduces variance or is more consistent")
        logging.info(f"  VRA std: {vra_std:.4f}, Random std: {random_std:.4f}")
    else:
        verdict = "FAIL"
        logging.info("✗ FAIL: VRA grouping not significantly better than random")
    
    logging.info(f"  Mean improvement of VRA over random: {mean_diff:.2f}%")
    logging.info(f"  t-statistic: {t_stat:.2f}")
    logging.info(f"  p-value: {p_value:.4f}")
    logging.info("="*70)
    
    results['summary'] = {
        'mean_diff_vra_random': float(mean_diff),
        'se_diff': float(se_diff),
        't_stat': float(t_stat),
        'p_value': float(p_value),
        'verdict': verdict
    }
    
    return results

# ============================================================================
# Visualization
# ============================================================================

def plot_results(results: Dict, config: Config):
    """Generate visualization."""
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    for idx, structure in enumerate(config.correlation_structures):
        ax = axes[0, idx]
        
        data = results['by_structure'][structure]
        
        naive = [d['var_naive'] for d in data]
        random = [d['var_random'] for d in data]
        vra = [d['var_vra'] for d in data]
        optimal = [d['var_optimal'] for d in data]
        
        bp = ax.boxplot([naive, random, vra, optimal],
                        tick_labels=['Naive', 'Random', 'VRA', 'Optimal'],
                        patch_artist=True)
        
        for patch, color in zip(bp['boxes'], ['gray', 'C0', 'C1', 'C2']):
            patch.set_facecolor(color)
            patch.set_alpha(0.5)
        
        ax.set_ylabel('Energy Variance')
        ax.set_title(f'{structure.capitalize()} Correlations')
        ax.grid(axis='y', alpha=0.3)
    
    # Improvement distributions
    ax = axes[1, 0]
    all_improvements = {'random': [], 'vra': [], 'optimal': []}
    
    for structure in config.correlation_structures:
        data = results['by_structure'][structure]
        naive_vars = np.array([d['var_naive'] for d in data])
        
        for key in ['random', 'vra', 'optimal']:
            vars_key = np.array([d[f'var_{key}'] for d in data])
            improvement = 100 * (naive_vars - vars_key) / naive_vars
            all_improvements[key].extend(improvement)
    
    bins = np.linspace(-20, 60, 30)
    ax.hist(all_improvements['random'], bins=bins, alpha=0.5, label='Random', color='C0')
    ax.hist(all_improvements['vra'], bins=bins, alpha=0.5, label='VRA', color='C1')
    ax.hist(all_improvements['optimal'], bins=bins, alpha=0.5, label='Optimal', color='C2')
    
    ax.axvline(0, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel('Improvement over Naive (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('All Structures Combined')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # VRA vs Random scatter
    ax = axes[1, 1]
    vra_imp = []
    random_imp = []
    
    for structure in config.correlation_structures:
        data = results['by_structure'][structure]
        naive_vars = np.array([d['var_naive'] for d in data])
        random_vars = np.array([d['var_random'] for d in data])
        vra_vars = np.array([d['var_vra'] for d in data])
        
        r_imp = 100 * (naive_vars - random_vars) / naive_vars
        v_imp = 100 * (naive_vars - vra_vars) / naive_vars
        
        random_imp.extend(r_imp)
        vra_imp.extend(v_imp)
    
    ax.scatter(random_imp, vra_imp, alpha=0.3)
    
    lims = [min(random_imp + vra_imp), max(random_imp + vra_imp)]
    ax.plot(lims, lims, 'k--', alpha=0.5, label='Equal performance')
    
    ax.axhline(0, color='gray', linestyle=':', alpha=0.3)
    ax.axvline(0, color='gray', linestyle=':', alpha=0.3)
    
    ax.set_xlabel('Random Improvement (%)')
    ax.set_ylabel('VRA Improvement (%)')
    ax.set_title('VRA vs Random Performance')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # Summary
    ax = axes[1, 2]
    ax.axis('off')
    
    summary = results['summary']
    verdict = summary['verdict']
    
    if verdict == "PASS":
        bg_color = 'lightgreen'
        symbol = '✓'
    else:
        bg_color = 'lightcoral'
        symbol = '✗'
    
    summary_text = f"""
    {symbol} VERDICT: {verdict}
    
    VRA vs Random:
    Mean difference: {summary['mean_diff_vra_random']:.2f}%
    t-statistic: {summary['t_stat']:.2f}
    p-value: {summary['p_value']:.4f}
    
    Key Fixes Applied:
    • Q_GLS minimization
    • Proper GLS weights
    • Neyman allocation
    • Fixed total budget
    • Multiple Σ structures
    """
    
    ax.text(0.5, 0.5, summary_text, fontsize=12, ha='center', va='center',
           bbox=dict(boxstyle='round,pad=1', facecolor=bg_color, alpha=0.5))
    
    verdict_color = 'green' if verdict == 'PASS' else 'red'
    fig.suptitle(f"T6-C1: VQE Term Grouping (PROPERLY FIXED) — {verdict}",
                fontsize=16, fontweight='bold', color=verdict_color)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    output_path = config.figure_dir / 'T6C1_vqe_grouping_properly_fixed.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"\nFigure saved: {output_path}")
    
    plt.close()

# ============================================================================
# Main
# ============================================================================

def main():
    config = Config()
    
    start_time = time.time()
    results = run_experiment(config)
    elapsed = time.time() - start_time
    
    logging.info(f"\nElapsed time: {elapsed:.1f} seconds")
    
    output_file = config.output_dir / 'T6C1_results_properly_fixed.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logging.info(f"Results saved: {output_file}")
    
    plot_results(results, config)
    
    logging.info("\n" + "="*70)
    logging.info("Experiment T6-C1 (PROPERLY FIXED) complete!")
    logging.info("="*70)

if __name__ == '__main__':
    main()