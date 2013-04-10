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

# System imports
import logging
import sys

# External modules
import cli.app

# Elasticluster imports
from elasticluster import log
from elasticluster.subcommands import Start
from elasticluster.subcommands import Stop
from elasticluster.subcommands import AbstractCommand
from elasticluster.subcommands import ListClusters
from elasticluster.subcommands import ListNodes
from elasticluster.conf import Configuration

class ElasticCloud(cli.app.CommandLineApp):        
        
    def setup(self):
        cli.app.CommandLineApp.setup(self)
        
        # all commands in this list will be added to the subcommands
        # if you add an object here, make sure it implements the commands.abstract_command contract
        commands = [
                    Start(self.params),
                    Stop(self.params),
                    ListClusters(self.params),
                    ListNodes(self.params)
                    ]
        
        # global parameters
        self.add_param('-c', '--cluster', help='name of the cluster', required=True)
        self.add_param('-v', '--verbose', action='count', default=0)
        self.add_param('-s', '--storage', help="storage folder, default is" + AbstractCommand.default_storage_dir, default=AbstractCommand.default_storage_dir)
        self.add_param('--config', help='configuration file, default is ' + AbstractCommand.default_configuration_file, default=AbstractCommand.default_configuration_file)
        

        # to parse subcommands
        self.subparsers = self.argparser.add_subparsers(title="subcommands", help="Sub commands")
        
        for command in commands:
            if isinstance(command, AbstractCommand):
                command.setup(self.subparsers)        
            
    def main(self):
        """
        This is the main entry point of the elasticluster.
        First the central configuration is created, which can be altered through the
        command line interface. Then the given command from the command line interface is called.
        """

        # Set verbosity level
        loglevel = max(1, logging.WARNING - 10 * max(0, self.params.verbose))
        log.setLevel(loglevel)
        
        # initialize configuration singleton with given global parameters
        try:
            Configuration.Instance().file_path = self.params.config
            Configuration.Instance().cluster_name = self.params.cluster
            Configuration.Instance().storage_path = self.params.storage
        except Exception as ex:
            print "please specify a valid configuration file"
            sys.exit()
        
        # call the subcommand function (ususally execute)
        return self.params.func()


def main():
    app = ElasticCloud()
    app.run()


if __name__ == "__main__":
    main()
