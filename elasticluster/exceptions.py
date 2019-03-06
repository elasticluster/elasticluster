#! /usr/bin/env python
#
#   Copyright (C) 2013-2018 University of Zurich
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
__author__ = '''
    Nicolas Baer <nicolas.baer@uzh.ch>,
    Riccardo Murri <riccardo.murri@gmail.com>
'''


class ConfigurationError(Exception):
    pass


class CredentialsError(Exception):
    pass


class UnsupportedError(ConfigurationError):
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
    """
    Generic error dealing with cloud-based VM.

    The difference between this and other errors raised by cloud APIs (e.g.,
    `FlavorError`:class:) is that `InstanceError` occurs when operations fail
    on a VM instance that ElastiCluster assumes *existing* (whereas, e.g.,
    `FlavorError`:class: might happen when starting a VM instance fails).
    """
    pass

class InstanceNotFoundError(InstanceError):
    """
    The cloud provider does not know about the given VM instance.
    """
    pass

class FlavorError(Exception):
    pass


class TimeoutError(Exception):
    pass


class ClusterNotFound(LookupError):
    pass


class ClusterError(Exception):
    pass


class ClusterSizeError(ClusterError):
    """
    Not enough nodes (of one or more kinds) are available.
    """
    def __init__(self, msg=None):
        super(ClusterSizeError, self).__init__(msg or
            "The cluster does not provide the minimum"
            " amount of nodes specified in the"
            " configuration. Some nodes are running,"
            " but the cluster will not be set up yet."
            " Please change the minimum amount of nodes in the"
            " configuration or try to start a new cluster"
            " after checking the cloud provider settings.")


class NodeNotFound(LookupError):
    pass


class ImageError(Exception):
    pass


class CloudProviderError(Exception):
    pass


class SetupProviderError(Exception):
    """
    Generic error happening during the setup phase.
    """
    pass
