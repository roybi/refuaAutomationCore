"""
Setup configuration for refua-automation-core framework package.

This package is a reusable test automation framework for the MEDITEK medical system.
Built with Python and Playwright.

Installation:
    pip install refua-automation-core

Development:
    pip install -e ".[dev]"

With Figma integration:
    pip install -e ".[figma]"
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="refua-automation-core",
    version="1.0.0",
    description="Reusable test automation framework for MEDITEK medical system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Team",
    author_email="your-team@example.com",
    url="https://github.com/your-org/refuaAutomationCore",
    license="Proprietary",

    # Package discovery
    packages=find_packages(exclude=["tests*", "*.tests"]),
    python_requires=">=3.9",

    # Core dependencies (minimal set required for framework)
    install_requires=[
        "playwright>=1.40.0",          # Browser automation
        "python-dotenv>=1.0.0",        # Environment configuration
        "requests>=2.31.0",            # HTTP requests (for Figma API)
    ],

    # Optional dependencies
    extras_require={
        # Figma visual regression testing
        "figma": [
            "pillow>=9.0.0",           # Image comparison
        ],

        # Development tools
        "dev": [
            "pytest>=7.0.0",
            "pytest-xdist>=3.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
        ],
    },

    # Include non-Python files
    include_package_data=True,
    package_data={
        "refua_core": [
            "config/devices.json",     # Device profiles
        ],
    },

    # Package metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Testing",
    ],

    keywords=[
        "automation",
        "testing",
        "playwright",
        "medical",
        "meditek",
        "qa",
        "pytest",
    ],

    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/your-org/refuaAutomationCore/issues",
        "Source": "https://github.com/your-org/refuaAutomationCore",
        "Documentation": "https://github.com/your-org/refuaAutomationCore/wiki",
    },
)
