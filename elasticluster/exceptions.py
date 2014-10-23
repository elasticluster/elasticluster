#! /usr/bin/env python
#
#   Copyright (C) 2013 GC3, University of Zurich
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
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'


class ConfigurationError(Exception):
    pass


class VpcError(Exception):
    pass


class SecurityGroupError(Exception):
    pass


class SubnetError(Exception):
    pass


class KeypairError(Exception):
    pass


class InstanceError(Exception):
    pass

class FlavorError(Exception):
    pass


class TimeoutError(Exception):
    pass


class ClusterNotFound(Exception):
    pass


class ClusterError(Exception):
    pass


class NodeNotFound(Exception):
    pass


class ImageError(Exception):
    pass

class CloudProviderError(Exception):
    pass
