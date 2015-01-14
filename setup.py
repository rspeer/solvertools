#!/usr/bin/env python
VERSION = "2015.0"

from setuptools import find_packages, setup

setup(
    name="solvertools",
    version=VERSION,
    packages=find_packages(),
    install_requires=[
        'numpy', 'nltk', 'whoosh', 'unidecode'
    ],
)
