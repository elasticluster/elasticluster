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

from mock import Mock, MagicMock, patch

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

    def get_cluster(self, cloud_provider=None, config=None):
        if not cloud_provider:
            cloud_provider = BotoCloudProvider("https://hobbes.gc3.uzh.ch/",
                                          "nova", "a-key", "s-key")
        if not config:
            config = Configuration().get_config(self.path)

        setup = Mock()
        configurator = Configurator(Configuration().get_config(self.path))
        nodes = {"compute": 2, "frontend": 1}
        cluster = Cluster("mycluster", "mycluster", "hobbes", cloud_provider,
                          setup, nodes, configurator)
        return cluster

    def test_add_node(self):
        """
        Add node
        """
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
        """
        Remove node
        """
        cluster = self.get_cluster()

        size = len(cluster.nodes['compute'])
        cluster.remove_node(cluster.nodes['compute'][1])
        self.assertEqual(size - 1, len(cluster.nodes['compute']))

    def test_start(self):
        """
        Start cluster
        """
        cluster = self.get_cluster()

        cloud_provider = MagicMock()
        cloud_provider.start_instance.return_value = u'test-id'
        cloud_provider.get_ips.return_value = ('127.0.0.1', '127.0.0.1')
        states = [True, True, True, True, True, False, False, False,
                  False, False]

        def is_running(id):
            return states.pop()

        cloud_provider.is_instance_running.side_effect = is_running

        cluster = self.get_cluster(cloud_provider=cloud_provider)
        cluster._storage = MagicMock()

        ssh_mock = MagicMock()
        with patch('elasticluster.cluster.paramiko.SSHClient') as ssh_mock:
            ssh_mock.connect.return_value = True
            cluster.start()

        cluster._storage.dump_cluster.assert_called_with(cluster)

        for node in cluster.get_all_nodes():
            assert node.instance_id == u'test-id'
            assert node.ip_public == '127.0.0.1'
            assert node.ip_private == '127.0.0.1'

    def test_get_all_nodes(self):
        """
        Get all nodes
        """
        cluster = self.get_cluster()
        self.assertEqual(len(cluster.get_all_nodes()), 3)

    def test_stop(self):
        cloud_provider = MagicMock()
        cloud_provider.start_instance.return_value = u'test-id'
        cloud_provider.get_ips.return_value = ('127.0.0.1', '127.0.0.1')
        states = [True, True, True, True, True, False, False, False, False,
                  False]

        def is_running(id):
            return states.pop()

        cloud_provider.is_instance_running.side_effect = is_running
        cluster = self.get_cluster(cloud_provider=cloud_provider)

        for node in cluster.get_all_nodes():
            node.instance_id = u'test-id'

        cluster._storage = MagicMock()

        cluster.stop()

        cloud_provider.stop_instance.assert_called_with(u'test-id')
        cluster._storage.delete_cluster.assert_called_once_with(cluster.name)

    def test_get_frontend_node(self):
        """
        Get frontend node
        """
        config = Configuration().get_config(self.path)
        ssh_to = "frontend"
        config["mycluster"]["cluster"]["ssh_to"] = ssh_to

        cluster = self.get_cluster(config=config)
        cluster.ssh_to = ssh_to
        frontend = cluster.get_frontend_node()

        self.assertEqual(cluster.nodes['frontend'][0], frontend)

    def test_setup(self):
        """
        Setup the nodes of a cluster
        """
        setup_provider = MagicMock()
        setup_provider.setup_cluster.return_value = True

        cluster = self.get_cluster()
        cluster._setup_provider = setup_provider

        cluster.setup()

        setup_provider.setup_cluster.assert_called_once_with(cluster)

    def test_update(self):
        storage = MagicMock()
        cloud_provider = MagicMock()
        ip = '127.0.0.1'
        cloud_provider.get_ips.return_value = (ip, ip)

        cluster = self.get_cluster(cloud_provider=cloud_provider)
        cluster._storage = storage

        cluster.update()

        for node in cluster.get_all_nodes():
            self.assertEqual(node.ip_private, node.ip_public, ip)
        
        
        
        
        
        
        
        
