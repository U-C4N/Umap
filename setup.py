from setuptools import setup, find_packages

setup(
    name="umap",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "osmnx>=2.0.0",
        "matplotlib>=3.0.0",
        "shapely>=2.0.0",
        "geopandas>=0.9.0",
        "numpy>=1.19.0",
        "pandas>=1.2.0",
    ],
    extras_require={
        "plotter": ["vsketch>=1.0.0"],
    },
    python_requires=">=3.8",
)
