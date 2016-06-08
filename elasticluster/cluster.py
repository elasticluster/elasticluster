#! /usr/bin/env python
#
# Copyright (C) 2013-2016 S3IT, University of Zurich
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
Riccardo Murri <riccardo.murri@uzh.ch>
'''

# System imports
from collections import defaultdict
import itertools
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
    startup_timeout = 60 * 15  #: timeout in seconds to start all nodes


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

        self.ssh_hostkeys_from_console_output = extra.get('ssh_hostkeys_from_console_output')

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

        self.extra = {}
        # FIXME: ugly fix needed when saving and loading the same
        # cluster using json. The `extra` keywords will become a
        # single, dictionary-valued, `extra` option when calling again
        # the constructor.
        self.extra.update(extra.pop('extra',{}))

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
                "Invalid name `%s`. The `kind` argument may only contain"
                " alphanumeric characters, as it is going to be used as"
                " host name" % kind
            )

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
                    if self.ssh_hostkeys_from_console_output:
                        self.get_ssh_key_from_console_output(keys, node.instance_id, node.ips)

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
        """Update all connection information of the nodes of this cluster.
        It occurs for example public ip's are not available imediatly,
        therefore calling this method might help.
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
                          node, str(ex))
        self.repository.save_or_update(self)

    def get_ssh_key_from_console_output(self, known_hosts, instance_id, names):
        console_output = self._cloud_provider.get_console_output(instance_id)
        hostkeys = re.sub(
            r'^.*-+BEGIN SSH HOST KEY KEYS-+\s*(.*)[\r\n]-+END SSH HOST KEY KEYS-+.*',
            r'\1', console_output, flags=re.DOTALL).strip()
        hostkeys = re.split(r'[\r\n]+', hostkeys)

        for key in hostkeys:
            for name in names:
                key_type, value = key.split()[0:2]
                entry = paramiko.hostkeys.HostKeyEntry.from_line('{} {} {}'.format(name, key_type, value))
                if entry:
                    known_hosts.add(name, key_type, entry.key)


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
    scheme, override methods :meth:`_format` and :meth:`_parse`.

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
    def _format(pattern, **args):
        """
        Form a node name by interpolating `args` into `pattern`.

        This is actually nothing more than a call to
        `pattern.format(...)` but is provided as a separate
        overrideable method as it is logically paired with
        :meth:`_parse`.
        """
        return pattern.format(**args)

    @staticmethod
    def _parse(name):
        """
        Return dict of parts forming `name`.  Raise `ValueError` if string
        `name` cannot be correctly parsed.

        The default implementation uses
        `NodeNamingPolicy._NODE_NAME_RE` to parse the name back into
        constituent parts.

        This is ideally the inverse of :meth:`_format` -- it should be
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
        re.I|re.X)

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
        return self._format(self.pattern, kind=kind, index=index, **extra)

    def use(self, kind, name):
        """
        Mark a node name as used.
        """
        try:
            params = self._parse(name)
            index = int(params['index'], 10)
            if index in self._free[kind]:
                self._free[kind].remove(index)
            top = self._top[kind]
            if index > top:
                self._free[kind].update(range(top+1, index))
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
            params = self._parse(name)
            index = int(params['index'], 10)
            self._free[kind].add(index)
            assert index <= self._top[kind]
            if index == self._top[kind]:
                self._top[kind] -= 1
        except ValueError:
            # ignore failures in self._parse()
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

        for ip in itertools.chain([self.preferred_ip], ips):
            if not ip:
                continue
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
