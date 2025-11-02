#!/usr/bin/env python3
"""
T6-C2 — Differentiable VRA Layer: Generalization Bound

Question:
    Does a VRA-based feature transform preserve class-separability
    under spectral shifts?

Hypothesis:
    For a binary classification task with margin γ_baseline,
    adding a VRA spectral layer should maintain:

        Margin_VRA ≥ Margin_baseline - C·ε

    where ε is the spectral perturbation magnitude and C is a
    bounded constant.

Falsification:
    If Margin_VRA < Margin_baseline - C·ε for small ε, or if
    margin degrades faster than O(ε), the claim is false.

Machine Learning Context:
    This tests whether VRA can serve as a robust feature extractor
    in neural networks, preserving learned decision boundaries even
    when input spectral characteristics drift (e.g., domain shift,
    distributional change).

Author: Dylan Vaca
Date: October 31, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import time
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Experimental parameters"""
    # Data generation
    n_samples_train = 1000
    n_samples_test = 500
    n_features = 64  # Input feature dimension

    # VRA layer parameters
    N_prime = 257  # Small prime for modular arithmetic
    r_fraction = 0.2  # Target order fraction

    # Spectral shift experiment
    epsilon_values = np.array([0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5])

    # Classification task
    noise_std = 0.1  # Label noise
    separation = 2.0  # Class separation in feature space

    # Monte Carlo
    n_trials = 30

    # Output paths
    output_dir = Path("../../Data/Experiments/Tier6/T6C2")
    figure_dir = Path("../../Figures/experiments/Tier6/T6C2")

    def __init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f'T6C2_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        self.setup_logging()

    def setup_logging(self):
        """Configure logging to file and console"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ],
            force=True
        )
        logging.info("="*70)
        logging.info("T6-C2: Differentiable VRA Layer - Generalization Bound")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")


# ============================================================================
# VRA Feature Transform Layer
# ============================================================================

class VRALayer:
    """
    Differentiable VRA-based feature transform.

    Applies modular sequence extraction followed by FFT to input features,
    creating spectral representations that capture multiplicative structure.
    """

    def __init__(self, N: int, r: int, n_features: int):
        """
        Args:
            N: Prime modulus
            r: Target multiplicative order
            n_features: Input feature dimension
        """
        self.N = N
        self.r = r
        self.n_features = n_features

        # Find a few bases with approximate order r
        self.bases = self._find_bases(n_bases=4)

    def _find_bases(self, n_bases: int) -> List[int]:
        """Find bases with order approximately r"""
        bases = []
        attempts = 0
        max_attempts = 10000

        while len(bases) < n_bases and attempts < max_attempts:
            a = np.random.randint(2, self.N)
            if np.gcd(a, self.N) == 1:
                # Quick order check
                if pow(a, self.r, self.N) == 1:
                    bases.append(a)
            attempts += 1

        if len(bases) < n_bases:
            logging.warning(f"Only found {len(bases)}/{n_bases} bases")

        return bases

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Apply VRA spectral transform to input features.

        Args:
            X: (n_samples, n_features) input data

        Returns:
            X_vra: (n_samples, n_features_vra) transformed features
        """
        n_samples = X.shape[0]

        # Map features to modular sequences
        # Use feature values as phase offsets
        X_mod = (X * self.N).astype(int) % self.N

        # For each base, create a sequence and extract spectral features
        features_list = []

        for a in self.bases:
            # Generate modular sequence with feature-dependent phase
            sequences = np.zeros((n_samples, self.n_features), dtype=complex)

            for i in range(n_samples):
                x = 1
                for t in range(self.n_features):
                    x = (x * a) % self.N
                    # Add feature-dependent phase shift
                    phase = 2 * np.pi * ((x + X_mod[i, t]) % self.N) / self.N
                    sequences[i, t] = np.exp(1j * phase)

            # FFT to extract spectral features
            fft_features = np.fft.fft(sequences, axis=1)

            # Take magnitude at key frequencies (real-valued features)
            # Focus on frequencies around f = n_features / r
            f_fundamental = self.n_features // self.r
            freq_range = max(1, f_fundamental // 4)

            freq_slice = slice(
                max(0, f_fundamental - freq_range),
                min(self.n_features // 2, f_fundamental + freq_range)
            )

            mag_features = np.abs(fft_features[:, freq_slice])
            features_list.append(mag_features)

        # Concatenate features from all bases
        X_vra = np.concatenate(features_list, axis=1)

        return X_vra


# ============================================================================
# Data Generation
# ============================================================================

def generate_binary_classification_data(
    n_samples: int,
    n_features: int,
    separation: float,
    noise_std: float,
    seed: int = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic binary classification data with spectral structure.

    Args:
        n_samples: Number of samples
        n_features: Feature dimension
        separation: Distance between class centroids
        noise_std: Label noise standard deviation
        seed: Random seed

    Returns:
        X: (n_samples, n_features) features
        y: (n_samples,) binary labels
    """
    if seed is not None:
        np.random.seed(seed)

    # Class 0: Low-frequency spectral content
    # Class 1: High-frequency spectral content

    n_per_class = n_samples // 2

    # Class 0: Smooth signals (low freq)
    t = np.linspace(0, 2*np.pi, n_features)
    freq_0 = 1.0
    X_0 = np.array([
        np.sin(freq_0 * t + np.random.uniform(0, 2*np.pi))
        + noise_std * np.random.randn(n_features)
        for _ in range(n_per_class)
    ])
    X_0 -= separation / 2

    # Class 1: Oscillatory signals (high freq)
    freq_1 = 5.0
    X_1 = np.array([
        np.sin(freq_1 * t + np.random.uniform(0, 2*np.pi))
        + noise_std * np.random.randn(n_features)
        for _ in range(n_per_class)
    ])
    X_1 += separation / 2

    # Combine
    X = np.vstack([X_0, X_1])
    y = np.concatenate([np.zeros(n_per_class), np.ones(n_per_class)])

    # Shuffle
    perm = np.random.permutation(n_samples)
    X = X[perm]
    y = y[perm]

    return X, y


def apply_spectral_shift(X: np.ndarray, epsilon: float) -> np.ndarray:
    """
    Apply spectral perturbation to data.

    Shifts frequency content by ε in Fourier domain.

    Args:
        X: (n_samples, n_features) input data
        epsilon: Shift magnitude

    Returns:
        X_shifted: Perturbed data
    """
    X_fft = np.fft.fft(X, axis=1)
    n_features = X.shape[1]

    # Circular shift in frequency domain
    shift_bins = int(epsilon * n_features)
    if shift_bins > 0:
        X_fft = np.roll(X_fft, shift_bins, axis=1)

    X_shifted = np.fft.ifft(X_fft, axis=1).real

    return X_shifted


# ============================================================================
# Margin Computation
# ============================================================================

def compute_margin(
    clf: LogisticRegression,
    X: np.ndarray,
    y: np.ndarray
) -> float:
    """
    Compute classification margin (average distance from decision boundary).

    Args:
        clf: Trained classifier
        X: Features
        y: Labels

    Returns:
        margin: Average signed distance to boundary (normalized)
    """
    # Decision function gives signed distance
    decision_values = clf.decision_function(X)

    # Correct predictions have positive margin, errors have negative
    margins = decision_values * (2 * y - 1)  # Convert y∈{0,1} to {-1,+1}

    # Return mean margin
    return float(np.mean(margins))


# ============================================================================
# Experiment Execution
# ============================================================================

def run_margin_preservation_experiment(config: Config) -> List[Dict]:
    """
    Test margin preservation under spectral shift.

    For each ε:
        1. Generate training data
        2. Train baseline classifier (direct features)
        3. Train VRA classifier (VRA-transformed features)
        4. Apply spectral shift ε to test data
        5. Measure margins on shifted test data
        6. Compare Margin_VRA vs Margin_baseline

    Returns:
        results: List of measurements for each (ε, trial)
    """
    logging.info("")
    logging.info("Starting margin preservation experiment...")
    logging.info(f"ε values: {config.epsilon_values}")
    logging.info(f"Trials: {config.n_trials}")
    logging.info(f"Samples: train={config.n_samples_train}, test={config.n_samples_test}")
    logging.info("")

    # Initialize VRA layer
    N = config.N_prime
    r = int(config.r_fraction * N)

    # Find divisor of N-1 close to r
    for candidate in range(r, r + 50):
        if (N - 1) % candidate == 0:
            r = candidate
            break

    logging.info(f"VRA layer: N={N}, r={r} (ρ={r/N:.4f})")

    results = []
    start_time = time.time()

    total_configs = len(config.epsilon_values) * config.n_trials
    config_idx = 0

    for epsilon in config.epsilon_values:
        logging.info(f"\n{'='*60}")
        logging.info(f"Testing ε = {epsilon:.3f}")
        logging.info('='*60)

        margins_baseline = []
        margins_vra = []
        acc_baseline = []
        acc_vra = []

        for trial in range(config.n_trials):
            config_idx += 1
            elapsed = time.time() - start_time
            rate = config_idx / elapsed if elapsed > 0 else 0
            eta = (total_configs - config_idx) / rate if rate > 0 else 0

            # Generate data
            X_train, y_train = generate_binary_classification_data(
                config.n_samples_train,
                config.n_features,
                config.separation,
                config.noise_std,
                seed=trial
            )

            X_test, y_test = generate_binary_classification_data(
                config.n_samples_test,
                config.n_features,
                config.separation,
                config.noise_std,
                seed=trial + 10000
            )

            # Apply spectral shift to test data
            X_test_shifted = apply_spectral_shift(X_test, epsilon)

            # === Baseline Classifier ===
            clf_baseline = LogisticRegression(max_iter=1000, random_state=trial)
            clf_baseline.fit(X_train, y_train)

            margin_baseline = compute_margin(clf_baseline, X_test_shifted, y_test)
            y_pred_baseline = clf_baseline.predict(X_test_shifted)
            acc_base = accuracy_score(y_test, y_pred_baseline)

            # === VRA Classifier ===
            vra_layer = VRALayer(N, r, config.n_features)

            X_train_vra = vra_layer.transform(X_train)
            X_test_vra = vra_layer.transform(X_test_shifted)

            clf_vra = LogisticRegression(max_iter=1000, random_state=trial)
            clf_vra.fit(X_train_vra, y_train)

            margin_vra = compute_margin(clf_vra, X_test_vra, y_test)
            y_pred_vra = clf_vra.predict(X_test_vra)
            acc_vr = accuracy_score(y_test, y_pred_vra)

            margins_baseline.append(margin_baseline)
            margins_vra.append(margin_vra)
            acc_baseline.append(acc_base)
            acc_vra.append(acc_vr)

            if trial % 10 == 0 or trial == config.n_trials - 1:
                logging.info(
                    f"  Trial {trial+1}/{config.n_trials} | "
                    f"Margin: base={margin_baseline:.4f}, vra={margin_vra:.4f} | "
                    f"Acc: base={acc_base:.3f}, vra={acc_vr:.3f} | "
                    f"ETA: {eta/60:.1f}m"
                )

        # Aggregate statistics
        margin_base_mean = float(np.mean(margins_baseline))
        margin_base_std = float(np.std(margins_baseline))
        margin_vra_mean = float(np.mean(margins_vra))
        margin_vra_std = float(np.std(margins_vra))

        acc_base_mean = float(np.mean(acc_baseline))
        acc_vra_mean = float(np.mean(acc_vra))

        margin_degradation = margin_base_mean - margin_vra_mean

        logging.info(f"\nε={epsilon:.3f} Summary:")
        logging.info(f"  Margin_baseline: {margin_base_mean:.4f} ± {margin_base_std:.4f}")
        logging.info(f"  Margin_VRA:      {margin_vra_mean:.4f} ± {margin_vra_std:.4f}")
        logging.info(f"  Degradation:     {margin_degradation:+.4f}")
        logging.info(f"  Acc_baseline:    {acc_base_mean:.3f}")
        logging.info(f"  Acc_VRA:         {acc_vra_mean:.3f}")

        results.append({
            'epsilon': float(epsilon),
            'margin_baseline_mean': margin_base_mean,
            'margin_baseline_std': margin_base_std,
            'margin_vra_mean': margin_vra_mean,
            'margin_vra_std': margin_vra_std,
            'margin_degradation': margin_degradation,
            'acc_baseline_mean': acc_base_mean,
            'acc_vra_mean': acc_vra_mean,
            'margins_baseline': margins_baseline,
            'margins_vra': margins_vra
        })

    elapsed = time.time() - start_time
    logging.info(f"\nExperiment complete: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    return results


# ============================================================================
# Analysis & Plotting
# ============================================================================

def analyze_margin_bound(results: List[Dict], config: Config):
    """
    Test hypothesis: Margin_VRA ≥ Margin_baseline - C·ε

    Fit linear degradation model and assess if bound holds.
    """
    logging.info("")
    logging.info("="*70)
    logging.info("MARGIN BOUND ANALYSIS: Margin_VRA ≥ Margin_baseline - C·ε")
    logging.info("="*70)

    epsilon_vals = np.array([r['epsilon'] for r in results])
    degradation_vals = np.array([r['margin_degradation'] for r in results])

    # Fit degradation model: Δmargin = C·ε + b
    slope, intercept, r_value, p_value, std_err = linregress(epsilon_vals, degradation_vals)
    r_squared = r_value**2

    logging.info(f"\nLinear fit: Δmargin = {slope:.4f}·ε + {intercept:.4f}")
    logging.info(f"  R² = {r_squared:.4f}, p = {p_value:.2e}")
    logging.info(f"  Degradation constant C ≈ {slope:.4f}")

    # Check if degradation is bounded
    if slope > 0 and intercept < 0.05:
        logging.info(f"\nVERDICT: PASS — Margin degradation is linear and bounded")
        logging.info(f"  Margin_VRA ≥ Margin_baseline - {slope:.4f}·ε")
    elif slope > 0:
        logging.info(f"\nVERDICT: PARTIAL — Linear degradation but with offset")
        logging.info(f"  Constant offset b={intercept:.4f} suggests systematic bias")
    else:
        logging.info(f"\nVERDICT: FAIL — No consistent degradation pattern")

    return {
        'slope': float(slope),
        'intercept': float(intercept),
        'r_squared': float(r_squared),
        'p_value': float(p_value)
    }


def plot_results(results: List[Dict], fit: Dict, config: Config):
    """Generate publication-quality figures"""
    logging.info("")
    logging.info("Generating figures...")

    epsilon_vals = np.array([r['epsilon'] for r in results])
    margin_base = np.array([r['margin_baseline_mean'] for r in results])
    margin_vra = np.array([r['margin_vra_mean'] for r in results])
    margin_base_std = np.array([r['margin_baseline_std'] for r in results])
    margin_vra_std = np.array([r['margin_vra_std'] for r in results])
    degradation = np.array([r['margin_degradation'] for r in results])

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    # Panel 1: Margins vs ε
    ax = axes[0]
    ax.errorbar(epsilon_vals, margin_base, yerr=margin_base_std,
                fmt='o-', label='Baseline', capsize=4, alpha=0.7)
    ax.errorbar(epsilon_vals, margin_vra, yerr=margin_vra_std,
                fmt='s-', label='VRA Layer', capsize=4, alpha=0.7)
    ax.set_xlabel('Spectral shift ε')
    ax.set_ylabel('Classification margin')
    ax.set_title('Margin Preservation Under Spectral Shift')
    ax.legend()
    ax.grid(alpha=0.3)

    # Panel 2: Degradation with linear fit
    ax = axes[1]
    ax.plot(epsilon_vals, degradation, 'o', label='Observed', markersize=8, alpha=0.7)

    # Plot fit line
    eps_range = np.linspace(0, epsilon_vals[-1], 100)
    deg_fit = fit['slope'] * eps_range + fit['intercept']
    ax.plot(eps_range, deg_fit, '--', alpha=0.6,
            label=f"Fit: Δ={fit['slope']:.3f}·ε + {fit['intercept']:.3f} (R²={fit['r_squared']:.3f})")

    ax.axhline(0, color='k', linestyle=':', alpha=0.3)
    ax.set_xlabel('Spectral shift ε')
    ax.set_ylabel('Margin degradation\n(Baseline - VRA)')
    ax.set_title('Margin Degradation Rate')
    ax.legend()
    ax.grid(alpha=0.3)

    fig.suptitle('T6-C2: VRA Layer Generalization Bound', fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_path = config.figure_dir / 'T6C2_margin_preservation.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"Figure saved: {output_path}")
    plt.close()


# ============================================================================
# Main
# ============================================================================

def main():
    """Execute T6-C2 experiment"""
    config = Config()

    # Run experiment
    start_time = time.time()
    results = run_margin_preservation_experiment(config)
    elapsed = time.time() - start_time

    # Save raw data
    output_file = config.output_dir / 'T6C2_results.json'
    with open(output_file, 'w') as f:
        json.dump({'results': results}, f, indent=2)
    logging.info(f"\nData saved: {output_file}")

    # Analyze margin bound
    fit = analyze_margin_bound(results, config)

    # Generate plots
    plot_results(results, fit, config)

    # Final summary
    logging.info("")
    logging.info("="*70)
    logging.info("T6-C2 COMPLETE")
    logging.info("="*70)
    logging.info(f"Total runtime: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    logging.info(f"Configurations tested: {len(results)}")
    logging.info(f"Hypothesis: Margin_VRA ≥ Margin_baseline - C·ε")
    logging.info(f"Degradation constant: C ≈ {fit['slope']:.4f}")
    logging.info(f"Fit quality: R² = {fit['r_squared']:.4f}")

    if fit['slope'] > 0 and fit['r_squared'] > 0.7 and abs(fit['intercept']) < 0.1:
        logging.info("VERDICT: PASS — Bounded degradation confirmed")
    elif fit['slope'] > 0 and fit['r_squared'] > 0.5:
        logging.info("VERDICT: PARTIAL — Degradation bounded but noisy")
    else:
        logging.info("VERDICT: FAIL — No consistent bound")
    logging.info("="*70)


if __name__ == '__main__':
    main()
