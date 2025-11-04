"""
VRA (Vaca Resonance Analysis) - Setup Configuration
====================================================

A spectral framework for multiplicative order detection using coherent
Fourier averaging.

Author: Dylan Vaca
License: MIT
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="vra",
    version="1.0.0",
    author="Dylan Vaca",
    author_email="dylan.vaca@example.com",
    description="Spectral framework for multiplicative order detection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/followthesapper/VRA",
    project_urls={
        "Bug Tracker": "https://github.com/followthesapper/VRA/issues",
        "Documentation": "https://github.com/followthesapper/VRA",
        "Source Code": "https://github.com/followthesapper/VRA",
    },
    packages=find_packages(where="Code"),
    package_dir={"": "Code"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Topic :: Security :: Cryptography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "matplotlib>=3.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=5.0",
        ],
        "docs": [
            "sphinx>=5.0",
            "sphinx-rtd-theme>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vra=Applications.vra_cli:main",
            "vra-check-rsa=Applications.rsa_quality_checker:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="multiplicative-order spectral-analysis number-theory cryptography fourier-transform",
)
