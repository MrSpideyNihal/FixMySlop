"""
Legacy setup.py for compatibility with older pip versions.
"""
from setuptools import setup, find_packages

setup(
    name="fixmyslop",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "openai>=1.30.0",
        "typer>=0.12.0",
        "rich>=13.7.0",
        "pyyaml>=6.0",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "fixmyslop=main:main",
        ],
    },
)
