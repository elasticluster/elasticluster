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

# System imports
import logging
import os
import shutil
import sys
import utils
import warnings

# External modules
import cli.app

import coloredlogs

from pkg_resources import resource_filename

# Elasticluster imports
from elasticluster import log
from elasticluster.subcommands import (
    AbstractCommand,
    ExportCluster,
    GC3PieConfig,
    ImportCluster,
    ListClusters,
    ListNodes,
    ListTemplates,
    RemoveNode,
    ResizeCluster,
    SetupCluster,
    SftpFrontend,
    SshFrontend,
    Start,
    Stop,
)
from elasticluster.conf import Creator
from elasticluster.exceptions import ConfigurationError
from elasticluster.migration_tools import MigrationCommand


__author__ = ', '.join([
    'Nicolas Baer <nicolas.baer@uzh.ch>',
    'Antonio Messina <antonio.s.messina@gmail.com>',
    'Riccardo Murri <riccardo.murri@gmail.com>',
])


class ElastiCluster(cli.app.CommandLineApp):
    name = "elasticluster"
    description = "Elasticluster starts, stops, grows, and shrinks clusters on a cloud."

    default_configuration_file = os.path.expanduser(
        "~/.elasticluster/config")

    def setup(self):
        cli.app.CommandLineApp.setup(self)

        # Global parameters
        self.add_param('-v', '--verbose', action='count', default=0,
                       help="Increase verbosity. If at least four `-v` option "
                       "are given, elasticluster will create new VMs "
                       "sequentially instead of doing it in parallel.")
        self.add_param('-s', '--storage', metavar="PATH",
                       help="Path to the storage folder. (Default: `%(default)s`",
                       default=Creator.DEFAULT_STORAGE_PATH)
        self.add_param('-c', '--config', metavar='PATH',
                       help=("Path to the configuration file;"
                             " default: `%(default)s`."
                             " If directory `PATH.d` exists,"
                             " all files matching"
                             " pattern `PATH.d/*.conf` are parsed."),
                       default=self.default_configuration_file)
        self.add_param('--version', action='store_true',
                       help="Print version information and exit.")

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

        # to parse subcommands
        self.subparsers = self.argparser.add_subparsers(
            title="COMMANDS",
            help=("Available commands. Run `elasticluster cmd --help`"
                  " to have information on command `cmd`."))

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

        # ensure we print tracebacks in DEBUG mode
        if self.params.verbose > 3:
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

        self.check_config_or_copy_template()

        assert self.params.func, "No subcommand defined in `ElastiCluster.setup()"
        try:
            self.params.func.pre_run()
        except (RuntimeError, ConfigurationError) as ex:
            sys.stderr.write(str(ex).strip())
            sys.stderr.write('\n')
            sys.exit(1)

    def check_config_or_copy_template(self):
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

    def main(self):
        """
        This is the main entry point of the ElastiCluster CLI.

        First the central configuration is created, which can be altered
        through the command line interface. Then the given command from
        the command line interface is called.
        """
        assert self.params.func, "No subcommand defined in `ElastiCluster.main()"
        try:
            return self.params.func()
        except Exception as err:
            log.error("Error: %s", err)
            if self.params.verbose > 2:
                import traceback
                traceback.print_exc()
            print("Aborting because of errors: {err}.".format(err=err))
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
