#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

import os
import re
import posixpath

try:
    import tomli
except ImportError:
    tomli = None

try:
    from setuptools import setup, Extension, find_packages
except ImportError:
    from distutils.core import setup, Extension
    
    def find_packages(where=''):
        import os
        packages = []
        for root, dirs, files in os.walk(where):
            if '__init__.py' in files:
                package = root.replace(where, '').replace(os.sep, '.').lstrip('.')
                packages.append(package)
        return packages

def get_version():
    with open('src/litefs/_version.py', 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
        return match.group(1) if match else "0.4.0"

def get_author():
    with open('src/litefs/_version.py', 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r"__author__\s*=\s*['\"]([^'\"]+)['\"]", content)
        return match.group(1) if match else "Leafcoder"

def get_license():
    with open('src/litefs/_version.py', 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r"__license__\s*=\s*['\"]([^'\"]+)['\"]", content)
        return match.group(1) if match else "MIT"

def get_long_description():
    with open('README.md', 'r', encoding='utf-8') as f:
        return f.read()

def get_dependencies():
    if tomli is not None:
        try:
            with open('pyproject.toml', 'rb') as f:
                config = tomli.load(f)
                return config.get('project', {}).get('dependencies', [])
        except Exception:
            pass
    
    return [
        "argh>=0.26.2",
        "greenlet>=0.4.13",
        "Mako>=1.0.6",
        "MarkupSafe>=1.1.1",
        "pathtools>=0.1.2",
        "PyYAML>=5.1",
        "watchdog>=0.8.3",
    ]

setup(
    name='litefs',
    version=get_version(),
    description='Build a web server framework using Python.',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    author=get_author(),
    author_email='leafcoder@gmail.com',
    url='https://github.com/leafcoder/litefs',
    license=get_license(),
    platforms='any',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    package_data={
        'litefs': ['py.typed'],
    },
    install_requires=get_dependencies(),
    entry_points={
        'console_scripts': [
           'litefs=litefs.cli:main',
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.8',
)