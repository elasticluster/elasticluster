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
from StringIO import StringIO
from mock import Mock
from mock import patch
from mock import MagicMock
from mock import mock_open
import ConfigParser

from elasticluster.conf import Configuration

"""
This section mocks the configuration file and defines the variables to mock it with.
We need this actually to test the classes related to configuration.
"""

config_storage_path = "~/.elasticluster/storage"

config_cloud_name = "test"
config_cloud_provider = "ec2_boto"
config_cloud_ec2_url = "http://130.60.24.4:8773/services/Cloud"
config_cloud_ec2_access_key = "test"
config_cloud_ec2_secret_key = "test"
config_cloud_ec2_region = "nova"

config_setup_name = "test"
config_setup_provider = "ansible"
config_setup_playbook_path = "~/.elasticluster/playbook"

config_login_name = "test"
config_login_image_user = "test"
config_login_image_user_sudo = "test"
config_login_image_sudo = "True"
config_login_user_key_name = "test"
config_login_user_key_private = "~/test.prv"
config_login_user_key_public = "~/test.pub"

config_cluster_name = "test"
config_cluster_cloud = config_cloud_name
config_cluster_setup_provider = config_setup_name
config_cluster_frontend = "1"
config_cluster_compute = "2"
config_cluster_login = "test"

config_frontend_image = "Ubuntu"
config_frontend_setup_classes = "slurm, ganglia"
config_frontend_security_group = "all"
config_frontend_flavor = "m1.tiny"
config_frontend_image_userdata = "none"

config_compute_image = "Ubuntu"
config_compute_setup_classes = "slurm"
config_compute_security_group = "all"
config_compute_flavor = "m1.tiny"
config_compute_image_userdata = "none"

config_section_cloud = "cloud/" + config_cloud_name
config_section_cluster = "cluster/" + config_cluster_name
config_section_frontend = "cluster/" + config_cluster_name + "/frontend"
config_section_compute = "cluster/"+ config_cluster_name +"/compute"
config_section_login = "login/" + config_login_name
config_section_setup = "setup/" + config_setup_name


def setup():
    config = Mock()
    def side_effect_has_section(name):
        sections = [config_section_cloud, config_section_cluster, config_section_compute, config_section_frontend, config_section_login, config_section_setup]
        if name in sections:
            return True
        else:
            return False
    
    def side_effect_items(name):
        content = {
                   config_section_cloud :
                   [("provider", config_cloud_provider), ("ec2_url", config_cloud_ec2_url),("ec2_access_key", config_cloud_ec2_access_key), ("ec2_secret_key", config_cloud_ec2_secret_key), ("ec2_region", config_cloud_ec2_region)],
                   
                   config_section_setup:
                   [("provider", config_setup_provider), ("playbook_path", config_setup_playbook_path)],
                   
                   config_section_login:
                   [("image_user", config_login_image_user), ("image_user_sudo", config_login_image_user_sudo), ("image_sudo", config_login_image_sudo), ("user_key_name", config_login_user_key_name), ("user_key_private", config_login_user_key_private), ("user_key_public", config_login_user_key_public)],
                   
                   config_section_cluster:
                   [("cloud", config_cluster_cloud), ("setup_provider", config_cluster_setup_provider), ("frontend", config_cluster_frontend), ("compute", config_cluster_compute), ("login", config_cluster_login)],
                   
                   config_section_frontend:
                   [("image", config_frontend_image), ("setup_classes", config_frontend_setup_classes), ("security_group", config_frontend_security_group), ("flavor", config_frontend_flavor), ("image_userdata", config_frontend_image_userdata)],
                   
                   config_section_compute:
                   [("image", config_compute_image), ("setup_classes", config_compute_setup_classes), ("security_group", config_compute_security_group), ("flavor", config_compute_flavor), ("image_userdata", config_compute_image_userdata)]
                   }
        if name in content:
            return content[name]
        else:
            raise ConfigParser.NoSectionError()
    
    config.has_section.side_effect = side_effect_has_section
    config.items.side_effect = side_effect_items
    config.read.return_vale = True
    
    Configuration.Instance()._config = config
    Configuration.Instance().cluster_name = config_cluster_name
    Configuration.Instance().storage_path = config_storage_path
    
    
