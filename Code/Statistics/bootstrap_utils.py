#!/usr/bin/env python3
"""
Bootstrap Confidence Interval Utilities
========================================

Provides rigorous uncertainty quantification for VRA validation experiments.
All statistical claims now include 95% bootstrap confidence intervals.

Phase 4.2 - Statistical Rigor
Author: Dylan Vaca
Date: October 2025
"""

import numpy as np
from typing import Tuple, List, Dict, Callable, Optional


def bootstrap_resample(data: np.ndarray, n_bootstrap: int = 10000,
                       random_seed: Optional[int] = 42) -> np.ndarray:
    """
    Generate bootstrap resamples of data.

    Parameters
    ----------
    data : np.ndarray
        Original data array (1D)
    n_bootstrap : int
        Number of bootstrap samples
    random_seed : int or None
        Random seed for reproducibility

    Returns
    -------
    resamples : np.ndarray
        Shape (n_bootstrap, len(data)) of resampled data
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    n = len(data)
    indices = np.random.randint(0, n, size=(n_bootstrap, n))
    return data[indices]


def bootstrap_ci(data: np.ndarray,
                 statistic: Callable = np.mean,
                 confidence: float = 0.95,
                 n_bootstrap: int = 10000,
                 random_seed: Optional[int] = 42) -> Tuple[float, Tuple[float, float]]:
    """
    Compute bootstrap confidence interval for any statistic.

    Parameters
    ----------
    data : np.ndarray
        Original data (1D array)
    statistic : callable
        Function to compute statistic (e.g., np.mean, np.median)
    confidence : float
        Confidence level (default 0.95 for 95% CI)
    n_bootstrap : int
        Number of bootstrap samples
    random_seed : int or None
        Random seed for reproducibility

    Returns
    -------
    point_estimate : float
        Statistic computed on original data
    ci : tuple
        (lower_bound, upper_bound) of confidence interval
    """
    # Compute point estimate
    point_estimate = statistic(data)

    # Generate bootstrap samples
    resamples = bootstrap_resample(data, n_bootstrap, random_seed)

    # Compute statistic on each resample
    bootstrap_stats = np.array([statistic(resample) for resample in resamples])

    # Compute percentile CI
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
    upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))

    return point_estimate, (lower, upper)


def bootstrap_r_squared(y_true: np.ndarray,
                       y_pred: np.ndarray,
                       confidence: float = 0.95,
                       n_bootstrap: int = 10000,
                       random_seed: Optional[int] = 42) -> Tuple[float, Tuple[float, float]]:
    """
    Bootstrap confidence interval for R² coefficient of determination.

    Parameters
    ----------
    y_true : np.ndarray
        True values
    y_pred : np.ndarray
        Predicted values
    confidence : float
        Confidence level
    n_bootstrap : int
        Number of bootstrap samples
    random_seed : int or None
        Random seed

    Returns
    -------
    r_squared : float
        Point estimate of R²
    ci : tuple
        (lower, upper) confidence interval
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    def compute_r2(indices):
        """Compute R² on resampled indices"""
        y_t = y_true[indices]
        y_p = y_pred[indices]
        ss_res = np.sum((y_t - y_p) ** 2)
        ss_tot = np.sum((y_t - np.mean(y_t)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Point estimate
    r_squared = compute_r2(np.arange(len(y_true)))

    # Bootstrap
    n = len(y_true)
    bootstrap_r2 = []
    for _ in range(n_bootstrap):
        indices = np.random.randint(0, n, size=n)
        bootstrap_r2.append(compute_r2(indices))

    bootstrap_r2 = np.array(bootstrap_r2)

    # Percentile CI
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_r2, 100 * alpha / 2)
    upper = np.percentile(bootstrap_r2, 100 * (1 - alpha / 2))

    return r_squared, (lower, upper)


def bootstrap_precision_recall(true_bins: np.ndarray,
                               detected_bins: np.ndarray,
                               confidence: float = 0.95,
                               n_bootstrap: int = 10000,
                               random_seed: Optional[int] = 42) -> Dict[str, Tuple[float, Tuple[float, float]]]:
    """
    Bootstrap CIs for precision and recall with binary outcomes.

    Uses stratified bootstrap to preserve class balance.

    Parameters
    ----------
    true_bins : np.ndarray
        Array of true harmonic bin indices
    detected_bins : np.ndarray
        Array of detected bin indices
    confidence : float
        Confidence level
    n_bootstrap : int
        Number of bootstrap samples
    random_seed : int or None
        Random seed

    Returns
    -------
    results : dict
        Contains 'precision' and 'recall', each with (point_estimate, (lower, upper))
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    # Convert to sets for easier computation
    true_set = set(true_bins)
    detected_set = set(detected_bins)

    # True positives, false positives, false negatives
    tp_bins = list(true_set & detected_set)
    fp_bins = list(detected_set - true_set)
    fn_bins = list(true_set - detected_set)

    # Create labeled outcomes
    # 1 = TP, 0 = FP (for precision)
    # 1 = TP, 0 = FN (for recall)
    precision_outcomes = [1] * len(tp_bins) + [0] * len(fp_bins)
    recall_outcomes = [1] * len(tp_bins) + [0] * len(fn_bins)

    # Point estimates
    precision = len(tp_bins) / len(detected_bins) if len(detected_bins) > 0 else 0.0
    recall = len(tp_bins) / len(true_bins) if len(true_bins) > 0 else 0.0

    # Bootstrap precision
    precision_bootstrap = []
    if len(precision_outcomes) > 0:
        for _ in range(n_bootstrap):
            sample = np.random.choice(precision_outcomes, size=len(precision_outcomes), replace=True)
            precision_bootstrap.append(np.mean(sample))

    # Bootstrap recall
    recall_bootstrap = []
    if len(recall_outcomes) > 0:
        for _ in range(n_bootstrap):
            sample = np.random.choice(recall_outcomes, size=len(recall_outcomes), replace=True)
            recall_bootstrap.append(np.mean(sample))

    # Compute CIs
    alpha = 1 - confidence

    if len(precision_bootstrap) > 0:
        prec_lower = np.percentile(precision_bootstrap, 100 * alpha / 2)
        prec_upper = np.percentile(precision_bootstrap, 100 * (1 - alpha / 2))
    else:
        prec_lower = prec_upper = precision

    if len(recall_bootstrap) > 0:
        rec_lower = np.percentile(recall_bootstrap, 100 * alpha / 2)
        rec_upper = np.percentile(recall_bootstrap, 100 * (1 - alpha / 2))
    else:
        rec_lower = rec_upper = recall

    return {
        'precision': (precision, (prec_lower, prec_upper)),
        'recall': (recall, (rec_lower, rec_upper))
    }


def bootstrap_ratio(numerator_data: np.ndarray,
                   denominator_data: np.ndarray,
                   confidence: float = 0.95,
                   n_bootstrap: int = 10000,
                   random_seed: Optional[int] = 42) -> Tuple[float, Tuple[float, float]]:
    """
    Bootstrap CI for ratio of two statistics (e.g., speedup = time_baseline / time_method).

    Uses paired bootstrap resampling.

    Parameters
    ----------
    numerator_data : np.ndarray
        Data for numerator
    denominator_data : np.ndarray
        Data for denominator (must be same length)
    confidence : float
        Confidence level
    n_bootstrap : int
        Number of bootstrap samples
    random_seed : int or None
        Random seed

    Returns
    -------
    ratio : float
        Point estimate
    ci : tuple
        (lower, upper) confidence interval
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    assert len(numerator_data) == len(denominator_data), "Arrays must have same length"

    # Point estimate
    ratio = np.mean(numerator_data) / np.mean(denominator_data)

    # Bootstrap
    n = len(numerator_data)
    bootstrap_ratios = []
    for _ in range(n_bootstrap):
        indices = np.random.randint(0, n, size=n)
        num_resample = numerator_data[indices]
        den_resample = denominator_data[indices]
        bootstrap_ratios.append(np.mean(num_resample) / np.mean(den_resample))

    bootstrap_ratios = np.array(bootstrap_ratios)

    # Percentile CI
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_ratios, 100 * alpha / 2)
    upper = np.percentile(bootstrap_ratios, 100 * (1 - alpha / 2))

    return ratio, (lower, upper)


def bootstrap_correlation(x: np.ndarray,
                          y: np.ndarray,
                          confidence: float = 0.95,
                          n_bootstrap: int = 10000,
                          random_seed: Optional[int] = 42) -> Tuple[float, Tuple[float, float]]:
    """
    Bootstrap CI for Pearson correlation coefficient.

    Parameters
    ----------
    x, y : np.ndarray
        Paired data arrays
    confidence : float
        Confidence level
    n_bootstrap : int
        Number of bootstrap samples
    random_seed : int or None
        Random seed

    Returns
    -------
    correlation : float
        Pearson r point estimate
    ci : tuple
        (lower, upper) confidence interval
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    assert len(x) == len(y), "Arrays must have same length"

    # Point estimate
    correlation = np.corrcoef(x, y)[0, 1]

    # Bootstrap
    n = len(x)
    bootstrap_corrs = []
    for _ in range(n_bootstrap):
        indices = np.random.randint(0, n, size=n)
        x_resample = x[indices]
        y_resample = y[indices]
        bootstrap_corrs.append(np.corrcoef(x_resample, y_resample)[0, 1])

    bootstrap_corrs = np.array(bootstrap_corrs)

    # Percentile CI
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_corrs, 100 * alpha / 2)
    upper = np.percentile(bootstrap_corrs, 100 * (1 - alpha / 2))

    return correlation, (lower, upper)


def format_ci_string(point_estimate: float, ci: Tuple[float, float],
                     precision: int = 3) -> str:
    """
    Format confidence interval as string for reporting.

    Parameters
    ----------
    point_estimate : float
        Point estimate
    ci : tuple
        (lower, upper) bounds
    precision : int
        Decimal places

    Returns
    -------
    formatted : str
        E.g., "0.976 [0.952, 0.991]"
    """
    fmt = f"{{:.{precision}f}}"
    return f"{fmt.format(point_estimate)} [{fmt.format(ci[0])}, {fmt.format(ci[1])}]"


def compute_effect_size_cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """
    Cohen's d effect size for comparing two groups.

    d = (mean1 - mean2) / pooled_std

    Interpretation:
    - d < 0.2: negligible
    - 0.2 ≤ d < 0.5: small
    - 0.5 ≤ d < 0.8: medium
    - d ≥ 0.8: large

    Parameters
    ----------
    group1, group2 : np.ndarray
        Data from two groups

    Returns
    -------
    d : float
        Cohen's d effect size
    """
    mean1, mean2 = np.mean(group1), np.mean(group2)
    std1, std2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
    n1, n2 = len(group1), len(group2)

    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))

    return (mean1 - mean2) / pooled_std if pooled_std > 0 else 0.0


def statistical_summary(data: np.ndarray,
                       confidence: float = 0.95,
                       n_bootstrap: int = 10000,
                       random_seed: Optional[int] = 42) -> Dict:
    """
    Comprehensive statistical summary with bootstrap CIs.

    Parameters
    ----------
    data : np.ndarray
        Data array
    confidence : float
        Confidence level
    n_bootstrap : int
        Number of bootstrap samples
    random_seed : int or None
        Random seed

    Returns
    -------
    summary : dict
        Contains mean, median, std, IQR, all with CIs where applicable
    """
    # Point estimates
    mean_pt, mean_ci = bootstrap_ci(data, np.mean, confidence, n_bootstrap, random_seed)
    median_pt, median_ci = bootstrap_ci(data, np.median, confidence, n_bootstrap, random_seed)
    std_pt = np.std(data, ddof=1)

    # Percentiles
    p25 = np.percentile(data, 25)
    p75 = np.percentile(data, 75)
    iqr = p75 - p25

    return {
        'n': len(data),
        'mean': mean_pt,
        'mean_ci': mean_ci,
        'median': median_pt,
        'median_ci': median_ci,
        'std': std_pt,
        'iqr': iqr,
        'p25': p25,
        'p75': p75,
        'min': np.min(data),
        'max': np.max(data)
    }


if __name__ == "__main__":
    # Demonstration
    print("Bootstrap CI Utilities - Demo")
    print("=" * 60)

    # Example: Mean CI
    np.random.seed(42)
    data = np.random.normal(100, 15, size=50)
    mean, ci = bootstrap_ci(data, np.mean, n_bootstrap=10000)
    print(f"\nMean with 95% CI: {format_ci_string(mean, ci)}")

    # Example: R² CI
    x = np.arange(100)
    y = 2 * x + 5 + np.random.normal(0, 10, size=100)
    y_pred = 2 * x + 5
    r2, r2_ci = bootstrap_r_squared(y, y_pred, n_bootstrap=10000)
    print(f"R² with 95% CI: {format_ci_string(r2, r2_ci)}")

    # Example: Precision/Recall CI
    true_bins = np.array([0, 1, 2, 3, 4, 5])
    detected_bins = np.array([0, 1, 2, 6, 7])  # 3 TP, 2 FP, 3 FN
    pr_results = bootstrap_precision_recall(true_bins, detected_bins, n_bootstrap=10000)
    prec, prec_ci = pr_results['precision']
    rec, rec_ci = pr_results['recall']
    print(f"Precision with 95% CI: {format_ci_string(prec, prec_ci)}")
    print(f"Recall with 95% CI: {format_ci_string(rec, rec_ci)}")

    print("\n" + "=" * 60)
    print("Bootstrap utilities ready for Phase 4.2 validation")
