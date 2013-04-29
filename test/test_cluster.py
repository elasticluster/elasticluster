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

import unittest
from test import config_cluster_name, config_cloud_ec2_url,\
    config_cloud_ec2_region, config_cloud_ec2_access_key,\
    config_cloud_ec2_secret_key, config_login_user_key_private,\
    config_login_image_user, config_login_image_user_sudo,\
    config_login_image_sudo, config_setup_playbook_path, config_cloud_name,\
    config_setup_frontend_groups, config_setup_compute_groups
from elasticluster.providers.ec2_boto import BotoCloudProvider
from elasticluster.providers.ansible_provider import AnsibleSetupProvider
from elasticluster.conf import Configurator
from elasticluster.cluster import Cluster, Node


from mock import Mock, MagicMock


class TestCluster(unittest.TestCase):

    def test_init(self):
        cloud_provider = BotoCloudProvider(config_cloud_ec2_url, config_cloud_ec2_region, config_cloud_ec2_access_key, config_cloud_ec2_secret_key)
        setup_provider = AnsibleSetupProvider(config_login_user_key_private, config_login_image_user, config_login_image_user_sudo, config_login_image_sudo, config_setup_playbook_path, config_setup_frontend_groups, config_setup_compute_groups)
        
        frontend_amount = 1
        compute_amount = 2
        
        cluster = Cluster(config_cluster_name, config_cloud_name, cloud_provider, setup_provider, frontend_amount, compute_amount, Configurator())
        
        assert len(cluster.frontend_nodes) == frontend_amount
        assert len(cluster.compute_nodes) == compute_amount
        
        for node in cluster.frontend_nodes:
            assert node.type == Node.frontend_type
        
        for node in cluster.compute_nodes:
            assert node.type == Node.compute_type
        
        

    def test_add_node(self):
        cloud_provider = BotoCloudProvider(config_cloud_ec2_url, config_cloud_ec2_region, config_cloud_ec2_access_key, config_cloud_ec2_secret_key)
        setup_provider = AnsibleSetupProvider(config_login_user_key_private, config_login_image_user, config_login_image_user_sudo, config_login_image_sudo, config_setup_playbook_path, config_setup_frontend_groups, config_setup_compute_groups)
        
        cluster = Cluster(config_cluster_name, config_cloud_name, cloud_provider, setup_provider, 1, 2, Configurator())
        
        frontend_amount = len(cluster.frontend_nodes)
        frontend_node = cluster.add_node(Node.frontend_type)
        
        assert frontend_amount == (len(cluster.frontend_nodes) - 1)
        assert frontend_node == cluster.frontend_nodes[-1]
        assert frontend_node.type == Node.frontend_type
        
        compute_amount = len(cluster.compute_nodes)
        compute_node = cluster.add_node(Node.compute_type)
        
        assert compute_amount == (len(cluster.compute_nodes) - 1)
        assert compute_node == cluster.compute_nodes[-1]
        assert compute_node.type == Node.compute_type


    def test_remove_node(self):
        cloud_provider = BotoCloudProvider(config_cloud_ec2_url, config_cloud_ec2_region, config_cloud_ec2_access_key, config_cloud_ec2_secret_key)
        setup_provider = AnsibleSetupProvider(config_login_user_key_private, config_login_image_user, config_login_image_user_sudo, config_login_image_sudo, config_setup_playbook_path, config_setup_frontend_groups, config_setup_compute_groups)
        
        cluster = Cluster(config_cluster_name, config_cloud_name, cloud_provider, setup_provider, 1, 2, Configurator())
        
        frontend_amount = len(cluster.frontend_nodes)
        frontend_node = cluster.frontend_nodes[-1]
        frontend_node_name = frontend_node.name
        cluster.remove_node(frontend_node)
        
        assert frontend_amount == (len(cluster.frontend_nodes) + 1)
        for node in cluster.frontend_nodes:
            assert node.name != frontend_node_name

        compute_amount = len(cluster.compute_nodes)
        compute_node = cluster.compute_nodes[-1]
        compute_node_name = compute_node.name
        cluster.remove_node(compute_node)
        
        assert compute_amount == (len(cluster.compute_nodes) + 1)
        for node in cluster.compute_nodes:
            assert node.name != compute_node_name
    
    
    def test_start(self):
        cloud_provider = MagicMock()
        cloud_provider.start_instance.return_value = u'test-id'
        cloud_provider.get_ips.return_value = ('127.0.0.1', '127.0.0.1')
        running_states = [True, True, True, True, True, False, False, False, False, False]
        def side_effect_is_instance_running(id):
            return running_states.pop()
        cloud_provider.is_instance_running.side_effect = side_effect_is_instance_running
        setup_provider = MagicMock()
        setup_provider.setup_cluster.return_value = True
        
        cluster = Cluster(config_cluster_name, config_cloud_name, cloud_provider, setup_provider, 1, 2, Configurator())
        cluster._storage = MagicMock()

        cluster.start()
        
        cluster._storage.dump_cluster.assert_called_once_with(cluster)

        for node in cluster.frontend_nodes + cluster.compute_nodes:
            assert node.instance_id == u'test-id'
            assert node.ip_public == '127.0.0.1'
            assert node.ip_private == '127.0.0.1'
            
    
    def test_stop(self):
        cloud_provider = MagicMock()
        cloud_provider.start_instance.return_value = u'test-id'
        cloud_provider.get_ips.return_value = ('127.0.0.1', '127.0.0.1')
        running_states = [True, True, True, True, True, False, False, False, False, False]
        def side_effect_is_instance_running(id):
            return running_states.pop()
        cloud_provider.is_instance_running.side_effect = side_effect_is_instance_running
        setup_provider = MagicMock()
        
        cluster = Cluster(config_cluster_name, config_cloud_name, cloud_provider, setup_provider, 1, 2, Configurator())
        
        
        for node in cluster.frontend_nodes + cluster.compute_nodes:
            node.instance_id = u'test-id'
        
        cluster._storage = MagicMock()
            
        cluster.stop()
        

        cloud_provider.stop_instance.assert_called_with(u'test-id')
        cluster._storage.delete_cluster.assert_called_once_with(cluster.name)

    
    def test_load_from_storage(self):
        cloud_provider = MagicMock()
        cloud_provider.is_instance_running.return_value = True
        cloud_provider.get_ips.return_value = ('127.0.0.1', '127.0.0.1')
        setup_provider = MagicMock()
        storage = MagicMock()
        
        cluster = Cluster(config_cluster_name, config_cloud_name, cloud_provider, setup_provider, 1, 2, Configurator())
        cluster._storage = storage
        cluster.load_from_storage()
        
        storage.load_cluster.assert_called_once_with(cluster)

    
    def setup(self):
        cloud_provider = MagicMock()
        setup_provider = MagicMock()
        setup_provider.setup_cluster.return_value = True
        
        cluster = Cluster(config_cluster_name, config_cloud_name, cloud_provider, setup_provider, 1, 2, Configurator())
        
        cluster.setup()
        
        setup_provider.setup_cluster.assert_called_once_with(cluster)
        
        
        
        
        
        
        
        
        
        
