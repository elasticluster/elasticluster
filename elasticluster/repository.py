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
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'

# System imports
import os
import pickle
from abc import ABCMeta, abstractmethod

# Elasticluster imports
from elasticluster import log
from elasticluster.exceptions import ClusterNotFound


class AbstractClusterRepository:
    """
    Defines the contract for a cluster repository to store clusters in a
    persistent state.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def save_or_update(self, cluster):
        """
        Save or update the cluster persistent
        :param `elasticluster.cluster.Cluster` cluster: cluster to save
        """
        pass

    @abstractmethod
    def get(self, name):
        """
        Retrieves the cluster with the given name.
        :param str name: name of the cluster (identifier)
        :return: instance of `elasticluster.cluster.Cluster` with the
                 corresponding name
        """
        pass

    @abstractmethod
    def get_all(self):
        """
        Retrieves all stored clusters from the persistent state.
        :return: list of `elasticluster.cluster.Cluster`
        """
        pass

    @abstractmethod
    def delete(self, cluster):
        """
        Deletes the cluster from persistent state.
        :param `elasticluster.cluster.Cluster` cluster: cluster to delete
                                                        from persistent state
        """
        pass


class ClusterRepository(AbstractClusterRepository):
    """
    This implementation of `elasticluster.repository.AbstractClusterRepositoy`
    stores the cluster on the local disc using pickle.
    """
    file_ending = 'pickle'

    def __init__(self, storage_path):
        """
        :param str storage_path: path to the folder to store the cluster
                                 information
        """
        self.storage_path = storage_path

    def get_all(self):
        """
        Retrieves the cluster with the given name.
        :param str name: name of the cluster (identifier)
        :return: instance of `elasticluster.cluster.Cluster` with the
                 corresponding name
        """
        file_ending = ClusterRepository.file_ending
        allfiles = os.listdir(self.storage_path)
        cluster_files = []
        for fname in allfiles:
            fpath = os.path.join(self.storage_path, fname)
            if fname.endswith('.%s' % file_ending) and os.path.isfile(fpath):
                cluster_files.append(fpath)
            else:
                log.info("Ignoring invalid storage file %s", fpath)

        clusters = list()
        for cluster_file in cluster_files:
            with open(cluster_file, 'rb') as f:
                cluster = pickle.load(f)
                clusters.append(cluster)

        return clusters

    def get(self, name):
        """
        Retrieves the cluster with the given name.
        :param str name: name of the cluster (identifier)
        :return: instance of `elasticluster.cluster.Cluster` with the
                 corresponding name
        """
        path = self._get_cluster_storage_path(name)
        if not os.path.exists(path):
            raise ClusterNotFound("Storage file %s not found" % path)

        with open(path, 'r') as storage:
            cluster = pickle.load(storage)
            return cluster

    def delete(self, cluster):
        """
        Deletes the cluster from persistent state.
        :param `elasticluster.cluster.Cluster` cluster: cluster to delete
                                                        from persistent state
        """
        cluster_file = '%s.%s' % (cluster.name, ClusterRepository.file_ending)
        path = os.path.join(self.storage_path, cluster_file)
        if os.path.exists(path):
            os.unlink(path)

    def save_or_update(self, cluster):
        """
        Save or update the cluster persistent
        :param `elasticluster.cluster.Cluster` cluster: cluster to save
        """
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

        path = self._get_cluster_storage_path(cluster.name)
        with open(path, 'wb') as storage:
            pickle.dump(cluster, storage)

    def _get_cluster_storage_path(self, name):
        cluster_file = '%s.%s' % (name, ClusterRepository.file_ending)
        return os.path.join(self.storage_path, cluster_file)