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
# pylint: disable=missing-docstring,unused-variable,wrong-import-position

from __future__ import absolute_import

# this is needed to get logging info in `py.test` when something fails
import logging
logging.basicConfig()

import pytest


__author__ = (', '.join([
    'Yaroslav Halchenko <debian@onerussian.com>',
]))


def test_smoke_imports_top():
    import elasticluster.__main__
    import elasticluster.migration_tools  # also a script
    import elasticluster.gc3pie_config
    import elasticluster.subcommands


def test_smoke_imports_providers():
    import elasticluster.providers.azure_provider
    import elasticluster.providers.libcloud_provider


if __name__ == "__main__":
    pytest.main(['-v', __file__])
