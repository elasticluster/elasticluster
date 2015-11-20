#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)migration_tools.py
# 
# 
# Copyright (C) 2014 S3IT, University of Zurich. All rights reserved.
# 
# 
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

__docformat__ = 'reStructuredText'
__author__ = 'Antonio Messina <antonio.s.messina@gmail.com>'

import os
import sys

from elasticluster.subcommands import AbstractCommand

from elasticluster import repository, cluster

# commit 73979e27b3cd8e62d2f023d915ffd162d36bb301
# Author: Antonio Messina <antonio.s.messina@gmail.com>
# Date:   Sun Nov 2 10:56:14 2014 +0100
#
#     Rename `ClusterRepository` to `PickleRepository`
repository.ClusterRepository = repository.PickleRepository

class NotPresent:
    def __str__(self):
        return "Not present before"

def __setstate_upgrade__(self, state):
    self.__dict__ = state
    self._patches = {}

    # commit cc446ac19907ef692ec08336f06b5e6b740d6387
    # Author: Antonio Messina <antonio.s.messina@gmail.com>
    # Date:   Sat Oct 25 16:57:58 2014 +0200
    #
    #     Save host keys in `storage_path` as <clustername>.known_hosts and use it when connecting to the cluster
    old_known_hosts_file = state.get('known_hosts_file', NotPresent())

    path = "%s/%s.known_hosts" % (self.repository.storage_path, self.name)
    known_hosts_file = path if os.path.isfile(path) else None

    if old_known_hosts_file != known_hosts_file:
        self._patches['known_hosts_file'] = (NotPresent(), known_hosts_file)

    # commit 6413374799e945953492e699cca4bcabf572b5df
    # Author: Antonio Messina <antonio.s.messina@gmail.com>
    # Date:   Mon Nov 3 09:49:32 2014 +0100
    #
    #     Also save the template name of a cluster, if known.
    if 'template' not in state:
        self._patches['template'] = (NotPresent(), self.extra['template'])

    # commit 7b4ed108a699c6801b2d22790ae30368f416c246
    # Author: Antonio Messina <antonio.s.messina@gmail.com>
    # Date:   Tue Nov 4 11:36:40 2014 +0100

    #     Add a configuration option `thread_pool_max_size` to limit
    #     the maximum amount of processes that are created when
    #     starting virtual machine
    if 'thread_pool_max_size' not in state:
        self._patches['thread_pool_max_size'] = (NotPresent(), 10)

    for attr, values in self._patches.items():
        self.__dict__[attr] = values[1]

def patch_cluster():
    """
    Patch Cluster class to allow Pickle to load old clusters
    """    
    cluster.Cluster.__setstate__ = __setstate_upgrade__
    

class MigrationCommand(AbstractCommand):
    """
    Migrate stored clusters from older versions of elasticluster.
    """

    def setup(self, subparsers):
        parser = subparsers.add_parser(
            "migrate", help="Migrate a stored cluster", description=self.__doc__)
        parser.set_defaults(func=self)
        parser.add_argument('cluster', nargs='*',
                            help='Only migrate CLUSTER. By default, all clusters are migrated')
        parser.add_argument('-s', '--storage-path', metavar='PATH',
                            default=os.path.expanduser('~/.elasticluster/storage'),
                            help="Path to elasticluster storage directory. Default: %(default)s")
        parser.add_argument('-n', '--dry-run', action='store_true',
                            help="Do not actually migrate anything, just show what's going to happen")

    def execute(self):
        """
        migrate storage
        """
        repo = repository.PickleRepository(self.params.storage_path)

        clusters = [i[:-7] for i in os.listdir(self.params.storage_path) if i.endswith('.pickle')]

        if self.params.cluster:
            clusters = filter(lambda x: x in self.params.cluster, clusters)

        if not clusters:
            print("No clusters")
            sys.exit(0)
        
        patch_cluster()
        for cluster in clusters:
            print("Cluster `%s`" % cluster)
            print("path: %s" % repo.storage_path + '/%s.pickle' % cluster)
            cl = repo.get(cluster)
            if cl._patches:
                print("Attributes changed: ")
                for attr, val in cl._patches.items():
                    print("  %s: %s -> %s" % (attr, val[0], val[1]))
            else:
                print("No upgrade needed")

            print("")
            if not self.params.dry_run:
                if cl._patches:
                    del cl._patches
                    print("Changes saved to disk")
                    cl.repository.save_or_update(cl)
            
                
