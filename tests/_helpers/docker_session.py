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

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

# declare public API
__all__ = (
    'DockerSession',
)

# package metadata
__author__ = ('Riccardo Murri <riccardo.murri@gmail.com>')


# imports etc
import logging
import os
import sys

try:
    import docker
except ImportError as err:
    sys.stderr.write("""
Could not import the `docker` Python module:
{err}

For Docker-based tests in ElastiCluster to work, *both* the Docker
Engine *and* the `docker-py` module need to be installed.  On
Debian/Ubuntu, you might need to run the following commands:

        sudo apt-get install lxc-docker
        sudo pip install docker-py

For other platforms, please see instead:

* https://docs.docker.com/engine/installation/
* https://docker-py.readthedocs.org/en/latest/#installation

    """.format(err=err))
    raise


class DockerSession(object):
    """
    Run commands in a Docker container.

    A container is created when the `Session` object is instanciated;
    all commands issued through the `run`:meth: are executed in it;
    the container is finally stopped and deleted when `done`:meth: is
    called.
    """

    def __init__(self, work_dir=None):
        if work_dir is None:
            work_dir = os.getcwd()
        self._docker = docker.Client()
        self._container = self._docker.create_container(
            image='s3it/pythonista',
            command='/bin/sleep 1d',
            working_dir='/src',
            user=os.geteuid(),
            volumes=['/src'],
            host_config=self._docker.create_host_config(
                binds={
                    work_dir:{
                        'bind': '/src',
                        'mode': 'rw',
                },
            }),
        )
        self._container_id = self._container[u'Id']
        self._docker.start(self._container_id)
        self._running = True
        logging.info(
            "Session %s will execute commands in container '%s'",
            self, self._container_id)


    def run(self, cmd, shell=True):
        """
        Run command in the container; return exitcode and output.
        """
        assert self._running
        if shell:
            cmd = 'sh -c "{cmd}"'.format(**locals())
        e = self._docker.exec_create(self._container_id, cmd)
        e_id = e[u'Id']

        logging.info("Running '%s' ...", cmd)
        output = self._docker.exec_start(e_id)
        details = self._docker.exec_inspect(e_id)
        exitcode = details[u'ExitCode']
        logging.debug(
            "Command '%s' exited with code %d and output '%s'",
            cmd, exitcode, output)
        with open('session.log', 'a') as w:
            w.write('''
COMMAND: {cmd}
EXITCODE: {exitcode}
OUTPUT:
{output}
            '''.format(**locals()))
        return exitcode, output


    def done(self):
        logging.info("Terminating session %s ...", self)
        self._docker.stop(self._container_id, timeout=1)
        self._running = False
        self._docker.remove_container(self._container_id, force=True)
        logging.debug("Removed Docker container '%s'", self._container_id)

    #
    # context manager protocol
    #

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.done()


## run tests for code in this file

def test_docker_session():
    session = DockerSession()
    exitcode, output = session.run('ls -1')
    entries_from_ls = set(line for line in output.split('\n') if line != '')
    entries_from_listdir = set(os.listdir(os.getcwd()))
    assert entries_from_ls == entries_from_listdir
    assert exitcode == 0
    exitcode, output = session.run('false')
    assert output == ''
    assert exitcode == 1
    session.done()

if __name__ == '__main__':
    import pytest
    pytest.main(['-v', __file__])
