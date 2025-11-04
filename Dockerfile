# VRA Reproducibility Environment
# ================================
# Exact environment for reproducing all VRA validation experiments
# November 2025 - Complete experimental validation (E1-E27)

FROM python:3.10-slim

LABEL maintainer="Dylan Vaca"
LABEL description="Reproducible environment for VRA (Vaca Resonance Analysis) validation experiments"
LABEL version="2.0.0"
LABEL experiments="E1-E27 (27 main experiments + 15 variants)"
LABEL validation="21/21 experiments validated, IBM Brisbane hardware verified"

# Set working directory
WORKDIR /vra

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies with exact versions
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire VRA codebase
COPY . .

# Set environment variables for reproducibility
ENV PYTHONHASHSEED=42
ENV NUMPY_RANDOM_SEED=42
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1

# Set Python path to include VRA core modules
ENV PYTHONPATH=/vra/Code/Core:/vra/Code/Statistics:${PYTHONPATH}

# Create output directories for experiments
RUN mkdir -p \
    Experiments/*/Data \
    Experiments/*/Figures \
    Data/Reproduced \
    Figures/Reproduced

# Verify installation
RUN python3 -c "import numpy; import matplotlib; import scipy; print('✓ Dependencies verified')"

# Default command: run full experimental validation suite
CMD ["python3", "Code/Scripts/REPRODUCE.py", "--all"]

# Alternative commands (documented):
# Run single experiment:     docker run vra python3 Code/Scripts/REPRODUCE.py --experiment E1
# Run by category:           docker run vra python3 Code/Scripts/REPRODUCE.py --category math
# Run specific categories:   docker run vra python3 Code/Scripts/REPRODUCE.py --category ai
# Interactive shell:         docker run -it vra /bin/bash
