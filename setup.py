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

from setuptools.command import sdist

# Newer versions of setuptools do not have `finders` attribute.
if hasattr(sdist, 'finders'):
    del sdist.finders[:]

ANSIBLE_PB_DIR = 'elasticluster/providers/ansible-playbooks'


def ansible_pb_files():
    basedir = os.path.dirname(__file__)
    ansible_data = [('share/elasticluster/etc', ['docs/config.template'])]
    for (dirname, dirnames, filenames) in os.walk(ANSIBLE_PB_DIR):
        tmp = []
        for fname in filenames:
            if fname.startswith('.git'): continue
            tmp.append(os.path.join(dirname, fname))
        ansible_data.append((os.path.join('share', dirname), tmp))
    return ansible_data


from setuptools import setup, find_packages

required_packages = [
    'PyCLI',
    'paramiko',
    'ansible~=1.9.4',
    'voluptuous>=0.8.2',
    'configobj',
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


setup(
    name="elasticluster",
    version="1.3.dev",
    description="A command line tool to create, manage and setup computing clusters hosted on a public or private cloud infrastructure.",
    long_description=open('README.rst').read(),
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
    tests_require=['tox', 'mock', 'nose'],
    data_files=ansible_pb_files(),
    entry_points={
        'console_scripts': [
            'elasticluster = elasticluster.main:main',
        ]
    },
)

if __name__ == "__main__":
    if sys.argv[1] in ['develop', 'install']:
        develop = True if sys.argv[1] == 'develop' else False
        curdir = os.path.abspath(os.path.dirname(__file__))
        sharedir = os.path.join(os.path.abspath(sys.prefix), 'share', 'elasticluster')
        etcdir = os.path.join(sharedir, 'etc')
        templatecfg = os.path.join(curdir, 'docs', 'config.template')
        templatedest = os.path.join(etcdir, os.path.basename(templatecfg))
        ansibledest = os.path.join(sharedir, 'providers', 'ansible-playbooks')
        ansiblesrc = os.path.join(curdir, 'elasticluster', 'providers', 'ansible-playbooks')

        if not os.path.exists(sharedir):
            os.makedirs(sharedir)

        if not os.path.exists(etcdir):
            os.makedirs(etcdir)

        if not os.path.exists(os.path.dirname(ansibledest)):
            os.makedirs(os.path.dirname(ansibledest))

        if not os.path.exists(ansibledest):
            if develop:
                os.symlink(ansiblesrc, ansibledest)
            else:
                shutil.copytree(ansiblesrc, ansibledest)

        if not os.path.exists(templatedest):
            if develop:
                os.symlink(templatecfg, templatedest)
            else:
                shutil.copy(templatecfg, etcdir)
