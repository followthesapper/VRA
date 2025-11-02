"""
VRA Core Package
================

Main VRA implementation for phase-coherent spectral order detection.

Modules:
    - core: Core VRA functions and algorithms
    - uncertainty: Uncertainty quantification and error analysis

Author: Dylan Vaca
Date: October 2025
"""

from .core import (
    modular_sequence,
    multiplicative_order,
    phase_embed,
    apply_window,
    compute_spectrum,
    compute_averaged_spectrum,
    compute_concentration,
    compute_precision_recall,
    validated_radius,
    classify_regime
)

__version__ = "1.0.0"
__all__ = [
    'modular_sequence',
    'multiplicative_order',
    'phase_embed',
    'apply_window',
    'compute_spectrum',
    'compute_averaged_spectrum',
    'compute_concentration',
    'compute_precision_recall',
    'validated_radius',
    'classify_regime'
]
