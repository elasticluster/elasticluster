#! /usr/bin/env python
#
# Copyright (C) 2016 S3IT, University of Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# make coding more python3-ish, must be the first statement
from __future__ import (absolute_import, division, print_function)


## module doc and other metadata
"""
Test to run prior to ElastiCluster release.
"""
__docformat__ = 'reStructuredText'
__author__ = ('Riccardo Murri <riccardo.murri@gmail.com>')


## declare public API
__all__ = (
    'check_release_ok',
)


## imports and other dependencies
from datetime import datetime
import logging
import os
from subprocess import  check_output
import sys
from time import time

try:
    import coloredlogs
    coloredlogs.install(level=logging.INFO)
except ImportError:
    # no colorization, not a major issue ...
    pass

import pytest

from _helpers.docker_session import DockerSession


## aux functions

def run(cmdline):
    """A shortcut ro run simple shell commands."""
    logging.info("Running '%s' ...", cmdline)
    output = check_output(cmdline, shell=True, universal_newlines=True)
    return output.strip()


## main: run tests

if not os.path.exists('setup.py'):
    logging.fatal(
        "This script must be run from the directory where `setup.py` is.")
    sys.exit(1)

@pytest.mark.parametrize("py_version", [
    ('2.6',),
    ('2.7',),
])
def check_release_ok(py_version):
    timestamp = int(time())

    # XXX: these could be globals, but let's wait until PEP 498's
    # f-string literals are available in all Pythons ...
    TEST_PYPI_URL='https://testpypi.python.org/pypi'
    PROD_PYPI_URL='https://pypi.python.org/simple'

    OUR_VERSION = run('python setup.py --version')
    if '+' in OUR_VERSION:
        # strip local part
        OUR_VERSION = OUR_VERSION.split('+')[0]
    if '.dev' in OUR_VERSION:
        # strip development N
        OUR_VERSION = OUR_VERSION.split('.dev')[0]
    GIT_COMMIT_ID = run('git rev-parse --short HEAD')
    VERSION = ('{OUR_VERSION}.dev{timestamp}'.format(**locals()))
    with open('version.txt', 'w') as version_file:
        version_file.write(VERSION)

    # set up context vars
    now = datetime.now().strftime('%Y-%m-%d.%H%M')
    today = datetime.now().strftime('%Y-%m-%d')
    python = 'python{py_version}'.format(**locals())
    testenv = 'test{py_version}.{now}.d'.format(**locals())

    with DockerSession() as session:

        # create *new* virtualenv for testing
        if os.path.exists(testenv):
            shutil.rmtree(testenv)
        rc, output = session.run(
            'virtualenv -p {python} --no-site-packages {testenv}'
            .format(**locals()))
        assert rc == 0

        # test PyPI package creation
        rc, output = session.run(
            '. {testenv}/bin/activate; python setup.py sdist upload -r {TEST_PYPI_URL}'
            .format(**locals()))
        assert 'error: ' not in output
        assert 'Server response (200): OK' in output
        assert rc == 0

        # test installation for PyPI
        rc, output = session.run(
            '. {testenv}/bin/activate; pip install --index-url {TEST_PYPI_URL} --extra-index-url {PROD_PYPI_URL} elasticluster=={VERSION}'
            .format(**locals()))
        # FIXME: it seems that long output lines are truncated!
        assert 'Successfully installed' in output
        assert rc == 0

        # test that we're running exactly the version just uploaded
        rc, output = session.run(
            '. {testenv}/bin/activate; elasticluster --version'
            .format(**locals()))
        assert (output.strip() ==
                'elasticluster version {VERSION}'.format(**locals()))
        assert rc == 0

        logging.info(
            "SUCCESSfully released and installed ElastiCluster %s",
            VERSION)

if __name__ == '__main__':
    check_release_ok('2.7')
    check_release_ok('2.6')
