#!/usr/bin/env python3

from setuptools import setup, find_packages
import re

# Detect version
with open('restomatic/__init__.py', 'r') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]+)[\'"]',
                        f.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Internal Error: Unable to find version information')

setup(name='restomatic',
      version=version,
      description='Automatic JSON-based API generator, including a SQL Query Compositor and WSGI Endpoint Router',
      url='https://github.com/dtulga/restomatic',
      author='David Tulga',
      author_email='davidtulga@gmail.com',
      license='MIT',
      py_modules=['restomatic'],
      packages=find_packages())
