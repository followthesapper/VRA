#!/usr/bin/env python3
"""
E12: VRA Tokens for Transformers

Goal: Convert harmonic structure to compact tokens for neural networks
Success Criteria: +1-2% accuracy or 30-50% fewer labeled samples
Expected GPU Speedup: 20-100x for batch token generation

Applications:
- Speech command classification
- Machinery fault detection
- ECG arrhythmia classification

VRA provides structure-aware embeddings capturing periodicity.

REQUIRES GPU - will fail fast if not available.
"""

import sys
import numpy as np
from pathlib import Path
import json
from datetime import datetime

# Add GPU utilities to path
sys.path.insert(0, str(Path(__file__).parent))
from gpu_utils import check_gpu_available, GPURequiredError, gpu_fft_batch

# Add VRA core to path
_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "Code" / "VRA"))
from core import modular_sequence, phase_embed, multiplicative_order


def vra_tokenize(signal_batch, N, a, L, M, token_dim=32, framework='cupy'):
    """
    Convert signal batch to VRA tokens on GPU.

    Parameters
    ----------
    signal_batch : ndarray, shape (batch_size, signal_length)
        Batch of input signals
    N : int
        Modulus
    a : int
        Base
    L : int
        Sequence length
    M : int
        Number of bases to average
    token_dim : int
        Dimension of output token embedding
    framework : str
        'cupy' or 'torch'

    Returns
    -------
    tokens : ndarray, shape (batch_size, token_dim)
        VRA token embeddings
    """
    cp = check_gpu_available(framework)

    batch_size = signal_batch.shape[0]
    r = multiplicative_order(a, N)

    # Generate modular sequence template (can be reused across batch)
    xs = modular_sequence(N, a, 1, L)
    u_template = phase_embed(xs, N)

    tokens = []

    for i in range(batch_size):
        # Simple embedding: modulate template by signal envelope
        # Real implementation would use more sophisticated encoding
        signal = signal_batch[i, :L]
        u_modulated = u_template * (1 + 0.1 * signal[:L])

        # Compute spectrum on GPU
        x_batch = np.array([u_modulated for _ in range(M)], dtype=np.complex64)
        spectra = gpu_fft_batch(x_batch, framework)

        # Extract harmonic bins
        Lzp = spectra.shape[1]
        harmonic_bins = [int(round(ell * Lzp / r)) for ell in range(1, min(r, token_dim+1))]

        # Token: complex amplitudes at harmonic bins
        harmonic_amplitudes = spectra[0, harmonic_bins[:token_dim]]

        # Real-valued token: [real part, imag part, magnitude, phase]
        token_features = np.concatenate([
            np.real(harmonic_amplitudes),
            np.imag(harmonic_amplitudes),
            np.abs(harmonic_amplitudes),
            np.angle(harmonic_amplitudes),
        ])

        # Truncate/pad to token_dim
        token_features = token_features[:token_dim]
        if len(token_features) < token_dim:
            token_features = np.pad(token_features, (0, token_dim - len(token_features)))

        tokens.append(token_features)

    return np.array(tokens)


def baseline_mfcc_tokens(signal_batch, n_mfcc=32):
    """
    Baseline: MFCC tokens for comparison.

    Parameters
    ----------
    signal_batch : ndarray
        Input signals
    n_mfcc : int
        Number of MFCC coefficients

    Returns
    -------
    tokens : ndarray
        MFCC token embeddings
    """
    # Placeholder - real implementation would compute MFCCs
    batch_size = signal_batch.shape[0]
    return np.random.randn(batch_size, n_mfcc)


def train_classifier(tokens, labels, method='logistic'):
    """
    Train simple classifier on tokens.

    Parameters
    ----------
    tokens : ndarray, shape (n_samples, token_dim)
        Token embeddings
    labels : ndarray, shape (n_samples,)
        Class labels
    method : str
        Classifier type

    Returns
    -------
    dict
        Training results including accuracy, F1
    """
    # Placeholder - real implementation would use sklearn or pytorch
    n_samples = tokens.shape[0]
    n_correct = int(0.85 * n_samples)  # Mock 85% accuracy

    return {
        'method': method,
        'accuracy': n_correct / n_samples,
        'f1_score': 0.85,
        'samples_used': n_samples,
    }


def few_shot_experiment(vra_tokens, mfcc_tokens, labels, shot_sizes=[10, 25, 50, 100]):
    """
    Test few-shot learning performance.

    Success Criteria: VRA should match MFCC accuracy with 30-50% fewer samples.
    """
    results = []

    for n_shot in shot_sizes:
        # Sample n_shot examples per class
        # Train on VRA tokens
        vra_result = train_classifier(vra_tokens[:n_shot], labels[:n_shot])
        vra_result['token_type'] = 'vra'
        vra_result['n_shot'] = n_shot

        # Train on MFCC tokens
        mfcc_result = train_classifier(mfcc_tokens[:n_shot], labels[:n_shot])
        mfcc_result['token_type'] = 'mfcc'
        mfcc_result['n_shot'] = n_shot

        results.append({'vra': vra_result, 'mfcc': mfcc_result})

        print(f"  {n_shot}-shot: VRA={vra_result['accuracy']:.3f}, MFCC={mfcc_result['accuracy']:.3f}")

    return results


def run_token_experiments(framework='cupy'):
    """
    Run full token generation and classification experiments.
    """
    print("=" * 70)
    print("E12: VRA Tokens for Transformers")
    print("=" * 70)

    # Test parameters
    N, a = 997, 9
    L = 4096
    M = 16
    token_dim = 32
    batch_size = 100

    print(f"\nParameters: N={N}, a={a}, L={L}, M={M}, token_dim={token_dim}")

    # Generate synthetic dataset
    # Real implementation would load speech commands, ECG, etc.
    signal_batch = np.random.randn(batch_size, L)
    labels = np.random.randint(0, 10, batch_size)  # 10 classes

    print(f"\nGenerating VRA tokens for {batch_size} samples...")
    vra_tokens = vra_tokenize(signal_batch, N, a, L, M, token_dim, framework)
    print(f"  VRA tokens shape: {vra_tokens.shape}")

    print(f"\nGenerating baseline MFCC tokens...")
    mfcc_tokens = baseline_mfcc_tokens(signal_batch, n_mfcc=token_dim)
    print(f"  MFCC tokens shape: {mfcc_tokens.shape}")

    print(f"\nRunning few-shot learning experiment...")
    few_shot_results = few_shot_experiment(vra_tokens, mfcc_tokens, labels)

    results = {
        'parameters': {
            'N': N, 'a': a, 'L': L, 'M': M,
            'token_dim': token_dim,
            'batch_size': batch_size,
        },
        'few_shot_results': few_shot_results,
    }

    return results


def main():
    """Main entry point - FAILS FAST if no GPU."""
    print("Checking GPU availability...")

    # FAIL FAST if no GPU
    try:
        cp = check_gpu_available('cupy')
    except GPURequiredError as e:
        print(e)
        print("\n" + "=" * 70)
        print("E12 ABORTED - GPU required")
        print("=" * 70)
        sys.exit(1)

    # Run experiments
    results = run_token_experiments(framework='cupy')

    # Save results
    output_dir = Path(__file__).parent.parent / "Data"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}_vra_tokens.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
    print("\nSuccess Criteria Check:")
    print("  Target: +1-2% accuracy OR 30-50% fewer labeled samples")
    print("  Status: [Manual review required with real datasets]")


if __name__ == "__main__":
    main()
