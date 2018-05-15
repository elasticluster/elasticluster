#! /usr/bin/env python
#
#   Copyright (C) 2013, 2015, 2016 S3IT, University of Zurich
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
# pylint: disable=missing-docstring,invalid-name

from __future__ import (absolute_import, division, print_function)

# this is needed to get logging info in `py.test` when something fails
import logging
logging.basicConfig()

import collections
from copy import copy, deepcopy
from os.path import join

#rom elasticluster.conf import ConfigReader, ConfigValidator, Creator
from elasticluster.conf import (
    load_config_files,
    make_creator,
    _read_config_files,
    _arrange_config_tree,
    _perform_key_renames,
    _dereference_config_tree,
    _build_node_section,
)
from elasticluster.cluster import Node
from elasticluster.exceptions import (
    ClusterNotFound,
    ConfigurationError,
)
from elasticluster.providers.ansible_provider import AnsibleSetupProvider
from elasticluster.providers.ec2_boto import BotoCloudProvider


CONFIG_TXT = ('''

[cloud/ec2]
provider = ec2_boto
ec2_url = https://ec2.us-east-1.amazonaws.com
ec2_access_key = XXXXXX
ec2_secret_key = XXXXXX
ec2_region = us-east-1


[cloud/ec2_vpc]
provider = ec2_boto
ec2_url = https://ec2.us-east-1.amazonaws.com
ec2_access_key = XXXXXX
ec2_secret_key = XXXXXX
ec2_region = us-east-1
vpc = vpc-c0ffee


[cloud/openstack]
provider = openstack
auth_url = http://hobbes.gc3.uzh.ch::5000/v2.0
username = XXXXXX
password = XXXXXX
project_name = test-tenant


[cloud/google]
provider = google
gce_project_id = gc3-uzh
gce_client_id = XXXXXX
gce_client_secret = XXXXXX


[cluster/example_ec2]
cloud = ec2
login = ubuntu
setup = example_setup
misc_nodes = 10

# cloud-specific params
image_id = i-12345
flavor = m1.tiny
security_group = default


[cluster/example_ec2_with_vpc]
cloud = ec2
login = ubuntu
setup = example_setup
misc_nodes = 10

# cloud-specific params
image_id = i-12345
flavor = m1.tiny
security_group = default

network_ids = subnet-deadbeef


[cluster/example_openstack]
cloud = openstack
login = ubuntu
setup = example_setup
misc_nodes = 10

# cloud-specific params
image_id = e23f2df2-d68c-4307-ace0-2571f8fdcd1f
flavor = 1cpu-4ram-hpc
security_group = default


[cluster/example_google]
cloud = google
setup = example_setup
misc_nodes = 10

# cloud-specific params
image_id = i-12345
login = ubuntu
flavor = m1.tiny
security_group = default
boot_disk_size = 15
boot_disk_type = pd-standard
node_name = my-node
scheduling = preemptible
tags = tag1,tag2,tag3


[cluster/wrong_example_google]
cloud = wrongle
setup = example_setup
misc_nodes = 10

# cloud-specific params
image_id = i-12345
login = ubuntu
flavor = m1.tiny
security_group = default


[setup/example_setup]
provider = ansible
misc_groups = whatever


[login/ubuntu]
image_user = ubuntu
image_user_sudo = root
image_sudo = False

user_key_name = {keyname}
user_key_private = {valid_path}
user_key_public = {valid_path}
''')

CONFIG_RAW = ({
    'cloud/ec2': {
        'provider': 'ec2_boto',
        'ec2_url': 'https://ec2.us-east-1.amazonaws.com',
        'ec2_access_key': 'XXXXXX',
        'ec2_secret_key': 'XXXXXX',
        'ec2_region': 'us-east-1',
    },

    'cloud/ec2_vpc': {
        'provider': 'ec2_boto',
        'ec2_url': 'https://ec2.us-east-1.amazonaws.com',
        'ec2_access_key': 'XXXXXX',
        'ec2_secret_key': 'XXXXXX',
        'ec2_region': 'us-east-1',
        'vpc': 'vpc-c0ffee',
    },

    'cloud/openstack': {
        'provider': 'openstack',
        'auth_url': 'http://hobbes.gc3.uzh.ch::5000/v2.0',
        'username': 'XXXXXX',
        'password': 'XXXXXX',
        'project_name': 'test-tenant',
    },

    'cloud/google': {
        'provider': 'google',
        'gce_project_id': 'gc3-uzh',
        'gce_client_id': 'XXXXXX',
        'gce_client_secret': 'XXXXXX',
    },

    'cluster/example_ec2': {
        'cloud': 'ec2',
        'login': 'ubuntu',
        'setup': 'example_setup',
        'misc_nodes': '10',
        'image_id': 'i-12345',
        'flavor': 'm1.tiny',
        'security_group': 'default',
    },

    'cluster/example_ec2_with_vpc': {
        'cloud': 'ec2',
        'login': 'ubuntu',
        'setup': 'example_setup',
        'misc_nodes': '10',
        'image_id': 'i-12345',
        'flavor': 'm1.tiny',
        'security_group': 'default',
        'network_ids': 'subnet-deadbeef',
    },

    'cluster/example_openstack': {
        'cloud': 'openstack',
        'login': 'ubuntu',
        'setup': 'example_setup',
        'misc_nodes': '10',
        'image_id': 'e23f2df2-d68c-4307-ace0-2571f8fdcd1f',
        'flavor': '1cpu-4ram-hpc',
        'security_group': 'default',
    },

    'cluster/example_google': {
        'cloud': 'google',
        'setup': 'example_setup',
        'misc_nodes': '10',
        'image_id': 'i-12345',
        'login': 'ubuntu',
        'flavor': 'm1.tiny',
        'security_group': 'default',
        'boot_disk_size': '15',
        'boot_disk_type' : 'pd-standard',
        'node_name' : 'my-node',
        'scheduling' : 'preemptible',
        'tags' : 'tag1,tag2,tag3'
    },

    'cluster/wrong_example_google': {
        'cloud': 'wrongle',
        'setup': 'example_setup',
        'misc_nodes': '10',
        'image_id': 'i-12345',
        'login': 'ubuntu',
        'flavor': 'm1.tiny',
        'security_group': 'default',
    },

    'setup/example_setup': {
        'provider': 'ansible',
        'misc_groups': 'whatever',
    },

    'login/ubuntu': {
        'image_user': 'ubuntu',
        'image_user_sudo': 'root',
        'image_sudo': 'False',
        'user_key_name': '{keyname}',
        'user_key_private': '{valid_path}',
        'user_key_public': '{valid_path}',
    },
})


CONFIG_TREE = ({
    'cloud': {
        'ec2': {
            'provider': 'ec2_boto',
            'ec2_url': 'https://ec2.us-east-1.amazonaws.com',
            'ec2_access_key': 'XXXXXX',
            'ec2_secret_key': 'XXXXXX',
            'ec2_region': 'us-east-1',
        },
        'ec2_vpc': {
            'provider': 'ec2_boto',
            'ec2_url': 'https://ec2.us-east-1.amazonaws.com',
            'ec2_access_key': 'XXXXXX',
            'ec2_secret_key': 'XXXXXX',
            'ec2_region': 'us-east-1',
            'vpc': 'vpc-c0ffee',
        },
        'openstack': {
            'provider': 'openstack',
            'auth_url': 'http://hobbes.gc3.uzh.ch::5000/v2.0',
            'username': 'XXXXXX',
            'password': 'XXXXXX',
            'project_name': 'test-tenant',
        },
        'google': {
            'provider': 'google',
            'gce_project_id': 'gc3-uzh',
            'gce_client_id': 'XXXXXX',
            'gce_client_secret': 'XXXXXX',
        },
    },  ## close the `cloud:` part
    'cluster': {
        'example_ec2': {
            'cloud': 'ec2',
            'login': 'ubuntu',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'i-12345',
            'flavor': 'm1.tiny',
            'security_group': 'default',
        },
        'example_ec2_with_vpc': {
            'cloud': 'ec2',
            'login': 'ubuntu',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'i-12345',
            'flavor': 'm1.tiny',
            'security_group': 'default',
            'network_ids': 'subnet-deadbeef',
        },
        'example_openstack': {
            'cloud': 'openstack',
            'login': 'ubuntu',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'e23f2df2-d68c-4307-ace0-2571f8fdcd1f',
            'flavor': '1cpu-4ram-hpc',
            'security_group': 'default',
        },
        'example_google': {
            'cloud': 'google',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'i-12345',
            'login': 'ubuntu',
            'flavor': 'm1.tiny',
            'security_group': 'default',
            'boot_disk_size': '15',
            'boot_disk_type': 'pd-standard',
            'node_name': 'my-node',
            'scheduling': 'preemptible',
            'tags': 'tag1,tag2,tag3'
        },
        'wrong_example_google': {
            'cloud': 'wrongle',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'i-12345',
            'login': 'ubuntu',
            'flavor': 'm1.tiny',
            'security_group': 'default',
        },
    },  ## close the `cluster:` part
    'setup': {
        'example_setup': {
            'provider': 'ansible',
            'misc_groups': 'whatever',
        },
    },  ## close the `setup:` part
    'login': {
        'ubuntu': {
            'image_user': 'ubuntu',
            'image_user_sudo': 'root',
            'image_sudo': 'False',
            'user_key_name': '{keyname}',
            'user_key_private': '{valid_path}',
            'user_key_public': '{valid_path}',
        },
    },
})


CONFIG_TREE_WITH_RENAMES = ({
    'cloud': {
        'ec2': {
            'provider': 'ec2_boto',
            'ec2_url': 'https://ec2.us-east-1.amazonaws.com',
            'ec2_access_key': 'XXXXXX',
            'ec2_secret_key': 'XXXXXX',
            'ec2_region': 'us-east-1',
        },
        'ec2_vpc': {
            'provider': 'ec2_boto',
            'ec2_url': 'https://ec2.us-east-1.amazonaws.com',
            'ec2_access_key': 'XXXXXX',
            'ec2_secret_key': 'XXXXXX',
            'ec2_region': 'us-east-1',
            'vpc': 'vpc-c0ffee',
        },
        'openstack': {
            'provider': 'openstack',
            'auth_url': 'http://hobbes.gc3.uzh.ch::5000/v2.0',
            'username': 'XXXXXX',
            'password': 'XXXXXX',
            'project_name': 'test-tenant',
        },
        'google': {
            'provider': 'google',
            'gce_project_id': 'gc3-uzh',
            'gce_client_id': 'XXXXXX',
            'gce_client_secret': 'XXXXXX',
        },
    },  ## close the `cloud:` part
    'cluster': {
        'example_ec2': {
            'cloud': 'ec2',
            'login': 'ubuntu',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'i-12345',
            'flavor': 'm1.tiny',
            'security_group': 'default',
        },
        'example_ec2_with_vpc': {
            'cloud': 'ec2',
            'login': 'ubuntu',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'i-12345',
            'flavor': 'm1.tiny',
            'security_group': 'default',
            'network_ids': 'subnet-deadbeef',
        },
        'example_openstack': {
            'cloud': 'openstack',
            'login': 'ubuntu',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'e23f2df2-d68c-4307-ace0-2571f8fdcd1f',
            'flavor': '1cpu-4ram-hpc',
            'security_group': 'default',
        },
        'example_google': {
            'cloud': 'google',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'i-12345',
            'login': 'ubuntu',
            'flavor': 'm1.tiny',
            'security_group': 'default',
            'boot_disk_size': '15',
            'boot_disk_type': 'pd-standard',
            'node_name': 'my-node',
            'scheduling': 'preemptible',
            'tags': 'tag1,tag2,tag3'
        },
        'wrong_example_google': {
            'cloud': 'wrongle',
            'setup': 'example_setup',
            'misc_nodes': '10',
            'image_id': 'i-12345',
            'login': 'ubuntu',
            'flavor': 'm1.tiny',
            'security_group': 'default',
        },
    },  ## close the `cluster:` part
    'setup': {
        'example_setup': {
            'provider': 'ansible',
            'misc_groups': 'whatever',
        },
    },  ## close the `setup:` part
    'login': {
        'ubuntu': {
            'image_user': 'ubuntu',
            'image_user_sudo': 'root',
            'image_sudo': 'False',
            'user_key_name': '{keyname}',
            'user_key_private': '{valid_path}',
            'user_key_public': '{valid_path}',
        },
    },
})


def test_read_config_file(tmpdir):
    with open(join(str(tmpdir), 'config.ini'), 'w') as cfgfile:
        cfgfile.write(CONFIG_TXT)
        cfgfile.flush()
        raw_config = _read_config_files([cfgfile.name])
    assert raw_config == CONFIG_RAW

def test_arrange_config_tree():
    tree = _arrange_config_tree(copy(CONFIG_RAW))
    assert tree == CONFIG_TREE


def test_perform_key_renames():
    tree_with_renames = _perform_key_renames(deepcopy(CONFIG_TREE))
    assert tree_with_renames == CONFIG_TREE_WITH_RENAMES


def test_dereference_config_tree_evict():
    deref_tree = _dereference_config_tree(deepcopy(CONFIG_TREE_WITH_RENAMES))
    for cluster_name, ref_section, ref_name in [
            # pylint: disable=bad-whitespace
            ('example_ec2',          'cloud', 'ec2'),
            ('example_ec2',          'login', 'ubuntu'),
            ('example_ec2',          'setup', 'example_setup'),
            ('example_ec2_with_vpc', 'cloud', 'ec2'),
            ('example_ec2_with_vpc', 'login', 'ubuntu'),
            ('example_ec2_with_vpc', 'setup', 'example_setup'),
            ('example_openstack',    'cloud', 'openstack'),
            ('example_openstack',    'login', 'ubuntu'),
            ('example_openstack',    'setup', 'example_setup'),
    ]:
        assert isinstance(deref_tree['cluster'][cluster_name][ref_section],
                          collections.Mapping)
        assert (deref_tree['cluster'][cluster_name][ref_section]
                is deref_tree[ref_section][ref_name])
    # check eviction of clusters w/ wrong config
    assert 'wrong_example_google' not in deref_tree['cluster']


def test_dereference_config_tree_no_evict():
    deref_tree = _dereference_config_tree(deepcopy(CONFIG_TREE_WITH_RENAMES),
                                          evict_on_error=False)
    for cluster_name, ref_section, ref_name in [
            ('wrong_example_google', 'login', 'ubuntu'),
            ('wrong_example_google', 'setup', 'example_setup'),
    ]:
        assert (deref_tree['cluster'][cluster_name][ref_section]
                is deref_tree[ref_section][ref_name])


def test_build_node_section():
    deref_tree = _dereference_config_tree(deepcopy(CONFIG_TREE_WITH_RENAMES))
    cfg = _build_node_section(deref_tree)['cluster']
    cluster_cfg = cfg['example_ec2']
    assert 'nodes' in cluster_cfg
    nodes_cfg = cluster_cfg['nodes']
    assert 'misc' in nodes_cfg
    assert nodes_cfg['misc']['flavor'] == 'm1.tiny'
    assert nodes_cfg['misc']['image_id'] == 'i-12345'
    assert nodes_cfg['misc']['num'] == 10
    assert nodes_cfg['misc']['min_num'] == 10


def test_build_node_section_google():
    deref_tree = _dereference_config_tree(deepcopy(CONFIG_TREE_WITH_RENAMES))
    cfg = _build_node_section(deref_tree)['cluster']
    cluster_cfg = cfg['example_google']
    assert 'nodes' in cluster_cfg
    nodes_cfg = cluster_cfg['nodes']
    assert 'misc' in nodes_cfg
    assert nodes_cfg['misc']['boot_disk_size'] == '15'
    assert nodes_cfg['misc']['boot_disk_type'] == 'pd-standard'
    assert nodes_cfg['misc']['scheduling'] == "preemptible"
    assert nodes_cfg['misc']['node_name'] == "my-node"
    assert nodes_cfg['misc']['tags'] == "tag1,tag2,tag3"
