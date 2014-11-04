# -*- coding: utf-8 -*-#
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
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>, Antonio Messina <antonio.s.messina@gmail.com>'

# System imports
import os
import pickle
from abc import ABCMeta, abstractmethod

# Elasticluster imports
from elasticluster import log
from elasticluster.exceptions import ClusterNotFound


class AbstractClusterRepository:
    """Defines the contract for a cluster repository to store clusters in a
    persistent state.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def save_or_update(self, cluster):
        """Save or update the cluster in a persistent state. Elasticluster
        will call this method multiple times, so the implementation
        should handle save and update seamlessly

        :param cluster: cluster object to store
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        pass

    @abstractmethod
    def get(self, name):
        """Retrieves the cluster by the given name.

        :param str name: name of the cluster (identifier)
        :return: instance of :py:class:`elasticluster.cluster.Cluster` that
                 matches the given name
        """
        pass

    @abstractmethod
    def get_all(self):
        """Retrieves all stored clusters from the persistent state.

        :return: list of :py:class:`elasticluster.cluster.Cluster`
        """
        pass

    @abstractmethod
    def delete(self, cluster):
        """Deletes the cluster from persistent state.

        :param cluster: cluster to delete from persistent state
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        pass


class MemRepository(AbstractClusterRepository):
    """
    This implementation of :py:class:`AbstractClusterRepository` stores
    the clusters in memory, without actually saving the data on disk.
    """
    def __init__(self):
        self.clusters = {}

    def save_or_update(self, cluster):
        """Save or update the cluster in a memory.

        :param cluster: cluster object to store
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        self.clusters[cluster.name] = cluster

    def get(self, name):
        """Retrieves the cluster by the given name.

        :param str name: name of the cluster (identifier)
        :return: instance of :py:class:`elasticluster.cluster.Cluster` that
                 matches the given name
        """
        if name not in self.clusters:
            raise ClusterNotFound("Cluster %s not found." % name)
        return self.clusters.get(name)

    def get_all(self):
        """Retrieves all stored clusters from the memory.

        :return: list of :py:class:`elasticluster.cluster.Cluster`
        """
        return self.clusters.values()

    def delete(self, cluster):
        """Deletes the cluster from memory.

        :param cluster: cluster to delete
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        if cluster.name not in self.clusters:
            raise ClusterNotFound(
                "Unable to delete non-existent cluster %s" % cluster.name)
        del self.clusters[cluster.name]


class PickleRepository(AbstractClusterRepository):
    """This implementation of :py:class:`AbstractClusterRepository` stores the
    cluster on the local disc using pickle. Therefore the cluster object and
    all its dependencies will be saved in a pickle (binary) file.

    :param str storage_path: path to the folder to store the cluster
                             information
    """

    file_ending = 'pickle'

    def __init__(self, storage_path):
        storage_path = os.path.expanduser(storage_path)
        storage_path = os.path.expandvars(storage_path)
        self.storage_path = storage_path

    def get_all(self):
        """Retrieves all clusters from the persistent state.

        :return: list of :py:class:`elasticluster.cluster.Cluster`
        """
        file_ending = PickleRepository.file_ending
        allfiles = os.listdir(self.storage_path)
        cluster_files = []
        for fname in allfiles:
            fpath = os.path.join(self.storage_path, fname)
            if fname.endswith('.%s' % file_ending) and os.path.isfile(fpath):
                cluster_files.append(fname[:-len(file_ending)-1])
            else:
                log.info("Ignoring invalid storage file %s", fpath)

        clusters = list()
        for cluster_file in cluster_files:
            try:
                cluster = self.get(cluster_file)
                clusters.append(cluster)
            except (ImportError, AttributeError) as ex:
                log.error("Unable to load cluster %s: `%s`", cluster_file, ex)
                log.error("If cluster %s was created with a previous version of elasticluster, you may need to run `elasticluster migrate %s %s` to update it.", cluster_file, self.storage_path, cluster_file)
        return clusters

    def get(self, name):
        """Retrieves the cluster with the given name.

        :param str name: name of the cluster (identifier)
        :return: :py:class:`elasticluster.cluster.Cluster`
        """
        path = self._get_cluster_storage_path(name)
        if not os.path.exists(path):
            raise ClusterNotFound("Storage file %s not found" % path)

        with open(path, 'r') as storage:
            cluster = pickle.load(storage)
            # Compatibility with previous version of Node
            for node in sum(cluster.nodes.values(), []):
                if not hasattr(node, 'ips'):
                    log.debug("Monkey patching old version of `Node` class: %s", node.name)
                    node.ips = [node.ip_public, node.ip_private]
                    node.preferred_ip = None
            return cluster

    def delete(self, cluster):
        """Deletes the cluster from persistent state.

        :param cluster: cluster to delete from persistent state
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        path = self._get_cluster_storage_path(cluster.name)
        if os.path.exists(path):
            os.unlink(path)

    def save_or_update(self, cluster):
        """Save or update the cluster to persistent state.

        :param cluster: cluster to save or update
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

        path = self._get_cluster_storage_path(cluster.name)
        with open(path, 'wb') as storage:
            pickle.dump(cluster, storage, pickle.HIGHEST_PROTOCOL)

    def _get_cluster_storage_path(self, name):
        cluster_file = '%s.%s' % (name, PickleRepository.file_ending)
        return os.path.join(self.storage_path, cluster_file)

