#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)test_repository.py
# 
# 
# Copyright (C) 2013, GC3, University of Zurich. All rights reserved.
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
import shutil
import tempfile
import unittest

import nose.tools as nt

from elasticluster.repository import PickleRepository, MemRepository

class FakeCluster(object):
    """Fake class used for the storage cluster class.  The only thing the
    PickleRepository class assumes is that the saved class has a `name`
    attribute.
    """
    def __init__(self, name='fake_cluster'):
        self.name = name
        self.nodes = {}

    def __eq__(self, other):
        return self.name == other.name


class MemRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.storage = MemRepository()

    def test_get_all(self):
        clusters = [FakeCluster('test_%d' % i) for i in range(10)]

        for cluster in clusters:
            self.storage.save_or_update(cluster)

        new_clusters = self.storage.get_all()
        for cluster in new_clusters:
            nt.assert_true(cluster in clusters)

    def test_get(self):
        clusters = [FakeCluster('test_%d' % i) for i in range(10)]

        for cluster in clusters:
            self.storage.save_or_update(cluster)

        new_clusters = [self.storage.get(cluster.name) for cluster in clusters]
        for cluster in new_clusters:
            nt.assert_true(cluster in clusters)

    def test_delete(self):
        cluster = FakeCluster('test1')
        self.storage.save_or_update(cluster)
        nt.assert_true(cluster.name in self.storage.clusters)

        self.storage.delete(cluster)
        nt.assert_false(cluster.name in self.storage.clusters)
    

class PickleRepositoryTests(MemRepositoryTests):
    def setUp(self):
        self.path = tempfile.mkdtemp()
        self.storage = PickleRepository(self.path)

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)
        del self.storage

    def test_delete(self):
        pass

    def test_save_and_delete(self):
        cluster = FakeCluster('test1')
        self.storage.save_or_update(cluster)

        clusterpath = os.path.join(self.path, 'test1.pickle')
        nt.assert_true(os.path.exists(clusterpath))

        self.storage.delete(cluster)
        nt.assert_false(os.path.exists(clusterpath))


if __name__ == "__main__":
    import nose
    nose.runmodule()
