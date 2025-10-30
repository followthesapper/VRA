# VRA Reproducibility Environment
# ================================
# Exact environment for reproducing all VRA validation experiments
# Phase 4.2 - Statistical Rigor & Reproducibility

FROM python:3.10-slim

LABEL maintainer="Dylan Vaca"
LABEL description="Reproducible environment for VRA (Vaca Resonance Analysis) validation experiments"
LABEL version="1.0.0"

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

# Create output directories
RUN mkdir -p Data/Reproduced Figures/Reproduced

# Set Python path
ENV PYTHONPATH=/vra/Code/Core:/vra/Code/Statistics:${PYTHONPATH}

# Default command: run reproduction verification
CMD ["python3", "REPRODUCE.py"]
