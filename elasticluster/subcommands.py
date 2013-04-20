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

import sys

from elasticluster.conf import Configurator
from elasticluster.conf import Configuration
from elasticluster import log
from elasticluster.exceptions import ClusterNotFound, ConfigurationError


class AbstractCommand():
    """
    Defines the general contract every command has to fullfill in
    order to be recognized by the arguments list and executed
    afterwards.
    """

    def __init__(self, params):
        """
        A reference to the parameters of the command line will be
        passed here to adjust the functionality of the command
        properly.
        """
        self.params = params

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
    frontend = cluster.frontend_nodes[0]
    return """
Cluster name: %s
Cluster template: %s
Frontend nodes: %3d
Compute nodes:  %3d

To login on the frontend node, run the command:

    ssh %s@%s -i %s
""" % (cluster.name, cluster.template, len(cluster.compute_nodes),
       len(cluster.frontend_nodes), frontend.image_user, frontend.ip_public,
       frontend.user_key_private)


class Start(AbstractCommand):
    """
    Handles the start of a cluster. The cluster parameters are mostly
    read from a configuration file in order to keep the parameter set
    to a minimum.
    """

    def setup(self, subparsers):
        """
        @see abstract_command contract
        """
        parser = subparsers.add_parser("start")
        parser.set_defaults(func=self)
        parser.add_argument('cluster',
                            help="Type of cluster. It refers to a "
                            "configuration stanza [cluster/<name>]")
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")
        parser.add_argument('-n', '--name', dest='cluster_name',
                            help='Name of the cluster.')
        parser.add_argument('-c', '--compute-nodes',
                            help='Number of compute nodes.')

    def pre_run(self):
        if self.params.compute_nodes:
            try:
                self.params.compute_nodes = int(self.params.compute_nodes)
            except ValueError:
                pass

    def execute(self):
        """
        Starts a new cluster.
        """

        # First, check if the cluster is already created.
        try:
            cluster = Configurator().load_cluster(self.params.cluster)
        except ClusterNotFound, ex:
            cluster_template = self.params.cluster
            extra_conf = dict()
            if self.params.compute_nodes:
                extra_conf['compute'] = self.params.compute_nodes

            if self.params.cluster_name:
                extra_conf['name'] = self.params.cluster_name

            try:
                cluster = Configurator().create_cluster(
                    cluster_template, **extra_conf)
            except ConfigurationError, ex:
                log.error("Cluster `%s` not found in configuration file." %
                          cluster_template)
                return

        print("Starting cluster `%s` with %d compute nodes." % (
            cluster.name, len(cluster.compute_nodes)))
        print("(this may take a while...)")
        cluster.start()
        print("Configuring the cluster.")
        print("(this too may take a while...)")

        cluster.setup()

        print("Your cluster is ready!")
        print(cluster_summary(cluster))


class Stop(AbstractCommand):
    """
    Handles the stop of a cluster.
    """
    def setup(self, subparsers):
        """
        @see abstract_command contract
        """
        parser = subparsers.add_parser("stop")
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")

    def execute(self):
        """
        Stops the cluster if it's running.
        """
        cluster_name = self.params.cluster
        try:
            cluster = Configurator().load_cluster(cluster_name)
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Stopping cluster %s: %s\n" %
                      (cluster_name, ex))
            return

        print("Destroying cluster `%s`" % cluster_name)
        cluster.stop()


class ResizeCluster(AbstractCommand):
    """
    Resize the cluster by adding or removing
    """
    def setup(self, subparsers):
        parser = subparsers.add_parser("resize")
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('N', help="Number of compute nodes, or, using +n"
                            "or -n, resize by adding or removing `n` nodes.")
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")

    def pre_run(self):
        self.params.nodes_to_add = 0
        self.params.nodes_to_remove = 0
        try:
            int(self.params.N)
        except ValueError:
            raise RuntimeError("Value of `N` must be an integer")

    def execute(self):
        # Get current cluster configuration
        cluster_name = self.params.cluster
        try:
            cluster = Configurator().load_cluster(cluster_name)
            cluster.update()
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Listing nodes from cluster %s: %s\n" %
                      (cluster_name, ex))
            return

        if self.params.N.startswith('+'):
            self.params.nodes_to_add = int(self.params.N)
        elif self.params.N.startswith('-'):
            self.params.nodes_to_remove = abs(int(self.params.N))
        else:
            N = int(self.params.N)
            nnodes = len(cluster.compute_nodes)
            if nnodes > N:
                self.params.nodes_to_remove = nnodes - N
            else:
                self.params.nodes_to_add = N - nnodes

        if self.params.nodes_to_add:
            print("Adding %d nodes to the cluster"
                  "" % self.params.nodes_to_add)
        for i in range(self.params.nodes_to_add):
            cluster.add_node('compute')

        if self.params.nodes_to_remove:
            print("Removing %d nodes from the cluster."
                  "" % self.params.nodes_to_remove)
        for i in range(self.params.nodes_to_remove):
            node = cluster.compute_nodes.pop()
            if node in cluster.compute_nodes:
                cluster.remove_node(node)
            node.stop()

        cluster.start()
        print("Reconfiguring the cluster.")
        cluster.setup()
        frontend = cluster.frontend_nodes[0]
        print("""
Your cluster is up and running.
To login on the frontend node, run the command:

    ssh %s@%s -i %s
""" % (frontend.image_user, frontend.ip_public, frontend.user_key_private))


class ListClusters(AbstractCommand):
    """
    Handles the listing of all clusters.
    """
    def setup(self, subparsers):
        parser = subparsers.add_parser("list")
        parser.set_defaults(func=self)
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")

    def execute(self):
        storage = Configurator().create_cluster_storage()
        cluster_names = storage.get_stored_clusters()

        if not cluster_names:
            print("No clusters found.")
        else:
            print("""
The following clusters appear in your storage.
Yet, there's no guarantee that they are up and running:
""")
            for name in cluster_names:
                print("- %s " % name)


class ListNodes(AbstractCommand):
    """
    Handles the listing of information about a cluster.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser("list-nodes")
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")
        parser.add_argument(
            '-u', '--update', action='store_true', default=False,
            help="By default `elasticluster list-nodes` will not contact the "
            "EC2 provider to get up-to-date information, unless `-u` option "
            "is given.")

    def execute(self):
        """
        Lists all nodes within the specified cluster with certain
        information like id and ip.
        """
        Configuration.Instance().cluster_name = self.params.cluster
        cluster_name = self.params.cluster
        try:
            cluster = Configurator().load_cluster(cluster_name)
            if self.params.update:
                cluster.update()
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Listing nodes from cluster %s: %s\n" %
                      (cluster_name, ex))
            return

        print(cluster_summary(cluster))
        print("")
        print("Frontend nodes:")
        for node in cluster.frontend_nodes:
            print("  " + str(node))

        print("")
        print("Compute nodes:")
        for node in cluster.compute_nodes:
            print("  " + str(node))


class SetupCluster(AbstractCommand):
    def setup(self, subparsers):
        parser = subparsers.add_parser("setup")
        parser.set_defaults(func=self)
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")

    def execute(self):
        Configuration.Instance().cluster_name = self.params.cluster
        cluster_name = self.params.cluster
        try:
            cluster = Configurator().load_cluster(cluster_name)
            cluster.update()
        except (ClusterNotFound, ConfigurationError), ex:
            log.error("Setting up cluster %s: %s\n" %
                      (cluster_name, ex))
            return

        print("Configuring cluster `%s`..." % cluster_name)
        cluster.setup()
        print("Your cluster is ready!")
        print(cluster_summary(cluster))
