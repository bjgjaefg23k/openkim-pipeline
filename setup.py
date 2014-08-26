#!/usr/bin/env python

from distutils.core import setup
import glob

setup(
    name='pipeline',
    version="1.0.0",
    description='OpenKIM Pipeline package',
    author='Matt Bierbaum, Alexander Alemi',
    author_email='mkb72@cornell.edu',
    url='http://www.python.org/sigs/distutils-sig/',
    packages=['pipeline'],
    scripts=glob.glob("tools/*"),
)
