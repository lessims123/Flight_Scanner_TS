"""Script de setup pour faciliter l'installation."""

from setuptools import setup, find_packages

setup(
    name="flight-deal-scanner",
    version="1.0.0",
    description="Scanner automatique de billets d'avion avec détection de deals",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.9.0",
        "aiosqlite>=0.19.0",
        "pyyaml>=6.0.1",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.11",
)

