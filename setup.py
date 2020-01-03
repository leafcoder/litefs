#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

import os
import re
import posixpath

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
try:
    from Cython.Build import cythonize
except ImportError:
    os.system('pip install cython')
    from Cython.Build import cythonize

language_level = 2
if sys.version_info[0] > 2:
    language_level = 3

def get_str(var_name):
    src_py = open('litefs.py').read()
    return re.search(
        r"%s\s*=\s*['\"]([^'\"]+)['\"]" % var_name, src_py).group(1)

def get_long_str(var_name):
    src_py = open('litefs.py').read()
    return re.search(
        r"%s\s*=\s*['\"]{3}([^'\"]+)['\"]{3}" % var_name, src_py).group(1)

version = get_str('__version__')
author  = get_str('__author__')
license = get_str('__license__')
long_description = get_long_str('__doc__')

setup(
    name='litefs',
    version=version,
    description='Build a web server framework using Python.',
    long_description=long_description,
    author=author,
    author_email='leafcoder@gmail.com',
    url='https://github.com/leafcoder/litefs',
    py_modules=['litefs'],
    ext_modules=cythonize(
        'litefs.py',
        compiler_directives={
            'language_level' : language_level
        }
    ),
    license=license,
    platforms='any',
    package_data={
        '': ['*.txt', '*.md', 'LICENSE', 'example.py', 'MANIFEST.in'],
        'site': ['site/*', '*.py'],
        'test': ['test/*', '*.py']
    },
    install_requires=open('requirements.txt').read().split('\n'),
    setup_requires=['cython', 'tox'],
    entry_points={
        'console_scripts': [
           'litefs=litefs.entry:test_server',
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
