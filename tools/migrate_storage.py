#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)migrate_storage.py
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

from elasticluster import repository, cluster
repository.ClusterRepository = repository.PickleRepository

def __fix_setstate__(self, state):
    self.__dict__ = state
    if 'known_hosts_file' not in state:
        self.known_hosts_file = None
    if 'template' not in state:
        self.template = self.extra['template']
    if 'thread_pool_max_size' not in state:
        self.thread_pool_max_size = 10

cluster.Cluster.__setstate__ = __fix_setstate__

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""This script is used to migrate clusters created with older version of Elasticluster to the latest one.""")
        print("Usage: %s storagepath [clustername]" % sys.argv[0])
        sys.exit(1)    

    storage_path = os.path.expanduser(sys.argv[1])
    repository = repository.PickleRepository(storage_path)
    clusters = repository.get_all()

    for cluster in clusters:
        # Fix known_hosts file missing attribute
        known_hosts_file = "%s/%s.known_hosts" % (storage_path, cluster.name)
        if os.path.isfile(known_hosts_file) and known_hosts_file != cluster.known_hosts_file:
            cluster.known_hosts_file = known_hosts_file
            
    for cl in clusters:
        print("Saving cluster %s" % cl.name)
        cl.repository.save_or_update(cl)
    
    
