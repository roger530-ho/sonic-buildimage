#!/usr/bin/env python

import os
from setuptools import setup
os.listdir

setup(
    name='as9817_64d_nb',
    version='1.0',
    description='Module to initialize Accton AS9817-64D-NB platforms',

    packages=['as9817_64d_nb'],
    package_dir={'as9817_64d_nb': 'as9817-64d-nb/classes'},
)
