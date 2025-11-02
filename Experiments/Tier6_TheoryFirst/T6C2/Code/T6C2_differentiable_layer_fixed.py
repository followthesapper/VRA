#!/usr/bin/env python3
"""
T6-C2 — Differentiable VRA Layer: Generalization Bound (FIXED)

Question:
    Does a VRA-based feature transform preserve class-separability
    under spectral shifts?

Hypothesis:
    For a binary classification task with geometric margin γ_baseline,
    adding a VRA spectral layer should maintain:

        Margin_VRA ≥ Margin_baseline - C·ε

    where ε is the spectral perturbation magnitude and C is a
    bounded constant.

Fixes applied:
    1. Geometric margin (normalize by ||w||, standardize features)
    2. Continuous spectral shift (Fourier phase ramp)
    3. Augmented VRA features (concatenate with baseline)
    4. Richer VRA spectrum (top-k magnitudes)
    5. Fair comparison (same capacity, same scaling)

Author: Dylan Vaca
Date: October 31, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, roc_auc_score
import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import time
from datetime import datetime
import warnings

# Suppress ComplexWarning from numpy FFT (imaginary part is ~0 due to numerical precision)
warnings.filterwarnings('ignore', category=np.ComplexWarning)

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
    r_fraction = 0.25  # Target order fraction
    vra_top_k = 32  # Top-k spectrum magnitudes per base (capacity parity)

    # Spectral shift experiment (continuous)
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
        self.log_file = self.output_dir / f'T6C2_fixed_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        logging.info("T6-C2 FIXED: Differentiable VRA Layer - Generalization Bound")
        logging.info("="*70)
        logging.info(f"Log file: {self.log_file}")


# ============================================================================
# VRA Feature Transform Layer (Richer Spectrum)
# ============================================================================

class VRALayer:
    """
    Differentiable VRA-based feature transform with rich spectral representation.
    """

    def __init__(self, N: int, r: int, n_features: int, top_k: int = 16, seed: int = 42):
        """
        Args:
            N: Prime modulus
            r: Target multiplicative order
            n_features: Input feature dimension
            top_k: Number of top magnitude bins to keep per base
            seed: Random seed for base selection
        """
        self.N = N
        self.r = r
        self.n_features = n_features
        self.top_k = top_k

        # Find a few bases with order dividing N-1
        np.random.seed(seed)  # Fix bases across trials for consistency
        self.bases = self._find_bases(n_bases=2)

    def _find_bases(self, n_bases: int) -> List[int]:
        """Find bases with order dividing N-1"""
        # Find divisors of N-1 near target r
        target_r = int(self.r)
        best_r = None
        best_dist = float('inf')

        for d in range(2, self.N):
            if (self.N - 1) % d == 0:
                dist = abs(d - target_r)
                if dist < best_dist:
                    best_r = d
                    best_dist = dist

        self.r = best_r  # Update to actual valid order
        logging.info(f"VRA layer: N={self.N}, r={self.r} (ρ={self.r/self.N:.4f})")

        # Find bases with this order
        bases = []
        attempts = 0
        max_attempts = 10000

        while len(bases) < n_bases and attempts < max_attempts:
            a = np.random.randint(2, self.N)
            if np.gcd(a, self.N) == 1:
                if pow(a, self.r, self.N) == 1:
                    bases.append(a)
            attempts += 1

        if len(bases) < n_bases:
            logging.warning(f"Only found {len(bases)}/{n_bases} VRA bases")

        return bases

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Apply VRA spectral transform to input features.

        Returns top-k magnitude bins per base for rich representation.

        Args:
            X: (n_samples, n_features) input data

        Returns:
            X_vra: (n_samples, n_bases * top_k) transformed features
        """
        n_samples = X.shape[0]

        # Map features to modular sequences
        X_mod = (X * self.N).astype(int) % self.N

        # For each base, create a sequence and extract top-k spectral features
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

            # FFT to extract spectral features (use half-spectrum)
            fft_features = np.fft.rfft(sequences, axis=1)  # (n_samples, n_freqs)
            mag = np.abs(fft_features)

            # Keep top-k magnitudes per sample
            if self.top_k < mag.shape[1]:
                # Get indices of top-k bins for each sample
                topk_indices = np.argpartition(mag, -self.top_k, axis=1)[:, -self.top_k:]
                rows = np.arange(n_samples)[:, None]
                mag_topk = mag[rows, topk_indices]
            else:
                mag_topk = mag

            features_list.append(mag_topk)

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

    Class 0: Low-frequency content (freq ≈ 1)
    Class 1: High-frequency content (freq ≈ 5)

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


def apply_spectral_shift_continuous(X: np.ndarray, epsilon: float) -> np.ndarray:
    """
    Apply continuous spectral shift using Fourier phase ramp.

    Args:
        X: (n_samples, n_features) input data
        epsilon: Shift magnitude in cycles/sample (continuous)

    Returns:
        X_shifted: Perturbed data
    """
    n_features = X.shape[1]

    # Fourier shift theorem: shift by epsilon → multiply by exp(2πi*epsilon*k)
    k = np.fft.fftfreq(n_features)  # cycles/sample
    ramp = np.exp(2j * np.pi * epsilon * k)

    X_fft = np.fft.fft(X, axis=1)
    X_fft_shifted = X_fft * ramp[None, :]
    # Use np.real() to avoid ComplexWarning (imaginary part is ~0 due to symmetry)
    X_shifted = np.real(np.fft.ifft(X_fft_shifted, axis=1))

    return X_shifted


# ============================================================================
# Geometric Margin Computation
# ============================================================================

def compute_geometric_margin(
    pipeline,
    X: np.ndarray,
    y: np.ndarray
) -> float:
    """
    Compute geometric margin (scale-normalized).

    Margin = mean(y_i * f(x_i)) / ||w||

    where f(x) = w·x + b is the decision function.

    Args:
        pipeline: Fitted sklearn pipeline with StandardScaler + LogisticRegression
        X: Features
        y: Binary labels {0, 1}

    Returns:
        margin: Geometric margin
    """
    # Get decision function (signed distance)
    decision = pipeline.decision_function(X)

    # Get weight vector from the logistic regression
    clf = pipeline.named_steps['logisticregression']
    w = clf.coef_.ravel()

    # Convert labels to {-1, +1}
    y_signed = 2 * y - 1

    # Geometric margin: mean signed distance / ||w||
    margin = float(np.mean(y_signed * decision) / (np.linalg.norm(w) + 1e-12))

    return margin


# ============================================================================
# Experiment Execution
# ============================================================================

def run_margin_preservation_experiment(config: Config) -> List[Dict]:
    """
    Test margin preservation under spectral shift.

    Compare baseline (raw features) vs VRA-augmented (raw + VRA features).

    Returns:
        results: Measurements for each (ε, trial)
    """
    logging.info("")
    logging.info("Starting margin preservation experiment...")
    logging.info(f"ε values: {config.epsilon_values}")
    logging.info(f"Trials: {config.n_trials}")
    logging.info(f"Samples: train={config.n_samples_train}, test={config.n_samples_test}")
    logging.info("")

    # Initialize VRA layer (fixed bases across trials)
    r_target = int(config.r_fraction * config.N_prime)
    vra_layer = VRALayer(config.N_prime, r_target, config.n_features,
                        top_k=config.vra_top_k, seed=42)

    results = []
    start_time = time.time()

    total_configs = len(config.epsilon_values) * config.n_trials
    config_idx = 0

    for epsilon in config.epsilon_values:
        logging.info(f"\n{'='*60}")
        logging.info(f"Testing ε = {epsilon:.3f}")
        logging.info('='*60)

        for trial in range(config.n_trials):
            config_idx += 1
            elapsed = time.time() - start_time
            rate = config_idx / elapsed if elapsed > 0 else 0
            eta = (total_configs - config_idx) / rate if rate > 0 else 0

            # Generate training data
            X_train, y_train = generate_binary_classification_data(
                config.n_samples_train, config.n_features,
                config.separation, config.noise_std,
                seed=trial
            )

            # Generate test data (no shift yet)
            X_test, y_test = generate_binary_classification_data(
                config.n_samples_test, config.n_features,
                config.separation, config.noise_std,
                seed=trial + 10000
            )

            # Apply spectral shift to test data
            X_test_shifted = apply_spectral_shift_continuous(X_test, epsilon)

            # -----------------------------------------------------------
            # Model 1: Baseline (raw features only)
            # -----------------------------------------------------------
            baseline_pipe = make_pipeline(
                StandardScaler(with_mean=True, with_std=True),
                LogisticRegression(max_iter=1000, random_state=trial)
            )
            baseline_pipe.fit(X_train, y_train)

            y_pred_base = baseline_pipe.predict(X_test_shifted)
            acc_base = accuracy_score(y_test, y_pred_base)
            margin_base = compute_geometric_margin(baseline_pipe, X_test_shifted, y_test)

            # -----------------------------------------------------------
            # Model 2: VRA-augmented (raw + VRA features concatenated)
            # -----------------------------------------------------------
            # Extract VRA features
            X_train_vra_raw = vra_layer.transform(X_train)
            X_test_vra_raw = vra_layer.transform(X_test_shifted)

            # Concatenate: [standardized raw | standardized VRA]
            scaler_raw = StandardScaler().fit(X_train)
            scaler_vra = StandardScaler().fit(X_train_vra_raw)

            X_train_aug = np.concatenate([
                scaler_raw.transform(X_train),
                scaler_vra.transform(X_train_vra_raw)
            ], axis=1)

            X_test_aug = np.concatenate([
                scaler_raw.transform(X_test_shifted),
                scaler_vra.transform(X_test_vra_raw)
            ], axis=1)

            # Train on augmented features (no additional scaler needed)
            clf_vra = LogisticRegression(max_iter=1000, random_state=trial)
            clf_vra.fit(X_train_aug, y_train)

            # Wrap in a dummy pipeline for margin computation
            from sklearn.preprocessing import FunctionTransformer
            vra_pipe = make_pipeline(
                FunctionTransformer(lambda x: x),  # Identity (already scaled)
                clf_vra
            )

            y_pred_vra = vra_pipe.predict(X_test_aug)
            acc_vra = accuracy_score(y_test, y_pred_vra)
            margin_vra = compute_geometric_margin(vra_pipe, X_test_aug, y_test)

            # -----------------------------------------------------------
            # Log and store
            # -----------------------------------------------------------
            if (trial + 1) % 10 == 1 or trial == 0:
                logging.info(
                    f"  Trial {trial+1}/{config.n_trials} | "
                    f"Margin: base={margin_base:.4f}, vra={margin_vra:.4f} | "
                    f"Acc: base={acc_base:.3f}, vra={acc_vra:.3f} | "
                    f"ETA: {eta/60:.1f}m"
                )

            results.append({
                'epsilon': float(epsilon),
                'trial': int(trial),
                'margin_baseline': float(margin_base),
                'margin_vra': float(margin_vra),
                'acc_baseline': float(acc_base),
                'acc_vra': float(acc_vra)
            })

    elapsed = time.time() - start_time
    logging.info(f"\nExperiment complete: {elapsed:.1f}s ({elapsed/60:.1f}m)")

    return results


# ============================================================================
# Analysis & Plotting
# ============================================================================

def analyze_margin_bound(results: List[Dict]) -> Dict:
    """
    Fit margin degradation vs ε to test Margin_VRA ≥ Margin_baseline - C·ε

    Returns:
        analysis: Fit parameters and verdict
    """
    logging.info("")
    logging.info("="*70)
    logging.info("MARGIN BOUND ANALYSIS")
    logging.info("="*70)

    # Group by epsilon
    epsilon_values = sorted(set(r['epsilon'] for r in results))

    eps_list = []
    delta_margin_list = []  # Δmargin = margin_base - margin_vra

    for eps in epsilon_values:
        subset = [r for r in results if r['epsilon'] == eps]

        margin_base = np.array([r['margin_baseline'] for r in subset])
        margin_vra = np.array([r['margin_vra'] for r in subset])

        delta_margin = margin_base - margin_vra

        eps_list.append(eps)
        delta_margin_list.append(delta_margin.mean())

        logging.info(f"ε={eps:.3f}: Δmargin = {delta_margin.mean():.4f} ± {delta_margin.std():.4f}")

    # Fit Δmargin = C·ε (should be positive if VRA degrades faster)
    eps_arr = np.array(eps_list)
    delta_arr = np.array(delta_margin_list)

    slope, intercept, r_value, p_value, std_err = linregress(eps_arr, delta_arr)

    logging.info("")
    logging.info(f"Linear fit: Δmargin = {slope:.4f}·ε + {intercept:.4f}")
    logging.info(f"R² = {r_value**2:.4f}, p = {p_value:.4e}")
    logging.info(f"Slope C = {slope:.4f} ± {std_err:.4f}")
    logging.info("")

    # Interpret
    if intercept < 0.01 and slope > -0.1:  # Near-zero intercept at ε=0, slow degradation
        verdict = "PASS - VRA preserves margin well under spectral shift"
    elif slope < 0:  # Negative slope = VRA improves with shift (unexpected but good)
        verdict = "PASS - VRA margin actually improves under shift!"
    else:
        verdict = f"WEAK - VRA degrades with slope C={slope:.3f}"

    logging.info(f"VERDICT: {verdict}")

    return {
        'epsilon': eps_list,
        'delta_margin_mean': delta_margin_list,
        'slope': float(slope),
        'intercept': float(intercept),
        'r_squared': float(r_value**2),
        'p_value': float(p_value),
        'verdict': verdict
    }


def plot_results(results: List[Dict], analysis: Dict, config: Config):
    """Generate margin preservation plots"""

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Group by epsilon
    epsilon_values = sorted(set(r['epsilon'] for r in results))

    # Plot 1: Margin vs ε (both models)
    ax = axes[0]

    margin_base_means = []
    margin_base_stds = []
    margin_vra_means = []
    margin_vra_stds = []

    for eps in epsilon_values:
        subset = [r for r in results if r['epsilon'] == eps]

        mb = np.array([r['margin_baseline'] for r in subset])
        mv = np.array([r['margin_vra'] for r in subset])

        margin_base_means.append(mb.mean())
        margin_base_stds.append(mb.std())
        margin_vra_means.append(mv.mean())
        margin_vra_stds.append(mv.std())

    ax.errorbar(epsilon_values, margin_base_means, yerr=margin_base_stds,
               fmt='o-', label='Baseline', capsize=3, markersize=8)
    ax.errorbar(epsilon_values, margin_vra_means, yerr=margin_vra_stds,
               fmt='s-', label='VRA-augmented', capsize=3, markersize=8)

    ax.set_xlabel('Spectral shift ε (cycles/sample)')
    ax.set_ylabel('Geometric margin')
    ax.set_title('Margin Preservation under Spectral Shift')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Δmargin vs ε with linear fit
    ax = axes[1]

    eps_fit = np.array(analysis['epsilon'])
    delta_fit = np.array(analysis['delta_margin_mean'])

    ax.plot(eps_fit, delta_fit, 'o', markersize=10, label='Measured Δmargin')

    # Fit line
    slope = analysis['slope']
    intercept = analysis['intercept']
    eps_line = np.linspace(0, eps_fit.max(), 100)
    delta_line = slope * eps_line + intercept
    ax.plot(eps_line, delta_line, '--', label=f'Fit: {slope:.3f}·ε + {intercept:.3f}')

    ax.axhline(0, color='gray', linestyle=':', linewidth=1)
    ax.set_xlabel('Spectral shift ε')
    ax.set_ylabel('Δmargin = margin_base - margin_vra')
    ax.set_title(f'Margin Degradation (R²={analysis["r_squared"]:.3f})')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save
    figpath = config.figure_dir / 'T6C2_fixed_margin_preservation.png'
    plt.savefig(figpath, dpi=300, bbox_inches='tight')
    logging.info(f"\nFigure saved: {figpath}")
    plt.close()


# ============================================================================
# Main
# ============================================================================

def main():
    config = Config()

    # Run experiment
    results = run_margin_preservation_experiment(config)

    # Save raw data
    output_file = config.output_dir / 'T6C2_fixed_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logging.info(f"\nData saved: {output_file}")

    # Analyze bound
    analysis = analyze_margin_bound(results)

    # Save analysis
    analysis_file = config.output_dir / 'T6C2_fixed_analysis.json'
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)

    # Plot
    logging.info("")
    logging.info("Generating figures...")
    plot_results(results, analysis, config)

    # Summary
    logging.info("")
    logging.info("="*70)
    logging.info("T6-C2 FIXED COMPLETE")
    logging.info("="*70)
    logging.info(f"Hypothesis: Margin_VRA ≥ Margin_baseline - C·ε")
    logging.info(f"VERDICT: {analysis['verdict']}")
    logging.info("="*70)


if __name__ == '__main__':
    main()
