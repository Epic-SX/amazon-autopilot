from setuptools import setup, find_packages

setup(
    name="product-search",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.7.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
    ],
) 