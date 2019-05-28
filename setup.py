#!/usr/bin/env python
# -*- coding: utf-8 -*-#
#
# Copyright (C) 2013-2019 University of Zurich. All rights reserved.
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

import sys
python_version = sys.version_info[:2]
if not (python_version == (2, 7) or python_version >= (3, 5)):
    raise RuntimeError("ElastiCluster requires Python 2.7 or 3.5+")


# fix Python issue 15881 (on Python <2.7.5)
try:
    import multiprocessing
except ImportError:
    pass


# Ensure we use a recent enough version of setuptools: CentOS7 still ships with
# 0.9.8! Although at the moment ElastiCluster does not make use of any advanced
# feature from `setuptools`, some dependent package requires >=17.1 (at the
# time of this writing) and this version number is likely to increase with time
# -- so just pick a "known good one".
from ez_setup import use_setuptools
use_setuptools(version='21.0.0')


## auxiliary functions
#
def read_whole_file(path):
    """
    Return file contents as a string.
    """
    with open(path, 'r') as stream:
        return stream.read()


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
    version='1.3.dev15',
    description="A command line tool to create, manage and setup computing clusters hosted on a public or private cloud infrastructure.",
    long_description=read_whole_file('README.rst'),
    author=", ".join([
        'Nicolas Baer',
        'Antonio Messina',
        'Riccardo Murri',
    ]),
    author_email="riccardo.murri@gmail.com",
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
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Clustering",
        "Topic :: Education",
        "Topic :: Scientific/Engineering",
        "Topic :: System :: Distributed Computing",
    ],
    packages=find_packages(),
    include_package_data=True,  # include files mentioned by MANIFEST.in
    entry_points={
        'console_scripts': [
            'elasticluster = elasticluster.__main__:main',
        ]
    },
    setup_requires=['Babel>=2.3.4,!=2.4.0'],  # see Issue #268
    install_requires=[
        # ElastiCluster core requirements
        'future',
        'pip>=9.0.0',  ## see issue #433
        #'ara',  # optional
        'PyCLI',
        'ansible>=2.7',
        'click>=4.0',  ## click.prompt() added in 4.0
        'coloredlogs',
        'netaddr',
        'paramiko',
        'schema',
        'subprocess32',  ## stdlib subprocess but correct under multithreading
        # Azure cloud
        'azure-common',
        'azure-mgmt-compute',
        'azure-mgmt-network',
        'azure-mgmt-resource',
        'msrestazure',
        # EC2 clouds
        'boto>=2.48',
        'pycrypto',   # for computing RSA key hash, see: PR #132
        # Google Cloud
        'google-api-python-client',
        'google-compute-engine',
        'oauth2client',
        'python-gflags',
        'pytz',   ## required by `positional` but somehow not picked up
        'simplejson>=2.5.0', # needed by `uritemplate` but somehow not picked up
        # OpenStack
        'netifaces',
        'apache-libcloud>=0.14.0',
        'requests~=2.16',  ## see issue #441 and #566
        'python-keystoneclient',
        'python-glanceclient',
        'python-neutronclient',
        'python-cinderclient',
        'python-novaclient<=9.1.2',
        # fix dependency conflict among OpenStack libraries:
        # `osc-lib` has a more strict dependency specifier
        # which is not picked up by `pip` because it's not
        # a top-level dependency of ElastiCluster
        'Babel>=2.3.4,!=2.4.0',
        'pbr>=2.0.0,!=2.1.0',
        ## the following 6 are all required dependencies
        ## which are not picked up, see issue #500
        'enum34; python_version<"3.4"',
        'functools32; python_version<"3.2"',
        'ipaddress',
        'pathlib2; python_version<"3.4"',
        'scandir',
        'secretstorage<=2.3.1',
    ],
    tests_require=['tox', 'mock', 'pytest-coverage', 'pytest>=2.10'],  # read right-to-left
    cmdclass={'test': Tox},
)
