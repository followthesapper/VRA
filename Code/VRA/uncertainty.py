#!/usr/bin/env python3
"""
VRA Uncertainty Quantification
===============================

Bootstrap resampling and confidence interval computation for VRA metrics.

Addresses the statistical rigor gap: uncertainty quantification for √M fits
and regime boundary estimates.

Author: Dylan Vaca
Date: October 2025
"""

import numpy as np


def bootstrap_sqrt_m_fit(M_values, concentrations, num_bootstrap=1000, confidence=95):
    """Compute bootstrap confidence intervals for √M fit

    Parameters:
        M_values (array-like): M values used
        concentrations (array-like): Measured concentrations
        num_bootstrap (int): Number of bootstrap samples
        confidence (float): Confidence level (%)

    Returns:
        dict: {
            'slope': point estimate,
            'slope_ci': [lower, upper],
            'intercept': point estimate,
            'intercept_ci': [lower, upper],
            'r_squared': point estimate,
            'r_squared_ci': [lower, upper]
        }
    """
    M_values = np.array(M_values)
    concentrations = np.array(concentrations)
    sqrt_M = np.sqrt(M_values)

    # Point estimates
    slope, intercept = np.polyfit(sqrt_M, concentrations, 1)
    ss_res = np.sum((concentrations - (slope * sqrt_M + intercept))**2)
    ss_tot = np.sum((concentrations - np.mean(concentrations))**2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Bootstrap
    bootstrap_slopes = []
    bootstrap_intercepts = []
    bootstrap_r2s = []

    for _ in range(num_bootstrap):
        # Resample with replacement
        indices = np.random.choice(len(M_values), len(M_values), replace=True)
        sqrt_M_boot = sqrt_M[indices]
        conc_boot = concentrations[indices]

        # Fit
        slope_boot, intercept_boot = np.polyfit(sqrt_M_boot, conc_boot, 1)

        # R²
        ss_res_boot = np.sum((conc_boot - (slope_boot * sqrt_M_boot + intercept_boot))**2)
        ss_tot_boot = np.sum((conc_boot - np.mean(conc_boot))**2)
        r2_boot = 1 - (ss_res_boot / ss_tot_boot) if ss_tot_boot > 0 else 0

        bootstrap_slopes.append(slope_boot)
        bootstrap_intercepts.append(intercept_boot)
        bootstrap_r2s.append(r2_boot)

    # Compute confidence intervals
    alpha = (100 - confidence) / 2
    lower_percentile = alpha
    upper_percentile = 100 - alpha

    slope_ci = np.percentile(bootstrap_slopes, [lower_percentile, upper_percentile])
    intercept_ci = np.percentile(bootstrap_intercepts, [lower_percentile, upper_percentile])
    r2_ci = np.percentile(bootstrap_r2s, [lower_percentile, upper_percentile])

    return {
        'slope': float(slope),
        'slope_ci': [float(slope_ci[0]), float(slope_ci[1])],
        'slope_std': float(np.std(bootstrap_slopes)),
        'intercept': float(intercept),
        'intercept_ci': [float(intercept_ci[0]), float(intercept_ci[1])],
        'intercept_std': float(np.std(bootstrap_intercepts)),
        'r_squared': float(r_squared),
        'r_squared_ci': [float(r2_ci[0]), float(r2_ci[1])],
        'r_squared_std': float(np.std(bootstrap_r2s)),
        'num_bootstrap': num_bootstrap,
        'confidence_level': confidence
    }


def bootstrap_concentration(mag2_list, num_bootstrap=1000, confidence=95):
    """Compute bootstrap CI for concentration from multiple spectra

    Parameters:
        mag2_list (list): List of power spectra
        num_bootstrap (int): Number of bootstrap samples
        confidence (float): Confidence level (%)

    Returns:
        dict: Point estimate and CI for concentration
    """
    mag2_list = [np.array(m) for m in mag2_list]
    M = len(mag2_list)

    # Point estimate (average then compute concentration)
    mag2_avg = np.mean(mag2_list, axis=0)
    concentration = np.max(mag2_avg) / np.sum(mag2_avg)

    # Bootstrap
    bootstrap_concentrations = []

    for _ in range(num_bootstrap):
        # Resample spectra with replacement
        indices = np.random.choice(M, M, replace=True)
        mag2_boot = np.mean([mag2_list[i] for i in indices], axis=0)
        conc_boot = np.max(mag2_boot) / np.sum(mag2_boot)
        bootstrap_concentrations.append(conc_boot)

    # CI
    alpha = (100 - confidence) / 2
    lower_percentile = alpha
    upper_percentile = 100 - alpha

    conc_ci = np.percentile(bootstrap_concentrations, [lower_percentile, upper_percentile])

    return {
        'concentration': float(concentration),
        'concentration_ci': [float(conc_ci[0]), float(conc_ci[1])],
        'concentration_std': float(np.std(bootstrap_concentrations)),
        'num_bootstrap': num_bootstrap,
        'confidence_level': confidence
    }


def sensitivity_analysis(compute_metric_fn, parameters, vary_param, vary_range,
                        num_samples=20):
    """Perform sensitivity analysis by varying a parameter

    Parameters:
        compute_metric_fn (callable): Function that computes metric given parameters
        parameters (dict): Base parameter set
        vary_param (str): Parameter to vary
        vary_range (tuple): (min, max) range for parameter
        num_samples (int): Number of samples in range

    Returns:
        dict: {
            'param_values': array of parameter values tested,
            'metric_values': array of metric values,
            'sensitivity': derivative estimate
        }
    """
    param_values = np.linspace(vary_range[0], vary_range[1], num_samples)
    metric_values = []

    for val in param_values:
        params = parameters.copy()
        params[vary_param] = val

        try:
            metric = compute_metric_fn(**params)
            metric_values.append(metric)
        except Exception as e:
            print(f"Warning: Failed at {vary_param}={val}: {e}")
            metric_values.append(np.nan)

    metric_values = np.array(metric_values)

    # Estimate sensitivity (derivative)
    valid_mask = ~np.isnan(metric_values)
    if np.sum(valid_mask) >= 2:
        slope, _ = np.polyfit(param_values[valid_mask], metric_values[valid_mask], 1)
        sensitivity = slope
    else:
        sensitivity = np.nan

    return {
        'param_name': vary_param,
        'param_values': param_values.tolist(),
        'metric_values': metric_values.tolist(),
        'sensitivity': float(sensitivity),
        'range': vary_range,
        'num_samples': num_samples
    }


def regime_boundary_uncertainty(modulus_results, target_r2=0.90):
    """Estimate uncertainty in regime boundary thresholds

    Given results from multiple moduli, estimate uncertainty in the
    ρ threshold where R² crosses a target value.

    Parameters:
        modulus_results (list): List of results from different moduli
        target_r2 (float): Target R² threshold

    Returns:
        dict: Estimated boundary and uncertainty
    """
    boundary_estimates = []

    for result in modulus_results:
        # Extract (ρ, R²) pairs
        rho_values = []
        r2_values = []

        for test_point in result.get('test_points', []):
            rho = test_point['actual_rho']
            r2 = test_point['sqrt_m_fit']['r_squared']
            rho_values.append(rho)
            r2_values.append(r2)

        # Sort by ρ
        sorted_indices = np.argsort(rho_values)
        rho_sorted = np.array(rho_values)[sorted_indices]
        r2_sorted = np.array(r2_values)[sorted_indices]

        # Find where R² crosses target
        # Linear interpolation
        for i in range(len(r2_sorted) - 1):
            if (r2_sorted[i] <= target_r2 <= r2_sorted[i+1]) or \
               (r2_sorted[i+1] <= target_r2 <= r2_sorted[i]):
                # Interpolate
                rho_boundary = rho_sorted[i] + \
                    (rho_sorted[i+1] - rho_sorted[i]) * \
                    (target_r2 - r2_sorted[i]) / (r2_sorted[i+1] - r2_sorted[i])
                boundary_estimates.append(rho_boundary)
                break

    if len(boundary_estimates) == 0:
        return {
            'target_r2': target_r2,
            'boundary_estimate': None,
            'boundary_ci': None,
            'boundary_std': None,
            'num_moduli': len(modulus_results)
        }

    boundary_estimates = np.array(boundary_estimates)

    return {
        'target_r2': float(target_r2),
        'boundary_estimate': float(np.mean(boundary_estimates)),
        'boundary_ci': [float(np.percentile(boundary_estimates, 2.5)),
                       float(np.percentile(boundary_estimates, 97.5))],
        'boundary_std': float(np.std(boundary_estimates)),
        'boundary_range': [float(np.min(boundary_estimates)),
                          float(np.max(boundary_estimates))],
        'num_moduli': len(boundary_estimates),
        'estimates': boundary_estimates.tolist()
    }


def format_uncertainty(value, ci_lower, ci_upper, precision=4):
    """Format value with confidence interval for display

    Parameters:
        value (float): Point estimate
        ci_lower (float): Lower CI bound
        ci_upper (float): Upper CI bound
        precision (int): Decimal places

    Returns:
        str: Formatted string "value [ci_lower, ci_upper]"
    """
    fmt = f"{{:.{precision}f}}"
    value_str = fmt.format(value)
    ci_lower_str = fmt.format(ci_lower)
    ci_upper_str = fmt.format(ci_upper)

    return f"{value_str} [{ci_lower_str}, {ci_upper_str}]"
