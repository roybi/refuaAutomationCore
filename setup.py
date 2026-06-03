from pathlib import Path
from setuptools import find_packages, setup

# Pull version from single source of truth
about: dict = {}
exec((Path(__file__).parent / "refua_core" / "version.py").read_text(), about)

readme = Path(__file__).parent / "README.md"

setup(
    name="refua-automation-core",
    version=about["__version__"],
    description="Reusable test automation framework for MEDITEK",
    long_description=readme.read_text(encoding="utf-8") if readme.exists() else "",
    long_description_content_type="text/markdown",
    author="Refua Automation Team",
    url="https://github.com/roybi/refuaAutomationCore",
    license="Proprietary",
    packages=find_packages(exclude=["tests*", "*.tests"]),
    python_requires=">=3.9",
    install_requires=[
        "playwright>=1.40.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "packaging>=21.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-xdist>=3.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
    ],
    keywords=["automation", "testing", "playwright", "meditek", "qa", "pytest"],
    project_urls={
        "Source": "https://github.com/roybi/refuaAutomationCore",
        "Bug Reports": "https://github.com/roybi/refuaAutomationCore/issues",
    },
)
