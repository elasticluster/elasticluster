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
from elasticluster.conf import Configurator
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'

from elasticluster.cluster import Cluster
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
        Starts a new Cluster with the given configuration file.
        """
        # ANTONIO: No need to call parent's `execute` method since
        # it's a noop.
        AbstractCommand.execute(self)
        
        cluster_name = self.params.cluster
        
        cluster = Configurator().create_cluster(cluster_name)
        cluster.start()
        
        
        
        
class Stop(AbstractCommand):
    
    def setup(self, subparsers):
        parser = subparsers.add_parser("stop")
        parser.set_defaults(func=self.execute)
    
    def execute(self):
        AbstractCommand.execute(self)
