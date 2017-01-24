#! /usr/bin/python
#
# Copyright (C) 2016 University of Zurich.
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
"""
Custom validator functions for checking the configuration file.
"""

from __future__ import (print_function, division, absolute_import)

# stdlib imports
import os
import string
from urlparse import urlparse

# 3rd-party modules
import schema

# ElastiCluster imports
from elasticluster.utils import string_to_boolean


## custom validators

def validator(fn):
    """
    Decorate a function for use as a validator with `schema`_

    .. _schema: https://github.com/keleshev/schema
    """
    return schema.Use(fn)


alphanumeric = schema.Regex(r'[0-9A-Za-z_]+')


boolean = schema.Use(string_to_boolean)


def _file_name(v):
    try:
        return os.path.expanduser(v)
    except Exception as err:
        raise ValueError("invalid file name `{0}`: {1}".format(v, err))


@validator
def existing_file(v):
    f = _file_name(v)
    if os.access(f, os.F_OK):
        return f
    else:
        raise ValueError("file `{v}` could not be found".format(v=v))


@validator
def readable_file(v):
    f = _file_name(v)
    if os.access(f, os.R_OK):
        return f
    else:
        raise ValueError("cannot read file `{v}`".format(v=v))


@validator
def executable_file(v):
    f = _file_name(v)
    if os.access(f, os.R_OK|os.X_OK):
        return f
    else:
        raise ValueError("cannot execute file `{v}`".format(v=v))


def hostname(value):
    """
    Check that `value` is a valid host name.

    From `RFC 952 <https://www.rfc-editor.org/rfc/rfc952.txt>`:

      A "name" (Net, Host, Gateway, or Domain name) is a text string up to 24
      characters drawn from the alphabet (A-Z), digits (0-9), minus sign (-),
      and period (.). Note that periods are only allowed when they serve to
      delimit components of "domain style names".
    """
    if set(value) <= _ALLOWED_HOSTNAME_CHARS:
        return value
    else:
        raise ValueError(
            "Invalid name `{0}` for a node group."
            " A valid node name can only consist of"
            " letters, digits or the hyphen character (`-`)"
            .format(value))

_ALLOWED_HOSTNAME_CHARS = set(string.letters + string.digits + '-')


@validator
def nonempty_str(v):
    converted = str(v)
    if not converted:
        raise ValueError("value must be a non-empty string")
    return converted


@validator
def nova_api_version(version):
    try:
        from novaclient import client, exceptions
        client.get_client_class(version)
        return version
    except exceptions.UnsupportedVersion as err:
        raise ValueError(
            "Unsupported Nova API version: {0}".format(err))


@validator
def url(value):
    try:
        url_str = str(value)
        urlparse(url_str)
        return url_str
    except Exception as err:
        raise ValueError("Invalid URL `{0}`: {1}".format(value, err))
