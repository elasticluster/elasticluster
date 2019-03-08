#! /usr/bin/env python
#
# Copyright (C) 2013-2018 University of Zurich
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
__author__ = '''
Nicolas Baer <nicolas.baer@uzh.ch>,
Antonio Messina <antonio.s.messina@gmail.com>,
Riccardo Murri <riccardo.murri@gmail.com>
'''

# System imports
from collections import defaultdict
from copy import copy
import itertools
import operator
import os
import re
import signal
import socket
import sys
import time
from multiprocessing.dummy import Pool

# External modules
import paramiko
from binascii import hexlify

# Elasticluster imports
from elasticluster import log
from elasticluster.exceptions import (
    ClusterError,
    ClusterSizeError,
    ConfigurationError,
    InstanceError,
    InstanceNotFoundError,
    NodeNotFound,
    TimeoutError,
)
from elasticluster.repository import MemRepository
from elasticluster.utils import (
    Struct,
    expand_ssh_proxy_command,
    get_num_processors,
    parse_ip_address_and_port,
    sighandler,
    timeout,
)

SSH_PORT = 22


def raise_timeout_error(signum, frame):
    raise TimeoutError()


class IgnorePolicy(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        log.info('Ignoring unknown %s host key for %s: %s' %
                 (key.get_name(), hostname, hexlify(key.get_fingerprint())))


class Cluster(Struct):
    """
    This is the heart of elasticluster and handles all cluster relevant
    behavior. You can basically start, setup and stop a cluster. Also it
    provides factory methods to add nodes to the cluster.
    A typical workflow is as follows:

    * create a new cluster
    * add nodes to fit your computing needs
    * start cluster; start all instances in the cloud
    * setup cluster; configure all nodes to fit your computing cluster
    * eventually stop cluster; destroys all instances in the cloud

    :param str name: unique identifier of the cluster

    :param cloud_provider: access to the cloud to manage nodes
    :type cloud_provider: :py:class:`elasticluster.providers.AbstractCloudProvider`

    :param setup_provider: provider to setup cluster
    :type setup_provider: :py:class:`elasticluster.providers.AbstractSetupProvider`

    :param str user_key_name: name of the ssh key to connect to cloud

    :param str user_key_public: path to ssh public key file

    :param str user_key_private: path to ssh private key file

    :param int start_timeout:
        Maximum time (in seconds) to wait for all cluster nodes to be
        up and running. Nodes that are not up and running (i.e., an
        SSH connection can be successfully established) within this
        time lapse are marked as "down".

    :param int ssh_probe_timeout: Maximum time (in seconds) to wait
        for each SSH connection attempt to succeed. If no attempt
        succeed within `start_timeout`, then the node is marked as
        "down".

    :param repository: by default the
                       :py:class:`elasticluster.repository.MemRepository` is
                       used to store the cluster in memory. Provide another
                       repository to store the cluster in a persistent state.
    :type repository: :py:class:`elasticluster.repository.AbstractClusterRepository`

    :param extra: tbd.


    :ivar nodes: dict [node_type] = [:py:class:`Node`] that represents all
                 nodes in this cluster
    """
    polling_interval = 10  #: how often to ask the cloud provider for node state

    def __init__(self, name, user_key_name='elasticluster-key',
                 user_key_public='~/.ssh/id_rsa.pub',
                 user_key_private='~/.ssh/id_rsa',
                 cloud_provider=None,
                 setup_provider=None,
                 availability_zone='',
                 repository=None,
                 start_timeout=600,
                 ssh_probe_timeout=5,
                 ssh_proxy_command='',
                 thread_pool_max_size=10,
                 **extra):
        self.name = name
        self.template = extra.pop('template', None)
        self._cloud_provider = cloud_provider
        self._setup_provider = setup_provider
        self.availability_zone = availability_zone
        self.ssh_probe_timeout = ssh_probe_timeout
        self.ssh_proxy_command = ssh_proxy_command
        self.start_timeout = start_timeout
        self.thread_pool_max_size = thread_pool_max_size
        self.user_key_name = user_key_name
        self.repository = repository if repository else MemRepository()

        self.ssh_to = extra.pop('ssh_to', None)

        self.user_key_private = os.path.expandvars(user_key_private)
        self.user_key_private = os.path.expanduser(user_key_private)

        self.user_key_public = os.path.expanduser(user_key_public)
        self.user_key_public = os.path.expandvars(user_key_public)

        # this needs to exist before `add_node()` is called
        self._naming_policy = NodeNamingPolicy()

        self.nodes = {}
        if 'nodes' in extra:
            # Build the internal nodes. This is mostly useful when loading
            # the cluster from json files.
            for kind, nodes in extra['nodes'].items():
                for node in nodes:
                    # adding un-named nodes before NodeNamingPolicy has
                    # been fully populated can lead to duplicate names
                    assert 'name' in node
                    self.add_node(**node)
            del extra['nodes']
        if 'paused_nodes' in extra:
            self.paused_nodes = dict(extra['paused_nodes'])
        else:
            self.paused_nodes = {}

        self.extra = {}
        # FIXME: ugly fix needed when saving and loading the same
        # cluster using json. The `extra` keywords will become a
        # single, dictionary-valued, `extra` option when calling again
        # the constructor.
        self.extra.update(extra.pop('extra', {}))

        # attributes that have already been defined trump whatever is
        # in the `extra` dictionary
        for key in extra.keys():
            if hasattr(self, key):
                del extra[key]
        self.extra.update(extra)

    @property
    def known_hosts_file(self):
        return os.path.join(self.repository.storage_path,
                            "%s.known_hosts" % self.name)

    @property
    def cloud_provider(self):
        return self._cloud_provider

    @cloud_provider.setter
    def cloud_provider(self, provider):
        self._cloud_provider = provider
        for node in self.get_all_nodes():
            node._cloud_provider = provider

    def to_dict(self, omit=()):
        """
        Return a (shallow) copy of self cast to a dictionary,
        optionally omitting some key/value pairs.
        """
        result = self.__dict__.copy()
        for key in omit:
            if key in result:
                del result[key]
        return result

    def to_vars_dict(self):
        """
        Return local state which is relevant to the cluster setup process.
        """
        return self.to_dict(omit=[
            '_cloud_provider',
            '_naming_policy',
            '_setup_provider',
            'repository',
            'ssh_proxy_command',
            'ssh_to',
            'storage_file',
            'thread_pool_max_size',
        ])

    def __getstate__(self):
        return self.to_dict(omit=('_cloud_provider', '_naming_policy',
                                  '_setup_provider',))

    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__['_setup_provider'] = None
        self.__dict__['_cloud_provider'] = None
        self.__dict__['_naming_policy'] = None

    def __update_option(self, cfg, key, attr):
        oldvalue = getattr(self, attr)
        if key in cfg and cfg[key] != oldvalue:
            setattr(self, attr, cfg[key])
            return oldvalue
        return False

    def keys(self):
        """Only expose some of the attributes when using as a dictionary"""
        keys = Struct.keys(self)
        for key in (
                '_cloud_provider',
                '_naming_policy',
                '_setup_provider',
                'known_hosts_file',
                'repository',
        ):
            if key in keys:
                keys.remove(key)
        return keys

    def update_config(self, cluster_config, login_config):
        """Update current configuration.

        This method is usually called after loading a `Cluster`
        instance from a persistent storage. Note that not all fields
        are actually updated, but only those that can be safely
        updated.
        """

        oldvalue = self.__update_option(cluster_config, 'ssh_to', 'ssh_to')
        if oldvalue:
            log.debug("Attribute 'ssh_to' updated: %s -> %s", oldvalue, self.ssh_to)

    # a kind must *not* end with a digit, otherwise we'll have a hard
    # time extracting the node index with the default naming policy
    _NODE_KIND_RE = re.compile(r'^[a-z0-9-]*[a-z-]+$', re.I)

    def add_node(self, kind, image_id, image_user, flavor,
                 security_group, image_userdata='', name=None, **extra):
        """
        Adds a new node to the cluster. This factory method provides an
        easy way to add a new node to the cluster by specifying all relevant
        parameters. The node does not get started nor setup automatically,
        this has to be done manually afterwards.

        :param str kind: kind of node to start. this refers to the
                         groups defined in the ansible setup provider
                         :py:class:`elasticluster.providers.AnsibleSetupProvider`
                         Please note that this can only contain
                         alphanumeric characters and hyphens (and must
                         not end with a digit), as it is used to build
                         a valid hostname

        :param str image_id: image id to use for the cloud instance (e.g.
                             ami on amazon)

        :param str image_user: user to login on given image

        :param str flavor: machine type to use for cloud instance

        :param str security_group: security group that defines firewall rules
                                   to the instance

        :param str image_userdata: commands to execute after instance starts

        :param str name: name of this node, automatically generated if None

        :raises: ValueError: `kind` argument is an invalid string.

        :return: created :py:class:`Node`
        """
        if not self._NODE_KIND_RE.match(kind):
            raise ValueError(
                "Invalid name `{kind}`. The `kind` argument may only contain"
                " alphanumeric characters, and must not end with a digit."
                    .format(kind=kind))

        if kind not in self.nodes:
            self.nodes[kind] = []

        # To ease json dump/load, use `extra` dictionary to
        # instantiate Node class
        extra.update(
            cloud_provider=self._cloud_provider,
            cluster_name=self.name,
            flavor=flavor,
            image_id=image_id,
            image_user=image_user,
            image_userdata=image_userdata,
            kind=kind,
            security_group=security_group,
        )
        for attr in (
                'flavor',
                'image_id',
                'image_user',
                'image_userdata',
                'security_group',
                'user_key_name',
                'user_key_private',
                'user_key_public',
        ):
            if attr not in extra:
                extra[attr] = getattr(self, attr)

        if not name:
            # `extra` contains key `kind` already
            name = self._naming_policy.new(**extra)
        else:
            self._naming_policy.use(kind, name)
        node = Node(name=name, **extra)

        self.nodes[kind].append(node)
        return node

    def add_nodes(self, kind, num, image_id, image_user, flavor,
                  security_group, image_userdata='', **extra):
        """Helper method to add multiple nodes of the same kind to a cluster.

        :param str kind: kind of node to start. this refers to the groups
                         defined in the ansible setup provider
                         :py:class:`elasticluster.providers.AnsibleSetupProvider`

        :param int num: number of nodes to add of this kind

        :param str image_id: image id to use for the cloud instance (e.g.
                             ami on amazon)

        :param str image_user: user to login on given image

        :param str flavor: machine type to use for cloud instance

        :param str security_group: security group that defines firewall rules
                                   to the instance

        :param str image_userdata: commands to execute after instance starts
        """
        for i in range(num):
            self.add_node(kind, image_id, image_user, flavor,
                          security_group, image_userdata=image_userdata, **extra)

    def remove_node(self, node, stop=False):
        """Removes a node from the cluster.

        By default, it doesn't also stop the node, just remove from
        the known hosts of this cluster.

        :param node: node to remove
        :type node: :py:class:`Node`

        :param stop: Stop the node
        :type stop: bool

        """
        if node.kind not in self.nodes:
            raise NodeNotFound("Unable to remove node %s: invalid node type `%s`.",
                               node.name, node.kind)
        else:
            try:
                index = self.nodes[node.kind].index(node)
                if self.nodes[node.kind][index]:
                    del self.nodes[node.kind][index]
                if stop:
                    node.stop()
                self._naming_policy.free(node.kind, node.name)
                self.repository.save_or_update(self)
                remaining_nodes = self.get_all_nodes()
                self._gather_node_ip_addresses(
                    remaining_nodes, self.start_timeout, self.ssh_probe_timeout,
                    remake=True)
            except ValueError:
                raise NodeNotFound("Node %s not found in cluster" % node.name)

    def start(self, min_nodes=None, max_concurrent_requests=0):
        """
        Starts up all the instances in the cloud.

        To speed things up, all
        instances are started in a seperate thread. To make sure
        ElastiCluster is not stopped during creation of an instance, it will
        overwrite the sigint handler. As soon as the last started instance
        is returned and saved to the repository, sigint is executed as usual.

        A VM instance is considered 'up and running' as soon as an SSH
        connection can be established. If the startup timeout is reached before
        all instances are started, ElastiCluster stops the cluster and
        terminates all VM instances.

        This method is blocking and might take some time depending on the
        amount of instances to start.

        :param min_nodes: minimum number of nodes to start in case the quota
                          is reached before all instances are up
        :type min_nodes: dict [node_kind] = number
        :param int max_concurrent_requests:
          Issue at most this number of requests to start
          VMs; if 1 or less, start nodes one at a time (sequentially).
          The special value ``0`` means run 4 threads for each available
          processor.
        """

        nodes = self.get_all_nodes()

        log.info(
            "Starting cluster nodes (timeout: %d seconds) ...",
            self.start_timeout)
        if max_concurrent_requests == 0:
            try:
                max_concurrent_requests = 4 * get_num_processors()
            except RuntimeError:
                log.warning(
                    "Cannot determine number of processors!"
                    " will start nodes sequentially...")
                max_concurrent_requests = 1
        if max_concurrent_requests > 1:
            nodes = self._start_nodes_parallel(nodes, max_concurrent_requests)
        else:
            nodes = self._start_nodes_sequentially(nodes)

        # checkpoint cluster state
        self.repository.save_or_update(self)

        not_started_nodes = self._check_starting_nodes(nodes, self.start_timeout)

        # now that all nodes are up, checkpoint cluster state again
        self.repository.save_or_update(self)

        # Try to connect to each node to gather IP addresses and SSH host keys
        started_nodes = nodes - not_started_nodes
        if not started_nodes:
            raise ClusterSizeError("No nodes could be started!")
        log.info(
            "Checking SSH connection to nodes (timeout: %d seconds) ...",
            self.start_timeout)
        self._gather_node_ip_addresses(
            started_nodes, self.start_timeout, self.ssh_probe_timeout)
        # It's possible that the node.connect() call updated the
        # `preferred_ip` attribute, so, let's save the cluster again.
        self.repository.save_or_update(self)

        # A lot of things could go wrong when starting the cluster.
        # Check that the minimum number of nodes within each groups is
        # reachable. Raise `ClusterSizeError()` if not.
        self._check_cluster_size(self._compute_min_nodes(min_nodes))

    def _start_nodes_sequentially(self, nodes):
        """
        Start the nodes sequentially without forking.

        Return set of nodes that were actually started.
        """
        log.debug("Note: will *not* issue parallel requests to cloud API.")
        started_nodes = set()
        for node in copy(nodes):
            started = self._start_node(node)
            if started:
                started_nodes.add(node)
            # checkpoint cluster state
            self.repository.save_or_update(self)
        return started_nodes

    def _start_nodes_parallel(self, nodes, max_thread_pool_size):
        """
        Start the nodes using a pool of multiprocessing threads for speed-up.

        Return set of nodes that were actually started.
        """
        # Create one thread for each node to start
        thread_pool_size = min(len(nodes), max_thread_pool_size)
        thread_pool = Pool(processes=thread_pool_size)
        log.debug("Note: starting %d nodes concurrently.", thread_pool_size)

        # pressing Ctrl+C flips this flag, which in turn stops the main loop
        # down below
        keep_running = True

        def sigint_handler(signal, frame):
            """
            Makes sure the cluster is saved, before the sigint results in
            exiting during node startup.
            """
            log.error(
                "Interrupted: will save cluster state and exit"
                " after all nodes have started.")
            keep_running = False

        # intercept Ctrl+C
        with sighandler(signal.SIGINT, sigint_handler):
            result = thread_pool.map_async(self._start_node, nodes)
            while not result.ready():
                result.wait(1)
                # check if Ctrl+C was pressed
                if not keep_running:
                    log.error("Aborting upon user interruption ...")
                    # FIXME: `.close()` will keep the pool running until all
                    # nodes have been started; should we use `.terminate()`
                    # instead to interrupt node creation as soon as possible?
                    thread_pool.close()
                    thread_pool.join()
                    self.repository.save_or_update(self)
                    # FIXME: should raise an exception instead!
                    sys.exit(1)

            # keep only nodes that were successfully started
            return set(node for node, ok
                       in itertools.izip(nodes, result.get()) if ok)

    @staticmethod
    def _start_node(node):
        """
        Start the given node VM.

        :return: bool -- True on success, False otherwise
        """
        log.debug("_start_node: working on node `%s`", node.name)
        # FIXME: the following check is not optimal yet. When a node is still
        # in a starting state, it will start another node here, since the
        # `is_alive` method will only check for running nodes (see issue #13)
        if node.is_alive():
            log.info("Not starting node `%s` which is already up.", node.name)
            return True
        else:
            try:
                node.start()
                log.info("Node `%s` has been started.", node.name)
                return True
            except Exception as err:
                log.exception("Could not start node `%s`: %s -- %s",
                              node.name, err, err.__class__)
                return False

    def _check_starting_nodes(self, nodes, lapse):
        """
        Wait until all given nodes are alive, for max `lapse` seconds.
        """
        with timeout(lapse, raise_timeout_error):
            try:
                while nodes:
                    nodes = set(node for node in nodes
                                if not node.is_alive())
                    if nodes:
                        log.debug("Waiting for %d more nodes to come up ...", len(nodes))
                        time.sleep(self.polling_interval)
            except TimeoutError:
                log.error("Some nodes did not start correctly"
                          " within the given %d-seconds timeout: %s",
                          lapse, ', '.join(node.name for node in nodes))
        # return list of not-yet-started nodes,
        # so we can exclude them from coming rounds
        return nodes

    def _gather_node_ip_addresses(self, nodes, lapse, ssh_timeout, remake=False):
        """
        Connect via SSH to each node.

        Return set of nodes that could not be reached with `lapse` seconds.
        """
        # for convenience, we might set this to ``None`` if the file cannot
        # be opened -- but we do not want to forget the cluster-wide
        # setting in case the error is transient
        known_hosts_path = self.known_hosts_file

        # If run with remake=True, deletes known_hosts_file so that it will
        # be recreated. Prevents "Invalid host key" errors
        if remake and os.path.isfile(known_hosts_path):
            os.remove(known_hosts_path)

        # Create the file if it's not present, otherwise the
        # following lines will raise an error
        try:
            fd = open(known_hosts_path, 'a')
            fd.close()
        except IOError as err:
            log.warning("Error opening SSH 'known hosts' file `%s`: %s",
                        known_hosts_path, err)
            known_hosts_path = None

        keys = paramiko.hostkeys.HostKeys(known_hosts_path)

        with timeout(lapse, raise_timeout_error):
            try:
                while nodes:
                    for node in copy(nodes):
                        ssh = node.connect(
                            keyfile=known_hosts_path,
                            timeout=ssh_timeout)
                        if ssh:
                            log.info("Connection to node `%s` successful,"
                                     " using IP address %s to connect.",
                                     node.name, node.connection_ip())
                            # Add host keys to the keys object.
                            for host, key in ssh.get_host_keys().items():
                                for keytype, keydata in key.items():
                                    keys.add(host, keytype, keydata)
                            self._save_keys_to_known_hosts_file(keys)
                            nodes.remove(node)
                    if nodes:
                        time.sleep(self.polling_interval)

            except TimeoutError:
                log.error(
                    "Some nodes of the cluster were unreachable"
                    " within the given %d-seconds timeout: %s",
                    lapse, ', '.join(node.name for node in nodes))

        # return list of nodes
        return nodes

    def _save_keys_to_known_hosts_file(self, keys):
        try:
            keys.save(self.known_hosts_file)
        except IOError:
            log.warning("Ignoring error saving known_hosts file: %s",
                        self.known_hosts_file)

    def _compute_min_nodes(self, min_nodes=None):
        if min_nodes is None:
            min_nodes = {}
        # check that each group has a minimum value
        for group, nodes in self.nodes.items():
            if group not in min_nodes:
                min_nodes[group] = len(nodes)
        return min_nodes

    def _check_cluster_size(self, min_nodes):
        """Checks the size of the cluster to fit the needs of the user. It
        considers the minimum values for the node groups if present.
        Otherwise it will imply the user wants the amount of specified
        nodes at least.

        :param min_nodes: minimum number of nodes for each kind
        :type min_nodes: dict [node_kind] = number
        :raises: ClusterError in case the size does not fit the minimum
                 number specified by the user.
        """
        # finding all node groups with an unsatisfied amount of nodes
        unsatisfied = 0
        for kind, required in min_nodes.iteritems():
            available = len(self.nodes[kind])
            if available < required:
                log.error(
                    "Not enough nodes of kind `%s`:"
                    " %d required, but only %d available.",
                )
                unsatisfied += 1

        if unsatisfied:
            raise ClusterSizeError()


    def get_all_nodes(self):
        """Returns a list of all nodes in this cluster as a mixed list of
        different node kinds.

        :return: list of :py:class:`Node`
        """
        nodes = self.nodes.values()
        if nodes:
            return reduce(operator.add, nodes, list())
        else:
            return []

    def get_node_by_name(self, nodename):
        """Return the node corresponding with name `nodename`

        :params nodename: Name of the node
        :type nodename: str
        """
        nodes = dict((n.name, n) for n in self.get_all_nodes())
        try:
            return nodes[nodename]
        except KeyError:
            raise NodeNotFound(
                "Node `{0}` not found in cluster `{1}`"
                .format(nodename, self.name))

    def stop(self, force=False, wait=False):
        """
        Terminate all VMs in this cluster and delete its repository.

        :param bool force:
          remove cluster from storage even if not all nodes could be stopped.
        """
        log.debug("Stopping cluster `%s` ...", self.name)

        failed = self._stop_all_nodes(wait)

        if failed:
            if force:
                self._delete_saved_data()
                log.warning(
                    "Not all cluster nodes have been terminated."
                    " However, as requested, data about the cluster"
                    " has been removed from local storage.")
            else:
                self.repository.save_or_update(self)
                log.warning(
                    "Not all cluster nodes have been terminated."
                    " Fix errors above and re-run `elasticluster stop %s`",
                    self.name)
        else:
            self._delete_saved_data()

    def pause(self):
        """Pause all VMs in this cluster and store data so that they
        can be restarted later.
        """
        log.info("Pausing cluster `%s` ...", self.name)
        failed = self._pause_all_nodes()
        if os.path.exists(self.known_hosts_file):
            os.remove(self.known_hosts_file)
        self.repository.save_or_update(self)
        if failed:
            log.warning(
                    "Not all cluster nodes have been successfully "
                    "stopped.  Some nodes may still be running - "
                    "check error messages above and consider "
                    "re-running `elasticluster pause %s` if "
                    "necessary.", self.name)

    def resume(self):
        """
        Resume all paused VMs in this cluster.
        """
        log.info("Resuming cluster `%s` ...", self.name)
        failed = self._resume_all_nodes()
        for node in self.get_all_nodes():
            node.update_ips()
        self._gather_node_ip_addresses(
            self.get_all_nodes(), self.start_timeout, self.ssh_probe_timeout)
        self.repository.save_or_update(self)
        if failed:
            log.warning(
                    "Not all cluster nodes have been successfully "
                    "restarted.  Check error messages above and consider "
                    "re-running `elasticluster resume %s` if "
                    "necessary.", self.name)
            return
        if not self._setup_provider.resume_cluster(self):
            log.warning("Elasticluster was not able to guarantee that the "
                        "cluster restarted correctly - check the errors "
                        "above and check your config.")

    def _delete_saved_data(self):
        self._setup_provider.cleanup(self)
        self.repository.delete(self)
        if os.path.exists(self.known_hosts_file):
            os.remove(self.known_hosts_file)

    def _stop_all_nodes(self, wait=False):
        """
        Terminate all cluster nodes. Return number of failures.
        """
        failed = 0
        for node in self.get_all_nodes():
            if not node.instance_id:
                log.warning(
                    "Node `%s` has no instance ID."
                    " Assuming it did not start correctly,"
                    " so removing it anyway from the cluster.", node.name)
                self.nodes[node.kind].remove(node)
                continue
            # try and stop node
            try:
                # wait and pause for and recheck.
                node.stop(wait)

                self.nodes[node.kind].remove(node)
                log.debug(
                    "Removed node `%s` from cluster `%s`", node.name, self.name)
            except InstanceNotFoundError as err:
                log.info(
                    "Node `%s` (instance ID `%s`) was not found;"
                    " assuming it has already been terminated.",
                    node.name, node.instance_id)
            except Exception as err:
                failed += 1
                log.error(
                    "Could not stop node `%s` (instance ID `%s`): %s %s",
                    node.name, node.instance_id, err, err.__class__)
        return failed

    def _make_thread_pool(self, max_thread_pool_size):
        try:
            if max_thread_pool_size == 0:
                max_thread_pool_size = 4 * get_num_processors()
        except RuntimeError:
            log.warning(
                "Cannot determine number of processors!"
                " will start nodes sequentially...")
            max_thread_pool_size = 1
        thread_pool_size = min(len(self.get_all_nodes()), max_thread_pool_size)
        return Pool(processes=thread_pool_size)

    def _pause_all_nodes(self, max_thread_pool_size=0):
        """Pause all cluster nodes - ensure that we store data so that in
        the future the nodes can be restarted.

        :return: int - number of failures.
        """
        failed = 0

        def _pause_specific_node(node):
            if not node.instance_id:
                log.warning("Node `%s` has no instance id."
                            " It is either already stopped, or"
                            " never created properly.  Not attempting"
                            " to stop it again.", node.name)
                return None
            try:
                return node.pause()
            except Exception as err:
                log.error(
                    "Could not stop node `%s` (instance ID `%s`): %s %s",
                    node.name, node.instance_id, err, err.__class__)
                node.update_ips()
                return None

        nodes = self.get_all_nodes()
        thread_pool = self._make_thread_pool(max_thread_pool_size)
        for node, state in zip(nodes, thread_pool.map(_pause_specific_node, nodes)):
            if state is None:
                failed += 1
            else:
                self.paused_nodes[node.name] = state

        return failed

    def _resume_all_nodes(self, max_thread_pool_size=0):
        if not self.paused_nodes:
            log.warning("Didn't find any paused nodes - not resuming anything.")
            return
        thread_pool = self._make_thread_pool(max_thread_pool_size)

        def _resume_single_node(node_name):
            node_state = self.paused_nodes[node_name]
            try:
                log.debug("Resuming node `%s`.", node_name)
                self._cloud_provider.resume_instance(node_state)
                log.debug("Successfully resumed node `%s`.", node_name)
                return node_name
            except Exception as err:
                log.error("Could not resume node `%s` - %s.", node_name, err)
                return None

        for node_name in thread_pool.map(_resume_single_node, self.paused_nodes):
            del self.paused_nodes[node_name]
        return len(self.paused_nodes)

    def get_ssh_to_node(self, ssh_to=None):
        """
        Return target node for SSH/SFTP connections.

        The target node is the first node of the class specified in
        the configuration file as ``ssh_to`` (but argument ``ssh_to``
        can override this choice).

        If not ``ssh_to`` has been specified in this cluster's config,
        then try node class names ``ssh``, ``login``, ``frontend``,
        and ``master``: if any of these is non-empty, return the first
        node.

        If all else fails, return the first node of the first class
        (in alphabetic order).

        :return: :py:class:`Node`
        :raise: :py:class:`elasticluster.exceptions.NodeNotFound`
          if no valid frontend node is found
        """
        if ssh_to is None:
            ssh_to = self.ssh_to

        # first try to interpret `ssh_to` as a node name
        if ssh_to:
            try:
                return self.get_node_by_name(ssh_to)
            except NodeNotFound:
                pass

        # next, ensure `ssh_to` is a class name
        if ssh_to:
            try:
                parts = self._naming_policy.parse(ssh_to)
                log.warning(
                    "Node `%s` not found."
                    " Trying to find other node in class `%s` ...",
                    ssh_to, parts['kind'])
                ssh_to = parts['kind']
            except ValueError:
                # it's already a class name
                pass

        # try getting first node of kind `ssh_to`
        if ssh_to:
            try:
                nodes = self.nodes[ssh_to]
            except KeyError:
                raise ConfigurationError(
                    "Invalid configuration item `ssh_to={ssh_to}` in cluster `{name}`:"
                    " node class `{ssh_to}` does not exist in this cluster."
                    .format(ssh_to=ssh_to, name=self.name))
            try:
                return nodes[0]
            except IndexError:
                log.warning(
                    "Chosen `ssh_to` class `%s` is empty: unable to "
                    "get the choosen frontend node from that class.",
                    ssh_to)

        # If we reach this point, `ssh_to` was not set or the
        # preferred class was empty. Try "natural" `ssh_to` values.
        for kind in ['ssh', 'login', 'frontend', 'master']:
            try:
                nodes = self.nodes[kind]
                return nodes[0]
            except (KeyError, IndexError):
                pass

        # ... if all else fails, return first node
        for kind in sorted(self.nodes.keys()):
            if self.nodes[kind]:
                return self.nodes[kind][0]

        # Uh-oh, no nodes in this cluster!
        raise NodeNotFound("Unable to find a valid frontend:"
                           " cluster has no nodes!")


    def setup(self, extra_args=tuple()):
        """
        Configure the cluster nodes.

        Actual action is delegated to the
        :py:class:`elasticluster.providers.AbstractSetupProvider` that
        was provided at construction time.

        :param list extra_args:
          List of additional command-line arguments
          that are appended to each invocation of the setup program.

        :return: bool - True on success, False otherwise
        """
        try:
            # setup the cluster using the setup provider
            ret = self._setup_provider.setup_cluster(self, extra_args)
        except Exception as err:
            log.error(
                "The cluster hosts are up and running,"
                " but %s failed to set the cluster up: %s",
                self._setup_provider.HUMAN_READABLE_NAME, err)
            ret = False

        if not ret:
            log.warning(
                "Cluster `%s` not yet configured. Please, re-run "
                "`elasticluster setup %s` and/or check your configuration",
                self.name, self.name)

        return ret

    def update(self):
        """
        Update connection information of all nodes in this cluster.

        It happens, for example, that public ip's are not available
        immediately, therefore calling this method might help.
        """
        for node in self.get_all_nodes():
            try:
                node.update_ips()

                # If we previously did not have a preferred_ip or the
                # preferred_ip is not in the current list, then try to connect
                # to one of the node ips and update the preferred_ip.
                if node.ips and \
                        not (node.preferred_ip and \
                                         node.preferred_ip in node.ips):
                    node.connect()
            except InstanceError as ex:
                log.warning("Ignoring error updating information on node %s: %s",
                            node, ex)
        self.repository.save_or_update(self)


class NodeNamingPolicy(object):
    """
    Create names for cluster nodes.

    This class takes care of the book-keeping associated to naming
    nodes in the cluster: generate new names (see :meth:`new`), record
    existing ones (see :meth:`use`), and marking unused names as
    "free" (see :meth:`free`).

    Basic usage is simple: mark any name that is already in use by
    calling :meth:`use` on it, and request new addresses with
    :meth:`new`; any name that is no longer used should be
    unregistered by calling :meth:`free` so that it can be re-used.
    Calls to either method can be freely intermixed.

    From each node name, a numerical "index" is extracted; methods in
    this class ensure that no two names are ever emitted with a
    duplicate index, and that the set of indices in use is as close as
    possible to an integer range starting at 1.

    When the node names in use form a numerical range, each call to
    :meth:`new` just increments the top of the range::

      >>> p = NodeNamingPolicy()
      >>> p.use('foo', 'foo001')
      >>> p.use('foo', 'foo002')
      >>> p.use('foo', 'foo003')
      >>> p.new('foo')
      'foo004'

    When a hole is pinched in the range, however, unused names
    *within* the range are used until all "holes" have been filled::

      >>> p.free('foo', 'foo002')
      >>> p.new('foo')
      'foo002'
      >>> p.new('foo')
      'foo005'

    *Warning:* calling :meth:`use` on a name with a larger sequential
    index than any name in the currently-used range extends the list
    of "holes" with all the names from the old top of the range up to
    the new one::

      >>> p.use('foo', 'foo009')
      >>> p.new('foo') in ['foo006', 'foo007', 'foo008']
      True

    The `pattern` constructor argument allows changing the way the
    node name is built::

      >>> p = NodeNamingPolicy(pattern='node-{kind}-{index}')
      >>> p.new('foo')
      'node-foo-1'

    If you change the pattern, however, you must make sure that
    :meth:`use` and :meth:`free` can parse the name back.  This
    implementation assumes that a node's numerical index is formed by
    the last digits in the name; to implement a more general/complex
    scheme, override methods :meth:`format` and :meth:`parse`.

    This class may seem over-engineered for the simple requirement
    that unique names be generated, but I've actually had to answer
    support requests of the kind "Hey, our cluster has ``compute001``
    and ``compute002`` and then ``compute004`` through ``compute010``
    -- what happened to ``compute003``?", so I'd rather spend a bit
    more time coding than explaining each time that gaps in the naming
    scheme are harmless.
    """

    def __init__(self, pattern=r'{kind}{index:03d}'):
        self.pattern = pattern
        # keep a record of unused node names (by kind) and of the
        # highest-numbered node, in case there are no free ones left.
        self._free = defaultdict(set)
        self._top = defaultdict(int)

    @staticmethod
    def format(pattern, **args):
        """
        Form a node name by interpolating `args` into `pattern`.

        This is actually nothing more than a call to
        `pattern.format(...)` but is provided as a separate
        overrideable method as it is logically paired with
        :meth:`parse`.
        """
        return pattern.format(**args)

    @staticmethod
    def parse(name):
        """
        Return dict of parts forming `name`.  Raise `ValueError` if string
        `name` cannot be correctly parsed.

        The default implementation uses
        `NodeNamingPolicy._NODE_NAME_RE` to parse the name back into
        constituent parts.

        This is ideally the inverse of :meth:`format` -- it should be
        able to parse a node name string into the parameter values
        that were used to form it.
        """
        match = NodeNamingPolicy._NODE_NAME_RE.match(name)
        if match:
            return match.groupdict()
        else:
            raise ValueError(
                "Cannot parse node name `{name}`"
                    .format(name=name))

    _NODE_NAME_RE = re.compile(
        r'(?P<kind>[a-z0-9-]*[a-z-]+) (?P<index>\d+)$',
        re.I | re.X)

    def new(self, kind, **extra):
        """
        Return a host name for a new node of the given kind.

        The new name is formed by interpolating ``{}``-format
        specifiers in the string given as ``pattern`` argument to the
        class constructor.  The following names can be used in the
        ``{}``-format specifiers:

        * ``kind`` -- the `kind` argument
        * ``index`` -- a positive integer number, garanteed to be unique (per kind)
        * any other keyword argument used in the call to :meth:`new`

        Example::

          >>> p = NodeNamingPolicy(pattern='node-{kind}-{index}{spec}')
          >>> p.new('foo', spec='bar')
          'node-foo-1bar'
          >>> p.new('foo', spec='quux')
          'node-foo-2quux'
        """
        if self._free[kind]:
            index = self._free[kind].pop()
        else:
            self._top[kind] += 1
            index = self._top[kind]
        return self.format(self.pattern, kind=kind, index=index, **extra)

    def use(self, kind, name):
        """
        Mark a node name as used.
        """
        try:
            params = self.parse(name)
            index = int(params['index'], 10)
            if index in self._free[kind]:
                self._free[kind].remove(index)
            top = self._top[kind]
            if index > top:
                self._free[kind].update(range(top + 1, index))
                self._top[kind] = index
        except ValueError:
            log.warning(
                "Cannot extract numerical index"
                " from node name `%s`!", name)

    def free(self, kind, name):
        """
        Mark a node name as no longer in use.

        It could thus be recycled to name a new node.
        """
        try:
            params = self.parse(name)
            index = int(params['index'], 10)
            self._free[kind].add(index)
            assert index <= self._top[kind]
            if index == self._top[kind]:
                self._top[kind] -= 1
        except ValueError:
            # ignore failures in self.parse()
            pass


class Node(Struct):
    """The node represents an instance in a cluster. It holds all
    information to connect to the nodes also manages the cloud instance. It
    provides the basic functionality to interact with the cloud instance,
    such as start, stop, check if the instance is up and ssh connect.

    :param str name: identifier of the node

    :param str kind: kind of node in regard to cluster. this usually
                     refers to a specified group in the
                     :py:class:`elasticluster.providers.AbstractSetupProvider`

    :param cloud_provider: cloud provider to manage the instance
    :type cloud_provider: :py:class:`elasticluster.providers.AbstractCloudProvider`

    :param str user_key_public: path to the ssh public key

    :param str user_key_private: path to the ssh private key

    :param str user_key_name: name of the ssh key

    :param str image_user: user to connect to the instance via ssh

    :param str security_group: security group to setup firewall rules

    :param str image: image id to launch instance with

    :param str flavor: machine type to launch instance

    :param str image_userdata: commands to execute after instance start


    :ivar instance_id: id of the node instance on the cloud

    :ivar preferred_ip: IP address used to connect to the node.

    :ivar ips: list of all the IPs defined for this node.
    """

    def __init__(self, name, cluster_name, kind, cloud_provider, user_key_public,
                 user_key_private, user_key_name, image_user, security_group,
                 image_id, flavor, image_userdata=None, ssh_proxy_command='',
                 **extra):
        self.name = name
        self.cluster_name = cluster_name
        self.kind = kind
        self._cloud_provider = cloud_provider
        self.user_key_public = user_key_public
        self.user_key_private = user_key_private
        self.user_key_name = user_key_name
        self.image_user = image_user
        self.security_group = security_group
        self.image_id = image_id
        self.image_userdata = image_userdata
        self.flavor = flavor
        self.ssh_proxy_command = ssh_proxy_command
        self.instance_id = extra.pop('instance_id', None)
        self.preferred_ip = extra.pop('preferred_ip', None)
        self.ips = extra.pop('ips', [])
        # Remove extra arguments, if defined
        for key in extra.keys():
            if hasattr(self, key):
                del extra[key]
        self.extra = {}
        self.extra.update(extra.pop('extra', {}))
        self.extra.update(extra)

    def __setstate__(self, state):
        self.__dict__.update(state)
        if 'image_id' not in state and 'image' in state:
            state['image_id'] = state['image']

    def start(self):
        """
        Start the node on the cloud using the given instance properties.

        This method is non-blocking: as soon as the node id is returned from
        the cloud provider, it will return. The `is_alive`:meth: and
        `update_ips`:meth: methods should be used to further gather details
        about the state of the node.
        """
        log.info("Starting node `%s` from image `%s` with flavor %s ...",
                 self.name, self.image_id, self.flavor)
        self.instance_id = self._cloud_provider.start_instance(
            self.user_key_name, self.user_key_public, self.user_key_private,
            self.security_group,
            self.flavor, self.image_id, self.image_userdata,
            username=self.image_user,
            node_name=("%s-%s" % (self.cluster_name, self.name)),
            **self.extra)
        log.debug("Node `%s` has instance ID `%s`", self.name, self.instance_id)

    def stop(self, wait=False):
        """
        Terminate the VM instance launched on the cloud for this specific node.
        """
        if self.instance_id is not None:
            log.info("Shutting down node `%s` (VM instance `%s`) ...",
                     self.name, self.instance_id)

            self._cloud_provider.stop_instance(self.instance_id)
            if wait:
                while self.is_alive():
                    time.sleep(1)
            # When an instance is terminated, the EC2 cloud provider will
            # basically return it as "running" state. Setting the
            # `instance_id` attribute to None will force `is_alive()`
            # method not to check with the cloud provider, and forever
            # forgetting about the instance id.
            self.instance_id = None

    def pause(self):
        """
        Pause the VM  instance and return the info needed to restart it.
        """
        if self.instance_id is None:
            raise ValueError("Trying to stop unstarted node.")
        resp = self._cloud_provider.pause_instance(self.instance_id)
        self.preferred_ip = None
        return resp

    def is_alive(self):
        """Checks if the current node is up and running in the cloud. It
        only checks the status provided by the cloud interface. Therefore a
        node might be running, but not yet ready to ssh into it.
        """
        running = False
        if not self.instance_id:
            return False

        try:
            log.debug("Getting information for instance %s",
                      self.instance_id)
            running = self._cloud_provider.is_instance_running(
                self.instance_id)
        except Exception as ex:
            log.debug("Ignoring error while looking for vm id %s: %s",
                      self.instance_id, str(ex))
        if running:
            log.debug("node `%s` (instance id %s) is up.",
                      self.name, self.instance_id)
            self.update_ips()
        else:
            log.debug("node `%s` (instance id `%s`) still building...",
                      self.name, self.instance_id)

        return running

    def connection_ip(self):
        """Returns the IP to be used to connect to this node.

        If the instance has a public IP address, then this is returned, otherwise, its private IP is returned.
        """
        return self.preferred_ip

    def connect(self, keyfile=None, timeout=5):
        """
        Connect to the node via SSH.

        :param keyfile: Path to the SSH host key.
        :param timeout: Maximum time to wait (in seconds) for the TCP
            connection to be established.

        :return: :py:class:`paramiko.SSHClient` - ssh connection or None on
                 failure
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if keyfile and os.path.exists(keyfile):
            ssh.load_host_keys(keyfile)

        # Try connecting using the `preferred_ip`, if
        # present. Otherwise, try all of them and set `preferred_ip`
        # using the first that is working.
        ips = self.ips[:]
        # This is done in order to "sort" the IPs and put the preferred_ip first.
        if self.preferred_ip:
            if self.preferred_ip in ips:
                ips.remove(self.preferred_ip)
            else:
                # Preferred is changed?
                log.debug(
                    "IP address %s does not seem to belong to %s anymore."
                    " Ignoring it.", self.preferred_ip, self.name)
                self.preferred_ip = ips[0]

        for ip in itertools.chain([self.preferred_ip], ips):
            if not ip:
                continue
            log.debug(
                "Trying to connect to host %s using IP address %s ...",
                self.name, ip)
            try:
                addr, port = parse_ip_address_and_port(ip, SSH_PORT)
                extra = {
                    'allow_agent':   True,
                    'key_filename':  self.user_key_private,
                    'look_for_keys': False,
                    'timeout':       timeout,
                    'username':      self.image_user,
                }
                if self.ssh_proxy_command:
                    proxy_command = expand_ssh_proxy_command(
                        self.ssh_proxy_command,
                        self.image_user, addr, port)
                    from paramiko.proxy import ProxyCommand
                    extra['sock'] = ProxyCommand(proxy_command)
                    log.debug("Using proxy command `%s`.", proxy_command)
                ssh.connect(str(addr), port=port, **extra)
                log.debug(
                    "Connection to %s succeeded on port %d,"
                    " will use this IP address for future connections.",
                    ip, port)
                if ip != self.preferred_ip:
                    self.preferred_ip = ip
                # Connection successful.
                return ssh
            except socket.error as ex:
                log.debug(
                    "Host %s (%s) not reachable within %d seconds: %s -- %r",
                    self.name, ip, timeout, ex, type(ex))
            except paramiko.BadHostKeyException as ex:
                log.error(
                    "Invalid SSH host key for %s (%s): %s.",
                    self.name, ip, ex)
            except paramiko.SSHException as ex:
                log.debug(
                    "Ignoring error connecting to %s: %s -- %r",
                    self.name, ex, type(ex))

        return None

    def update_ips(self):
        """Retrieves the public and private ip of the instance by using the
        cloud provider. In some cases the public ip assignment takes some
        time, but this method is non blocking. To check for a public ip,
        consider calling this method multiple times during a certain timeout.
        """
        self.ips = self._cloud_provider.get_ips(self.instance_id)
        if self.preferred_ip not in self.ips:
            self.preferred_ip = None
        return self.ips[:]

    def __str__(self):
        ips = ', '.join(ip for ip in self.ips if ip)
        return ("name=`{name}`, id=`{id}`,"
                " ips=[{ips}], connection_ip=`{preferred_ip}`"
                .format(name=self.name, id=self.instance_id,
                        ips=ips, preferred_ip=self.preferred_ip))

    def to_dict(self, omit=()):
        """
        Return a (shallow) copy of self cast to a dictionary,
        optionally omitting some key/value pairs.
        """
        result = dict(self)
        for key in omit:
            if key in result:
                del result[key]
        return result

    def to_vars_dict(self):
        """
        Return local state which is relevant to the cluster setup process.
        """
        return self.to_dict(omit=[
            '_cloud_provider',
            'ssh_proxy_command',
            'cluster_name',
            'user_key_public',
            'user_key_private',
        ])

    def pprint(self):
        """Pretty print information about the node.

        :return: str - representaion of a node in pretty print
        """
        ips = ', '.join(ip for ip in self.ips if ip)
        return """%s
connection IP: %s
IPs:    %s
instance id:   %s
instance flavor: %s""" % (self.name, self.preferred_ip, ips,
                          self.instance_id, self.flavor)

    def keys(self):
        """Only expose some of the attributes when using as a dictionary"""
        keys = Struct.keys(self)
        keys.remove('_cloud_provider')
        return keys
