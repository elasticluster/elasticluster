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


## stdlib imports
import os


## module metadata
__author__ = ('Riccardo Murri <riccardo.murri@gmail.com>')


## actual code

def clean_os_environ_ec2():
    for varname in os.environ.keys():
        if varname.startswith('EC2_') or varname.startswith('AWS_'):
            del os.environ[varname]

def clean_os_environ_openstack():
    for varname in os.environ.keys():
        if varname.startswith('OS_'):
            del os.environ[varname]
