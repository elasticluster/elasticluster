#! /usr/bin/env python
#
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
import operator
import os
import re
import signal
import socket
import sys
import time
from multiprocessing.dummy import Pool
import UserDict

# External modules
import paramiko
from binascii import hexlify

# Elasticluster imports
from elasticluster import log
from elasticluster.exceptions import TimeoutError, NodeNotFound, \
    InstanceError, ClusterError
from elasticluster.repository import MemRepository

class IgnorePolicy(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        log.info('Ignoring unknown %s host key for %s: %s' %
                 (key.get_name(), hostname, hexlify(key.get_fingerprint())))


class Struct(object, UserDict.DictMixin):
    """
    This class is a clone of gc3libs.utils.Struct class from GC3Pie project: https://code.google.com/p/gc3pie/

    A `dict`-like object, whose keys can be accessed with the usual
    '[...]' lookup syntax, or with the '.' get attribute syntax.

    Examples::
      >>> a = Struct()
      >>> a['x'] = 1
      >>> a.x
      1
      >>> a.y = 2
      >>> a['y']
      2

    Values can also be initially set by specifying them as keyword
    arguments to the constructor::

      >>> a = Struct(z=3)
      >>> a['z']
      3
      >>> a.z
      3

    Like `dict` instances, `Struct`s have a `copy` method to get a
    shallow copy of the instance:

      >>> b = a.copy()
      >>> b.z
      3
    """

    def __init__(self, initializer=None, **extra):
        if initializer is not None:
            try:
                # initializer is `dict`-like?
                for name, value in initializer.items():
                    self[name] = value
            except AttributeError:
                # initializer is a sequence of (name,value) pairs?
                for name, value in initializer:
                    self[name] = value
        for name, value in extra.items():
            self[name] = value

    def copy(self):
        """Return a (shallow) copy of this `Struct` instance."""
        return Struct(self)

    # the `DictMixin` class defines all std `dict` methods, provided
    # that `__getitem__`, `__setitem__` and `keys` are defined.
    def __setitem__(self, name, val):
        self.__dict__[name] = val

    def __getitem__(self, name):
        return self.__dict__[name]

    def keys(self):
        return self.__dict__.keys()


class Cluster(Struct):
    """This is the heart of elasticluster and handles all cluster relevant
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

    :param repository: by default the
                       :py:class:`elasticluster.repository.MemRepository` is
                       used to store the cluster in memory. Provide another
                       repository to store the cluster in a persistent state.
    :type repository: :py:class:`elasticluster.repository.AbstractClusterRepository`

    :param extra: tbd.


    :ivar nodes: dict [node_type] = [:py:class:`Node`] that represents all
                 nodes in this cluster
   """
    startup_timeout = 60 * 10  #: timeout in seconds to start all nodes


    def __init__(self, name, user_key_name='elasticluster-key',
                 user_key_public='~/.ssh/id_rsa.pub',
                 user_key_private='~/.ssh/id_rsa',
                 cloud_provider=None, setup_provider=None,
                 repository=None, thread_pool_max_size=10,
                 **extra):
        self.name = name
        self.template = extra.pop('template', None)
        self.thread_pool_max_size = thread_pool_max_size
        self._cloud_provider = cloud_provider
        self._setup_provider = setup_provider
        self.user_key_name = user_key_name
        self.repository = repository if repository else MemRepository()

        self.ssh_to = extra.pop('ssh_to', None)

        self.user_key_private = os.path.expandvars(user_key_private)
        self.user_key_private = os.path.expanduser(user_key_private)

        self.user_key_public = os.path.expanduser(user_key_public)
        self.user_key_public = os.path.expandvars(user_key_public)

        self.nodes = dict()
        if 'nodes' in extra:
            # Build the internal nodes. This is mostly useful when loading
            # the cluster from json files.
            for kind, nodes in extra['nodes'].items():
                for node in nodes:
                    self.add_node(**node)

        self.extra = {}
        # FIXME: ugly fix needed when saving and loading the same
        # cluster using json. The `extra` keywords will become a
        # single, dictionary-valued, `extra` option when calling again
        # the constructor.
        self.extra.update(extra.pop('extra',{}))

        # Remove extra arguments, if defined
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

    def __getstate__(self):
        result = self.__dict__.copy()
        result['_setup_provider'] = None
        result['_cloud_provider'] = None
        return result

    def __setstate__(self, state):
        self.__dict__ = state
        # New attribute added to Cluster class, need to ensure it is defined.

    def __update_option(self, cfg, key, attr):
        oldvalue = getattr(self, attr)
        if key in cfg and cfg[key] != oldvalue:
            setattr(self, attr, cfg[key])
            return oldvalue
        return False

    def keys(self):
        """Only expose some of the attributes when using as a dictionary"""
        keys = Struct.keys(self)
        for key in ('_setup_provider', '_cloud_provider',
                    'repository', 'known_hosts_file'):
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

    def add_node(self, kind, image_id, image_user, flavor,
                 security_group, image_userdata='', name=None, **extra):
        """Adds a new node to the cluster. This factory method provides an
        easy way to add a new node to the cluster by specifying all relevant
        parameters. The node does not get started nor setup automatically,
        this has to be done manually afterwards.

        :param str kind: kind of node to start. this refers to the
                         groups defined in the ansible setup provider
                         :py:class:`elasticluster.providers.AnsibleSetupProvider`
                         Please note that this must match the
                         `[a-zA-Z0-9-]` regexp, as it is used to build
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
        if not re.match("^[a-zA-Z0-9-]+$", kind):
            raise ValueError(
                "Invalid name `%s`. The `kind` argument may only contains "
                "characters in [a-z0-9-] range, as it is going to be used as "
                "hostname" % kind
            )

        if kind not in self.nodes:
            self.nodes[kind] = []

        if not name:
            nodenames = [i.name for i in self.nodes[kind]]
            numnodes = len(nodenames)
            for index in range(numnodes+1, numnodes+50):
                _name = "%s%03d" % (kind, index)
                if _name in nodenames:
                    continue
                else:
                    name = _name
                    break

        if not name:
            log.error("while adding a new node of type `%s`, I was unable to find a good name for it.", kind)
            return None
        # To ease json dump/load, use `extra` dictionary to
        # instantiate Node class
        extra.update({'name': name,
                      'cluster_name' : self.name,
                      'kind': kind,
                      'cloud_provider': self._cloud_provider,
                      'image_user': image_user,
                      'security_group': security_group,
                      'image_id': image_id,
                      'flavor': flavor,
                      'image_userdata':image_userdata})
        for attr in ('user_key_public', 'user_key_private', 'user_key_name',
                     'security_group', 'image_user', 'image_id', 'flavor',
                     'image_userdata'):
            if attr not in extra:
                extra[attr] = getattr(self, attr)
        node = Node(**extra)

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
                self.repository.save_or_update(self)
            except ValueError:
                raise NodeNotFound("Node %s not found in cluster" % node.name)

    @staticmethod
    def _start_node(node):
        """Static method to start a specific node on a cloud

        :return: bool -- True on success, False otherwise
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
                log.info("_start_node: node '%s' has been started", node.name)
                return True
            except Exception as e:
                log.error("could not start node `%s` for reason "
                          "`%s`" % (node.name, e))
                return None

    def start(self, min_nodes=None):
        """Starts up all the instances in the cloud. To speed things up all
        instances are started in a seperate thread. To make sure
        elasticluster is not stopped during creation of an instance, it will
        overwrite the sigint handler. As soon as the last started instance
        is returned and saved to the repository, sigint is executed as usual.
        An instance is up and running as soon as a ssh connection can be
        established. If the startup timeout is reached before all instances
        are started, the cluster will stop and destroy all instances.

        This method is blocking and might take some time depending on the
        amount of instances to start.

        :param min_nodes: minimum number of nodes to start in case the quota
                          is reached before all instances are up
        :type min_nodes: dict [node_kind] = number
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

        if log.DO_NOT_FORK:
            # Start the nodes sequentially without forking, in order
            # to ease the debugging
            for node in nodes:
                self._start_node(node)
                self.repository.save_or_update(self)
        else:
            # Create one thread for each node to start
            thread_pool = Pool(processes=min(len(nodes),
                                             self.thread_pool_max_size))
            log.debug("Created pool of %d threads" % len(nodes))
            # Intercept Ctrl-c
            signal.signal(signal.SIGINT, sigint_handler)

            # This is blocking
            result = thread_pool.map_async(self._start_node, nodes)

            while not result.ready():
                result.wait(1)
                if not self.keep_running:
                    # the user did abort the start of the cluster. We
                    # finish the current start of a node and save the
                    # status to the storage, so we don't have
                    # unmanaged instances laying around
                    log.error("Aborting upon Ctrl-C")
                    thread_pool.close()
                    thread_pool.join()
                    self.repository.save_or_update(self)
                    sys.exit(1)

        # dump the cluster here, so we don't loose any knowledge
        self.repository.save_or_update(self)

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
            # FIXME: this is wrong: the reason why `node.is_alive()` fails could be caused by a network error, and we shouldn't just delete the nodes.

            log.error("Not all nodes were started correctly within the given"
                      " timeout `%s`" % Cluster.startup_timeout)
            log.error("Please check if image, keypair, and network configuration is correct and try again.")
            # for node in starting_nodes:
            #     log.error("Stopping node `%s`, since it could not start "
            #               "within the given timeout" % node.name)
            #     node.stop()
            #     self.remove_node(node)

        signal.alarm(0)

        # If we reached this point, we should have IP addresses for
        # the nodes, so update the storage file again.
        self.repository.save_or_update(self)

        # Try to connect to each node. Run the setup action only when
        # we successfully connect to all of them.
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(Cluster.startup_timeout)
        pending_nodes = self.get_all_nodes()[:]

        if not os.path.exists(self.known_hosts_file):
            # Create the file if it's not present, otherwise the
            # following lines will raise an error
            try:
                fd = open(self.known_hosts_file, 'a')
                fd.close()
            except IOError as err:
                log.warning("Error while opening known_hosts file `%s`: `%s`"
                            " NOT using known_hosts_file.",
                            self.known_hosts_file, err)
        try:
            keys = paramiko.hostkeys.HostKeys(self.known_hosts_file)
        except IOError:
            keys = paramiko.hostkeys.HostKeys()
            log.warning("Ignoring error while opening known_hosts file %s" % self.known_hosts_file)

        try:
            while pending_nodes:
                for node in pending_nodes[:]:
                    ssh = node.connect(keyfile=self.known_hosts_file)
                    if ssh:
                        log.info("Connection to node %s (%s) successful.",
                                 node.name, node.connection_ip())
                        # Add host keys to the keys object.
                        for host, key in ssh.get_host_keys().items():
                            for ktype, keydata in key.items():
                                keys.add(host, ktype, keydata)
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
                self.remove_node(node, stop=True)

        signal.alarm(0)

        # It might be possible that the node.connect() call updated
        # the `preferred_ip` attribute, so, let's save the cluster
        # again.
        self.repository.save_or_update(self)

        # Save host keys
        try:
            keys.save(self.known_hosts_file)
        except IOError:
            log.warning("Ignoring error while saving known_hosts file %s" % self.known_hosts_file)

        # A lot of things could go wrong when starting the cluster. To
        # ensure a stable cluster fitting the needs of the user in terms of
        # cluster size, we check the minimum nodes within the node groups to
        # match the current setup.
        if not min_nodes:
            # the node minimum is implicit if not specified.
            min_nodes = dict((key, len(self.nodes[key])) for key in
                             self.nodes.iterkeys())
        else:
            # check that each group has a minimum value
            for group, nodes in nodes.iteritems():
                if group not in min_nodes:
                    min_nodes[group] = len(nodes)

        self._check_cluster_size(min_nodes)

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
        # check the total sizes before moving the nodes around
        minimum_nodes = 0
        for group, size in min_nodes.iteritems():
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
        for group, size in min_nodes.iteritems():
            if len(self.nodes[group]) < size:
                unsatisfied_groups.append(group)

        # trying to move nodes around to fill the groups with missing nodes
        for ugroup in unsatisfied_groups[:]:
            missing = min_nodes[ugroup] - len(self.nodes[ugroup])
            for group, nodes in self.nodes.iteritems():
                spare = len(self.nodes[group]) - min_nodes[group]
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
            raise NodeNotFound("Node %s not found" % nodename)

    def stop(self, force=False):
        """Destroys all instances of this cluster and calls delete on the
        repository.

        :param bool force: force termination of instances in any case
        """
        for node in self.get_all_nodes():
            if node.instance_id:
                try:
                    node.stop()
                    self.nodes[node.kind].remove(node)
                    log.debug("Removed node with instance id %s from %s"
                              % (node.instance_id, node.kind))
                except:
                    # Boto does not always raises an `Exception` class!
                    log.error("could not stop instance `%s`, it might "
                              "already be down.", node.instance_id)
            else:
                log.debug("Not stopping node with no instance id. It seems "
                          "like node `%s` did not start correctly."
                          % node.name)
                self.nodes[node.kind].remove(node)

        if not self.get_all_nodes():
            log.debug("Removing cluster %s.", self.name)
            self._setup_provider.cleanup(self)
            self.repository.delete(self)
        elif not force:
            log.warning("Not all instances have been terminated. "
                        "Please rerun the `elasticluster stop %s`", self.name)
            self.repository.save_or_update(self)
        else:
            log.warning("Not all instances have been terminated. However, "
                        "as requested, the cluster has been force-removed.")
            self._setup_provider.cleanup(self)
            self.repository.delete(self)

        # Remove also ssh known hosts
        if os.path.exists(self.known_hosts_file):
            os.remove(self.known_hosts_file)


    def get_frontend_node(self):
        """Returns the first node of the class specified in the
        configuration file as `ssh_to`, or the first node of
        the first class in alphabetic order.

        :return: :py:class:`Node`
        :raise: :py:class:`elasticluster.exceptions.NodeNotFound` if no
                valid frontend node is found
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
        """Configure the cluster nodes with the specified  This
        is delegated to the provided :py:class:`elasticluster.providers.AbstractSetupProvider`

        :return: bool - True on success, False otherwise
        """
        try:
            # setup the cluster using the setup provider
            ret = self._setup_provider.setup_cluster(self)
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
        """Update all connection information of the nodes of this cluster.
        It occurs for example public ip's are not available imediatly,
        therefore calling this method might help.
        """
        for node in self.get_all_nodes():
            try:
                node.update_ips()
            except InstanceError as ex:
                log.warning("Ignoring error updating information on node %s: %s",
                          node, str(ex))
        self.repository.save_or_update(self)


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
    connection_timeout = 5  #: timeout in seconds to connect to host via ssh

    def __init__(self, name, cluster_name, kind, cloud_provider, user_key_public,
                 user_key_private, user_key_name, image_user, security_group,
                 image_id, flavor, image_userdata=None, **extra):
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
        self.__dict__ = state
        if 'image_id' not in state and 'image' in state:
            state['image_id'] = state['image']

    def start(self):
        """Starts the node on the cloud using the given
        instance properties. This method is non-blocking, as soon
        as the node id is returned from the cloud provider, it will return.
        Therefore the `is_alive` and `update_ips` methods can be used to
        further gather details about the state of the node.
        """
        log.info("Starting node %s.", self.name)
        self.instance_id = self._cloud_provider.start_instance(
            self.user_key_name, self.user_key_public, self.user_key_private,
            self.security_group,
            self.flavor, self.image_id, self.image_userdata,
            username=self.image_user, node_name="%s-%s" % (self.cluster_name, self.name), **self.extra)
        log.debug("Node %s has instance_id: `%s`", self.name, self.instance_id)

    def stop(self):
        """Destroys the instance launched on the cloud for this specific node.
        """
        log.info("shutting down instance `%s`",
                 self.instance_id)
        self._cloud_provider.stop_instance(self.instance_id)
        # When an instance is terminated, the EC2 cloud provider will
        # basically return it as "running" state. Setting the
        # `instance_id` attribute to None will force `is_alive()`
        # method not to check with the cloud provider, and forever
        # forgetting about the instance id.
        self.instance_id = None

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
            log.debug("node `%s` (instance id %s) is up and running",
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

    def connect(self, keyfile=None):
        """Connect to the node via ssh using the paramiko library.

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
        ips=self.ips[:]
        # This is done in order to "sort" the IPs and put the preferred_ip first.
        if self.preferred_ip:
            if self.preferred_ip in ips:
                ips.remove(self.preferred_ip)
            else:
                # Preferred is changed?
                log.debug("IP %s does not seem to belong to %s anymore. Ignoring!", self.preferred_ip, self.name)
                self.preferred_ip = ips[0]

        for ip in [self.preferred_ip] + ips:
            if not ip: continue
            try:
                log.debug("Trying to connect to host %s (%s)",
                          self.name, ip)
                ssh.connect(ip,
                            username=self.image_user,
                            allow_agent=True,
                            key_filename=self.user_key_private,
                            timeout=Node.connection_timeout)
                log.debug("Connection to %s succeeded!", ip)
                if ip != self.preferred_ip:
                    log.debug("Setting `preferred_ip` to %s", ip)
                    self.preferred_ip = ip
                    cluster_changed = True
                # Connection successful.
                return ssh
            except socket.error as ex:
                log.debug("Host %s (%s) not reachable: %s.",
                          self.name, ip, ex)
            except paramiko.BadHostKeyException as ex:
                log.error("Invalid host key: host %s (%s); check keyfile: %s",
                          self.name, ip, keyfile)
            except paramiko.SSHException as ex:
                log.debug("Ignoring error %s connecting to %s",
                          str(ex), self.name)

        return None

    def update_ips(self):
        """Retrieves the public and private ip of the instance by using the
        cloud provider. In some cases the public ip assignment takes some
        time, but this method is non blocking. To check for a public ip,
        consider calling this method multiple times during a certain timeout.
        """
        self.ips = self._cloud_provider.get_ips(self.instance_id)
        return self.ips[:]

    def __str__(self):
        ips = ', '.join(ip for ip in self.ips if ip)
        return ("name=`{name}`, id=`{id}`,"
                " ips=[{ips}], connection_ip=`{preferred_ip}`"
                .format(name=self.name, id=self.instance_id,
                        ips=ips, preferred_id=self.preferred_ip))

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
