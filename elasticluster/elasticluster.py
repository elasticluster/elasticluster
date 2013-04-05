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


import cli.app
from cmd import Start
from cmd import Stop
from cmd import AbstractCommand
from conf import Configuration

class ElasticCloud(cli.app.CommandLineApp):        
        
    def setup(self):
        cli.app.CommandLineApp.setup(self)
        
        # all commands in this list will be added to the subcommands
        # if you add an object here, make sure it implements the commands.abstract_command contract
        commands = [
                    Start(self.params),
                    Stop(self.params)
                    ]
        
        # global parameters
        self.add_param('-c', '--cluster', help='name of the cluster', required=True)
        self.add_param('-v', '--verbose', action='count')
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
        
        # initialize configuration singleton with given global parameters
        try:
            if self.params.config:
                Configuration.Instance().file_path = self.params.config
            else:
                Configuration.Instance().file_path = AbstractCommand.default_configuration_file
            Configuration.Instance().cluster_name = self.params.cluster
        except Exception as ex:
            print ex
            print "please specify a valid configuration file"
        
        # call the subcommand function (ususally execute)
        return self.params.func()
        
        
if __name__ == "__main__":
    app = ElasticCloud()
    app.run()
