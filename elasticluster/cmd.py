#! /usr/bin/env python
#
#   Copyright (C) 2013 GC3, University of Zurich
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'

from elasticluster.conf import Configurator

import os


class AbstractCommand():
    """
    Defines the general contract every command has to fullfill in order to be recognized
    by the arguments list and executed afterwards.
    """
    default_configuration_file = os.getenv("HOME") + os.sep + ".elasticluster" + os.sep + "config.cfg"
    default_storage_dir = os.getenv("HOME") + os.sep + ".elasticluster" + os.sep + "storage"
    
    def __init__(self, params):
        """
        A reference to the parameters of the command line will be passed here
        to adjust the functionality of the command properly.
        """
        self.params = params
    
    def setup(self, subparsers):
        """
        This method handles the setup of the subcommand. In order to do so, every command has to
        add a parser to the subparsers reference given as parameter. The following example is the
        minimum implementation of such a setup procedure:
        parser = subparsers.add_parser("start")
        parser.set_defaults(func=self.execute)
        """
        pass
        
    def execute(self):
        """
        This method is executed after a command was recognized and may vary in its behavior.
        """
        pass
    
    
class Start(AbstractCommand):
    """
    Handles the start of a cluster. The cluster parameters are mostly read from a configuration file in order
    to keep the parameter set to a minimum.
    """    
    
    def setup(self, subparsers):
        """
        @see abstract_command contract
        """        
        parser = subparsers.add_parser("start")
        parser.set_defaults(func=self.execute)
        
    def execute(self):
        """
        Starts a new cluster.
        """
        AbstractCommand.execute(self)
        
        cluster_name = self.params.cluster
        
        cluster = Configurator().create_cluster(cluster_name)
        cluster.start()
        
        print "your cluster is up and running:"
        
        
        
class Stop(AbstractCommand):
    """
    Handles the stop of a cluster.
    """
    def setup(self, subparsers):
        """
        @see abstract_command contract
        """
        parser = subparsers.add_parser("stop")
        parser.set_defaults(func=self.execute)
    
    def execute(self):
        """
        Stops the cluster if it's running.
        """
        AbstractCommand.execute(self)
        
        cluster_name = self.params.cluster
        cluster = Configurator().create_cluster(cluster_name)
        cluster.load_from_storage()
        cluster.stop()
        
        
class ListClusters(AbstractCommand):
    """
    Handles the listing of all clusters.
    TODO: this command still needs the --cluster argument to run, since that is a mandatory global parameter, tho it makes no sense here.
    """
    def setup(self, subparsers):
        parser = subparsers.add_parser("listclusters")
        parser.set_defaults(func=self.execute)
        
    def execute(self):
        storage = Configurator().create_cluster_storage()
        cluster_names = storage.get_stored_clusters()
        
        print "The following clusters appear in your storage. Yet, there's no guarantee that they are up and running tho:"
        for name in cluster_names:
            print "- %s " % name
            

class ListNodes(AbstractCommand):
    """
    Handles the listing of information about a cluster.
    """
    def setup(self, subparsers):
        parser = subparsers.add_parser("listnodes")
        parser.set_defaults(func=self.execute)
    
    def execute(self):
        """
        Lists all nodes within the specified cluster with certain information like id and ip.
        """
        AbstractCommand.execute(self)
        
        cluster_name = self.params.cluster
        cluster = Configurator().create_cluster(cluster_name)
        cluster.load_from_storage()
        
        print "The following nodes are in your cluster:"
        print "\nfrontend nodes:"
        for node in cluster.frontend_nodes:
            print "id=`%s`, public_ip=`%s`, private_ip=`%s`" % (node.instance_id, node.ip_public, node.ip_private)
            
        print "\ncompute nodes:"
        for node in cluster.compute_nodes:
            print "id=`%s`, public_ip=`%s`, private_ip=`%s`" % (node.instance_id, node.ip_public, node.ip_private)
            
            
            
