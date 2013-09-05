#! /usr/bin/env python
#
# Copyright (C) 2013 GC3, University of Zurich
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
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'


# stdlib imports
from abc import ABCMeta, abstractmethod


class AbstractCloudProvider:
    """
    Defines the contract for a cloud provider to proper function with
    elasticluster.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def start_instance(self, key_name, public_key_path, private_key_path,
                       security_group, flavor, image_name, image_userdata,
                       username=None):
        """
        Starts a new instance with the given properties and returns
        the instance id.
        """
        pass

    @abstractmethod
    def stop_instance(self, instance_id):
        """
        Stops the instance with the given id gracefully.
        """
        pass

    @abstractmethod
    def get_ips(self, instance_id):
        """
        Finds the private and public ip addresses for a given instance.
        :return tuple (ip_private, ip_public)
        """
        pass

    @abstractmethod
    def is_instance_running(self, instance_id):
        """
        Checks if the instance with the given id is up and running.
        """
        pass


class AbstractSetupProvider:
    """
    TODO: define...
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def setup_cluster(self, cluster):
        """
        Setup a cluster. `cluster` must be a
        `elasticluster.cluster.Cluster` class.

        This method *must* be idempotent, i.e. it should always be
        safe calling it multiple times..

        :return: `True` if the cluster is correctly configured, even
                  if the method didn't actually do anything.

                 `False` if the cluster is not configured.
        """
        pass

    @abstractmethod
    def cleanup(self):
        """
        Cleanup any temporary file or directory created during setup.

        This method is called every time a cluster is stopped.

        :return: None
        """
        pass
