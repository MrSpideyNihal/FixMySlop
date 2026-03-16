"""
Legacy setup.py for compatibility with older pip versions.
"""
from setuptools import setup, find_packages

setup(
    name="fixmyslop",
    version="0.2.1",
    packages=find_packages(include=["fixmyslop*", "cli*", "core*", "ui*", "utils*"]),
    py_modules=["main"],
    python_requires=">=3.10",
    install_requires=[
        "openai>=1.30.0",
        "typer>=0.12.0",
        "rich>=13.7.0",
        "pyyaml>=6.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "gui": ["PyQt5>=5.15.10"],
        "analysis": ["ruff>=0.4.0", "bandit>=1.7.0"],
        "dev": ["pytest>=8.0.0", "pytest-qt>=4.4.0"],
    },
    entry_points={
        "console_scripts": [
            "fixmyslop=fixmyslop.__main__:main",
        ],
    },
)
