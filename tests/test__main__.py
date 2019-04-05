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
import pytest
import sys

from io import StringIO
from elasticluster import __main__, __version__


__author__ = (', '.join([
    'Yaroslav Halchenko <debian@onerussian.com>',
]))


# TODO: Could be a parametric fixture I guess
def _run_command(monkeypatch, argv, exit_code=None):
    """Helper to run __main__ given a list of argvs and return stdout, stderr, exitcode

    if `exit_code` is not None, we verify that it matches
    """
    fakestdout = StringIO()
    fakestderr = StringIO()
    monkeypatch.setattr(sys, "stdout", fakestdout)
    monkeypatch.setattr(sys, "stderr", fakestderr)
    monkeypatch.setattr(sys, "argv", ["does not matter"] + argv)
    with pytest.raises(SystemExit) as cme:
        __main__.main()

    return fakestdout.getvalue(), fakestderr.getvalue(), cme.value.code


def test_main_help(monkeypatch):
    out, err, code = _run_command(monkeypatch, argv=["--help"])
    assert out.startswith("usage: elasticluster [-h] [-v]")
    assert not err
    assert not code


def test_main_version(monkeypatch):
    out, err, code = _run_command(monkeypatch, argv=["--version"])
    assert not err
    assert not code
    assert out.rstrip() == "elasticluster version %s" % __version__


# most probably would need to be disabled or fixed to be tested on a real box
# or global fixture should be introduced to set HOME to a fake one globally
def test_main_list_default(monkeypatch, tmpdir):
    # unfortunately it is too late since configuration is read already
    # I guess.  So either code should be RFed to not have config that
    # persistent and be specific to the app, or just run externally but
    # that would loose coverage reporting
    monkeypatch.setitem(os.environ, 'HOME', str(tmpdir))
    out, err, code = _run_command(monkeypatch, argv=["list"])
    assert out.rstrip() == "No clusters found."
    # Default configuration is either broken or insufficient
    assert "references non-existing login section" in err
    # Does not result in error
    assert not code