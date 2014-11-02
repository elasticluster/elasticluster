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

import json
import os
import shutil
import tempfile
import unittest

from mock import Mock, MagicMock, patch

from elasticluster.conf import Configurator
from elasticluster.cluster import Cluster, Node
from elasticluster.exceptions import ClusterError
from elasticluster.providers.ec2_boto import BotoCloudProvider
from elasticluster.repository import PickleRepository
from tests.test_conf import Configuration


class TestCluster(unittest.TestCase):

    def setUp(self):
        self.storage_path = tempfile.mkdtemp()
        f, path = tempfile.mkstemp()
        self.path = path

    def tearDown(self):
        shutil.rmtree(self.storage_path)
        os.unlink(self.path)

    def get_cluster(self, cloud_provider=None, config=None, nodes=None):
        if not cloud_provider:
            cloud_provider = BotoCloudProvider("https://hobbes.gc3.uzh.ch/",
                                               "nova", "a-key", "s-key")
        if not config:
            config = Configuration().get_config(self.path)

        setup = Mock()
        configurator = Configurator(config)
        conf_login = configurator.cluster_conf['mycluster']['login']
        repository = PickleRepository(self.storage_path)

        cluster = Cluster("mycluster", cloud_provider,
                          setup, repository, conf_login['user_key_name'],
                          conf_login['user_key_public'],
                          conf_login['user_key_private'],
                          )

        if not nodes:
            nodes = {"compute": 2, "frontend": 1}

        for kind, num in nodes.iteritems():
            conf_kind = configurator.cluster_conf['mycluster']['nodes'][kind]
            cluster.add_nodes(kind, num, conf_kind['image_id'],
                              conf_login['image_user'],
                              conf_kind['flavor'],
                              conf_kind['security_group'])

        return cluster

    def test_add_node(self):
        """
        Add node
        """
        cluster = self.get_cluster()

        # without name
        size = len(cluster.nodes['compute'])
        cluster.add_node("compute", 'image_id', 'image_user', 'flavor',
                         'security_group')
        self.assertEqual(size + 1, len(cluster.nodes['compute']))
        new_node = cluster.nodes['compute'][2]
        self.assertEqual(new_node.name, 'compute003')
        self.assertEqual(new_node.kind, 'compute')

        # with custom name
        name = "test-node"
        size = len(cluster.nodes['compute'])
        cluster.add_node("compute", 'image_id', 'image_user', 'flavor',
                         'security_group', image_userdata="", name=name)
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
        cloud_provider = MagicMock()
        cloud_provider.start_instance.return_value = u'test-id'
        cloud_provider.get_ips.return_value = ['127.0.0.1']
        cloud_provider.is_instance_running.return_value = True

        cluster = self.get_cluster(cloud_provider=cloud_provider)
        cluster.repository = MagicMock()

        ssh_mock = MagicMock()
        with patch('paramiko.SSHClient') as ssh_mock:
            cluster.start()

        cluster.repository.save_or_update.assert_called_with(cluster)

        for node in cluster.get_all_nodes():
            assert node.instance_id == u'test-id'
            assert node.ips == ['127.0.0.1']

    def test_check_cluster_size(self):
        nodes = {"compute": 3, "frontend": 1}
        nodes_min = {"compute": 1, "frontend": 3}
        cluster = self.get_cluster(nodes=nodes)

        cluster._check_cluster_size(nodes_min)

        self.assertEqual(len(cluster.nodes["frontend"]), 3)
        self.assertTrue(len(cluster.nodes["compute"]) >= 1)

        # not satisfiable cluster setup
        nodes = {"compute": 3, "frontend": 1}
        nodes_min = {"compute": 5, "frontend": 3}
        cluster = self.get_cluster(nodes=nodes)

        self.failUnlessRaises(ClusterError, cluster._check_cluster_size,
                              min_nodes=nodes_min)

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

        def is_running(instance_id):
            return states.pop()

        cloud_provider.is_instance_running.side_effect = is_running
        cluster = self.get_cluster(cloud_provider=cloud_provider)

        for node in cluster.get_all_nodes():
            node.instance_id = u'test-id'

        cluster.repository = MagicMock()

        cluster.stop()

        cloud_provider.stop_instance.assert_called_with(u'test-id')
        cluster.repository.delete.assert_called_once_with(cluster)

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
        cluster.repository = storage

        cluster.update()

        for node in cluster.get_all_nodes():
            self.assertEqual(node.ips[0], ip)


class TestNode(unittest.TestCase):

    def setUp(self):
        f, path = tempfile.mkstemp()
        self.path = path

        self.cluster_name = "cluster"
        self.name = "test"
        self.node_kind = "frontend"
        self.user_key_public = self.path
        self.user_key_private = self.path
        self.user_key_name = "key"
        self.image_user = "gc3-user"
        self.security_group = "security"
        self.image = "ami-000000"
        self.flavor = "m1.tiny"
        self.image_userdata = None

    def tearDown(self):
        os.unlink(self.path)

    def get_node(self):
        cloud_provider = MagicMock()
        node = Node(self.name, self.cluster_name, self.node_kind, 
                    cloud_provider, self.user_key_public, 
                    self.user_key_private, self.user_key_name, 
                    self.image_user, self.security_group, 
                    self.image, self.flavor,
                    self.image_userdata)

        return node

    def test_start(self):
        """
        Start node
        """
        node = self.get_node()
        instance_id = "test-id"

        cloud_provider = node._cloud_provider

        cloud_provider.start_instance.return_value = instance_id

        node.start()


        node_name = "%s-%s" % (self.cluster_name, node.name)
        cloud_provider.start_instance.assert_called_once_with(
            self.user_key_name, self.user_key_public, self.user_key_private,
            self.security_group, self.flavor, self.image,
            self.image_userdata, username=self.image_user, node_name=node_name)
        self.assertEqual(node.instance_id, instance_id)

    def test_stop(self):
        """
        Stop Node
        """
        node = self.get_node()
        instance_id = "test-id"
        node.instance_id = instance_id

        node.stop()

        cloud_provider = node._cloud_provider
        cloud_provider.stop_instance.assert_called_once_with(instance_id)

    def test_is_alive(self):
        """
        Node is alive
        """
        # check without having any knowlegde of the node (e.g. instance id)
        node = self.get_node()
        self.assertFalse(node.is_alive())

        # check with knowledge and cloud provider and mock ip update
        instance_id = "test-id"
        node.instance_id = instance_id

        provider = node._cloud_provider
        provider.is_instance_running.return_value = True
        provider.get_ips.return_value = ['127.0.0.1', '127.0.0.1']

        node.is_alive()

        provider.is_instance_running.assert_called_once_with(instance_id)

    def test_connect(self):
        """
        Connect to node
        """
        node = self.get_node()

        # check without any ips set on the host
        self.assertEqual(node.connect(), None)

        # check with mocking the ssh connection
        ssh_mock = MagicMock()
        with patch('elasticluster.cluster.paramiko.SSHClient') as ssh_mock:
            ssh_mock.connect.return_value = True
            node.connect()

    def test_update_ips(self):
        """
        Update node ip address
        """
        # check without any ip addresses set
        node = self.get_node()
        instance_id = "test-id"
        node.instance_id = instance_id
        provider = node._cloud_provider

        ips = ['127.0.0.1', '127.0.0.2']
        node.ips = ips
        provider.get_ips.return_value = ips

        node.update_ips()

        self.assertEqual(node.ips, ips)
        provider.get_ips.assert_called_once_with(instance_id)

if __name__ == "__main__":
    import nose
    nose.runmodule()
