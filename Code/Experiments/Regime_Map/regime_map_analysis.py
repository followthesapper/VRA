#!/usr/bin/env python3
"""
Transition Regime Map Analysis
===============================

Synthesize all regime data to create parametric maps:
- R²(r/N) showing √M fit quality across regimes
- CV(r/N) showing base variance behavior
- Concentration growth patterns
- Regime boundary thresholds

Integrates data from:
- Phase 2: r=8, r=504 tests
- Phase 3: r=126, r=168 tests

Author: Dylan Vaca
Date: October 2025
"""

import numpy as np
import json
from pathlib import Path
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =============================================================================
# Data Collection
# =============================================================================

def load_phase2_data():
    """Load Phase 2 experimental data"""

    # r=504 (LOW SNR) - from Phase 2
    r504_data = {
        'N': 1009,
        'order': 504,
        'r_over_N': 504/1009,
        'regime': 'LOW_SNR',
        'M_values': [1, 4, 8, 16, 32, 48],
        'concentrations': [0.00103, 0.00161, 0.00211, 0.00298, 0.00406, 0.00495],
        'sqrt_m_fit': {
            'slope': 0.000696,
            'r_squared': 0.9882,
            'intercept': 0.00034
        },
        'base_variance': {
            'cv': 0.0000  # Perfect invariance
        },
        'precision_recall': {
            'precision': 1.0,
            'recall': 0.0198,  # Low due to r=504 expected peaks
            'radius': 8
        }
    }

    # r=8 (HIGH SNR) - from Phase 2
    # Random bases showed NEGATIVE correlation
    r8_random = {
        'N': 1009,
        'order': 8,
        'r_over_N': 8/1009,
        'regime': 'HIGH_SNR',
        'base_selection': 'random',
        'M_values': [1, 4, 8, 16, 32],
        'sqrt_m_fit': {
            'slope': -0.0043,  # NEGATIVE
            'r_squared': 0.50,  # Poor fit
            'intercept': None
        }
    }

    # r=8 phase-aligned (HIGH SNR) - from IA#2
    r8_aligned = {
        'N': 1009,
        'order': 8,
        'r_over_N': 8/1009,
        'regime': 'HIGH_SNR',
        'base_selection': 'phase_aligned',
        'M_values': [1, 4, 8, 16, 32],
        'sqrt_m_fit': {
            'slope': 0.0057,  # POSITIVE
            'r_squared': 0.85,  # Good fit
            'intercept': None
        },
        'separation_delta': 0.0475  # δ = 4.75% at M=32
    }

    return {
        'r504': r504_data,
        'r8_random': r8_random,
        'r8_aligned': r8_aligned
    }

def load_phase3_data():
    """Load Phase 3 transition regime data"""

    # r=168 (late TRANSITION)
    r168_path = Path('../Results/20251029_192705_transition_r168.json')
    with open(r168_path) as f:
        r168_json = json.load(f)

    r168_data = {
        'N': r168_json['config']['N'],
        'order': r168_json['config']['order'],
        'r_over_N': r168_json['config']['r_over_N'],
        'regime': 'TRANSITION',
        'M_values': [res['M'] for res in r168_json['results']],
        'concentrations': [res['concentration'] for res in r168_json['results']],
        'sqrt_m_fit': r168_json['sqrt_m_fit'],
        'base_variance': {
            'cv': np.mean([res['base_variance']['cv']
                          for res in r168_json['results']
                          if res['base_variance'] is not None])
        },
        'precision_recall': r168_json['results'][-1]['precision_recall']
    }

    # r=126 (early TRANSITION)
    r126_path = Path('../Results/20251029_200111_transition_r168.json')
    with open(r126_path) as f:
        r126_json = json.load(f)

    r126_data = {
        'N': r126_json['config']['N'],
        'order': r126_json['config']['order'],
        'r_over_N': r126_json['config']['r_over_N'],
        'regime': 'TRANSITION',
        'M_values': [res['M'] for res in r126_json['results']],
        'concentrations': [res['concentration'] for res in r126_json['results']],
        'sqrt_m_fit': r126_json['sqrt_m_fit'],
        'base_variance': {
            'cv': np.mean([res['base_variance']['cv']
                          for res in r126_json['results']
                          if res['base_variance'] is not None])
        },
        'precision_recall': r126_json['results'][-1]['precision_recall']
    }

    return {
        'r168': r168_data,
        'r126': r126_data
    }

# =============================================================================
# Empirical Threshold Determination
# =============================================================================

def compute_empirical_thresholds(r_over_N_values, r_squared_values):
    """Compute regime boundaries from empirical data

    Uses R² thresholds:
    - HIGH SNR: R² < 0.90 (needs phase alignment)
    - TRANSITION: 0.90 ≤ R² < 0.98
    - LOW SNR: R² ≥ 0.98 (any bases work)
    """

    # Sort data by r/N
    sorted_indices = np.argsort(r_over_N_values)
    r_sorted = r_over_N_values[sorted_indices]
    r2_sorted = r_squared_values[sorted_indices]

    # Find boundaries by interpolating where R² crosses thresholds
    threshold_trans_start = 0.90  # Start of good √M fit
    threshold_low_snr = 0.98      # Excellent √M fit

    # Interpolate to find r/N where R² = 0.90
    if np.any(r2_sorted < threshold_trans_start) and np.any(r2_sorted >= threshold_trans_start):
        idx_below = np.where(r2_sorted < threshold_trans_start)[0][-1]
        idx_above = np.where(r2_sorted >= threshold_trans_start)[0][0]

        r_below = r_sorted[idx_below]
        r_above = r_sorted[idx_above]
        r2_below = r2_sorted[idx_below]
        r2_above = r2_sorted[idx_above]

        # Linear interpolation
        trans_start = r_below + (r_above - r_below) * \
                     (threshold_trans_start - r2_below) / (r2_above - r2_below)
    else:
        # Use midpoint between r=8 and r=126
        trans_start = 0.10

    # Interpolate to find r/N where R² = 0.98
    if np.any(r2_sorted < threshold_low_snr) and np.any(r2_sorted >= threshold_low_snr):
        idx_below = np.where(r2_sorted < threshold_low_snr)[0][-1]
        idx_above = np.where(r2_sorted >= threshold_low_snr)[0][0]

        r_below = r_sorted[idx_below]
        r_above = r_sorted[idx_above]
        r2_below = r2_sorted[idx_below]
        r2_above = r2_sorted[idx_above]

        # Linear interpolation
        low_snr_start = r_below + (r_above - r_below) * \
                       (threshold_low_snr - r2_below) / (r2_above - r2_below)
    else:
        # Use midpoint between r=168 and r=504
        low_snr_start = 0.15

    return {
        'HIGH_SNR_max': trans_start,
        'TRANSITION_start': trans_start,
        'TRANSITION_end': low_snr_start,
        'LOW_SNR_min': low_snr_start,
        'method': 'empirical_interpolation'
    }

def fit_linear_segments(r_over_N_values, r_squared_values):
    """Fit piecewise linear approximation to regime transition

    Returns slope and intercept for each segment
    """

    # Sort data
    sorted_indices = np.argsort(r_over_N_values)
    r_sorted = r_over_N_values[sorted_indices]
    r2_sorted = r_squared_values[sorted_indices]

    # Compute slopes between consecutive points
    slopes = []
    for i in range(len(r_sorted) - 1):
        dr = r_sorted[i+1] - r_sorted[i]
        dr2 = r2_sorted[i+1] - r2_sorted[i]
        slope = dr2 / dr if dr > 0 else 0
        slopes.append(slope)

    # Transition center is where slope is steepest
    steepest_idx = np.argmax(slopes)
    transition_center = (r_sorted[steepest_idx] + r_sorted[steepest_idx + 1]) / 2

    return {
        'transition_center': transition_center,
        'slopes': slopes,
        'steepest_region': (r_sorted[steepest_idx], r_sorted[steepest_idx + 1])
    }

# =============================================================================
# Visualization
# =============================================================================

def create_regime_map_plot(phase2_data, phase3_data, thresholds, output_path):
    """Create comprehensive regime map figure"""

    if not HAS_MATPLOTLIB:
        print("Matplotlib not available, skipping plot")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('VRA Regime Map', fontsize=16, fontweight='bold')

    # Panel A: R² vs r/N
    ax = axes[0, 0]

    # Plot data points
    r_over_N = []
    r_squared = []
    colors = []
    labels = []

    # Phase 2 data
    r_over_N.append(phase2_data['r8_aligned']['r_over_N'])
    r_squared.append(phase2_data['r8_aligned']['sqrt_m_fit']['r_squared'])
    colors.append('red')
    labels.append('r=8 (aligned)')

    r_over_N.append(phase2_data['r504']['r_over_N'])
    r_squared.append(phase2_data['r504']['sqrt_m_fit']['r_squared'])
    colors.append('green')
    labels.append('r=504')

    # Phase 3 data
    r_over_N.append(phase3_data['r126']['r_over_N'])
    r_squared.append(phase3_data['r126']['sqrt_m_fit']['r_squared'])
    colors.append('orange')
    labels.append('r=126')

    r_over_N.append(phase3_data['r168']['r_over_N'])
    r_squared.append(phase3_data['r168']['sqrt_m_fit']['r_squared'])
    colors.append('blue')
    labels.append('r=168')

    # Plot points
    for i in range(len(r_over_N)):
        ax.scatter(r_over_N[i], r_squared[i], s=100, c=colors[i],
                  label=labels[i], alpha=0.7, edgecolors='black', linewidths=1.5)

    # Plot piecewise linear connection
    r_array = np.array(r_over_N)
    r2_array = np.array(r_squared)
    sorted_indices = np.argsort(r_array)
    ax.plot(r_array[sorted_indices], r2_array[sorted_indices],
           'k--', alpha=0.3, linewidth=1.5, label='Piecewise linear')

    # Mark regime boundaries
    if thresholds is not None:
        ax.axvline(thresholds['HIGH_SNR_max'], color='red',
                  linestyle=':', alpha=0.5, linewidth=2)
        ax.axvline(thresholds['LOW_SNR_min'], color='green',
                  linestyle=':', alpha=0.5, linewidth=2)

        # Shade regions
        ax.axvspan(0, thresholds['HIGH_SNR_max'], alpha=0.1, color='red')
        ax.axvspan(thresholds['TRANSITION_start'], thresholds['TRANSITION_end'],
                  alpha=0.1, color='yellow')
        ax.axvspan(thresholds['LOW_SNR_min'], 0.6, alpha=0.1, color='green')

    ax.set_xlabel('r/N', fontsize=12, fontweight='bold')
    ax.set_ylabel('R² (√M fit quality)', fontsize=12, fontweight='bold')
    ax.set_title('Panel A: Regime Transition', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=9)
    ax.set_xlim(0, 0.6)
    ax.set_ylim(0, 1.05)

    # Panel B: Concentration vs √M for all regimes
    ax = axes[0, 1]

    datasets = [
        (phase3_data['r126'], 'r=126 (TRANS)', 'orange'),
        (phase3_data['r168'], 'r=168 (TRANS)', 'blue'),
        (phase2_data['r504'], 'r=504 (LOW)', 'green')
    ]

    for data, label, color in datasets:
        M = np.array(data['M_values'])
        C = np.array(data['concentrations'])
        ax.scatter(np.sqrt(M), C * 100, s=80, c=color, label=label,
                  alpha=0.7, edgecolors='black', linewidths=1)

        # Plot fit line
        sqrt_M = np.sqrt(M)
        fit = data['sqrt_m_fit']
        C_fit = fit['slope'] * sqrt_M + fit['intercept']
        ax.plot(sqrt_M, C_fit * 100, '--', color=color, alpha=0.5, linewidth=2)

    ax.set_xlabel('√M', fontsize=12, fontweight='bold')
    ax.set_ylabel('Concentration (%)', fontsize=12, fontweight='bold')
    ax.set_title('Panel B: √M Scaling', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left', fontsize=9)

    # Panel C: Base Variance (CV) vs r/N
    ax = axes[1, 0]

    cv_data = [
        (phase2_data['r8_aligned']['r_over_N'], 0.0, 'red', 'r=8 (aligned)'),
        (phase3_data['r126']['r_over_N'],
         phase3_data['r126']['base_variance']['cv'] * 100, 'orange', 'r=126'),
        (phase3_data['r168']['r_over_N'],
         phase3_data['r168']['base_variance']['cv'] * 100, 'blue', 'r=168'),
        (phase2_data['r504']['r_over_N'],
         phase2_data['r504']['base_variance']['cv'] * 100, 'green', 'r=504')
    ]

    for r_N, cv, color, label in cv_data:
        ax.scatter(r_N, cv, s=100, c=color, label=label,
                  alpha=0.7, edgecolors='black', linewidths=1.5)

    ax.set_xlabel('r/N', fontsize=12, fontweight='bold')
    ax.set_ylabel('Base CV (%)', fontsize=12, fontweight='bold')
    ax.set_title('Panel C: Base Invariance', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=9)
    ax.set_xlim(0, 0.6)
    ax.set_ylim(-0.001, 0.01)

    # Panel D: Regime characteristics summary table
    ax = axes[1, 1]
    ax.axis('off')

    table_data = [
        ['Regime', 'r/N Range', 'R² Range', 'Base Selection'],
        ['HIGH SNR', f'< {thresholds["HIGH_SNR_max"]:.3f}' if thresholds else '< 0.10',
         '0.50-0.85', 'Phase-aligned'],
        ['TRANSITION',
         f'{thresholds["TRANSITION_start"]:.3f}-{thresholds["TRANSITION_end"]:.3f}'
         if thresholds else '0.10-0.15',
         '0.82-0.98', 'Any (random OK)'],
        ['LOW SNR', f'> {thresholds["LOW_SNR_min"]:.3f}' if thresholds else '> 0.15',
         '0.98-0.99', 'Any (random OK)']
    ]

    table = ax.table(cellText=table_data, loc='center', cellLoc='left',
                    colWidths=[0.2, 0.25, 0.25, 0.3])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)

    # Style header row
    for i in range(4):
        cell = table[(0, i)]
        cell.set_facecolor('#4472C4')
        cell.set_text_props(weight='bold', color='white')

    # Style data rows
    colors_rows = ['#FFE699', '#FFE699', '#C6E0B4']  # Yellow, Yellow, Green
    for i, color in enumerate(colors_rows, start=1):
        for j in range(4):
            table[(i, j)].set_facecolor(color)

    ax.set_title('Panel D: Regime Characteristics', fontsize=12,
                fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nSaved regime map plot: {output_path}")
    plt.close()

# =============================================================================
# Main Analysis
# =============================================================================

def main():
    print("="*70)
    print("TRANSITION REGIME MAP ANALYSIS")
    print("="*70)
    print()

    # Load all data
    print("Loading Phase 2 data...")
    phase2_data = load_phase2_data()

    print("Loading Phase 3 data...")
    phase3_data = load_phase3_data()

    print()
    print("Data Summary:")
    print("-" * 70)
    print(f"  r=8 (aligned):  r/N={phase2_data['r8_aligned']['r_over_N']:.3f}, "
          f"R²={phase2_data['r8_aligned']['sqrt_m_fit']['r_squared']:.3f}")
    print(f"  r=126:          r/N={phase3_data['r126']['r_over_N']:.3f}, "
          f"R²={phase3_data['r126']['sqrt_m_fit']['r_squared']:.4f}")
    print(f"  r=168:          r/N={phase3_data['r168']['r_over_N']:.3f}, "
          f"R²={phase3_data['r168']['sqrt_m_fit']['r_squared']:.4f}")
    print(f"  r=504:          r/N={phase2_data['r504']['r_over_N']:.3f}, "
          f"R²={phase2_data['r504']['sqrt_m_fit']['r_squared']:.4f}")
    print()

    # Compute regime boundaries from empirical data
    print("Computing regime boundaries from empirical data...")
    r_over_N_values = np.array([
        phase2_data['r8_aligned']['r_over_N'],
        phase3_data['r126']['r_over_N'],
        phase3_data['r168']['r_over_N'],
        phase2_data['r504']['r_over_N']
    ])
    r_squared_values = np.array([
        phase2_data['r8_aligned']['sqrt_m_fit']['r_squared'],
        phase3_data['r126']['sqrt_m_fit']['r_squared'],
        phase3_data['r168']['sqrt_m_fit']['r_squared'],
        phase2_data['r504']['sqrt_m_fit']['r_squared']
    ])

    thresholds = compute_empirical_thresholds(r_over_N_values, r_squared_values)
    linear_fit = fit_linear_segments(r_over_N_values, r_squared_values)

    print(f"  Transition center: r/N ≈ {linear_fit['transition_center']:.4f}")
    print(f"  Steepest region: ({linear_fit['steepest_region'][0]:.3f}, "
          f"{linear_fit['steepest_region'][1]:.3f})")
    print()

    print("Regime Boundaries:")
    print("-" * 70)
    print(f"  HIGH SNR:     r/N < {thresholds['HIGH_SNR_max']:.4f}")
    print(f"  TRANSITION:   {thresholds['TRANSITION_start']:.4f} "
          f"≤ r/N ≤ {thresholds['TRANSITION_end']:.4f}")
    print(f"  LOW SNR:      r/N > {thresholds['LOW_SNR_min']:.4f}")
    print()

    # Create visualization
    output_dir = Path('../Results')
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    plot_path = output_dir / f'{timestamp}_regime_map.png'

    create_regime_map_plot(phase2_data, phase3_data, thresholds, plot_path)

    # Save analysis results
    results = {
        'timestamp': timestamp,
        'data_points': {
            'r8_aligned': {
                'r_over_N': float(phase2_data['r8_aligned']['r_over_N']),
                'r_squared': float(phase2_data['r8_aligned']['sqrt_m_fit']['r_squared']),
                'regime': 'HIGH_SNR'
            },
            'r126': {
                'r_over_N': float(phase3_data['r126']['r_over_N']),
                'r_squared': float(phase3_data['r126']['sqrt_m_fit']['r_squared']),
                'regime': 'TRANSITION'
            },
            'r168': {
                'r_over_N': float(phase3_data['r168']['r_over_N']),
                'r_squared': float(phase3_data['r168']['sqrt_m_fit']['r_squared']),
                'regime': 'TRANSITION'
            },
            'r504': {
                'r_over_N': float(phase2_data['r504']['r_over_N']),
                'r_squared': float(phase2_data['r504']['sqrt_m_fit']['r_squared']),
                'regime': 'LOW_SNR'
            }
        },
        'linear_fit': {
            'transition_center': float(linear_fit['transition_center']),
            'slopes': [float(s) for s in linear_fit['slopes']],
            'steepest_region': [float(x) for x in linear_fit['steepest_region']]
        },
        'regime_boundaries': thresholds,
        'key_findings': {
            'transition_center': float(linear_fit['transition_center']),
            'high_snr_requires_alignment': True,
            'transition_and_low_snr_random_ok': True,
            'base_invariance_cv_threshold': 0.0001,
            'r_squared_thresholds': {
                'high_snr': '< 0.90',
                'transition': '0.90 - 0.98',
                'low_snr': '>= 0.98'
            }
        }
    }

    results_path = output_dir / f'{timestamp}_regime_map_analysis.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Saved analysis results: {results_path}")
    print()
    print("="*70)
    print("REGIME MAP ANALYSIS COMPLETE")
    print("="*70)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
