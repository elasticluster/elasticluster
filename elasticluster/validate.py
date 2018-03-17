#! /usr/bin/python
#
# Copyright (C) 2016, 2018 University of Zurich.
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
from warnings import warn

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


def alert(errmsg, cls=DeprecationWarning):
    """
    Allow value, but warn user with the specified error message.
    """
    def _alert(v):
        warn(errmsg, cls)
    return validator(_alert)


alphanumeric = schema.Regex(r'[0-9A-Za-z_]+')
"""
Allow alphanumeric strings.
"""


boolean = schema.Use(string_to_boolean)
"""
Allow values *1/yes/true* and *0/no/false* (case insensitive).
"""


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
def positive_int(v):
    converted = int(v)
    if converted > 0:
        return converted
    else:
        raise ValueError("value must be integer > 0")


@validator
def nonnegative_int(v):
    converted = int(v)
    if converted < 0:
        raise ValueError("value must be a non-negative integer")
    return converted


@validator
def nova_api_version(version):
    """
    Check that the ``OS_COMPUTE_API_VERSION`` is valid.

    For what is a valid "Nova client" version, see:
    `<https://github.com/openstack/python-novaclient/blob/master/novaclient/client.py#L282>`_
    """
    if version in ['1.1', '2']:
        return version
    elif version.startswith('2.'):
        try:
            microversion = int(version[2:])
        except (ValueError, TypeError):
            raise ValueError(
                "Invalid OpenStack Compute API version: {0}"
                " -- must be either '1.1', '2', or '2.X'"
                " (where 'X' is a microversion integer)"
                .format(version))
        return version
    else:
        raise ValueError(
            "Invalid OpenStack Compute API version: {0}"
            " -- must be either '1.1', '2', or '2.X'"
            " (where 'X' is a microversion integer)"
            .format(version))


def reject(errmsg):
    """
    Reject any value with the specified error message.
    """
    def _reject(v):
        raise ValueError(errmsg.format(v))
    return validator(_reject)


@validator
def url(value):
    try:
        url_str = str(value)
        urlparse(url_str)
        return url_str
    except Exception as err:
        raise ValueError("Invalid URL `{0}`: {1}".format(value, err))
