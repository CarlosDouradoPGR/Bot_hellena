from setuptools import setup, find_packages

setup(
    name="kisoft-dashboard",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "streamlit==1.28.1",
        "pandas==2.0.3",
        "plotly==5.15.0",
        "numpy==1.24.3",
        "setuptools==68.2.2"
    ],
    python_requires=">=3.8",
)
