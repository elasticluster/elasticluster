#! /usr/bin/env python
#
#   Copyright (C) 2013-2016 S3IT, University of Zurich
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
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>, Antonio Messina <antonio.s.messina@gmail.com>'

# System imports
import logging
import os
import shutil
import sys
import utils
import warnings

# External modules
import cli.app
try:
    # Voluptuous version >= 0.8.1
    from voluptuous import MultipleInvalid, Invalid
except ImportError:
    # Voluptuous version <= 0.7.2
    from voluptuous.voluptuous import MultipleInvalid, Invalid

import coloredlogs

from pkg_resources import resource_filename


# Elasticluster imports
from elasticluster import log
from elasticluster.subcommands import Start, SetupCluster
from elasticluster.subcommands import Stop
from elasticluster.subcommands import AbstractCommand
from elasticluster.subcommands import ListClusters
from elasticluster.subcommands import ListNodes
from elasticluster.subcommands import ListTemplates
from elasticluster.subcommands import ResizeCluster
from elasticluster.subcommands import SshFrontend
from elasticluster.subcommands import SftpFrontend
from elasticluster.subcommands import GC3PieConfig
from elasticluster.subcommands import RemoveNode
from elasticluster.subcommands import ExportCluster
from elasticluster.subcommands import ImportCluster
from elasticluster.conf import Configurator
from elasticluster.exceptions import ConfigurationError
from elasticluster.migration_tools import MigrationCommand

class ElastiCluster(cli.app.CommandLineApp):
    name = "elasticluster"
    description = "Elasticluster will start, stop, grow, shrink clusters on an EC2 cloud."

    default_configuration_file = os.path.expanduser(
        "~/.elasticluster/config")

    def setup(self):
        cli.app.CommandLineApp.setup(self)

        # all commands in this list will be added to the subcommands
        # if you add an object here, make sure it implements the
        # subcommands.abstract_command contract
        commands = [Start(self.params),
                    Stop(self.params),
                    ListClusters(self.params),
                    ListNodes(self.params),
                    ListTemplates(self.params),
                    SetupCluster(self.params),
                    ResizeCluster(self.params),
                    SshFrontend(self.params),
                    SftpFrontend(self.params),
                    GC3PieConfig(self.params),
                    MigrationCommand(self.params),
                    RemoveNode(self.params),
                    ExportCluster(self.params),
                    ImportCluster(self.params),
                    ]

        # global parameters
        self.add_param('-v', '--verbose', action='count', default=0,
                       help="Increase verbosity. If at least four `-v` option "
                       "are given, elasticluster will create new VMs "
                       "sequentially instead of doing it in parallel.")
        self.add_param('-s', '--storage', metavar="PATH",
                       help="Path to the storage folder. Default: `%s`" %
                            Configurator.default_storage_path,
                       default=Configurator.default_storage_path)
        self.add_param('-c', '--config', metavar='PATH',
                       help=("Path to the configuration file; default: `%s`. "
                            "If directory `PATH.d` exists, also all files matching"
                            " pattern `PATH.d/*.conf` are parsed."
                             % self.default_configuration_file),
                       default=self.default_configuration_file)
        self.add_param('--version', action='store_true',
                       help="Print version information and exit.")

        # to parse subcommands
        self.subparsers = self.argparser.add_subparsers(
            title="COMMANDS",
            help="Available commands. Run `elasticluster cmd --help` "
                 "to have information on command `cmd`.")

        for command in commands:
            if isinstance(command, AbstractCommand):
                command.setup(self.subparsers)

    def pre_run(self):
        # Hack around http://bugs.python.org/issue9253 ?
        if "--version" in sys.argv:
            import pkg_resources
            version = pkg_resources.get_distribution("elasticluster").version
            print("elasticluster version %s" % version)
            sys.exit(0)

        cli.app.CommandLineApp.pre_run(self)

        # print *all* Python warnings through the logging subsystem
        warnings.resetwarnings()
        warnings.simplefilter('once')
        utils.redirect_warnings(logger='gc3.elasticluster')

        # Set verbosity level
        loglevel = max(logging.DEBUG, logging.WARNING - 10 * max(0, self.params.verbose))
        coloredlogs.install(logger=log, level=loglevel)
        log.setLevel(loglevel)

        # In debug mode, avoid forking
        if self.params.verbose > 3:
            log.DO_NOT_FORK = True
            log.raiseExceptions = True

        if not os.path.isdir(self.params.storage):
            # We do not create *all* the parents, but we do create the
            # directory if we can.
            try:
                os.makedirs(self.params.storage)
            except OSError as ex:
                sys.stderr.write("Unable to create storage directory: "
                                 "%s\n" % (str(ex)))
                sys.exit(1)

        # If no configuration file was specified and default does not exists and the user did not create a config dir...
        if not os.path.isfile(self.params.config) and not os.path.isdir(self.params.config + '.d'):
            if self.params.config == self.default_configuration_file:
            # Copy the default configuration file to the user's home
                if not os.path.exists(os.path.dirname(self.params.config)):
                    os.mkdir(os.path.dirname(self.params.config))
                template = resource_filename(
                    'elasticluster', 'share/etc/config.template')
                log.warning("Deploying default configuration file to %s.",
                            self.params.config)
                shutil.copyfile(template, self.params.config)
            else:
                # Exit if supplied configuration file does not exists.
                if not os.path.isfile(self.params.config):
                    sys.stderr.write(
                        "Unable to read configuration file `%s`.\n" %
                        self.params.config)
                    sys.exit(1)

        assert self.params.func, ("No subcommand defined in `ElastiCluster.setup()")
        try:
            self.params.func.pre_run()
        except (RuntimeError, ConfigurationError) as ex:
            sys.stderr.write(str(ex).strip())
            sys.stderr.write('\n')
            sys.exit(1)


    def main(self):
        """
        This is the main entry point of the ElastiCluster CLI.

        First the central configuration is created, which can be altered
        through the command line interface. Then the given command from
        the command line interface is called.
        """
        assert self.params.func, ("No subcommand defined in `ElastiCluster.main()")
        try:
            return self.params.func()
        except MultipleInvalid as ex:
            print("Multiple errors: %s" % str.join(', ', [str(e) for e in ex.errors]))
            print("Exiting.")
            sys.exit(1)
        except Invalid as ex:
            print("Error: %s" % ex)
            print("Exiting.")
            sys.exit(1)


def main():
    try:
        app = ElastiCluster()
        app.run()
    except KeyboardInterrupt:
        sys.stderr.write("""
WARNING: execution interrupted by the user!
Your clusters may be in inconsistent state!
""")
        return 1


if __name__ == "__main__":
    main()
