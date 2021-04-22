#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

import os
import re
import posixpath

try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension

def get_str(var_name):
    src_py = open('litefs.py').read()
    return re.search(
        r"%s\s*=\s*['\"]([^'\"]+)['\"]" % var_name, src_py).group(1)

def get_long_str(var_name):
    src_py = open('litefs.py').read()
    return re.search(
        r"%s\s*=\s*['\"]{3}([^'\"]+)['\"]{3}" % var_name, src_py).group(1)

setup(
    name='litefs',
    version=get_str('__version__'),
    description='Build a web server framework using Python.',
    long_description=get_long_str('__doc__'),
    author=get_str('__author__'),
    author_email='leafcoder@gmail.com',
    url='https://github.com/leafcoder/litefs',
    py_modules=['litefs'],
    license=get_str('__license__'),
    platforms='any',
    package_data={
        '': ['*.txt', '*.md', 'LICENSE', 'MANIFEST.in'],
        'demo': ['demo/*', '*.py'],
        'test': ['test/*', '*.py']
    },
    install_requires=open('requirements.txt').read().split('\n'),
    entry_points={
        'console_scripts': [
           'litefs=litefs:test_server',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        "Operating System :: OS Independent",
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
