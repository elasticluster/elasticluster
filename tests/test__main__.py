#! /usr/bin/env python
#
#   Copyright (C) 2019 University of Zurich
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# pylint: disable=missing-docstring, wrong-import-position

# compatibility imports
from future import standard_library
standard_library.install_aliases()

from io import StringIO
import os
import subprocess
import sys

import pytest

from elasticluster.utils import temporary_dir, environment

__author__ = (', '.join([
    'Yaroslav Halchenko <debian@onerussian.com>',
    'Riccardo Murri <riccardo.murri@gmail.com>',
]))


# TODO: Could be a parametric fixture I guess
def _run_command(argv):
    """
    Run the `elasticluster` command with additional arguments.

    Return STDOUT, STDERR, and the process exit status.
    """
    with temporary_dir() as tmpdir:
        with environment(HOME=os.getcwd()) as env:
            proc = subprocess.Popen(
                ['elasticluster'] + argv,
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
                shell=False)
            stdout, stderr = proc.communicate()
            return stdout, stderr, proc.returncode


def test_main_help():
    out, err, code = _run_command(["--help"])
    assert out.startswith(b"usage: elasticluster [-h] [-v]")
    assert not err
    assert not code


def test_main_version():
    from elasticluster import __version__ as elasticluster_version
    out, err, code = _run_command(["--version"])
    assert not err
    assert not code
    assert out.rstrip() == ("elasticluster version {0}".format(elasticluster_version)).encode('ascii')


def test_main_list_default(tmpdir):
    out, err, code = _run_command(["list"])
    assert out.rstrip() == b"No clusters found."
    # default configuration is insufficient
    assert b"references non-existing login section" in err
    # does not result in error
    assert not code
