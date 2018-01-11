#!/usr/bin/env python
# -*- coding: utf-8 -*-#
#
#
# Copyright (C) 2013-2018 University of Zurich. All rights reserved.
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

import sys

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


## conditional dependencies
#
# Although PEP-508 and a number of predecessors specify a syntax for
# conditional dependencies in Python packages, support for it is inconsistent
# (at best) among the PyPA tools. An attempt to use the conditional syntax has
# already caused issues #308, #249, #227, and many more headaches to me while
# trying to find a combination of `pip`, `setuptools`, `wheel`, and dependency
# specification syntax that would work reliably across all supported Linux
# distributions. I give up, and revert to computing the dependencies via
# explicit Python code in `setup.py`; this will possibly break wheels but it's
# the least damage I can do ATM.

python_version = sys.version_info[:2]
if python_version == (2, 6):
    version_dependent_requires = [
        # Alternate dependencies for Python 2.6:
        # - PyCLI requires argparse,
        'argparse',
        # - OpenStack's "keystoneclient" requires `importlib`
        'importlib',
        # Paramiko ceased support for Python 2.6 in version 2.4.0
        'paramiko<2.4',
        # - support for Python 2.6 was removed from `novaclient` in commit
        #   81f8fa655ccecd409fe6dcda0d3763592c053e57 which is contained in
        #   releases 3.0.0 and above; however, we also need to pin down
        #   the version of `oslo.config` and all the dependencies thereof,
        #   otherwise `pip` will happily download the latest and
        #   incompatible version,since `python-novaclient` specifies only
        #   the *minimal* version of dependencies it is compatible with...
        'stevedore<1.10.0',
        'debtcollector<1.0.0',
        'keystoneauth<2.0.0',
        # yes, there"s `keystoneauth` and `keystoneauth1` !!
        'keystoneauth1<2.0.0',
        'oslo.config<3.0.0',
        'oslo.i18n<3.1.0',
        'oslo.serialization<2.1.0',
        'oslo.utils<3.1.0',
        'python-keystoneclient<2.0.0',
        'python-novaclient<3.0.0',
        'python-cinderclient<1.6.0',
    ]
elif python_version == (2, 7):
    version_dependent_requires = [
        # Paramiko ceased support for Python 2.6 so we need it here
        'paramiko',
        # OpenStack
        'python-keystoneclient',
        'python-glanceclient',
        'python-neutronclient',
        'python-cinderclient',
        'python-novaclient',
        # fix dependency conflict among OpenStack libraries:
        # `osc-lib` has a more strict dependency specifier
        # which is not picked up by `pip` because it's not
        # a top-level dependency of ElastiCluster
        'Babel>=2.3.4,!=2.4.0',
        'pbr>=2.0.0,!=2.1.0',
        # MS-Azure
        'azure',
        ## the following 6 are all required dependencies
        ## which are not picked up, see issue #500
        'enum34',
        'functools32',
        'ipaddress',
        'pathlib2',
        'scandir',
        'secretstorage',
    ]
else:
    raise RuntimeError("ElastiCluster requires Python 2.6 or 2.7")


## real setup description begins here
#
from setuptools import setup, find_packages

setup(
    name="elasticluster",
    version=read_whole_file("version.txt").strip(),
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
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
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
    setup_requires=['Babel>=2.3.4'],  # see Issue #268
    install_requires=([
        # ElastiCluster core requirements
        'pip>=9.0.0',  ## see issue #433
        'PyCLI',
        'ansible>=2.2.3,!=2.3.0,<2.4',  ## whitelist only "known good" versions of Ansible
        'click>=4.0',  ## click.prompt() added in 4.0
        'coloredlogs',
        'netaddr',
        'schema',
        'subprocess32',  ## stdlib subprocess but correct under multithreading
        # EC2 clouds
        'boto>=2.48',
        # GCE cloud
        'google-api-python-client',
        'google-compute-engine',
        'python-gflags',
        'simplejson>=2.5.0', # needed by `uritemplate` but somehow not picked up
        'pytz',   ## required by `positional` but somehow not picked up
        'httplib2>=0.9.1',  ## required by `oauth2client` but somehow not picked up
        # Azure cloud
        #'azure',  ## only available on Py 2.7, see `version_dependent_requires`
        # OpenStack clouds
        'netifaces',
        'apache-libcloud>=0.14.0',
        'requests~=2.14.1',  ## see issue #441
        #'python-novaclient' ## this needs special treatment depending on Python version
    ] + version_dependent_requires),
    tests_require=['tox', 'mock', 'pytest>=2.10'],  # read right-to-left
    cmdclass={'test': Tox},
)
