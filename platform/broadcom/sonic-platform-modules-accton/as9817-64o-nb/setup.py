#!/usr/bin/env python

import os
from setuptools import setup
os.listdir

setup(
    name='as9817_64o_nb',
    version='1.0',
    description='Module to initialize Accton AS9817-64O-NB platforms',

    packages=['as9817_64o_nb'],
    package_dir={'as9817_64o_nb': 'as9817-64o-nb/classes'},
)
