# -*- coding: utf-8 -*-#
# Copyright (C) 2013, 2015 S3IT, University of Zurich
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
import glob
import json
import yaml

# Elasticluster imports
from elasticluster import log
from elasticluster.exceptions import ClusterNotFound

def migrate_cluster(cluster):
    """Called when loading a cluster when it comes from an older version
    of elasticluster"""

    for old, new in [('_user_key_public', 'user_key_public'),
                     ('_user_key_private', 'user_key_private'),
                     ('_user_key_name', 'user_key_name'),]:
        if hasattr(cluster, old):
            setattr(cluster, new, getattr(cluster, old))
            delattr(cluster, old)
    for kind, nodes in cluster.nodes.items():
        for node in nodes:
            if hasattr(node, 'image'):
                image_id = getattr(node, 'image_id', None) or node.image
                setattr(node, 'image_id', image_id)
                delattr(node, 'image')

    # Possibly related to issue #129
    if not hasattr(cluster, 'thread_pool_max_size'):
        cluster.thread_pool_max_size = 10
    return cluster


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


class DiskRepository(AbstractClusterRepository):
    """This is a generic repository class that assumes each cluster is
saved on a file on disk. It only defines a few methods, to avoid
duplication of code.
    """

    def __init__(self, storage_path):
        storage_path = os.path.expanduser(storage_path)
        storage_path = os.path.expandvars(storage_path)
        self.storage_path = storage_path

    def get_all(self):
        """Retrieves all clusters from the persistent state.

        :return: list of :py:class:`elasticluster.cluster.Cluster`
        """

        clusters = []
        cluster_files = glob.glob("%s/*.%s" % (self.storage_path, self.file_ending))
        for fname in cluster_files:
            try:
                name = fname[:-len(self.file_ending)-1]
                clusters.append(self.get(name))
            except (ImportError, AttributeError) as ex:
                log.error("Unable to load cluster %s: `%s`", fname, ex)
                log.error("If cluster %s was created with a previous version of elasticluster, you may need to run `elasticluster migrate %s %s` to update it.", cluster_file, self.storage_path, fname)
        return clusters

    def _get_cluster_storage_path(self, name):
        cluster_file = '%s.%s' % (name, self.file_ending)
        return os.path.join(self.storage_path, cluster_file)

    def get(self, name):
        """Retrieves the cluster with the given name.

        :param str name: name of the cluster (identifier)
        :return: :py:class:`elasticluster.cluster.Cluster`
        """
        path = self._get_cluster_storage_path(name)

        try:
            with open(path, 'r') as storage:
                cluster = self.load(storage)
                # Compatibility with previous version of Node
                for node in sum(cluster.nodes.values(), []):
                    if not hasattr(node, 'ips'):
                        log.debug("Monkey patching old version of `Node` class: %s", node.name)
                        node.ips = [node.ip_public, node.ip_private]
                        node.preferred_ip = None
                cluster.storage_file = path
                return cluster
        except IOError as ex:
            raise ClusterNotFound("Error accessing storage file %s: %s" % (path, ex))

    def save_or_update(self, cluster):
        """Save or update the cluster to persistent state.

        :param cluster: cluster to save or update
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

        path = self._get_cluster_storage_path(cluster.name)
        cluster.storage_file = path
        with open(path, 'wb') as storage:
            self.dump(cluster, storage)

    def delete(self, cluster):
        """Deletes the cluster from persistent state.

        :param cluster: cluster to delete from persistent state
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        path = self._get_cluster_storage_path(cluster.name)
        if os.path.exists(path):
            os.unlink(path)


class PickleRepository(DiskRepository):
    """This implementation of :py:class:`AbstractClusterRepository` stores the
    cluster on the local disc using pickle. Therefore the cluster object and
    all its dependencies will be saved in a pickle (binary) file.

    :param str storage_path: path to the folder to store the cluster
                             information
    """

    file_ending = 'pickle'
    def __init__(self, storage_path):
        DiskRepository.__init__(self, storage_path)
        self.repository_types = [PickleRepository]

    def load(self, fp):
        """Load cluster from file descriptor fp"""
        cluster = pickle.load(fp)
        cluster.repository = self
        return cluster

    @staticmethod
    def dump(cluster, fp):
        pickle.dump(cluster, fp, pickle.HIGHEST_PROTOCOL)


class JsonRepository(DiskRepository):
    """This implementation of :py:class:`AbstractClusterRepository` stores the
    cluster on a file in json format.

    :param str storage_path: path to the folder to store the cluster
                             information
    """
    file_ending = 'json'

    def load(self, fp):
        data = json.load(fp)
        from elasticluster import Cluster
        cluster = Cluster(**data)
        cluster.repository = self
        return cluster

    @staticmethod
    def dump(cluster, fp):
        state = cluster.to_dict(omit=(
            '_cloud_provider',
            '_naming_policy',
            '_setup_provider',
            'repository',
            'storage_file',
        ))
        json.dump(state, fp, default=dict, indent=4)


class YamlRepository(DiskRepository):
    """This implementation of :py:class:`AbstractClusterRepository` stores the
    cluster on a file in yaml format.

    :param str storage_path: path to the folder to store the cluster
                             information
    """
    file_ending = 'yaml'

    def load(self, fp):
        data = yaml.load(fp)
        from elasticluster import Cluster
        cluster = Cluster(**data)
        cluster.repository = self
        return cluster

    @staticmethod
    def dump(cluster, fp):
        state = cluster.to_dict(omit=(
            '_cloud_provider',
            '_naming_policy',
            '_setup_provider',
            'repository',
            'storage_file',
        ))
        # FIXME: This round-trip to JSON and back is used to
        # deep-convert the contents of `state` into basic Python
        # types, so that PyYAML can handle serialization without
        # additional hints. It should be rewritten to use PyYAML's
        # native "representers" mechanism, see:
        # http://pyyaml.org/wiki/PyYAMLDocumentation#Constructorsrepresentersresolvers
        state = json.loads(json.dumps(state, default=dict))
        yaml.safe_dump(state, fp, default_flow_style=False, indent=4)


class MultiDiskRepository(AbstractClusterRepository):
    """
    This class is able to deal with multiple type of storage types.
    """
    storage_type_map = {'pickle': PickleRepository,
                        'json': JsonRepository,
                        'yaml': YamlRepository}

    def __init__(self, storage_path, default_store='yaml'):
        storage_path = os.path.expanduser(storage_path)
        storage_path = os.path.expandvars(storage_path)
        self.storage_path = storage_path
        try:
            self.default_store = self.storage_type_map[default_store]
        except KeyError:
            raise ValueError(
                "Invalid storage type %s. Allowed values: %s" % (
                    default_store, str.join(', ', self.storage_type_map)))

    def get_all(self):
        clusters = []
        for cls in self.storage_type_map.values():
            cluster_files = glob.glob(
                '%s/*.%s' % (self.storage_path, cls.file_ending))

            for fname in cluster_files:
                try:
                    store = cls(self.storage_path)
                    name = fname[:-len(store.file_ending)-1]
                    cluster = store.get(name)
                    cluster = migrate_cluster(cluster)
                    clusters.append(cluster)
                except (ImportError, AttributeError) as ex:
                    log.error("Unable to load cluster %s: `%s`", fname, ex)
                    log.error("If cluster %s was created with a previous version of elasticluster, you may need to run `elasticluster migrate %s %s` to update it.", fname, self.storage_path, fname)
        return clusters

    def _get_store_by_name(self, name):
        """Return an instance of the correct DiskRepository based on the *first* file that matches the standard syntax for repository files"""
        for cls in self.storage_type_map.values():
            cluster_files = glob.glob(
                '%s/%s.%s' % (self.storage_path, name, cls.file_ending))
            if cluster_files:
                try:
                    return cls(self.storage_path)
                except:
                    continue
        raise ClusterNotFound("No cluster %s was found" % name)


    def get(self, name):
        store = self._get_store_by_name(name)
        return store.get(name)

    def save_or_update(self, cluster):
        if cluster.repository is self:
            # That's a pity, we have to find out the best class
            try:
                store = self._get_store_by_name(cluster.name)
            except ClusterNotFound:
                # Use one of the substores
                store = self.default_store(self.storage_path)
            store.save_or_update(cluster)

    def delete(self, cluster):
        store = self._get_store_by_name(name)
        store.delete(cluster)
