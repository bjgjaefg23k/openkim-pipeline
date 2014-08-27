#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
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
    install_requires=[
        'simplejson==3.6.3',
        'pyzmq==14.3.1',
        'beanstalkc==0.4.0',
        'Pygments==1.6',
        'Jinja2==2.7.3',
        'pymongo==2.7.2',
        "pyzmq==14.3.1",
        "numpy==1.8.2",
    ]
)
