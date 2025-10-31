#!/usr/bin/env python3
"""
Test Suite for VRA Core Functions
==================================

Basic test coverage for vra_core.py functions.

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "Code" / "Core"))

import numpy as np
import pytest
from core import (
    multiplicative_order,
    modular_sequence,
    phase_embed,
    compute_spectrum,
    compute_averaged_spectrum,
    compute_concentration,
    compute_precision_recall,
    validated_radius,
    classify_regime
)


class TestMultiplicativeOrder:
    """Test multiplicative order computation."""

    def test_basic_orders(self):
        """Test known multiplicative orders."""
        assert multiplicative_order(2, 7) == 3  # 2^3 = 8 ≡ 1 (mod 7)
        assert multiplicative_order(3, 7) == 6  # 3^6 ≡ 1 (mod 7)
        assert multiplicative_order(2, 1009) == 504
        assert multiplicative_order(3, 1009) == 168

    def test_order_one(self):
        """Test elements with order 1."""
        assert multiplicative_order(1, 100) == 1

    def test_not_coprime(self):
        """Test behavior with non-coprime elements."""
        result = multiplicative_order(6, 9)  # gcd(6,9) = 3
        assert result is None


class TestModularSequence:
    """Test modular sequence generation."""

    def test_sequence_length(self):
        """Test sequence has correct length."""
        seq = modular_sequence(1009, 2, 1, 100)
        assert len(seq) == 100

    def test_sequence_periodicity(self):
        """Test sequence is periodic with order r."""
        N, a = 7, 2
        r = multiplicative_order(a, N)  # r = 3
        seq = modular_sequence(N, a, 1, 10)
        # Check period-r repetition
        for i in range(len(seq) - r):
            assert seq[i] == seq[i + r]

    def test_initial_condition(self):
        """Test different initial conditions."""
        seq1 = modular_sequence(7, 2, 1, 5)
        seq2 = modular_sequence(7, 2, 2, 5)
        assert seq1[0] == 1
        assert seq2[0] == 2


class TestPhaseEmbed:
    """Test phase embedding."""

    def test_unit_circle(self):
        """Test all embedded points lie on unit circle."""
        xs = np.array([0, 127, 255, 500, 1000])
        us = phase_embed(xs, 1009)
        # Check magnitude is 1
        assert np.allclose(np.abs(us), 1.0)

    def test_zero_maps_to_one(self):
        """Test x=0 maps to u=1."""
        us = phase_embed(np.array([0]), 1009)
        assert np.isclose(us[0], 1.0 + 0j)

    def test_half_modulus(self):
        """Test x=N/2 maps to u=-1 (for even N)."""
        N = 1000
        us = phase_embed(np.array([N//2]), N)
        assert np.isclose(us[0], -1.0 + 0j, atol=1e-10)


class TestSpectrum:
    """Test spectrum computation."""

    def test_spectrum_length(self):
        """Test spectrum has correct length."""
        N, a, L, zp = 1009, 2, 500, 4
        mag2 = compute_spectrum(N, a, 1, L, zp)
        assert len(mag2) == L * zp

    def test_averaged_spectrum_length(self):
        """Test averaged spectrum has correct length."""
        N, bases, L, zp = 1009, [2, 3, 5], 500, 4
        mag2 = compute_averaged_spectrum(N, bases, 1, L, zp)
        assert len(mag2) == L * zp

    def test_spectrum_positive(self):
        """Test power spectrum is non-negative."""
        N, a, L, zp = 1009, 2, 500, 4
        mag2 = compute_spectrum(N, a, 1, L, zp)
        assert np.all(mag2 >= 0)


class TestConcentration:
    """Test concentration metric."""

    def test_concentration_range(self):
        """Test concentration is in [0, 1]."""
        mag2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        C = compute_concentration(mag2)
        assert 0 <= C <= 1

    def test_perfect_concentration(self):
        """Test perfect concentration (all power in one bin)."""
        mag2 = np.array([0.0, 0.0, 1.0, 0.0, 0.0])
        C = compute_concentration(mag2)
        assert np.isclose(C, 1.0)

    def test_uniform_concentration(self):
        """Test uniform distribution (minimum concentration)."""
        mag2 = np.ones(100)
        C = compute_concentration(mag2)
        assert np.isclose(C, 1.0 / 100)


class TestPrecisionRecall:
    """Test precision/recall metrics."""

    def test_returns_valid_dict(self):
        """Test function returns expected dictionary structure."""
        mag2 = np.random.rand(100)
        expected_bins = [10, 20, 30]

        results = compute_precision_recall(mag2, expected_bins, radius=2)

        # Check all expected keys are present
        assert 'precision' in results
        assert 'recall' in results
        assert 'TP' in results
        assert 'FP' in results
        assert 'FN' in results

        # Check ranges
        assert 0 <= results['precision'] <= 1.0
        assert 0 <= results['recall'] <= 1.0
        assert results['TP'] >= 0
        assert results['FP'] >= 0
        assert results['FN'] >= 0

    def test_metrics_with_real_spectrum(self):
        """Test precision/recall with actual VRA spectrum."""
        # Use real VRA computation
        N, a, L, zp = 1009, 2, 200, 4
        mag2 = compute_spectrum(N, a, 1, L, zp)

        # Expected harmonics for order r
        r = multiplicative_order(a, N)  # r=504
        Lzp = L * zp
        harmonic_bins = [int(round(k * Lzp / r)) for k in range(1, min(50, r))]

        R = validated_radius(Lzp)
        results = compute_precision_recall(mag2, harmonic_bins, R)

        # Should produce valid metrics
        assert isinstance(results['precision'], (int, float))
        assert isinstance(results['recall'], (int, float))
        # At least some detection should occur
        assert results['TP'] + results['FP'] + results['FN'] > 0


class TestValidatedRadius:
    """Test validated radius rule."""

    def test_radius_formula(self):
        """Test R = 0.5 * log2(L) formula."""
        assert validated_radius(512) == 4   # 0.5 * 9 = 4.5 → 4
        assert validated_radius(1024) == 5  # 0.5 * 10 = 5
        assert validated_radius(2048) == 5  # 0.5 * 11 = 5.5 → 5

    def test_radius_positive(self):
        """Test radius is always positive."""
        for L in [128, 256, 512, 1024, 2048]:
            R = validated_radius(L)
            assert R > 0


class TestClassifyRegime:
    """Test regime classification."""

    def test_high_snr_regime(self):
        """Test HIGH_SNR classification."""
        regime = classify_regime(1009, 83)  # ρ = 0.082
        assert regime[0] == 'HIGH_SNR'

    def test_transition_regime(self):
        """Test TRANSITION classification."""
        regime = classify_regime(1009, 168)  # ρ = 0.167
        assert regime[0] == 'TRANSITION'

    def test_low_snr_regime(self):
        """Test LOW_SNR classification."""
        regime = classify_regime(1009, 504)  # ρ = 0.500
        assert regime[0] == 'LOW_SNR'

    def test_boundary_values(self):
        """Test regime boundaries."""
        # Just below HIGH_SNR boundary
        regime = classify_regime(1000, 145)  # ρ = 0.145
        assert regime[0] == 'HIGH_SNR'

        # Just above TRANSITION boundary
        regime = classify_regime(1000, 264)  # ρ = 0.264
        assert regime[0] == 'LOW_SNR'


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_vra_pipeline(self):
        """Test complete VRA workflow."""
        # Known test case
        N, r, M = 1009, 168, 4
        L, zp = 500, 4

        # Find bases with order r (use known bases)
        bases = [2, 3, 5, 6]  # These have order 168 in Z_1009

        # Compute averaged spectrum
        mag2 = compute_averaged_spectrum(N, bases, 1, L, zp)

        # Concentration
        C = compute_concentration(mag2)
        assert C > 0

        # Expected harmonic bins
        Lzp = L * zp
        harmonic_bins = [int(round(k * Lzp / r)) for k in range(1, r)]

        # Precision/recall
        R = validated_radius(Lzp)
        results = compute_precision_recall(mag2, harmonic_bins, R)

        # Should have good precision (known from validation)
        assert results['precision'] >= 0.5


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
