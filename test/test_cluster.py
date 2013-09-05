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
from elasticluster.cluster import Cluster, Node, ClusterStorage
from elasticluster.exceptions import ClusterError
from elasticluster.providers.ec2_boto import BotoCloudProvider
from test.test_conf import Configuration


class TestCluster(unittest.TestCase):

    def setUp(self):
        f, path = tempfile.mkstemp()
        self.path = path


    def tearDown(self):
        os.unlink(self.path)

    def get_cluster(self, cloud_provider=None, config=None, nodes=None):
        if not cloud_provider:
            cloud_provider = BotoCloudProvider("https://hobbes.gc3.uzh.ch/",
                                          "nova", "a-key", "s-key")
        if not config:
            config = Configuration().get_config(self.path)

        setup = Mock()
        configurator = Configurator(config)
        if not nodes:
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
        cloud_provider = MagicMock()
        cloud_provider.start_instance.return_value = u'test-id'
        cloud_provider.get_ips.return_value = ('127.0.0.1', '127.0.0.1')
        states = [True, True, True, True, True, False, False, False,
                  False, False]

        def is_running(instance_id):
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

    def test_check_cluster_size(self):
        nodes = {"compute": 3, "frontend": 1}
        nodes_min = {"compute": 1, "frontend": 3}
        cluster = self.get_cluster(nodes=nodes)
        cluster.min_nodes = nodes_min

        cluster._check_cluster_size()

        self.assertEqual(len(cluster.nodes["frontend"]), 3)
        self.assertTrue(len(cluster.nodes["compute"]) >= 1)

        # not satisfiable cluster setup
        nodes = {"compute": 3, "frontend": 1}
        nodes_min = {"compute": 5, "frontend": 3}
        cluster = self.get_cluster(nodes=nodes)
        cluster.min_nodes = nodes_min

        self.failUnlessRaises(ClusterError, cluster._check_cluster_size)


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

        
        
class TestNode(unittest.TestCase):

    def setUp(self):
        f, path = tempfile.mkstemp()
        self.path = path

        self.name = "test"
        self.node_type = "frontend"
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
        node = Node(self.name, self.node_type, cloud_provider,
                    self.user_key_public, self.user_key_private,
                    self.user_key_name, self.image_user,
                    self.security_group, self.image, self.flavor,
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

        cloud_provider.start_instance.assert_called_once_with(
            self.user_key_name, self.user_key_public, self.user_key_private,
            self.security_group, self.flavor, self.image,
            self.image_userdata, username=self.image_user)
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
        provider.get_ips.return_value = ('127.0.0.1', '127.0.0.1')

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

        node.ip_private = None
        node.ip_public = None

        ip_public = '127.0.0.1'
        ip_private = '127.0.0.2'
        provider.get_ips.return_value = (ip_private, ip_public)

        node.update_ips()

        self.assertEqual(node.ip_private, ip_private)
        self.assertEqual(node.ip_public, ip_public)
        provider.get_ips.assert_called_once_with(instance_id)

        # check with already present ips
        ip_unused = "127.0.0.3"
        provider.get_ips.return_value = (ip_unused, ip_unused)

        node.update_ips()

        self.assertEqual(node.ip_private, ip_private)
        self.assertEqual(node.ip_public, ip_public)


class TestClusterStorage(unittest.TestCase):

    def setUp(self):
        self.storage_path = tempfile.mkdtemp()
        f, path = tempfile.mkstemp()
        self.path = path

    def tearDown(self):
        shutil.rmtree(self.storage_path)
        os.unlink(self.path)

    def get_cluster_storage(self):
        storage = ClusterStorage(self.storage_path)
        return storage

    def test_dump_cluster(self):
        """
        Dump cluster to json
        """
        storage = self.get_cluster_storage()

        configurator = Configurator(Configuration().get_config(self.path))
        nodes = {"compute": 2, "frontend": 1}
        cluster = Cluster("mycluster", "cluster_name", "hobbes", MagicMock(),
                          MagicMock(), nodes, configurator)
        instance_id = "test-id"
        ip_public = "127.0.0.1"
        ip_private = "127.0.0.2"
        for node in cluster.get_all_nodes():
            node.instance_id = instance_id
            node.ip_public = ip_public
            node.ip_private = ip_private

        storage.dump_cluster(cluster)

        dump = os.path.join(self.storage_path, "cluster_name.json")

        f = open(dump, "r")
        content = f.read()

        expected = """
            {"compute_nodes": 2, "nodes":
                [{"instance_id": "test-id", "ip_public": "127.0.0.1",
                    "type": "compute", "name": "compute001",
                    "ip_private": "127.0.0.2"},
                 {"instance_id": "test-id", "ip_public": "127.0.0.1",
                    "type": "compute", "name": "compute002",
                    "ip_private": "127.0.0.2"},
                 {"instance_id": "test-id", "ip_public": "127.0.0.1",
                    "type": "frontend", "name": "frontend001",
                    "ip_private": "127.0.0.2"}],
                "frontend_nodes": 1, "name": "cluster_name",
                "template": "mycluster"}"""

        self.assertEqual(json.loads(content), json.loads(expected))

        os.unlink(dump)

    def test_load_cluster(self):
        content = """
            {"compute_nodes": 2, "nodes":
                [{"instance_id": "test-id", "ip_public": "127.0.0.1",
                    "type": "compute", "name": "compute001",
                    "ip_private": "127.0.0.2"},
                 {"instance_id": "test-id", "ip_public": "127.0.0.1",
                    "type": "compute", "name": "compute002",
                    "ip_private": "127.0.0.2"},
                 {"instance_id": "test-id", "ip_public": "127.0.0.1",
                    "type": "frontend", "name": "frontend001",
                    "ip_private": "127.0.0.2"}],
                "frontend_nodes": 1, "name": "cluster_name",
                "template": "mycluster"}"""
        content = " ".join(content.split())

        path = os.path.join(self.storage_path, "cluster_name.json")
        f = open(path, 'w')
        f.write(content)
        f.close()

        storage = self.get_cluster_storage()
        cluster = storage.load_cluster("cluster_name")

        self.assertEqual(cluster['name'], "cluster_name")
        self.assertEqual(cluster['template'], "mycluster")

        self.assertEqual(cluster['compute_nodes'], 2)
        self.assertEqual(cluster['frontend_nodes'], 1)

        self.assertEqual(len(cluster['nodes']), 3)

        for i in range(2):
            self.assertEqual(cluster['nodes'][i]['instance_id'], "test-id")
            self.assertEqual(cluster['nodes'][i]['ip_public'], "127.0.0.1")
            self.assertEqual(cluster['nodes'][i]['ip_private'], "127.0.0.2")

        self.assertEqual(cluster['nodes'][0]['name'], "compute001")
        self.assertEqual(cluster['nodes'][1]['name'], "compute002")
        self.assertEqual(cluster['nodes'][2]['name'], "frontend001")

        self.assertEqual(cluster['nodes'][0]['type'], "compute")
        self.assertEqual(cluster['nodes'][1]['type'], "compute")
        self.assertEqual(cluster['nodes'][2]['type'], "frontend")

    def test_delete_cluster(self):
        """
        Delete cluster storage file
        """
        storage = self.get_cluster_storage()

        path = os.path.join(self.storage_path, "cluster_name.json")
        f = open(path, 'w')
        f.write("test")
        f.close()

        storage.delete_cluster("cluster_name")

        self.assertFalse(os.path.exists(path))

        if os.path.exists(path):
            os.unlink(path)

    def test_get_stored_clusters(self):
        """
        Reading all stored clusters (json)
        """
        storage = self.get_cluster_storage()

        clusters = []
        for i in range(10):
            clusters.append("cluster0%i" % i)

        for cluster in clusters:
            file_name = cluster + ".json"
            path = os.path.join(self.storage_path, file_name)
            f = open(path, 'w')
            f.close()

        stored_clusters = storage.get_stored_clusters()

        self.assertEqual(len(clusters), len(stored_clusters))
        for cluster in stored_clusters:
            self.assertTrue(cluster in clusters)

        # directory cleanup
        for cluster in clusters:
            path = os.path.join(self.storage_path, cluster + '.json')
            os.unlink(path)

    def test_get_json_path(self):
        """
        Storage json path getter
        """
        storage = self.get_cluster_storage()

        path = storage._get_json_path("cluster_name")
        path_valid = os.path.join(self.storage_path, "cluster_name.json")

        self.assertEqual(path, path_valid)

