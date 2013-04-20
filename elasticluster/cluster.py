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

import json
import os
import signal
import socket
import time

import paramiko

from elasticluster import log
from elasticluster.exceptions import TimeoutError, ClusterNotFound


class Cluster(object):
    """
    Handles all cluster related functionality such as start, setup,
    load, stop, storage etc.
    """
    startup_timeout = 60*10

    def __init__(self, name, cloud, cloud_provider, setup_provider,
                 frontend, compute, configurator, **extra):
        self.name = name
        self._cloud = cloud
        self._frontend = frontend
        self._compute = compute
        self._cloud_provider = cloud_provider
        self._setup_provider = setup_provider

        self._configurator = configurator
        self._storage = configurator.create_cluster_storage()

        self.compute_nodes = []
        self.frontend_nodes = []

        # initialize nodes
        for _ in range(self._frontend):
            self.add_node(Node.frontend_type)

        for _ in range(self._compute):
            self.add_node(Node.compute_type)

    def add_node(self, node_type, name=""):
        """
        Adds a new node, but doesn't start the instance on the cloud.
        Returns the created node instance
        """
        name = ""
        if not name:
            if node_type == Node.frontend_type:
                name = "frontend" + str(len(self.frontend_nodes) + 1).zfill(3)
            elif node_type == Node.compute_type:
                name = "compute" + str(len(self.compute_nodes) + 1).zfill(3)
            else:
                log.warning("Invalid node type %s given. Unable to add node" % node_type)
                return

        node = self._configurator.create_node(self.name, node_type,
                                              self._cloud_provider, name)
        if node_type == Node.frontend_type:
            self.frontend_nodes.append(node)
        else:
            self.compute_nodes.append(node)

        return node

    def remove_node(self, node):
        """
        Removes a node from the cluster, but does not stop it.
        """
        if node.type == Node.compute_type:
            self.compute_nodes.remove(node)
        elif node.type == Node.frontend_type:
            self.frontend_nodes.remove(node)

    def start(self):
        """
        Starts the cluster with the properties given in the
        constructor. It will create the nodes through the configurator
        and delegate all the work to them. After the identifiers of
        all instances are available, it will save the cluster throgh
        the cluster storage.
        """

        # start every node
        for node in self.frontend_nodes + self.compute_nodes:
            if node.is_alive():
                log.warning("Not starting node %s which is "
                            "already up&running.", node.name)
            else:
                node.start()

        # dump the cluster here, so we don't loose any knowledge about nodes
        self._storage.dump_cluster(self)

        # check if all nodes are running, stop all nodes if the
        # timeout is reached
        def timeout_handler(signum, frame):
            raise TimeoutError("problems occured while starting the nodes, "
                               "timeout `%i`", Cluster.startup_timeout)

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(Cluster.startup_timeout)

        try:
            starting_nodes = self.compute_nodes + self.frontend_nodes
            while starting_nodes:
                starting_nodes = [n for n in starting_nodes
                                  if not n.is_alive()]
                if starting_nodes:
                    time.sleep(5)
        except TimeoutError as timeout:
            log.error(timeout.message)
            log.error("timeout error occured: "
                      "stopping all nodes")
            self.stop()

        signal.alarm(0)

        # Try to connect to each node. Run the setup action only when
        # we successfully connect to all of them.
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(Cluster.startup_timeout)
        pending_nodes = self.compute_nodes + self.frontend_nodes
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            while pending_nodes:
                for node in pending_nodes:
                    try:
                        log.debug("Trying to connect to host %s (%s)",
                                  node.name, node.ip_public)
    
                        ssh.connect(node.ip_public,
                                    username=node.image_user,
                                    allow_agent=True,
                                    key_filename=node.user_key_private)
                        log.debug("success!")
                        pending_nodes.remove(node)
                    except socket.error, ex:
                        log.debug("Host %s (%s) not reachable: %s.",
                                  node.name, node.ip_public, ex)
                    except paramiko.SSHException, ex:
                        log.debug("Ignoring error %s connecting to %s",
                                  str(ex), node.name)
                time.sleep(5)
                
            # setup the cluster
            self.setup()
        
        except TimeoutError:
            log.error("Timeout occured after trying to connect to the nodes \
                        via ssh. The nodes are running, but no connection\
                        could be established and the setup did not run. \
                        Please re-run `elasticluster setup %s`", self.name)
            
        signal.alarm(0)

    def stop(self):
        """
        Terminates all instances corresponding to this cluster and
        deletes the cluster storage.
        """
        for node in self.frontend_nodes + self.compute_nodes:
            node.stop()
        self._storage.delete_cluster(self.name)

    def load_from_storage(self):
        """
        Fills the cluster with the stored informations such as
        instance ids, so its possible to resume operations on the
        cloud.
        """
        self._storage.load_cluster(self)

        for n in self.frontend_nodes + self.compute_nodes:
            if not n.is_alive():
                # TODO: this is very dangerous..., start a new
                # instance at least
                log.error(
                    "instance `%s` with name `%s` is not correclty running "
                    "anymore, terminating it.", n.instance_id, n.name)
                n.stop()

    def setup(self):
        try:
            # setup the cluster using the setup provider
            ret = self._setup_provider.setup_cluster(self)
        except Exception, e:
            log.error(
                "the setup provider was not able to setup the cluster, "
                "but the cluster is running by now. Setup provider error "
                "message: `%s`", str(e))
            ret = False

        if not ret:
            log.warning(
                "Cluster `%s` not yet configured. Please, re-run "
                "`elasticluster setup %s` and/or check your configuration",
                self.name, self.name)

        return ret


class Node(object):
    """
    Handles all the node related funcitonality such as start, stop,
    configure, etc.
    """
    frontend_type = 'frontend'
    compute_type = 'compute'

    def __init__(self, name, node_type, cloud_provider, user_key_public,
                 user_key_private, user_key_name, image_user, security_group,
                 image, flavor, setup_classes, image_userdata=None):
        self.name = name
        self.type = node_type
        self._cloud_provider = cloud_provider
        self.user_key_public = user_key_public
        self.user_key_private = user_key_private
        self.user_key_name = user_key_name
        self.image_user = image_user
        self.security_group = security_group
        self.image = image
        self.image_userdata = image_userdata
        self.flavor = flavor
        self.setup_classes = setup_classes

        self.instance_id = None
        self.ip_public = None
        self.ip_private = None

    def start(self):
        """
        Starts an instance for this node on the cloud through the
        clode provider. This method is non-blocking, as soon as the
        node id is returned from the cloud provider, it will return.
        """
        log.info("Starting node %s.", self.name)
        self.instance_id = self._cloud_provider.start_instance(
            self.user_key_name, self.user_key_public, self.security_group,
            self.flavor, self.image, self.image_userdata)
        log.info("starting node with id `%s`" % self.instance_id)

    def stop(self):
        log.info("shutting down instance `%s`",
                 self.instance_id)
        try:
            self._cloud_provider.stop_instance(self.instance_id)
        except:
            log.error("could not stop instance `%s`, it might "
                      "already be down." % self.instance_id)

    def is_alive(self):
        """
        Checks if the current node is up and running in the cloud
        """
        running = False
        if self.instance_id:
            try:
                log.debug("Getting information for instance %s",
                          self.instance_id)
                running = self._cloud_provider.is_instance_running(
                    self.instance_id)
            except Exception, ex:
                log.debug("Ignoring error while looking form vm id %s: %s",
                          self.instance_id, str(ex))

        if running:
            log.info("node `%s` is up and running",
                     self.instance_id)
            self.update_ips()
        else:
            log.debug("waiting for node `%s` to start",
                      self.instance_id)

        return running

    def update_ips(self):
        """
        Updates the ips of the node through the cloud provider.
        """
        if not self.ip_private and not self.ip_public:
            private, public = self._cloud_provider.get_ips(self.instance_id)
            self.ip_public = public
            self.ip_private = private

    def __str__(self):
        return "name=`%s`, id=`%s`, public_ip=`%s`, private_ip=`%s`" % (
            self.name, self.instance_id, self.ip_public, self.ip_private)


class ClusterStorage(object):
    """
    Handles the storage to save information about all the clusters
    managed by this tool.
    """

    def __init__(self, storage_dir):
        self._storage_dir = storage_dir

    def dump_cluster(self, cluster):
        """
        Saves the information of the cluster to disk in json format to
        load it later on.
        """
        db = {"name": cluster.name}
        db["frontend"] = [
            (node.instance_id, node.name) for node in cluster.frontend_nodes]
        db["compute"] = [
            (node.instance_id, node.name) for node in cluster.compute_nodes]

        db_json = json.dumps(db)

        db_path = self._get_json_path(cluster.name)
        self._clear_storage(db_path)

        f = open(db_path, 'w')
        f.write(unicode(db_json))
        f.close()

    def load_cluster(self, cluster):
        """
        Loads a cluster from the local storage and fills the given
        cluster object with the known information.
        """
        db_path = self._get_json_path(cluster.name)

        if not os.path.exists(db_path):
            raise ClusterNotFound("Storage file %s not found" % db_path)
        f = open(db_path, 'r')
        db_json = f.readline()

        information = json.loads(db_json)

        # if a cluster grows the number of nodes in the config is not
        # enough
        compute_names = [n.name for n in cluster.compute_nodes]
        for node in information['compute']:
            if node[1] not in compute_names:
                cluster.add_node(Node.compute_type, name=node[1])

        # The same happens if the cluster is shrunk.
        compute_names = [n[1] for n in information['compute']]
        for node in cluster.compute_nodes:
            if node.name not in compute_names:
                cluster.remove_node(node)

        # fill the information of the nodes
        for node, cache in zip(cluster.frontend_nodes,
                               information['frontend']):
            node.instance_id = cache[0]
            node.name = cache[1]
        for node, cache in zip(cluster.compute_nodes,
                               information['compute']):
            node.instance_id = cache[0]
            node.name = cache[1]

    def delete_cluster(self, cluster_name):
        """
        Deletes the storage of a cluster.
        """
        db_file = self._get_json_path(cluster_name)
        self._clear_storage(db_file)

    def get_stored_clusters(self):
        """
        Returns a list of all stored clusters.
        """
        from os import listdir
        from os.path import isfile, join
        db_files = [f.split(os.extsep, 1)[0]
                    for f in listdir(self._storage_dir)
                    if isfile(join(self._storage_dir, f))]
        return db_files

    def _get_json_path(self, cluster_name):
        """
        Gets the path to the json storage file.
        """
        if not os.path.exists(self._storage_dir):
            os.makedirs(self._storage_dir)
        return os.path.join(self._storage_dir, cluster_name + ".json")

    def _clear_storage(self, db_path):
        """
        Clears a storage file.
        """
        if os.path.exists(db_path):
            os.unlink(db_path)
