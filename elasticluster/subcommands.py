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

from elasticluster.conf import Configurator
from elasticluster.conf import Configuration
from elasticluster import log


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
        parser.add_argument('cluster', help='name of the cluster')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity.")

    def execute(self):
        """
        Starts a new cluster.
        """
        Configuration.Instance().cluster_name = self.params.cluster
        cluster_name = self.params.cluster

        cluster = Configurator().create_cluster(cluster_name)

        # ANTONIO: You must check if the cluster is already present.
        # Note: this should be one of the possible way to do it, but
        # it rasies an error later on!
        storage = Configurator().create_cluster_storage()
        log.debug("Starting cluster %s", cluster_name)
        cluster_names = storage.get_stored_clusters()
        if cluster_name in cluster_names:
            cluster.load_from_storage()
        cluster.start()

        log.info("Your cluster is up and running.")


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
        Configuration.Instance().cluster_name = self.params.cluster
        cluster_name = self.params.cluster
        cluster = Configurator().create_cluster(cluster_name)
        cluster.load_from_storage()
        cluster.stop()


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
            print "No clusters found."
        else:
            print """
The following clusters appear in your storage.
Yet, there's no guarantee that they are up and running:
"""
            for name in cluster_names:
                print "- %s " % name


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
        cluster = Configurator().create_cluster(cluster_name)
        cluster.load_from_storage()

        print "The following nodes are in your cluster:"
        print "\nfrontend nodes:"
        for node in cluster.frontend_nodes:
            print node

        print "\ncompute nodes:"
        for node in cluster.compute_nodes:
            print node


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
        cluster = Configurator().create_cluster(cluster_name)
        cluster.load_from_storage()

        cluster.setup()
