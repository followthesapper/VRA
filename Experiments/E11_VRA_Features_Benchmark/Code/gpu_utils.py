#!/usr/bin/env python3
"""
GPU Utilities for Tier 5 AI/ML Experiments

CRITICAL: All Tier 5 experiments REQUIRE GPU.
If GPU is not available, experiments will FAIL with clear error message.
NO silent CPU fallback - this prevents multi-day accidental CPU runs.
"""

import sys
import numpy as np

class GPURequiredError(Exception):
    """Raised when GPU is required but not available."""
    pass

def check_gpu_available(framework='cupy'):
    """
    Check if GPU is available and working.

    Parameters
    ----------
    framework : str
        'cupy' or 'torch'

    Raises
    ------
    GPURequiredError
        If GPU is not available or not working

    Returns
    -------
    module
        The GPU framework module (cupy or torch)
    """
    if framework == 'cupy':
        try:
            import cupy as cp
            # Test GPU is actually working
            test_array = cp.array([1.0, 2.0, 3.0])
            _ = cp.fft.fft(test_array)
            del test_array

            device_name = cp.cuda.Device(0).compute_capability
            print(f"✅ GPU available: CuPy {cp.__version__}, Compute Capability {device_name}")
            return cp

        except ImportError as e:
            raise GPURequiredError(
                f"❌ CuPy not installed or failed to import: {e}\n"
                f"   Install with: pip install cupy-cuda12x (adjust for your CUDA version)\n"
                f"   See: https://docs.cupy.dev/en/stable/install.html"
            ) from e
        except Exception as e:
            raise GPURequiredError(
                f"❌ GPU not available or not working with CuPy: {e}\n"
                f"   Check: nvidia-smi\n"
                f"   Check: echo $CUDA_VISIBLE_DEVICES"
            ) from e

    elif framework == 'torch':
        try:
            import torch
            if not torch.cuda.is_available():
                raise GPURequiredError(
                    f"❌ PyTorch installed but CUDA not available\n"
                    f"   torch.cuda.is_available() = False\n"
                    f"   Install GPU-enabled PyTorch from: https://pytorch.org/get-started/locally/"
                )

            # Test GPU is actually working
            test_tensor = torch.randn(10, 10).cuda()
            _ = torch.fft.fft(test_tensor, dim=-1)
            del test_tensor
            torch.cuda.empty_cache()

            device_name = torch.cuda.get_device_name(0)
            print(f"✅ GPU available: PyTorch {torch.__version__}, Device: {device_name}")
            return torch

        except ImportError as e:
            raise GPURequiredError(
                f"❌ PyTorch not installed: {e}\n"
                f"   Install with: pip install torch (with CUDA support)\n"
                f"   See: https://pytorch.org/get-started/locally/"
            ) from e
        except GPURequiredError:
            raise
        except Exception as e:
            raise GPURequiredError(
                f"❌ GPU not available or not working with PyTorch: {e}"
            ) from e
    else:
        raise ValueError(f"Unknown framework: {framework}. Use 'cupy' or 'torch'")


def gpu_fft_batch(x_batch, framework='cupy'):
    """
    Batch FFT on GPU with automatic framework selection.

    Parameters
    ----------
    x_batch : array_like, shape (M, L)
        M sequences of length L
    framework : str
        'cupy' or 'torch'

    Returns
    -------
    ndarray, shape (M, L)
        FFT of each sequence

    Raises
    ------
    GPURequiredError
        If GPU is not available
    """
    if framework == 'cupy':
        cp = check_gpu_available('cupy')
        x_gpu = cp.asarray(x_batch, dtype=cp.complex64)
        fft_gpu = cp.fft.fft(x_gpu, axis=-1)
        return cp.asnumpy(fft_gpu)

    elif framework == 'torch':
        torch = check_gpu_available('torch')
        x_gpu = torch.as_tensor(x_batch, dtype=torch.complex64).cuda()
        fft_gpu = torch.fft.fft(x_gpu, dim=-1)
        return fft_gpu.cpu().numpy()
    else:
        raise ValueError(f"Unknown framework: {framework}")


def gpu_coherent_average(x_batch, framework='cupy'):
    """
    Compute coherent average on GPU: |mean(FFT(x_m))|^2

    Parameters
    ----------
    x_batch : array_like, shape (M, L)
        M sequences of length L
    framework : str
        'cupy' or 'torch'

    Returns
    -------
    ndarray, shape (L,)
        Power spectrum of coherent average

    Raises
    ------
    GPURequiredError
        If GPU is not available
    """
    if framework == 'cupy':
        cp = check_gpu_available('cupy')
        x_gpu = cp.asarray(x_batch, dtype=cp.complex64)
        fft_gpu = cp.fft.fft(x_gpu, axis=-1)  # (M, L)
        avg_gpu = cp.mean(fft_gpu, axis=0)     # (L,)
        power_gpu = cp.abs(avg_gpu) ** 2       # (L,)
        return cp.asnumpy(power_gpu)

    elif framework == 'torch':
        torch = check_gpu_available('torch')
        x_gpu = torch.as_tensor(x_batch, dtype=torch.complex64).cuda()
        fft_gpu = torch.fft.fft(x_gpu, dim=-1)      # (M, L)
        avg_gpu = torch.mean(fft_gpu, dim=0)        # (L,)
        power_gpu = torch.abs(avg_gpu) ** 2         # (L,)
        return power_gpu.cpu().numpy()
    else:
        raise ValueError(f"Unknown framework: {framework}")


def print_gpu_info():
    """Print detailed GPU information for debugging."""
    print("=" * 70)
    print("GPU Environment Check")
    print("=" * 70)

    # Check nvidia-smi
    import subprocess
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,compute_cap',
                               '--format=csv,noheader'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"NVIDIA GPU: {result.stdout.strip()}")
        else:
            print(f"❌ nvidia-smi failed: {result.stderr}")
    except Exception as e:
        print(f"❌ nvidia-smi not available: {e}")

    # Check CuPy
    print("\nCuPy Status:")
    try:
        import cupy as cp
        print(f"  Version: {cp.__version__}")
        print(f"  CUDA available: {cp.cuda.is_available()}")
        if cp.cuda.is_available():
            print(f"  Device count: {cp.cuda.runtime.getDeviceCount()}")
            print(f"  Current device: {cp.cuda.Device()}")
    except ImportError:
        print("  ❌ Not installed")
    except Exception as e:
        print(f"  ⚠️  Import failed: {e}")

    # Check PyTorch
    print("\nPyTorch Status:")
    try:
        import torch
        print(f"  Version: {torch.__version__}")
        print(f"  CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  Device count: {torch.cuda.device_count()}")
            print(f"  Device name: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("  ❌ Not installed")
    except Exception as e:
        print(f"  ⚠️  Import failed: {e}")

    print("=" * 70)


if __name__ == "__main__":
    """Test GPU availability when run as script."""
    print_gpu_info()

    print("\nTesting GPU frameworks...")

    # Test CuPy
    print("\n1. Testing CuPy...")
    try:
        cp = check_gpu_available('cupy')
        print("   CuPy GPU test passed ✅")
    except GPURequiredError as e:
        print(f"   CuPy GPU test FAILED ❌\n{e}")

    # Test PyTorch
    print("\n2. Testing PyTorch...")
    try:
        torch = check_gpu_available('torch')
        print("   PyTorch GPU test passed ✅")
    except GPURequiredError as e:
        print(f"   PyTorch GPU test FAILED ❌\n{e}")

    print("\nGPU check complete.")
