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


# Config variables to test with
config_cloud_name = "test"
config_cloud_provider = "ec2_boto"
config_cloud_ec2_url = "http://130.60.24.4:8773/services/Cloud"
config_cloud_ec2_access_key = "test"
config_cloud_ec2_secret_key = "test"
config_cloud_ec2_region = "nova"

config_setup_name = "test"
config_setup_provider = "ansible"
config_setup_playbook_path = "~/.elasticluster/playbook"
config_setup_frontend_groups = "slurm_master"
config_setup_compute_groups = "slurm_clients"

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

config_frontend_image = "ami-00000"
config_frontend_security_group = "all"
config_frontend_flavor = "m1.tiny"
config_frontend_image_userdata = "none"

config_compute_image = "Ubuntu"
config_compute_security_group = "all"
config_compute_flavor = "m1.tiny"
config_compute_image_userdata = "none"


def setup():
    pass