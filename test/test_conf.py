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
import shutil
import tempfile
import unittest

from voluptuous import Invalid

from elasticluster.conf import ConfigReader, ConfigValidator, Configurator
from elasticluster.cluster import Node
from elasticluster.exceptions import ClusterNotFound
from elasticluster.providers.ansible_provider import AnsibleSetupProvider
from elasticluster.providers.ec2_boto import BotoCloudProvider


class Configuration(object):

    def get_config(self, path):
        config = {
            "mycluster": {
                "setup": {
                    "provider": "ansible",
                    "playbook_path": "%(ansible_pb_dir)s/site.yml",
                    "frontend_groups": "slurm_master",
                    "compute_groups": "slurm_clients",
                    },
                "cloud": {
                    "provider": "ec2_boto",
                    "ec2_url": "http://cloud.gc3.uzh.ch:8773/services/Cloud",
                    "ec2_access_key": "***fill in your data here***",
                    "ec2_secret_key": "***fill in your data here***",
                    "ec2_region": "nova",
                    },
                "login": {
                    "image_user": "gc3-user",
                    "image_user_sudo": "root",
                    "image_sudo": True,
                    "user_key_name": "***name of SSH keypair on Hobbes***",
                    "user_key_private": path,
                    "user_key_public": path,
                    },
                "cluster": {
                    "cloud": "hobbes",
                    "login": "gc3-user",
                    "setup_provider": "my-slurm-cluster",
                    "frontend_nodes": "1",
                    "compute_nodes": "2",
                    },
                "nodes": {
                    "frontend": {
                        "security_group": "default",
                        "flavor": "m1.tiny",
                        "image_id": "ami-00000048",
                        },
                    "compute": {
                        "security_group": "default",
                        "flavor": "m1.large",
                        "image_id": "ami-00000048",
                        }
                    }
                }
            }

        return config


class TestConfigurator(unittest.TestCase):

    def setUp(self):
        file, path = tempfile.mkstemp()
        self.path = path
        self.config = Configuration().get_config(self.path)


    def tearDown(self):
        os.unlink(self.path)

    def test_create_cloud_provider(self):
        configurator = Configurator(self.config)
        provider = configurator.create_cloud_provider("mycluster")

        url = self.config['mycluster']['cloud']['ec2_url']
        self.assertEqual(provider._url, url)

        access_key = self.config['mycluster']['cloud']['ec2_access_key']
        self.assertEqual(provider._access_key, access_key)

        secret_key = self.config['mycluster']['cloud']['ec2_secret_key']
        self.assertEqual(provider._secret_key, secret_key)

        region = self.config['mycluster']['cloud']['ec2_region']
        self.assertEqual(provider._region_name, region)

    def test_create_cluster(self):
        configurator = Configurator(self.config)
        cluster = configurator.create_cluster("mycluster")

        self.assertEqual(cluster.template, "mycluster")
        self.assertEqual(cluster.name, "mycluster")

        cloud = self.config['mycluster']['cluster']['cloud']
        self.assertEqual(cluster._cloud, cloud)

        self.assertTrue(type(cluster._cloud_provider) is BotoCloudProvider)
        self.assertTrue(type(cluster._setup_provider) is AnsibleSetupProvider)

        self.assertTrue("compute" in cluster.nodes)
        self.assertTrue("frontend" in cluster.nodes)

        self.assertTrue(len(cluster.nodes["compute"]) == 2)
        self.assertTrue(len(cluster.nodes["frontend"]) == 1)


    def test_load_cluster(self):
        # test without storage file
        storage_path = tempfile.mkdtemp()
        configurator = Configurator(self.config, storage_path=storage_path)
        self.assertRaises(ClusterNotFound,
                          configurator.load_cluster, "mycluster")

        shutil.rmtree(storage_path)

        # TODO: test with storage file; the problem is to give a fixed
        # directory as a parameter to configurator, since it should work
        # anywhere



    def test_create_node(self):
        configurator = Configurator(self.config)
        node = configurator.create_node("mycluster", "compute", None,
                                            "test-1")

        self.assertTrue(type(node) is Node)
        self.assertEqual(node.name, "test-1")
        self.assertEqual(node.type, "compute")
        self.assertEqual(node._cloud_provider, None)

        pub_key = self.config['mycluster']['login']['user_key_public']
        self.assertEqual(node.user_key_public, pub_key)

        prv_key = self.config['mycluster']['login']['user_key_private']
        self.assertEqual(node.user_key_private, prv_key)

        key_name = self.config['mycluster']['login']['user_key_name']
        self.assertEqual(node.user_key_name, key_name)

        usr = self.config['mycluster']['login']['image_user']
        self.assertEqual(node.image_user, usr)

        sec_group = self.config['mycluster']['nodes']['compute'] \
                                                        ['security_group']
        self.assertEqual(node.security_group, sec_group)

        image = self.config['mycluster']['nodes']['compute']['image_id']
        self.assertEqual(node.image, image)

        flavor = self.config['mycluster']['nodes']['compute']['flavor']
        self.assertEqual(node.flavor, flavor)

        self.assertEqual(node.image_userdata, '')



    def test_create_cluster_storage(self):
        # default storage path
        configurator = Configurator(self.config)
        storage = configurator.create_cluster_storage()
        default_storage = configurator.general_conf['storage']
        self.assertEqual(storage._storage_dir, default_storage)

        # custom storage path
        path = "/tmp"
        configurator = Configurator(self.config, storage_path=path)
        storage = configurator.create_cluster_storage()
        self.assertEqual(storage._storage_dir, path)

    def test_create_setup_provider(self):
        configurator = Configurator(self.config)
        provider = configurator.create_setup_provider("mycluster")

        self.assertTrue(type(provider) is AnsibleSetupProvider)

        prv_key = self.config['mycluster']['login']['user_key_private']
        self.assertEqual(provider._private_key_file, prv_key)

        usr = self.config['mycluster']['login']['image_user']
        self.assertEqual(provider._remote_user, usr)

        usr_sudo = self.config['mycluster']['login']['image_user_sudo']
        self.assertEqual(provider._sudo_user, usr_sudo)

        sudo = self.config['mycluster']['login']['image_sudo']
        self.assertEqual(provider._sudo, sudo)

        pb = self.config['mycluster']['setup']['playbook_path']
        self.assertEqual(provider._playbook_path, pb)



class TestConfigValidator(unittest.TestCase):

    def setUp(self):
        file, path = tempfile.mkstemp()
        self.path = path
        self.config = Configuration().get_config(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_gce_config(self):
        self.config['mycluster']['cloud'] = {
            "provider": "google",
            "gce_client_id": "***fill in your data here***",
            "gce_client_secret": "***fill in your data here***",
            "gce_project_id": "test-id"}

        validator = ConfigValidator(self.config)
        validator.validate()


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
        self.assertRaises(Invalid, validator.validate)

        # check wrong url
        config = copy.deepcopy(config)
        config["mycluster"]["setup"]["ec2_host"] = "www.elasticluster"
        validator = ConfigValidator(config)
        self.assertRaises(Invalid, validator.validate)

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
                        self.assertRaises(Invalid, validator.validate)

        # check all node properties
        mandatory = ["flavor", "image_id", "security_group"]
        config = copy.deepcopy(config)
        for node, properties in config["mycluster"]["nodes"].iteritems():
            for property in properties.iterkeys():
                if property in mandatory:
                    config_tmp = copy.deepcopy(config)
                    del config_tmp["mycluster"]["nodes"][node][property]
                    validator = ConfigValidator(config_tmp)
                    self.assertRaises(Invalid, validator.validate)


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
            ssh_to=frontend

            [cluster/torque]
            cloud=hobbes
            frontend_nodes=1
            compute_nodes=2
            ssh_to=frontend
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
            ssh_to=frontend
            """
        self.assertRaises(Invalid, self._check_read_config, config)

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
            ssh_to=frontend
            """
        self.assertRaises(Invalid, self._check_read_config, config)
