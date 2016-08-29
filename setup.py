#!/usr/bin/env python
# -*- coding: utf-8 -*-#
# @(#)setup.py
#
#
# Copyright (C) 2013, 2015, 2016 S3IT, University of Zurich. All rights reserved.
#
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

__docformat__ = 'reStructuredText'

import os
import sys
import shutil

# fix Python issue 15881 (on Python <2.7.5)
try:
    import multiprocessing
except ImportError:
    pass

# Ensure we use a recent enough version of setuptools: CentOS7 still
# ships with 0.9.8!  There has been some instability in the support
# for PEP-496 environment markers recently, but Setuptools 20.6.8
# seems to have restored full support for them.  See also issue #249.
from ez_setup import use_setuptools
use_setuptools(version='20.6.8')

from setuptools.command import sdist


## auxiliary functions
#
def read_whole_file(path):
    """
    Return file contents as a string.
    """
    with open(path, 'r') as stream:
        return stream.read()

def read_file_lines(path):
    """
    Return list of file lines, stripped of leading and trailing
    whitespace (including newlines), and of comment lines.
    """
    with open(path, 'r') as stream:
        lines = [line.strip() for line in stream.readlines()]
        return [line for line in lines
                if line != '' and not line.startswith('#')]


## state run-time dependencies
#

required_packages = [
    'PyCLI',
    'pycrypto',
    'paramiko',
    'ansible>=2.0',
    'voluptuous>=0.8.2',
    'configobj',
    'coloredlogs',
    # EC2 clouds
    'boto',
    # OpenStack clouds
    'netifaces',
    #'python-novaclient',  # need different vers for Py 2.6 and 2.7, see below
    'pbr',
    # GCE cloud
    'google-api-python-client',
    'python-gflags',
]

if sys.version_info < (2, 7):
    # Additional dependencies for Python 2.6:
    # - Google api python client *requires* argparse,
    #   cfr. http://code.google.com/p/google-api-python-client/issues/detail?id=299
    required_packages.append('argparse')
    # - OpenStack's "keystoneclient" requires `importlib`
    required_packages.append('importlib')
    # - support for Python 2.6 was removed from `novaclient` in commit
    #   81f8fa655ccecd409fe6dcda0d3763592c053e57 which is contained in
    #   releases 3.0.0 and above; however, we also need to pin down
    #   the version of `oslo.config` and all the dependencies thereof,
    #   otherwise `pip` will happily download the latest and
    #   incompatible version,since `python-novaclient` specifies only
    #   the *minimal* version of dependencies it is compatible with...
    required_packages.append('stevedore<1.10.0')
    required_packages.append('debtcollector<1.0.0')
    required_packages.append('keystoneauth<2.0.0')
    required_packages.append('keystoneauth1<2.0.0')  # yes, there's `keystoneauth` and `keystoneauth1` !!
    required_packages.append('oslo.config<3.0.0')
    required_packages.append('oslo.i18n<3.1.0')
    required_packages.append('oslo.serialization<2.1.0')
    required_packages.append('oslo.utils<3.1.0')
    required_packages.append('python-novaclient<3.0.0')
else:
    required_packages.append('python-novaclient')


## test runner setup
#
# See http://tox.readthedocs.org/en/latest/example/basic.html#integration-with-setuptools-distribute-test-commands
# on how to run tox when python setup.py test is run
#
from setuptools.command.test import test as TestCommand

class Tox(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        errno = tox.cmdline(self.test_args)
        sys.exit(errno)


## real setup description begins here
#
from setuptools import setup, find_packages

setup(
    name="elasticluster",
    version=read_whole_file("version.txt").strip(),
    description="A command line tool to create, manage and setup computing clusters hosted on a public or private cloud infrastructure.",
    long_description=read_whole_file('README.rst'),
    author="Services and Support for Science IT, University of Zurich",
    author_email="team@s3it.lists.uzh.ch",
    license="LGPL",
    keywords="cloud openstack amazon ec2 ssh hpc gridengine torque slurm batch job elastic",
    url="https://github.com/gc3-uzh-ch/elasticluster",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "License :: DFSG approved",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Operating System :: POSIX :: Other",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: System :: Clustering",
        "Topic :: Education",
        "Topic :: Scientific/Engineering",
        "Topic :: System :: Distributed Computing",
    ],
    packages=find_packages(),
    install_requires=required_packages,
    include_package_data=True,  # include files mentioned by MANIFEST.in
    entry_points={
        'console_scripts': [
            'elasticluster = elasticluster.main:main',
        ]
    },
    tests_require=['tox', 'mock', 'pytest'],  # read right-to-left
    cmdclass={'test': Tox},
)
