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

import os
import tempfile
import unittest

from mock import Mock

from elasticluster.conf import Configurator
from elasticluster.cluster import Cluster
from elasticluster.providers.ec2_boto import BotoCloudProvider
from test.test_conf import Configuration


class TestCluster(unittest.TestCase):

    def setUp(self):
        file, path = tempfile.mkstemp()
        self.path = path


    def tearDown(self):
        os.unlink(self.path)

    def get_cluster(self):
        cloud = BotoCloudProvider("http://test.os.com", "nova", "a-key",
                                    "s-key")
        setup = Mock()
        configurator = Configurator(Configuration().get_config(self.path))
        nodes = {"compute": 2, "frontend": 1}
        cluster = Cluster("mycluster", "mycluster", "hobbes", cloud, setup,
                          nodes, configurator)
        return cluster

    def test_add_node(self):
        cluster = self.get_cluster()

        # without name
        size = len(cluster.nodes['compute'])
        cluster.add_node("compute")
        self.assertEqual(size + 1, len(cluster.nodes['compute']))
        new_node = cluster.nodes['compute'][2]
        self.assertEqual(new_node.name, 'compute003')
        self.assertEqual(new_node.type, 'compute')

        # with custom name
        name = "test-node"
        size = len(cluster.nodes['compute'])
        cluster.add_node("compute", name=name)
        self.assertEqual(size + 1, len(cluster.nodes['compute']))
        self.assertEqual(cluster.nodes['compute'][3].name, name)


    def test_remove_node(self):
        cluster = self.get_cluster()

        size = len(cluster.nodes['compute'])
        cluster.remove_node(cluster.nodes['compute'][1])
        self.assertEqual(size - 1, len(cluster.nodes['compute']))



        
        
        
        
        
        
        
        
        
        
