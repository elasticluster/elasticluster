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
from fnmatch import fnmatch
import os
import sys

# Elasticluster imports
from elasticluster.conf import Configurator
from elasticluster import log
from elasticluster.exceptions import ClusterNotFound, ConfigurationError, \
    ImageError, SecurityGroupError, NodeNotFound, ClusterError


class AbstractCommand():
    """
    Defines the general contract every command has to fulfill in
    order to be recognized by the arguments list and executed
    afterwards.
    """
    __metaclass__ = ABCMeta

    def __init__(self, params):
        """
        A reference to the parameters of the command line will be
        passed here to adjust the functionality of the command
        properly.
        """
        self.params = params

    @abstractmethod
    def setup(self, subparsers):
        """
        This method handles the setup of the subcommand. In order to
        do so, every command has to add a parser to the subparsers
        reference given as parameter. The following example is the
        minimum implementation of such a setup procedure: parser =
        subparsers.add_parser("start")
        parser.set_defaults(func=self.execute)
        """
        pass

    @abstractmethod
    def execute(self):
        """
        This method is executed after a command was recognized and may
        vary in its behavior.
        """
        pass

    def __call__(self):
        return self.execute()

    def pre_run(self):
        """
        Overrides this method to execute any pre-run code, especially
        to check any command line options.
        """
        pass


def cluster_summary(cluster):
    try:
        frontend = cluster.get_frontend_node().name
    except NodeNotFound, ex:
        frontend = 'unknown'
        log.error("Unable to get information on the frontend node: "
                  "%s", str(ex))
    msg = """
Cluster name:     %s
Frontend node: %s
""" % (cluster.name, frontend)

    for cls in cluster.nodes:
        msg += "- %s nodes: %d\n" % (cls, len(cluster.nodes[cls]))
    msg += """
To login on the frontend node, run the command:

    elasticluster ssh %s

To upload or download files to the cluster, use the command:

    elasticluster sftp %s
""" % (cluster.name, cluster.name)
    return msg


class Start(AbstractCommand):
    """
    Create a new cluster using the given cluster template.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser(
            "start", help="Create a cluster using the supplied configuration.",
            description=self.__doc__)
        parser.set_defaults(func=self)
        parser.add_argument('cluster',
                            help="Type of cluster. It refers to a "
                                 "configuration stanza [cluster/<name>]")
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")
        parser.add_argument('-n', '--name', dest='cluster_name',
                            help='Name of the cluster.')
        parser.add_argument('--nodes', metavar='N1:GROUP[,N2:GROUP2,...]',
                            help='Override the values in of the configuration '
                                 'file and starts `N1` nodes of group `GROUP`,'
                                 'N2 of GROUP2 etc...')
        parser.add_argument('--no-setup', action="store_true", default=False,
                            help="Only start the cluster, do not configure it")

    def pre_run(self):
        self.params.extra_conf = {}
        try:
            if self.params.nodes:
                nodes = self.params.nodes.split(',')
                for nspec in nodes:
                    n, group = nspec.split(':')
                    if not n.isdigit():
                        raise ConfigurationError(
                            "Invalid syntax for option `--nodes`: "
                            "`%s` is not an integer." % n)
                    n = int(n)
                    self.params.extra_conf[group + '_nodes'] = n
        except ValueError:
            raise ConfigurationError(
                "Invalid argument for option --nodes: %s" % self.params.nodes)

    def execute(self):
        """
        Starts a new cluster.
        """

        cluster_template = self.params.cluster
        if self.params.cluster_name:
            cluster_name = self.params.cluster_name
        else:
            cluster_name = self.params.cluster

        configurator = Configurator.fromConfig(
            self.params.config, storage_path=self.params.storage)

        # overwrite configuration
        for option, value in self.params.extra_conf.iteritems():
            cconf = configurator.cluster_conf[cluster_template]['cluster']
            if option in cconf:
                cconf[option] = value

        # First, check if the cluster is already created.
        try:
            cluster = configurator.load_cluster(cluster_name)
        except ClusterNotFound as e:
            try:
                cluster = configurator.create_cluster(
                    cluster_template, cluster_name)
            except ConfigurationError, e:
                log.error("Starting cluster %s: %s\n" % (cluster_template, e))
                return

        try:
            for cls in cluster.nodes:
                print("Starting cluster `%s` with %d %s nodes." % (
                    cluster.name, len(cluster.nodes[cls]), cls))
            print("(this may take a while...)")
            conf = configurator.cluster_conf[cluster_template]
            min_nodes = dict(
                (k[:-10], int(v)) for k, v in conf['cluster'].iteritems() if
                k.endswith('_nodes_min'))
            cluster.start(min_nodes=min_nodes)
            if self.params.no_setup:
                print("NOT configuring the cluster as requested.")
            else:
                print("Configuring the cluster.")
                print("(this too may take a while...)")
                ret = cluster.setup()
                if ret:
                    print("Your cluster is ready!")
                else:
                    print("\nWARNING: YOUR CLUSTER IS NOT READY YET!")
            print(cluster_summary(cluster))
        except (KeyError, ImageError, SecurityGroupError, ClusterError) as ex:
            print("Your cluster could not start `%s`" % ex)


class Stop(AbstractCommand):
    """
    Stop a cluster and terminate all associated virtual machines.
    """

    def setup(self, subparsers):
        """
        @see abstract_command contract
        """
        parser = subparsers.add_parser(
            "stop", help="Stop a cluster and all associated VM instances.",
            description=self.__doc__)
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")
        parser.add_argument('--force', action="store_true", default=False,
                            help="Remove the cluster even if not all the nodes"
                                 " have been terminated properly.")
        parser.add_argument('--yes', action="store_true", default=False,
                            help="Assume `yes` to all queries and "
                                 "do not prompt.")

    def execute(self):
        """
        Stops the cluster if it's running.
        """
        cluster_name = self.params.cluster
        configurator = Configurator.fromConfig(
            self.params.config, storage_path=self.params.storage)
        try:
            cluster = configurator.load_cluster(cluster_name)
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Stopping cluster %s: %s\n" %
                      (cluster_name, ex))
            return

        if not self.params.yes:
            # Ask for confirmation
            yesno = raw_input(
                "Do you want really want to stop "
                "cluster %s? [yN] " % cluster_name)
            if yesno.lower() not in ['yes', 'y']:
                print("Aborting as per user request.")
                sys.exit(0)
        print("Destroying cluster `%s`" % cluster_name)
        cluster.stop(force=self.params.force)


class ResizeCluster(AbstractCommand):
    """
    Resize the cluster by adding or removing compute nodes.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser(
            "resize", help="Resize a cluster by adding or removing "
                           "compute nodes.", description=self.__doc__)
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-a', '--add', metavar='N1:GROUP1[,N2:GROUP2]',
                            help="Add N1 nodes of group GROUP1, "
                                 "N2 of group GROUP2 etc...")
        parser.add_argument('-r', '--remove', metavar='N1:GROUP1[,N2:GROUP2]',
                            help="Remove N1 nodes of group GROUP1, "
                                 "N2 of group GROUP2 etc...")
        parser.add_argument('-t', '--template', help='name of the template '
                                                     'of this cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")
        parser.add_argument('--no-setup', action="store_true", default=False,
                            help="Only start the cluster, do not configure it")
        parser.add_argument('--yes', action="store_true", default=False,
                            help="Assume `yes` to all queries and "
                                 "do not prompt.")

    def pre_run(self):
        self.params.nodes_to_add = {}
        self.params.nodes_to_remove = {}
        try:
            if self.params.add:
                nodes = self.params.add.split(',')
                for nspec in nodes:
                    n, group = nspec.split(':')
                    if not n.isdigit():
                        raise ConfigurationError(
                            "Invalid syntax for option `--nodes`: "
                            "`%s` is not an integer." % n)
                    self.params.nodes_to_add[group] = int(n)

            if self.params.remove:
                nodes = self.params.remove.split(',')
                for nspec in nodes:
                    n, group = nspec.split(':')
                    self.params.nodes_to_remove[group] = int(n)

        except ValueError as ex:
            raise ConfigurationError(
                "Invalid syntax for argument: %s" % ex)

    def execute(self):
        configurator = Configurator.fromConfig(
            self.params.config, storage_path=self.params.storage)

        # Get current cluster configuration
        cluster_name = self.params.cluster
        template = self.params.template

        try:
            cluster = configurator.load_cluster(cluster_name)
            cluster.update()
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Listing nodes from cluster %s: %s\n" %
                      (cluster_name, ex))
            return
        for grp in self.params.nodes_to_add:
            print("Adding %d %s node(s) to the cluster"
                  "" % (self.params.nodes_to_add[grp], grp))

            # Currently we can't save which template was used to setup a
            # cluster, therefore we imply the configuration of the new nodes
            # to match already existent nodes in this group. If no node was
            # added to this group yet, it will abort and ask for the
            # `--template` argument.
            # TODO: find a better solution for this problem, it makes things
            #       complicated for the user
            if (not grp in cluster.nodes or not cluster.nodes[grp]) \
                    and not template:
                print "Elasticluster can not infer which template to use for "\
                      "the new node(s). Please provide the template with " \
                      "the `-t` or `--template` option"
                return

            if not template:
                sample_node = cluster.nodes[grp][0]
                for i in range(self.params.nodes_to_add[grp]):
                    cluster.add_node(grp,
                                     sample_node.image,
                                     sample_node.image_user,
                                     sample_node.flavor,
                                     sample_node.security_group,
                                     image_userdata=sample_node.image_userdata)
            else:
                conf = configurator.cluster_conf[template]
                conf_kind = conf['nodes'][grp]
                for i in range(self.params.nodes_to_add[grp]):
                    image_user = conf['login']['image_user']
                    userdata = conf_kind.get('image_userdata', '')
                    cluster.add_node(grp,
                                     conf_kind['image_id'],
                                     image_user,
                                     conf_kind['flavor'],
                                     conf_kind['security_group'],
                                     image_userdata=userdata)

        for grp in self.params.nodes_to_remove:
            n_to_rm = self.params.nodes_to_remove[grp]
            print("Removing %d %s node(s) from the cluster."
                  "" % (n_to_rm, grp))
            to_remove = cluster.nodes[grp][-n_to_rm:]
            print("The following nodes will be removed from the cluster.")
            print("    " + str.join("\n    ", [n.name for n in to_remove]))

            if not self.params.yes:
                # Ask for confirmation.
                yesno = raw_input(
                    "Do you really want to remove them? [yN] ")
                if yesno.lower() not in ['yes', 'y']:
                    print("Aborting as per user request.")
                    sys.exit(0)

            for node in to_remove:
                cluster.nodes[grp].remove(node)
                node.stop()

        cluster.start()
        if self.params.no_setup:
            print("NOT configuring the cluster as requested.")
        else:
            print("Reconfiguring the cluster.")
            cluster.setup()
        print(cluster_summary(cluster))


class ListClusters(AbstractCommand):
    """
    Print a list of all clusters that have been started.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser(
            "list", help="List all started clusters.",
            description=self.__doc__)
        parser.set_defaults(func=self)
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")

    def execute(self):
        configurator = Configurator.fromConfig(
            self.params.config, storage_path=self.params.storage)
        repository = configurator.create_repository()
        clusters = repository.get_all()

        if not clusters:
            print("No clusters found.")
        else:
            print("""
The following clusters have been started.
Please note that there's no guarantee that they are fully configured:
""")
            for cluster in sorted(clusters):
                print("%s " % cluster.name)
                print("-" * len(cluster.name))
                print("  name:           %s" % cluster.name)
                for cls in cluster.nodes:
                    print("  - %s nodes: %d" % (cls, len(cluster.nodes[cls])))
                print("")


class ListTemplates(AbstractCommand):
    """
    List the available templates defined in the configuration file.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser(
            "list-templates", description=self.__doc__,
            help="Show the templates defined in the configuration file.")

        parser.set_defaults(func=self)
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")
        parser.add_argument('clusters', nargs="*",
                            help="List only this cluster. Accepts globbing.")

    def execute(self):

        configurator = Configurator.fromConfig(
            self.params.config, storage_path=self.params.storage)
        config = configurator.cluster_conf

        print("""%d cluster templates found in configuration file.""" % len(config))
        templates = config.keys()
        for pattern in self.params.clusters:
            templates = [t for t in templates if fnmatch(t, pattern)]

        if self.params.clusters:
            print("""%d cluter templates found matching pattern(s) '%s'""" % (len(templates), str.join(", ", self.params.clusters)))

        for template in templates:
            try:
                cluster = configurator.create_cluster(template, template)
                print("""
name:     %s""" % template)
                for nodekind in cluster.nodes:
                    print("%s nodes: %d" % (
                        nodekind,
                        len(cluster.nodes[nodekind])))
            except ConfigurationError, ex:
                log.warning("unable to load cluster `%s`: %s", template, ex)


class ListNodes(AbstractCommand):
    """
    Show some information on all the nodes belonging to a given
    cluster.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser(
            "list-nodes", help="Show information about the nodes in the "
                               "cluster", description=self.__doc__)
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")
        parser.add_argument(
            '-u', '--update', action='store_true', default=False,
            help="By default `elasticluster list-nodes` will not contact the "
                 "EC2 provider to get up-to-date information, unless `-u` "
                 "option is given.")

    def execute(self):
        """
        Lists all nodes within the specified cluster with certain
        information like id and ip.
        """
        configurator = Configurator.fromConfig(
            self.params.config, storage_path=self.params.storage)
        cluster_name = self.params.cluster
        try:
            cluster = configurator.load_cluster(cluster_name)
            if self.params.update:
                cluster.update()
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Listing nodes from cluster %s: %s\n" %
                      (cluster_name, ex))
            return

        print(cluster_summary(cluster))
        for cls in cluster.nodes:
            print("%s nodes:" % cls)
            print("")
            for node in cluster.nodes[cls]:
                txt = ["    " + i for i in node.pprint().splitlines()]
                print('  - ' + str.join("\n", txt)[4:])
                print("")


class SetupCluster(AbstractCommand):
    """
    Setup the given cluster by calling the setup provider defined for
    this cluster.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser(
            "setup", help="Configure the cluster.", description=self.__doc__)
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")

    def execute(self):
        configurator = Configurator.fromConfig(
            self.params.config, storage_path=self.params.storage)
        cluster_name = self.params.cluster
        try:
            cluster = configurator.load_cluster(cluster_name)
            cluster.update()
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Setting up cluster %s: %s\n" %
                      (cluster_name, ex))
            return

        print("Configuring cluster `%s`..." % cluster_name)
        ret = cluster.setup()
        if ret:
            print("Your cluster is ready!")
        else:
            print("\nWARNING: YOUR CLUSTER IS NOT READY YET!")
        print(cluster_summary(cluster))


class SshFrontend(AbstractCommand):
    """
    Connect to the frontend of the cluster using `ssh`.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser(
            "ssh", help="Connect to the frontend of the cluster using the "
                        "`ssh` command", description=self.__doc__)
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")
        parser.add_argument('ssh_args', metavar='args', nargs='*',
                            help="Execute the following command on the remote "
                            "machine instead of opening an interactive shell.")

    def execute(self):
        configurator = Configurator.fromConfig(
            self.params.config, storage_path=self.params.storage)
        cluster_name = self.params.cluster
        try:
            cluster = configurator.load_cluster(cluster_name)
            cluster.update()
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Setting up cluster %s: %s\n" %
                      (cluster_name, ex))
            return

        try:
            frontend = cluster.get_frontend_node()
        except NodeNotFound, ex:
            log.error("Unable to connect to the frontend node: %s" % str(ex))
            sys.exit(1)
        host = frontend.connection_ip()
        username = frontend.image_user
        log.warning("Ignoring known_hosts file.")
        ssh_cmdline = ["ssh",
                       "-i", frontend.user_key_private,
                       "-o", "UserKnownHostsFile=/dev/null",
                       "-o", "StrictHostKeyChecking=no",
                       '%s@%s' % (username, host)]
        ssh_cmdline.extend(self.params.ssh_args)
        log.debug("Running command `%s`" % str.join(' ', ssh_cmdline))
        os.execlp("ssh", *ssh_cmdline)


class SftpFrontend(AbstractCommand):
    """
    Open an SFTP session to the cluster frontend host.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser(
            "sftp",
            help="Open an SFTP session to the cluster frontend host.",
            description=self.__doc__)
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")
        parser.add_argument('sftp_args', metavar='args', nargs='*',
                            help="Arguments to pass to ftp, instead of "
                                 "opening an interactive shell.")

    def execute(self):
        configurator = Configurator.fromConfig(
            self.params.config, storage_path=self.params.storage)
        cluster_name = self.params.cluster
        try:
            cluster = configurator.load_cluster(cluster_name)
            cluster.update()
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Setting up cluster %s: %s\n" %
                      (cluster_name, ex))
            return

        try:
            frontend = cluster.get_frontend_node()
        except NodeNotFound, ex:
            log.error("Unable to connect to the frontend node: %s" % str(ex))
            sys.exit(1)
        host = frontend.connection_ip()
        username = frontend.image_user
        sftp_cmdline = ["sftp",
                        "-i", frontend.user_key_private,
                        "-o", "UserKnownHostsFile=/dev/null",
                        "-o", "StrictHostKeyChecking=no"]
        sftp_cmdline.extend(self.params.sftp_args)
        sftp_cmdline.append('%s@%s' % (username, host))
        os.execlp("sftp", *sftp_cmdline)
