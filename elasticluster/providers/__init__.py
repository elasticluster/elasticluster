#
# Copyright (C) 2013, 2015, 2019 University of Zurich.
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


# compatibility imports
from future.utils import with_metaclass

# stdlib imports
from builtins import object
from abc import ABCMeta, abstractmethod


class AbstractCloudProvider(with_metaclass(ABCMeta, object)):
    """Defines the contract for a cloud provider to proper function with
    elasticluster.
    """

    @abstractmethod
    def __init__(self, **config):
        """The constructor of a `CloudProvider` class is called only
        using keyword arguments.

        Usually these are configuration option of the corresponding
        `setup` section in the configuration file.
        """
        pass

    @abstractmethod
    def to_vars_dict(self):
        """
        Return local state which is relevant for the cluster setup process.
        """
        return {}

    @abstractmethod
    def start_instance(self, key_name, public_key_path, private_key_path,
                       security_group, flavor, image_id, image_userdata,
                       username=None, node_name=None):
        """Starts a new instance on the cloud using the given properties.
        Multiple instances might be started in different threads at the same
        time. The implementation should handle any problems regarding this
        itself.

        :param str key_name: name of the ssh key to connect
        :param str public_key_path: path to ssh public key
        :param str private_key_path: path to ssh private key
        :param str security_group: firewall rule definition to apply on the
                                   instance
        :param str flavor: machine type to use for the instance
        :param str image_name: image type (os) to use for the instance
        :param str image_userdata: command to execute after startup
        :param str username: username for the given ssh key, default None

        :return: Dictionary of instance attributes to record.
        """
        pass

    @abstractmethod
    def pause_instance(self, instance_id):
        """Pauses the instance - retaining disks and configuration.

        :param str instance_id: instance identifier

        :return: dict - Dictionary of configuration required to restart instance.
        """
        pass

    @abstractmethod
    def resume_instance(self, instance_config):
        """Restart an instance from a dictionary of configuration.

        :param dict instance_config:
          Dictionary of configuration returned from `pause_instance`:meth:
        :return: str - instance_id
        """
        pass

    @abstractmethod
    def stop_instance(self, instance_id):
        """Stops the instance gracefully.

        :param str instance_id: instance identifier

        :return: None
        """
        pass

    @abstractmethod
    def get_ips(self, instance_id):
        """Retrieves the private and public ip addresses for a given instance.

        :return: list (IPs)
        """
        pass

    @abstractmethod
    def is_instance_running(self, instance_id):
        """Checks if the instance is up and running.

        :param str instance_id: instance identifier

        :return: bool - True if running, False otherwise
        """
        pass


class AbstractSetupProvider(with_metaclass(ABCMeta, object)):
    """
    TODO: define...
    """

    #: to identify this provider type in messages; override in subclasses
    HUMAN_READABLE_NAME = 'setup provider'

    @abstractmethod
    def setup_cluster(self, cluster, extra_args=tuple()):
        """
        Configure all nodes of a cluster.

        This method *must* be idempotent, i.e. it should always be
        safe to call multiple times over.

        :param cluster: cluster to configure
        :type cluster: :py:class:`elasticluster.cluster.Cluster`

        :param list extra_args:
          List of additional command-line arguments
          that are appended to each invocation of the setup program.

        :return: `True` if the cluster is correctly configured, even
                  if the method didn't actually do anything. `False` if the
                  cluster is not configured.
        """
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup any temporary file or directory created during setup.
        This method is called every time a cluster is stopped.

        :return: None
        """
        pass
