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

import os
import subprocess
import sys

from elasticluster.utils import temporary_dir, environment

__author__ = (', '.join([
    'Yaroslav Halchenko <debian@onerussian.com>',
    'Riccardo Murri <riccardo.murri@gmail.com>',
]))


# TODO: Could be a parametric fixture I guess
def _run_elasticluster_cmd(argv):
    """
    Run the `elasticluster` command with additional arguments.

    Return STDOUT, STDERR, and the process exit status.
    """
    with temporary_dir() as tmpdir:
        with environment(
            HOME=os.getcwd(),
            PYTHONWARNINGS=(
                # as support for Py2 wanes, we must silence warnings that
                # Python 2.7 will no longer be supported, as they make the
                # tests fail unnecessarily (functionality is OK, we just get
                # some extra lines into STDERR). However,
                # `cryptography.utils.CryptographyDeprecationWarning` is a
                # subclass of `UserWarning` exactly because
                # `DeprecationWarnings` are ignored by default, so we need to
                # ignore all `UserWarnings` as well (cannot ignore a non-builtin
                # exception class via an environmental variable)
                'ignore::DeprecationWarning,ignore::UserWarning' if sys.version_info < (3, 6)
                # display all warnings on Py3.6+
                else ''),
        ) as env:
            proc = subprocess.Popen(
                ['elasticluster'] + argv,
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
                shell=False)
            stdout, stderr = proc.communicate()
            return stdout, stderr, proc.returncode


def test_cli_help():
    out, err, code = _run_elasticluster_cmd(["--help"])
    assert out.startswith(b"usage: elasticluster [-h] [-v]")
    assert not err
    assert not code


def test_cli_version():
    from elasticluster import __version__ as elasticluster_version
    out, err, code = _run_elasticluster_cmd(["--version"])
    assert not err
    assert not code
    assert out.rstrip() == ("elasticluster version {0}".format(elasticluster_version)).encode('ascii')


def test_cli_list_default(tmpdir):
    out, err, code = _run_elasticluster_cmd(["list"])
    assert out.rstrip() == b"No clusters found."
    # default configuration is insufficient
    assert b"references non-existing login section" in err
    # does not result in error
    assert not code
