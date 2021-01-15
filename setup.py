#!/usr/bin/env python
VERSION = "2020.0"

from setuptools import find_packages, setup

setup(
    name="solvertools",
    version=VERSION,
    packages=find_packages(),
    install_requires=[
        'pandas', 'unidecode', 'natsort', 'flask', 'tqdm'
    ],
)
