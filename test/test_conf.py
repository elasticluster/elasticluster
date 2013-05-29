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

import copy
import os
import tempfile
import unittest

from voluptuous.voluptuous import MultipleInvalid


from elasticluster.conf import ConfigReader, ConfigValidator


class TestConfigValidator(unittest.TestCase):

    def setUp(self):
        # create a file to pass the checks
        file, path = tempfile.mkstemp()
        self.path = path
        self.config = {
            "mycluster" : {
                "setup" : {
                    "provider" : "ansible",
                    "playbook_path" : "%(ansible_pb_dir)s/site.yml",
                    "frontend_groups" : "slurm_master",
                    "compute_groups" : "slurm_clients",
                    },
                "cloud" : {
                    "provider" : "ec2_boto",
                    "ec2_url" : "http://cloud.gc3.uzh.ch:8773/services/Cloud",
                    "ec2_access_key" : "***fill in your data here***",
                    "ec2_secret_key" : "***fill in your data here***",
                    "ec2_region" : "nova",
                    },
                "login" : {
                    "image_user" : "gc3-user",
                    "image_user_sudo" : "root",
                    "image_sudo" : True,
                    "user_key_name" : "***name of SSH keypair on Hobbes***",
                    "user_key_private" : self.path,
                    "user_key_public" : self.path,
                    },
                "cluster" : {
                    "cloud" : "hobbes",
                    "login" : "gc3-user",
                    "setup_provider" : "my-slurm-cluster",
                    "frontend_nodes" : "1",
                    "compute_nodes" : "2",
                    },
                "nodes": {
                    "frontend" : {
                        "security_group" : "default",
                        "flavor" : "m1.tiny",
                        "image_id" : "ami-00000048",
                        },
                    "compute" : {
                        "security_group" : "default",
                        "flavor" : "m1.large",
                        "image_id" : "ami-00000048",
                        }
                }
            }
        }

    def tearDown(self):
        os.unlink(self.path)





    def test_valid_config(self):
        '''
        Valid configuration
        '''
        validator = ConfigValidator(self.config)
        validator.validate()

    def test_invalid_config(self):
        '''
        Invalid configuration
        '''
        # check wrong file path
        config = copy.deepcopy(self.config)
        config["mycluster"]["login"]["user_key_public"] = "/tmp/elastic-test"
        validator = ConfigValidator(config)
        with self.assertRaises(MultipleInvalid):
            validator.validate()

        # check wrong url
        config = copy.deepcopy(config)
        config["mycluster"]["setup"]["ec2_host"] = "www.elasticluster"
        validator = ConfigValidator(config)
        with self.assertRaises(MultipleInvalid):
            validator.validate()

        # check all mandatory properties
        optional = ["frontend_groups", "compute_groups", "frontend_nodes",
                    "compute_nodes", "security_group", "flavor", "image_id",
                    "playbook_path", "frontend", "compute"]
        config = copy.deepcopy(config)
        for cluster, sections in config.iteritems():
            for section, properties in sections.iteritems():
                for property, value in properties.iteritems():
                    if property not in optional:
                        config_tmp = copy.deepcopy(config)
                        del config_tmp[cluster][section][property]
                        validator = ConfigValidator(config_tmp)
                        with self.assertRaises(MultipleInvalid):
                            validator.validate()

        # check all node properties
        mandatory = ["flavor", "image_id", "security_group"]
        config = copy.deepcopy(config)
        for node, properties in config["mycluster"]["nodes"].iteritems():
            for property in properties.iterkeys():
                if property in mandatory:
                    config_tmp = copy.deepcopy(config)
                    del config_tmp["mycluster"]["nodes"][node][property]
                    validator = ConfigValidator(config_tmp)
                    with self.assertRaises(MultipleInvalid):
                        validator.validate()









class TestConfigReader(unittest.TestCase):

    def _check_read_config(self, config):
        (conf_file, conf_path) = tempfile.mkstemp()
        conf_file = os.fdopen(conf_file, 'w+')
        conf_file.write(config)
        conf_file.close()

        result = None
        try:
            config_reader = ConfigReader(conf_path)
            result =  config_reader.read_config()
            os.unlink(conf_path)
        except:
            os.unlink(conf_path)
            raise

        return result

    def test_read_valid_config(self):
        '''
        Read valid config into dictionary
        '''

        config = """
            [cloud/hobbes]
            provider=ec2_boto
            ec2_url=http://hobbes.gc3.uzh.ch:8773/services/Cloud
            ec2_access_key=****REPLACE WITH YOUR ACCESS ID****
            ec2_secret_key=****REPLACE WITH YOUR SECRET KEY****
            ec2_region=nova

            [cloud/amazon-us-east-1]
            provider=ec2_boto
            ec2_url=https://ec2.us-east-1.amazonaws.com
            ec2_access_key=****REPLACE WITH YOUR ACCESS ID****
            ec2_secret_key=****REPLACE WITH YOUR SECRET KEY****
            ec2_region=us-east-1

            [login/ubuntu]
            image_user=ubuntu
            image_user_sudo=root
            image_sudo=True
            user_key_name=elasticluster
            user_key_private=~/.ssh/id_rsa
            user_key_public=~/.ssh/id_rsa.pub

            [login/gc3-user]
            image_user=gc3-user
            image_user_sudo=root
            image_sudo=True
            user_key_name=elasticluster
            user_key_private=~/.ssh/id_dsa.cloud
            user_key_public=~/.ssh/id_dsa.cloud.pub

            [setup/ansible-slurm]
            provider=ansible
            frontend_groups=slurm_master
            compute_groups=slurm_clients

            [setup/ansible-gridengine]
            provider=ansible
            frontend_groups=gridengine_master
            compute_groups=gridengine_clients

            [setup/ansible-pbs]
            provider=ansible
            frontend_groups=pbs_master,maui_master
            compute_groups=pbs_clients

            [setup/ansible_matlab]
            provider=ansible
            frontend_groups=mdce_master,mdce_worker,ganglia_monitor,ganglia_master
            worker_groups=mdce_worker,ganglia_monitor

            [cluster/slurm]
            cloud=hobbes
            login=gc3-user
            setup_provider=ansible-slurm
            security_group=default
            image_id=ami-00000048
            flavor=m1.small
            frontend_nodes=1
            compute_nodes=2
            frontend_class=frontend

            [cluster/torque]
            cloud=hobbes
            frontend_nodes=1
            compute_nodes=2
            frontend_class=frontend
            security_group=default
            # CentOS image
            image_id=ami-0000004f
            flavor=m1.small
            login=gc3-user
            setup_provider=ansible-pbs

            [cluster/aws-slurm]
            cloud=amazon-us-east-1
            login=ubuntu
            setup_provider=ansible-slurm
            security_group=default
            # ubuntu image
            image_id=ami-90a21cf9
            flavor=m1.small
            frontend=1
            compute=2

            [cluster/matlab]
            cloud=hobbes
            login=gc3-user
            setup_provider=ansible_matlab
            security_group=default
            image_id=ami-00000099
            flavor=m1.medium
            frontend_nodes=1
            worker_nodes=10
            image_userdata=
            ssh_to=frontend

            [cluster/slurm/frontend]
            flavor=bigdisk
            """
        cfg = self._check_read_config(config)

        # check all clusters are there
        self.assertTrue(("matlab" in cfg and "aws-slurm" in cfg
                         and "torque" in cfg and "slurm" in cfg))

        # check for nodes
        self.assertTrue("frontend" in cfg["matlab"]["nodes"])
        self.assertTrue("worker" in cfg["matlab"]["nodes"])

        # check one property in each category
        self.assertTrue(cfg["matlab"]["cluster"]["security_group"] ==
                        "default")
        self.assertTrue(cfg["matlab"]["login"]["image_user"] == "gc3-user")
        self.assertTrue(cfg["matlab"]["setup"]["provider"] == "ansible")
        self.assertTrue(cfg["matlab"]["cloud"]["ec2_region"] == "nova")

        # check frontend overwrite in slurm cluster
        self.assertTrue(cfg["slurm"]["nodes"]["frontend"]["flavor"] ==
                        "bigdisk")



    def test_read_missing_section(self):
        '''
        Read config with missing section
        '''
        config = """
            [login/gc3-user]
            image_user=gc3-user
            image_user_sudo=root
            image_sudo=True
            user_key_name=elasticluster
            user_key_private=~/.ssh/id_dsa.cloud
            user_key_public=~/.ssh/id_dsa.cloud.pub

            [setup/ansible-slurm]
            provider=ansible
            frontend_groups=slurm_master
            compute_groups=slurm_clients

            [cluster/slurm]
            cloud=hobbes
            login=gc3-user
            setup_provider=ansible-slurm
            security_group=default
            # Ubuntu image
            image_id=ami-00000048
            flavor=m1.small
            frontend_nodes=1
            compute_nodes=2
            frontend_class=frontend
            """
        with self.assertRaises(MultipleInvalid):
            cfg = self._check_read_config(config)

    def test_read_section_linking(self):
        '''
        Read config with wrong section links
        '''
        config = """
            [cloud/hobbes]
            provider=ec2_boto
            ec2_url=http://hobbes.gc3.uzh.ch:8773/services/Cloud
            ec2_access_key=****REPLACE WITH YOUR ACCESS ID****
            ec2_secret_key=****REPLACE WITH YOUR SECRET KEY****
            ec2_region=nova

            [login/gc3-user]
            image_user=gc3-user
            image_user_sudo=root
            image_sudo=True
            user_key_name=elasticluster
            user_key_private=~/.ssh/id_dsa.cloud
            user_key_public=~/.ssh/id_dsa.cloud.pub

            [setup/ansible-slurm]
            provider=ansible
            frontend_groups=slurm_master
            compute_groups=slurm_clients

            [cluster/slurm]
            cloud=hobbes-new
            login=gc3-user
            setup_provider=ansible-slurm
            security_group=default
            # Ubuntu image
            image_id=ami-00000048
            flavor=m1.small
            frontend_nodes=1
            compute_nodes=2
            frontend_class=frontend
            """
        with self.assertRaises(MultipleInvalid):
            cfg = self._check_read_config(config)











