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
import os

from elasticluster.conf import Configuration, Configurator
from elasticluster.cluster import Node, Cluster, ClusterStorage
from elasticluster.providers import AbstractCloudProvider, AbstractSetupProvider
from elasticluster.providers.cloud_providers import BotoCloudProvider

from test import config_cloud_ec2_url, config_cloud_provider,\
    config_cloud_ec2_access_key, config_cloud_ec2_secret_key,\
    config_cloud_ec2_region, config_setup_provider, config_setup_playbook_path,\
    config_cloud_name, config_cluster_name, config_cluster_cloud,\
    config_cluster_frontend, config_cluster_compute,\
    config_login_user_key_public, config_login_user_key_name,\
    config_login_image_user, config_frontend_security_group,\
    config_frontend_image, config_frontend_image_userdata,\
    config_frontend_flavor,\
    config_compute_security_group, config_compute_image,\
    config_compute_image_userdata, config_compute_flavor,\
    config_storage_path, config_setup_name,\
    config_cluster_setup_provider, config_cluster_login, config_login_name,\
    config_login_image_user_sudo, config_login_image_sudo,\
    config_login_user_key_private, config_setup_frontend_groups,\
    config_setup_compute_groups
    

class TestConfigurator(unittest.TestCase):


    def test_create_cloud_provider(self):
        configurator = Configurator()
        cloud_provider = configurator.create_cloud_provider(config_cloud_name)
        
        assert cloud_provider
        assert isinstance(cloud_provider, AbstractCloudProvider)
        assert cloud_provider._url == config_cloud_ec2_url
        assert cloud_provider._region_name == config_cloud_ec2_region
        assert cloud_provider._access_key == config_cloud_ec2_access_key
        assert cloud_provider._secret_key == config_cloud_ec2_secret_key
        
    def test_create_cluster(self):
        configurator = Configurator()
        cluster = configurator.create_cluster(config_cluster_name)
        
        assert cluster
        assert isinstance(cluster, Cluster)
        assert cluster.name == config_cluster_name
        assert cluster._cloud == config_cluster_cloud
        assert isinstance(cluster._cloud_provider, AbstractCloudProvider)
        assert cluster._frontend == int(config_cluster_frontend)
        assert cluster._compute == int(config_cluster_compute)
        assert isinstance(cluster._setup_provider, AbstractSetupProvider)


    def test_create_node(self):
        configurator = Configurator()
        cloud_provider = BotoCloudProvider(config_cloud_ec2_url, config_cloud_ec2_region, config_cloud_ec2_access_key, config_cloud_ec2_secret_key)
        node_frontend = configurator.create_node(config_cluster_name, Node.frontend_type, cloud_provider, "node001")
        assert node_frontend
        assert isinstance(node_frontend, Node)
        assert node_frontend.name == "node001"
        assert node_frontend.type == Node.frontend_type
        assert node_frontend._cloud_provider == cloud_provider
        assert node_frontend.user_key_public == os.path.expanduser(config_login_user_key_public)
        assert node_frontend.user_key_name == os.path.expanduser(config_login_user_key_name)
        assert node_frontend.image_user == config_login_image_user
        assert node_frontend.security_group == config_frontend_security_group
        assert node_frontend.image == config_frontend_image
        assert node_frontend.image_userdata == config_frontend_image_userdata
        assert node_frontend.flavor == config_frontend_flavor
        
        node_compute = configurator.create_node(config_cluster_name, Node.compute_type, cloud_provider, "node001")
        assert node_compute
        assert isinstance(node_compute, Node)
        assert node_compute.name == "node001"
        assert node_compute.type == Node.compute_type
        assert node_compute._cloud_provider == cloud_provider
        assert node_compute.user_key_public == os.path.expanduser(config_login_user_key_public)
        assert node_compute.user_key_name == config_login_user_key_name
        assert node_compute.image_user == config_login_image_user
        assert node_compute.security_group == config_compute_security_group
        assert node_compute.image == config_compute_image
        assert node_compute.image_userdata == config_compute_image_userdata
        assert node_compute.flavor == config_compute_flavor
        
    def test_create_cluster_storage(self):
        configurator = Configurator()
        storage = configurator.create_cluster_storage()
        assert storage
        assert isinstance(storage, ClusterStorage)
        assert storage._storage_dir == config_storage_path
        
    def test_create_setup_provider(self):
        configurator = Configurator()
        setup_provider = configurator.create_setup_provider(config_setup_name, config_cluster_name)
        
        assert setup_provider
        assert isinstance(setup_provider, AbstractSetupProvider)
        

class TestConfiguration(unittest.TestCase):
    
    def test_read_cloud_section(self):        
        cloud = Configuration.Instance().read_cloud_section(config_cloud_name)
        assert cloud["provider"] == config_cloud_provider
        assert cloud["ec2_url"] == config_cloud_ec2_url
        assert cloud["ec2_access_key"] == config_cloud_ec2_access_key
        assert cloud["ec2_secret_key"] == config_cloud_ec2_secret_key
        assert cloud["ec2_region"] == config_cloud_ec2_region
        
        
    def test_read_cluster_section(self):
        cluster = Configuration.Instance().read_cluster_section(config_cluster_name)
        assert cluster["cloud"] == config_cluster_cloud
        assert cluster["setup_provider"] == config_cluster_setup_provider
        assert cluster["frontend"] == config_cluster_frontend
        assert cluster["compute"] == config_cluster_compute
        assert cluster["login"] == config_cluster_login
        
        
    def test_read_node_section(self):
        node_frontend = Configuration.Instance().read_node_section(config_cluster_name, Node.frontend_type)
        assert node_frontend["security_group"] == config_frontend_security_group
        assert node_frontend["image"] == config_frontend_image
        assert node_frontend["flavor"] == config_frontend_flavor
        
        node_compute = Configuration.Instance().read_node_section(config_cluster_name, Node.compute_type)
        assert node_compute["security_group"] == config_compute_security_group
        assert node_compute["image"] == config_compute_image
        assert node_compute["flavor"] == config_compute_flavor
        
    
    def test_read_login_section(self):
        login = Configuration.Instance().read_login_section(config_login_name)
        assert login["image_user"] == config_login_image_user
        assert login["image_user_sudo"] == config_login_image_user_sudo
        assert login["image_sudo"] == config_login_image_sudo
        assert login["user_key_name"] == config_login_user_key_name
        assert login["user_key_private"] == os.path.expanduser(config_login_user_key_private)
        assert login["user_key_public"] == os.path.expanduser(config_login_user_key_public)
        
    def test_read_setup_section(self):
        setup = Configuration.Instance().read_setup_section(config_setup_name, config_cluster_name)
        assert setup["provider"] == config_setup_provider
        assert setup["playbook_path"] == os.path.expanduser(os.path.expandvars(config_setup_playbook_path))
        assert setup["frontend_groups"] == config_setup_frontend_groups
        assert setup["compute_groups"] == config_setup_compute_groups
        
        
        