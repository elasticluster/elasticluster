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
import ConfigParser
import os
import shutil
import tempfile
import unittest
import sys

import nose.tools
from voluptuous import Invalid, MultipleInvalid

from elasticluster.conf import ConfigReader, ConfigValidator, Configurator
from elasticluster.cluster import Node
from elasticluster.exceptions import ClusterNotFound
from elasticluster.providers.ansible_provider import AnsibleSetupProvider
from elasticluster.providers.ec2_boto import BotoCloudProvider


def minimal_configuration(valid_path):

    cfg = ConfigParser.ConfigParser()

    # Create a valid, minimal configuration object.
    cfg.add_section('cloud/boto1')
    cfg.set('cloud/boto1', 'provider', 'ec2_boto')
    cfg.set('cloud/boto1', 'ec2_url', 'https://ec2.us-east-1.amazonaws.com')
    cfg.set('cloud/boto1', 'ec2_access_key', 'XXXXXX')
    cfg.set('cloud/boto1', 'ec2_secret_key', 'XXXXXX')
    cfg.set('cloud/boto1', 'ec2_region', 'us-east-1')

    cfg.add_section('cloud/boto_vpc')
    cfg.set('cloud/boto_vpc', 'provider', 'ec2_boto')
    cfg.set('cloud/boto_vpc', 'ec2_url', 'https://ec2.us-east-1.amazonaws.com')
    cfg.set('cloud/boto_vpc', 'ec2_access_key', 'XXXXXX')
    cfg.set('cloud/boto_vpc', 'ec2_secret_key', 'XXXXXX')
    cfg.set('cloud/boto_vpc', 'ec2_region', 'us-east-1')
    cfg.set('cloud/boto_vpc', 'vpc', 'vpc-c0ffee')

    cfg.add_section('cloud/hobbes')
    cfg.set('cloud/hobbes', 'provider', 'openstack')
    cfg.set('cloud/hobbes', 'auth_url', 'http://hobbes.gc3.uzh.ch::5000/v2.0')
    cfg.set('cloud/hobbes', 'username', 'XXXXXX')
    cfg.set('cloud/hobbes', 'password', 'XXXXXX')
    cfg.set('cloud/hobbes', 'project_name', 'test-tenant')

    cfg.add_section('cloud/google1')
    cfg.set('cloud/google1', 'provider', 'google')
    cfg.set('cloud/google1', 'gce_project_id', 'gc3-uzh')
    cfg.set('cloud/google1', 'gce_client_id', 'XXXXXX')
    cfg.set('cloud/google1', 'gce_client_secret', 'XXXXXX')

    cfg.add_section('cluster/c1')
    cfg.set('cluster/c1', 'cloud', 'boto1')
    cfg.set('cluster/c1', 'login', 'log1')
    cfg.set('cluster/c1', 'setup_provider', 'sp1')
    cfg.set('cluster/c1', 'login', 'log1')
    cfg.set('cluster/c1', 'image_id', 'i-12345')
    cfg.set('cluster/c1', 'flavor', 'm1.tiny')
    cfg.set('cluster/c1', 'misc_nodes', '10')
    cfg.set('cluster/c1', 'security_group', 'default')

    cfg.add_section('cluster/boto_vpc')
    cfg.set('cluster/boto_vpc', 'cloud', 'boto_vpc')
    cfg.set('cluster/boto_vpc', 'login', 'log1')
    cfg.set('cluster/boto_vpc', 'setup_provider', 'sp1')
    cfg.set('cluster/boto_vpc', 'login', 'log1')
    cfg.set('cluster/boto_vpc', 'image_id', 'i-12345')
    cfg.set('cluster/boto_vpc', 'flavor', 'm1.tiny')
    cfg.set('cluster/boto_vpc', 'misc_nodes', '10')
    cfg.set('cluster/boto_vpc', 'security_group', 'default')
    cfg.set('cluster/boto_vpc', 'network_ids', 'subnet-deadbeef')


    cfg.add_section('cluster/os-hobbes')
    cfg.set('cluster/os-hobbes', 'cloud', 'hobbes')
    cfg.set('cluster/os-hobbes', 'login', 'log1')
    cfg.set('cluster/os-hobbes', 'setup_provider', 'sp1')
    cfg.set('cluster/os-hobbes', 'login', 'log1')
    cfg.set('cluster/os-hobbes', 'image_id', 'i-12345')
    cfg.set('cluster/os-hobbes', 'flavor', 'm1.tiny')
    cfg.set('cluster/os-hobbes', 'misc_nodes', '10')
    cfg.set('cluster/os-hobbes', 'security_group', 'default')


    cfg.add_section('cluster/c2')
    cfg.set('cluster/c2', 'cloud', 'google1')
    cfg.set('cluster/c2', 'login', 'log1')
    cfg.set('cluster/c2', 'setup_provider', 'sp1')
    cfg.set('cluster/c2', 'login', 'log1')
    cfg.set('cluster/c2', 'image_id', 'i-12345')
    cfg.set('cluster/c2', 'flavor', 'm1.tiny')
    cfg.set('cluster/c2', 'misc_nodes', '10')
    cfg.set('cluster/c2', 'security_group', 'default')

    cfg.add_section('setup/sp1')
    cfg.set('setup/sp1', 'provider', 'ansible')

    cfg.add_section('login/log1')
    cfg.set('login/log1', 'image_user', 'ubuntu')
    cfg.set('login/log1', 'image_user_sudo', 'root')
    cfg.set('login/log1', 'image_sudo', 'False')
    cfg.set('login/log1', 'user_key_name', 'keyname')
    cfg.set('login/log1', 'user_key_private', valid_path)
    cfg.set('login/log1', 'user_key_public', valid_path)

    return cfg


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
                    "image_sudo": "True",
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
                },

            "os-cluster": {
                "setup": {
                    "provider": "ansible",
                    "playbook_path": "%(ansible_pb_dir)s/site.yml",
                    "frontend_groups": "slurm_master",
                    "compute_groups": "slurm_clients",
                    },
                "cloud": {
                    "provider": "openstack",
                    "auth_url": "http://cloud.gc3.uzh.ch:5000/v2.0",
                    "username": "myusername",
                    "password": "mypassword",
                    "project_name": "myproject",
                    },
                "login": {
                    "image_user": "gc3-user",
                    "image_user_sudo": "root",
                    "image_sudo": "True",
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

        self.assertEqual(cluster.name, "mycluster")

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

    def test_create_setup_provider(self):
        configurator = Configurator(self.config)
        provider = configurator.create_setup_provider("mycluster")

        self.assertTrue(type(provider) is AnsibleSetupProvider)

        conf = self.config['mycluster']['setup']
        groups = dict((k[:-7], v.split(',')) for k, v
                      in conf.items() if k.endswith('_groups'))
        self.assertEqual(groups, provider.groups)

        playbook_path = os.path.join(sys.prefix,
                                     'share/elasticluster/providers/ansible-playbooks', 'site.yml')
        self.assertEqual(playbook_path, provider._playbook_path)

        storage_path = configurator.general_conf['storage']
        self.assertEqual(provider._storage_path, storage_path)

        usr_sudo = self.config['mycluster']['login']['image_user_sudo']
        self.assertEqual(provider._sudo_user, usr_sudo)

        sudo = self.config['mycluster']['login']['image_sudo']
        self.assertEqual(provider._sudo, sudo)

    def test_setup_provider_using_environment(self):
        config = copy.deepcopy(self.config)
        configurator = Configurator(config)
        # Save current variable, modify it and check if it's correctly read
        SAVEDUSERNAME=os.getenv('OS_USERNAME')
        os.environ['OS_USERNAME'] = 'newusername'
        provider = configurator.create_cloud_provider("os-cluster")
        try:

            self.assertEqual(provider._os_username, 'newusername')
        except:
            if SAVEDUSERNAME:
                os.environ['OS_USERNAME'] = SAVEDUSERNAME
            else:
                del os.environ['OS_USERNAME']
            raise


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

    def test_invalid_ec2_vpc_config(self):
        """
        Invalid EC2 VPC configuration
        """
        # VPC without cluster network_ids definition
        config = copy.deepcopy(self.config)
        self.assertEqual(config["mycluster"]["cloud"]["provider"], "ec2_boto")
        config["mycluster"]["cloud"]["vpc"] = "vpc-c0ffee"
        if "network_ids" in config["mycluster"]["cluster"]:
            del config["mycluster"]["cluster"]["network_ids"]
        validator = ConfigValidator(config)
        self.assertRaises(Invalid, validator.validate)

        # network_ids definition without a VPC
        config = copy.deepcopy(self.config)
        self.assertEqual(config["mycluster"]["cloud"]["provider"], "ec2_boto")
        config["mycluster"]["nodes"]["frontend"]["network_ids"] = "subnet-deadbeef"
        if "vpc" in config["mycluster"]["cloud"]:
            del config["mycluster"]["cloud"]["vpc"]
        validator = ConfigValidator(config)
        self.assertRaises(Invalid, validator.validate)


class TestConfigReader(unittest.TestCase):
    def setUp(self):
        file, path = tempfile.mkstemp()
        self.path = path
        self.cfgfile = path

    def tearDown(self):
        os.unlink(self.cfgfile)

    def _check_read_config(self, config):
        with open(self.cfgfile, 'wb') as fd:
            fd.write(config)

        return Configurator.fromConfig(self.cfgfile)
        # config_reader = ConfigReader(self.cfgfile)
        # return config_reader.read_config()

    def _check_read_config_object(self, cfgobj):
        with open(self.cfgfile, 'wb') as fd:
            cfgobj.write(fd)

        ret = Configurator.fromConfig(self.cfgfile)
        return ret

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

[cloud/os-hobbes]
provider=openstack
auth_url=http://hobbes.gc3.uzh.ch:5000/v2.0
username=antonio
password=***
project_name=academic-cloud
request_floating_ip=False
nova_api_version=2

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
user_key_private=""" + self.path + """
user_key_public=""" + self.path + """

[login/gc3-user]
image_user=gc3-user
image_user_sudo=root
image_sudo=True
user_key_name=elasticluster
user_key_private=""" + self.path + """
user_key_public=""" + self.path + """

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


[cluster/os-slurm]
cloud=os-hobbes
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
frontend_nodes=1
compute_nodes=2

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
        config = self._check_read_config(config)

        # check all clusters are there
        cfg = config.cluster_conf
        self.assertTrue("matlab" in cfg)
        self.assertTrue("aws-slurm" in cfg)
        self.assertTrue("torque" in cfg)
        self.assertTrue("slurm" in cfg)

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

    def test_read_missing_section_cluster(self):
        '''
        Check if a configuration file with no `cluster` sections will
        raise an error.
        '''
        cfg = minimal_configuration(self.path)
        cfg.remove_section('cluster/c1')
        cfg.remove_section('cluster/c2')
        cfg.remove_section('cluster/boto_vpc')
        cfg.remove_section('cluster/os-hobbes')
        self.assertRaises(Invalid, self._check_read_config_object, cfg)

    def test_read_missing_section_cloud(self):
        '''
        Read config with missing section
        '''
        cfg = minimal_configuration(self.path)
        cfg.remove_section('cloud/boto1')
        self.assertRaises(Invalid, self._check_read_config_object, cfg)

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


    def test_missing_options(self):
        cfg = minimal_configuration(self.path)

        @nose.tools.raises(Invalid, MultipleInvalid)
        def missing_option(section, option):
            tmpcfg = minimal_configuration()
            _, cfgfile = tempfile.mkstemp()
            tmpcfg.remove_option(section, option)
            with open(cfgfile, 'w') as fd:
                tmpcfg.write(fd)
            try:
                config = Configurator.fromConfig(cfgfile)
            finally:
                os.unlink(cfgfile)

        for section in cfg.sections():
            for option, value in cfg.items(section):
                yield missing_option, section, option


class TestConfigurationFile(unittest.TestCase):

    def setUp(self):
        file, path = tempfile.mkstemp()
        self.cfgfile = path

    def tearDown(self):
        os.unlink(self.cfgfile)

    def test_valid_minimal_configuration(self):
        cfg = minimal_configuration(self.cfgfile)

        with open(self.cfgfile, 'w') as fd:
            cfg.write(fd)
        config = Configurator.fromConfig(self.cfgfile)

    def test_parsing_of_multiple_ansible_groups(self):
        """Fix regression causing multiple ansible groups to be incorrectly parsed

        The bug caused this configuration snippet:

        [setup/ansible]
        frontend_groups=slurm_master,ganglia_frontend

        to lead to the following inventory file:

        [slurm_master,ganglia_frontend]
        frontend001 ...
        """
        cfg = minimal_configuration(self.cfgfile)
        cfg.set('setup/sp1', 'misc_groups', 'misc_master,misc_client')
        with open(self.cfgfile, 'w') as fd:
            cfg.write(fd)
        config = Configurator.fromConfig(self.cfgfile)
        setup = config.create_setup_provider('c1')
        self.assertEqual(setup.groups['misc'], ['misc_master', 'misc_client'])

if __name__ == "__main__":
    import nose
    nose.runmodule()
