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

# System imports
import json
import operator
import os
import signal
import socket
import sys
import time
from multiprocessing.dummy import Manager, Pool
from Queue import Empty

# External modules
import paramiko
from binascii import hexlify

# Elasticluster imports
from elasticluster import log
from elasticluster.exceptions import TimeoutError, ClusterNotFound, \
    NodeNotFound, InstanceError, SecurityGroupError, ImageError, KeypairError,\
    ClusterError

class IgnorePolicy(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        log.info('Ignoring unknown %s host key for %s: %s' %
                 (key.get_name(), hostname, hexlify(key.get_fingerprint())))


class Cluster(object):
    """
    Handles all cluster related functionality such as start, setup,
    load, stop, storage etc.
    """
    startup_timeout = 60 * 10

    def __init__(self, template, name, cloud, cloud_provider, setup_provider,
                 nodes, configurator, min_nodes=None, **extra):
        self.template = template
        self.name = name
        self._cloud = cloud
        self._cloud_provider = cloud_provider
        self._setup_provider = setup_provider

        self._configurator = configurator
        self._storage = configurator.create_cluster_storage()
        self.nodes = dict((k, []) for k in nodes)
        self.ssh_to = extra.get('ssh_to')
        self.extra = extra.copy()
        # initialize nodes
        for cls in nodes:
            for i in range(nodes[cls]):
                self.add_node(cls)

        # set the minimum number of nodes per group
        self.min_nodes = min_nodes
        if not self.min_nodes:
            # the node minimum is implicit if not specified.
            self.min_nodes = nodes
        else:
            # check that each group has a minimum value
            for group, nodes in self.nodes.iteritems():
                if group not in self.min_nodes:
                    self.min_nodes[group] = len(nodes)


    def add_node(self, node_type, name=None):
        """
        Adds a new node, but doesn't start the instance on the cloud.
        Returns the created node instance
        """
        if not name:
            name = "%s%03d" % (node_type, len(self.nodes[node_type]) + 1)

        node = self._configurator.create_node(self.template, node_type,
                                              self._cloud_provider, name)
        self.nodes[node_type].append(node)
        return node

    def remove_node(self, node):
        """
        Removes a node from the cluster, but does not stop it.
        """
        if node.type not in self.nodes:
            log.error("Unable to remove node %s: invalid node type `%s`.",
                      node.name, node.type)
        else:
            index = self.nodes[node.type].index(node)
            if self.nodes[node.type][index]:
                del self.nodes[node.type][index]

    @staticmethod
    def _start_node(node):
        """
        Static method to start a specific node on a cloud
        """
        log.debug("_start_node: working on node %s" % node.name)
        # TODO: the following check is not optimal yet. When a
        # node is still in a starting state,
        # it will start another node here,
        # since the `is_alive` method will only check for
        # running nodes (see issue #13)
        if node.is_alive():
            log.info("Not starting node %s which is "
                     "already up&running.", node.name)
            return True
        else:
            try:
                node.start()
                log.info("_start_node: node has been started")
                return True
            except Exception as e:
                log.error("could not start node `%s` for reason "
                          "`%s`" % (node.name, e))
                return None

    def start(self):
        """
        Starts the cluster with the properties given in the
        constructor. It will create the nodes through the configurator
        and delegate all the work to them. After the identifiers of
        all instances are available, it will save the cluster through
        the cluster storage.
        """

        # To not mess up the cluster management we start the nodes in a
        # different thread. In this case the main thread receives the sigint
        # and communicates to the `start_node` thread. The nodes to work on
        # are passed in a managed queue.
        self.keep_running = True
        def sigint_handler(signal, frame):
            """
            Makes sure the cluster is stored, before the sigint results in
            exiting during the node startup.
            """
            log.error("user interruption: saving cluster before exit.")
            self.keep_running = False

        nodes = self.get_all_nodes()
        thread_pool = Pool(processes=len(nodes))
        log.debug("Created pool of %d threads" % len(nodes))
        signal.signal(signal.SIGINT, sigint_handler)

        # This is blocking
        result = thread_pool.map_async(self._start_node, nodes)

        while not result.ready():
            result.wait(1)
            if not self.keep_running:
                # the user did abort the start of the cluster. We finish the
                #  current start of a node and save the status to the
                # storage, so we don't have not managed instances laying
                # around
                log.error("Aborting upon Ctrl-C")
                thread_pool.close()
                thread_pool.join()
                self._storage.dump_cluster(self)
                sys.exit(1)

        # dump the cluster here, so we don't loose any knowledge
        self._storage.dump_cluster(self)

        signal.alarm(0)

        def sigint_reset(signal, frame):
            sys.exit(1)
        signal.signal(signal.SIGINT, sigint_reset)

        # check if all nodes are running, stop all nodes if the
        # timeout is reached
        def timeout_handler(signum, frame):
            raise TimeoutError("problems occured while starting the nodes, "
                               "timeout `%i`", Cluster.startup_timeout)

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(Cluster.startup_timeout)

        starting_nodes = self.get_all_nodes()
        try:
            while starting_nodes:
                starting_nodes = [n for n in starting_nodes
                                  if not n.is_alive()]
                if starting_nodes:
                    time.sleep(10)
        except TimeoutError as timeout:
            log.error("Not all nodes were started correctly within the given"
                      " timeout `%s`" % Cluster.startup_timeout)
            for node in starting_nodes:
                log.error("Stopping node `%s`, since it could not start "
                          "within the given timeout" % node.name)
                node.stop()
                self.remove_node(node)

        signal.alarm(0)

        # If we reached this point, we should have IP addresses for
        # the nodes, so update the storage file again.
        self._storage.dump_cluster(self)

        # Try to connect to each node. Run the setup action only when
        # we successfully connect to all of them.
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(Cluster.startup_timeout)
        pending_nodes = self.get_all_nodes()[:]

        try:
            while pending_nodes:
                for node in pending_nodes[:]:
                    if node.connect():
                        log.info("Connection to node %s (%s) successful.",
                                 node.name, node.ip_public)
                        pending_nodes.remove(node)
                if pending_nodes:
                    time.sleep(5)

        except TimeoutError:
            # remove the pending nodes from the cluster
            log.error("Could not connect to all the nodes of the "
                      "cluster within the given timeout `%s`."
                      % Cluster.startup_timeout)
            for node in pending_nodes:
                log.error("Stopping node `%s`, since we could not connect to"
                          " it within the timeout." % node.name)
                node.stop()
                self.remove_node(node)

        signal.alarm(0)

        # A lot of things could go wrong when starting the cluster. To
        # ensure a stable cluster fitting the needs of the user in terms of
        # cluster size, we check the minimum nodes within the node groups to
        # match the current setup.
        self._check_cluster_size()


    def _check_cluster_size(self):
        """
        Checks the size of the cluster to fit the needs of the user. It
        considers the minimum values for the node groups if present.
        Otherwise it will assume the user wants the amount of specified
        nodes.
        :raises: ClusterError
        """
        # check the total sizes before moving the nodes around
        minimum_nodes = 0
        for group, size in self.min_nodes.iteritems():
            minimum_nodes = minimum_nodes + size

        if len(self.get_all_nodes()) < minimum_nodes:
            raise ClusterError("The cluster does not provide the minimum "
                               "amount of nodes specified in the "
                               "configuration. The nodes are still running, "
                               "but will not be setup yet. Please change the"
                               " minimum amount of nodes in the "
                               "configuration or try to start a new cluster "
                               "after checking the cloud provider settings.")

        # finding all node groups with an unsatisfied amount of nodes
        unsatisfied_groups = []
        for group, size in self.min_nodes.iteritems():
            if len(self.nodes[group]) < size:
                unsatisfied_groups.append(group)

        # trying to move nodes around to fill the groups with missing nodes
        for ugroup in unsatisfied_groups[:]:
            missing = self.min_nodes[ugroup] - len(self.nodes[ugroup])
            for group, nodes in self.nodes.iteritems():
                spare = len(self.nodes[group]) - self.min_nodes[group]
                while spare > 0 and missing > 0:
                    self.nodes[ugroup].append(self.nodes[group][-1])
                    del self.nodes[group][-1]
                    spare = spare - 1
                    missing = missing - 1

                    if missing == 0:
                        unsatisfied_groups.remove(ugroup)

        if unsatisfied_groups:
            raise ClusterError("Could not find an optimal solution to "
                               "distribute the started nodes into the node "
                               "groups to satisfy the minimum amount of "
                               "nodes. Please change the minimum amount of "
                               "nodes in the configuration or try to start a"
                               " new clouster after checking the cloud "
                               "provider settings")

    def get_all_nodes(self):
        """
        Returns a list of all the nodes of the cluster.
        """
        nodes = self.nodes.values()
        if nodes:
            return reduce(operator.add, nodes, list())
        else:
            return []

    def stop(self, force=False):
        """
        Terminates all instances corresponding to this cluster and
        deletes the cluster storage.
        """
        for node in self.get_all_nodes():
            if node.instance_id:
                try:
                    node.stop()
                    self.nodes[node.type].remove(node)
                    log.debug("Removed node with instance id %s from %s"
                              % (node.instance_id, node.type))
                except:
                    # Boto does not always raises an `Exception` class!
                    log.error("could not stop instance `%s`, it might "
                              "already be down.", node.instance_id)
            else:
                log.debug("Not stopping node with no instance id. It seems "
                          "like node `%s` did not start correctly."
                          % node.name)
                self.nodes[node.type].remove(node)
        if not self.get_all_nodes():
            log.debug("Removing cluster %s.", self.name)
            self._setup_provider.cleanup()
            self._storage.delete_cluster(self.name)
        elif not force:
            log.warning("Not all instances have been terminated. "
                        "Please rerun the `elasticluster stop %s`", self.name)
            self._storage.dump_cluster(self)
        else:
            log.warning("Not all instances have been terminated. However, "
                        "as requested, the cluster has been force-removed.")
            self._setup_provider.cleanup()
            self._storage.delete_cluster(self.name)

    def get_frontend_node(self):
        """
        Returns the first node of the class specified in the
        configuration file as `ssh_to`, or the first node of
        the first class in alphabetic order.
        """
        if self.ssh_to:
            if self.ssh_to in self.nodes:
                cls = self.nodes[self.ssh_to]
                if cls:
                    return cls[0]
                else:
                    log.warning(
                        "preferred `ssh_to` `%s` is empty: unable to "
                        "get the choosen frontend node from that class.",
                        self.ssh_to)
            else:
                raise NodeNotFound(
                    "Invalid ssh_to `%s`. Please check your "
                    "configuration file." % self.ssh_to)

        # If we reach this point, the preferred class was empty. Pick
        # one using the default logic.
        for cls in sorted(self.nodes.keys()):
            if self.nodes[cls]:
                return self.nodes[cls][0]
        # Uh-oh, no nodes in this cluster.
        raise NodeNotFound("Unable to find a valid frontend: "
                           "cluster has no nodes!")

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

    def update(self):
        for node in self.get_all_nodes():
            try:
                node.update_ips()
            except InstanceError, ex:
                log.warning("Ignoring error updating information on node %s: %s",
                          node, str(ex))
        self._storage.dump_cluster(self)


class Node(object):
    """
    Handles all the node related funcitonality such as start, stop,
    configure, etc.
    """
    frontend_type = 'frontend'
    compute_type = 'compute'
    connection_timeout = 10

    def __init__(self, name, node_type, cloud_provider, user_key_public,
                 user_key_private, user_key_name, image_user, security_group,
                 image, flavor, image_userdata=None):
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
            self.user_key_name, self.user_key_public, self.user_key_private,
            self.security_group,
            self.flavor, self.image, self.image_userdata,
            username=self.image_user)
        log.debug("Node %s has instance_id: `%s`", self.name, self.instance_id)

    def stop(self):
        log.info("shutting down instance `%s`",
                 self.instance_id)
        self._cloud_provider.stop_instance(self.instance_id)

    def is_alive(self):
        """
        Checks if the current node is up and running in the cloud
        """
        running = False
        if not self.instance_id:
            return running

        try:
            log.debug("Getting information for instance %s",
                      self.instance_id)
            running = self._cloud_provider.is_instance_running(
                self.instance_id)
        except Exception, ex:
            log.debug("Ignoring error while looking for vm id %s: %s",
                      self.instance_id, str(ex))
        if running:
            log.debug("node `%s` (instance id %s) is up and running",
                      self.name, self.instance_id)
            self.update_ips()
        else:
            log.debug("node `%s` (instance id `%s`) still building...",
                      self.name, self.instance_id)

        return running

    def connect(self):
        """
        Connect to the node via ssh and returns a paramiko.SSHClient
        object, or None if we are unable to connect.
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(IgnorePolicy())
        try:
            log.debug("Trying to connect to host %s (%s)",
                      self.name, self.ip_public)
            ssh.connect(self.ip_public,
                        username=self.image_user,
                        allow_agent=True,
                        key_filename=self.user_key_private,
                        timeout=Node.connection_timeout)
            log.debug("Connection to %s succeded!", self.ip_public)
            return ssh
        except socket.error, ex:
            log.debug("Host %s (%s) not reachable: %s.",
                      self.name, self.ip_public, ex)
        except paramiko.SSHException, ex:
            log.debug("Ignoring error %s connecting to %s",
                      str(ex), self.name)

        return None

    def update_ips(self):
        """
        Updates the ips of the node through the cloud provider.
        """
        if not self.ip_private or not self.ip_public:
            private, public = self._cloud_provider.get_ips(self.instance_id)
            self.ip_public = public
            self.ip_private = private

    def __str__(self):
        return "name=`%s`, id=`%s`, public_ip=`%s`, private_ip=`%s`" % (
            self.name, self.instance_id, self.ip_public, self.ip_private)

    def pprint(self):
        """
        Pretty print information about the node.
        """
        return """%s
public IP:   %s
private IP:  %s
instance id: %s
instance flavor: %s""" % (self.name, self.ip_public, self.ip_private,
                          self.instance_id, self.flavor)


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
        db = {"name": cluster.name, "template": cluster.template}
        for cls in cluster.nodes:
            db[cls + '_nodes'] = len(cluster.nodes[cls])
        db["nodes"] = [
            {'instance_id': node.instance_id,
             'name': node.name,
             'type': node.type,
             'ip_public': node.ip_public,
             'ip_private': node.ip_private}
            for node in cluster.get_all_nodes()]

        db_json = json.dumps(db)

        db_path = self._get_json_path(cluster.name)

        f = open(db_path, 'w')
        f.write(unicode(db_json))
        f.close()

    def load_cluster(self, cluster_name):
        """
        Read the storage file, create a cluster and return a `Cluster`
        object.
        """
        db_path = self._get_json_path(cluster_name)

        if not os.path.exists(db_path):
            raise ClusterNotFound("Storage file %s not found" % db_path)
        f = open(db_path, 'r')
        db_json = f.readline()

        information = json.loads(db_json)

        return information

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
        allfiles = os.listdir(self._storage_dir)
        db_files = []
        for fname in allfiles:
            fpath = os.path.join(self._storage_dir, fname)
            if fname.endswith('.json') and os.path.isfile(fpath):
                db_files.append(fname[:-5])
            else:
                log.info("Ignoring invalid storage file %s", fpath)

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
