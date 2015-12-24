#!/usr/bin/env python
# -*- coding: utf-8 -*-#
# @(#)test_repository.py
#
#
# Copyright (C) 2013, 2015 S3IT, University of Zurich. All rights reserved.
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


import json
import os
import shutil
import tempfile
import unittest

import nose.tools as nt

from elasticluster import Cluster
from elasticluster.cluster import Struct
from elasticluster.repository import PickleRepository, MemRepository, \
    JsonRepository, YamlRepository, MultiDiskRepository


class MemRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.storage = MemRepository()

    def test_get_all(self):
        clusters = [Cluster('test_%d' % i) for i in range(10)]

        for cluster in clusters:
            self.storage.save_or_update(cluster)

        new_clusters = self.storage.get_all()
        for cluster in new_clusters:
            nt.assert_true(cluster in clusters)

    def test_get(self):
        clusters = [Cluster('test_%d' % i) for i in range(10)]

        for cluster in clusters:
            self.storage.save_or_update(cluster)

        new_clusters = [self.storage.get(cluster.name) for cluster in clusters]
        for cluster in new_clusters:
            nt.assert_true(cluster in clusters)

    def test_delete(self):
        cluster = Cluster('test1')
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
        cluster = Cluster('test1')
        self.storage.save_or_update(cluster)

        clusterpath = os.path.join(self.path, 'test1.pickle')
        nt.assert_true(os.path.exists(clusterpath))

        self.storage.delete(cluster)
        nt.assert_false(os.path.exists(clusterpath))


class JsonRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()
        self.storage = JsonRepository(self.path)

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)
        del self.storage

    def test_get_all(self):
        clusters = [Cluster(name='test_%d' % i,
                            cloud_provider=None,
                            setup_provider=None,
                            user_key_name='key') for i in range(10)]

        for cluster in clusters:
            self.storage.save_or_update(cluster)

        new_clusters = self.storage.get_all()
        for cluster in new_clusters:
            nt.assert_true(cluster.name in [c.name for c in clusters])

    def test_get(self):
        clusters = [Cluster('test_%d' % i) for i in range(10)]

        for cluster in clusters:
            self.storage.save_or_update(cluster)

        new_clusters = [self.storage.get(cluster.name) for cluster in clusters]
        for cluster in new_clusters:
            nt.assert_true(cluster.name in [c.name for c in clusters])

    def test_delete(self):
        pass

    def test_save_and_delete(self):
        cluster = Cluster(name='test1',
                          cloud_provider=None,
                          setup_provider=None,
                          user_key_name='key')
        self.storage.save_or_update(cluster)

        clusterpath = os.path.join(self.path, 'test1.json')
        nt.assert_true(os.path.exists(clusterpath))

        self.storage.delete(cluster)
        nt.assert_false(os.path.exists(clusterpath))

    def test_saving_cluster_with_nodes(self):
        cluster = Cluster(name='test1',
                          cloud_provider=None,
                          setup_provider=None,
                          user_key_name='key',
                          repository=self.storage)
        cluster.add_node(kind='foo', image_id='123',
                         image_user='s3it', flavor='m1.tiny',
                         security_group='default', name='foo123')
        self.storage.save_or_update(cluster)
        new = self.storage.get(cluster.name)
        nt.assert_true('foo' in cluster.nodes)
        nt.assert_true(cluster.nodes['foo'], 1)
        nt.assert_true(cluster.nodes['foo'][0].name, 'foo123')


class YamlRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()
        self.storage = YamlRepository(self.path)

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)
        del self.storage

    def test_get_all(self):
        clusters = [Cluster(name='test_%d' % i,
                            cloud_provider=None,
                            setup_provider=None,
                            user_key_name='key') for i in range(10)]

        for cluster in clusters:
            self.storage.save_or_update(cluster)

        new_clusters = self.storage.get_all()
        for cluster in new_clusters:
            nt.assert_true(cluster.name in [c.name for c in clusters])

    def test_get(self):
        clusters = [Cluster('test_%d' % i) for i in range(10)]

        for cluster in clusters:
            self.storage.save_or_update(cluster)

        new_clusters = [self.storage.get(cluster.name) for cluster in clusters]
        for cluster in new_clusters:
            nt.assert_true(cluster in clusters)

    def test_delete(self):
        pass

    def test_save_and_delete(self):
        cluster = Cluster(name='test1',
                          cloud_provider=None,
                          setup_provider=None,
                          user_key_name='key')
        self.storage.save_or_update(cluster)

        clusterpath = os.path.join(self.path, 'test1.yaml')
        nt.assert_true(os.path.exists(clusterpath))

        self.storage.delete(cluster)
        nt.assert_false(os.path.exists(clusterpath))

    def test_saving_cluster_with_nodes(self):
        cluster = Cluster(name='test1',
                          cloud_provider=None,
                          setup_provider=None,
                          user_key_name='key',
                          repository=self.storage)
        cluster.add_node(kind='foo', image_id='123',
                         image_user='s3it', flavor='m1.tiny',
                         security_group='default', name='foo123')
        self.storage.save_or_update(cluster)
        new = self.storage.get(cluster.name)
        nt.assert_true('foo' in cluster.nodes)
        nt.assert_true(cluster.nodes['foo'], 1)
        nt.assert_true(cluster.nodes['foo'][0].name, 'foo123')


# Note: do not subclass from unittest.TestCase if you want to use test
# generators.
class TestMultiDiskRepository(object):
    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)
        if hasattr(self, 'storage'):
            del self.storage

    @nt.raises(ValueError)
    def test_invalid_storage_type(self):
        MultiDiskRepository('/tmp/foo', 'foo')

    def store_is_of_type(self, store_type):
        """Check store type %s""" % store_type
        storage = MultiDiskRepository(self.path, default_store=store_type)
        cluster = Cluster(name='test1',
                          cloud_provider=None,
                          setup_provider=None,
                          user_key_name='key',
                          repository=storage)
        storage.save_or_update(cluster)

        nt.assert_true(
            os.path.exists(
                os.path.join(self.path, cluster.name + '.' + store_type)))

    def test_repository_default_type(self):
        for store_type in ['yaml', 'json', 'pickle']:
            yield self.store_is_of_type, store_type

if __name__ == "__main__":
    import nose
    nose.runmodule()
