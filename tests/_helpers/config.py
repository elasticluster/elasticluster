#! /usr/bin/env python
#
#   Copyright (C) 2016 S3IT, University of Zurich
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

from __future__ import (absolute_import, division, print_function)

# stdlib imports
from string import Template

# 3rd party imports
from mock import Mock

# ElastiCLuster imports
from elasticluster.conf import Creator


_CONFIG_TXT = {
    'cloud':{

        'ec2': """
provider = ec2_boto
ec2_url = https://ec2.us-east-1.amazonaws.com
ec2_access_key = ${EC2_ACCESS_KEY}
ec2_secret_key = ${EC2_SECRET_KEY}
ec2_region = us-east-1
        """,

        'ec2_vpc':"""
provider = ec2_boto
ec2_url = https://ec2.us-east-1.amazonaws.com
ec2_access_key = ${EC2_ACCESS_KEY}
ec2_secret_key = ${EC2_SECRET_KEY}
ec2_region = us-east-1
vpc = vpc-c0ffee
        """,

        'openstack': """
provider = openstack
auth_url = http://openstack.example.com:5000/v2.0
username = ${USER}
password = XXXXXX
project_domain_name = Default
user_domain_name = Default
project_name = test-tenant
        """,

        'google':"""
provider = google
gce_project_id = gc3-uzh
gce_client_id = XXXXXX
gce_client_secret = ${GCE_CLIENT_SECRET}
        """,
        },

    'cluster':{

        'example_ec2':"""
cloud = ec2
login = ubuntu
setup = misc_setup
misc_nodes = 10

# cloud-specific params
image_id = i-12345
flavor = m1.tiny
security_group = default
        """,

        'example_ec2_with_vpc':"""
cloud = ec2
login = ubuntu
setup = misc_setup
misc_nodes = 10

# cloud-specific params
image_id = i-12345
flavor = m1.tiny
security_group = default

network_ids = subnet-deadbeef
        """,

        'example_openstack':"""
cloud = openstack
login = ubuntu
setup = slurm_setup_old
frontend_nodes = 1
compute_nodes = 2

# cloud-specific params
image_id = e23f2df2-d68c-4307-ace0-2571f8fdcd1f
flavor = 1cpu-4ram-hpc
security_group = default
        """,

        'example_google':"""
cloud = google
setup = misc_setup
misc_nodes = 10

# cloud-specific params
image_id = i-12345
login = ubuntu
flavor = m1.tiny
security_group = default
        """,
    },

    'login':{
        'ubuntu':"""
image_user = ubuntu
image_user_sudo = root
image_sudo = False

user_key_name = ${keyname}
user_key_private = ${valid_path}
user_key_public = ${valid_path}
        """,
    },

    'setup':{
        'misc_setup':"""
provider = ansible
misc_groups = whatever
        """,

        'slurm_setup':"""
provider = ansible
master_groups = slurm_master
worker_groups = slurm_worker
        """,

        'slurm_setup_old':"""
provider = ansible
frontend_groups = slurm_master
compute_groups = slurm_worker
        """,
    },
}


def make_config_snippet(section, name, *morelines, **kwargs):
    """
    Return am example configuration snippet for the given `[section/name]`.
    See `_CONFIG_TXT` for a catalog of available snippets.

    Additional arguments are interpreted as follows:

    - `morelines`: each of these should be a string, which is appeneded as a
       separate line to the returned snippet.
    - `kwargs`: additional named arguments are used to expand
       ``${...}``-constructs in the snippet text.
    - Named argument `rename`, if provided and non-empty, is used in place of
      argument ``name`` when constructing the snippet title (``[section/name]``)
    """
    return Template('\n'.join(
        # leave a blank line before the section header
        ['\n',
         # snippet title
         '[{section}/{name}]'
         .format(section=section,
                 name=(kwargs.get('rename') if kwargs.get('rename') else name))]
        # contents
        + [_CONFIG_TXT[section][name]]
        # additional content
        + list(morelines)
    )).safe_substitute(**kwargs)


# `_CONFIG_KV` can be re-generated from `_CONFIG_TXT` using the following
# Python snippet::
#
# if __name__ == '__main__':
#     from elasticluster.conf import make_creator
#     from tempfile import NamedTemporaryFile
#     with NamedTemporaryFile() as fd, NamedTemporaryFile() as ssh_key:
#         for section in _CONFIG_TXT:
#             for name in _CONFIG_TXT[section]:
#                 fd.write(make_config_snippet(section, name,
#                                              valid_path=ssh_key.name))
#         fd.flush()
#         creator = make_creator(fd.name)
#     import json
#     import sys
#     json.dump(creator.cluster_conf, sys.stdout, indent=4, sort_keys=True)
#
_CONFIG_KV = {
    'cluster': {
        "example_ec2": {
            "cloud": {
                "ec2_access_key": "${EC2_ACCESS_KEY}",
                "ec2_region": "us-east-1",
                "ec2_secret_key": "${EC2_SECRET_KEY}",
                "ec2_url": "https://ec2.us-east-1.amazonaws.com",
                "price": 0,
                "provider": "ec2_boto",
                "request_floating_ip": False,
                "timeout": 0
            },
            "flavor": "m1.tiny",
            "image_id": "i-12345",
            "login": {
                "image_sudo": False,
                "image_user": "ubuntu",
                "image_user_sudo": "root",
                "image_userdata": "",
                "user_key_name": "${keyname}",
                "user_key_private": "/tmp/tmpKaSacv",
                "user_key_public": "/tmp/tmpKaSacv"
            },
            "misc_nodes": "10",
            "nodes": {
                "misc": {
                    "flavor": "m1.tiny",
                    "image_id": "i-12345",
                    "image_userdata": "",
                    "login": "ubuntu",
                    "min_num": 10,
                    "num": 10,
                    "security_group": "default"
                }
            },
            "security_group": "default",
            "setup": {
                "misc_groups": "whatever",
                "playbook_path": "/home/rmurri/w/elasticluster/elasticluster/share/playbooks/site.yml",
                "provider": "ansible"
            }
        },
        "example_openstack": {
            "cloud": {
                "auth_url": "http://openstack.example.com:35357",
                "password": "XXXXXX",
                "project_name": "test-tenant",
                "provider": "openstack",
                "project_domain_name": "Default",
                "user_domain_name": "Default",
                "username": "rmurri"
            },
            "compute_nodes": "2",
            "flavor": "1cpu-4ram-hpc",
            "frontend_nodes": "1",
            "image_id": "e23f2df2-d68c-4307-ace0-2571f8fdcd1f",
            "login": {
                "image_sudo": False,
                "image_user": "ubuntu",
                "image_user_sudo": "root",
                "image_userdata": "",
                "user_key_name": "${keyname}",
                "user_key_private": "/tmp/tmpKaSacv",
                "user_key_public": "/tmp/tmpKaSacv"
            },
            "nodes": {
                "compute": {
                    "flavor": "1cpu-4ram-hpc",
                    "image_id": "e23f2df2-d68c-4307-ace0-2571f8fdcd1f",
                    "image_userdata": "",
                    "login": "ubuntu",
                    "min_num": 2,
                    "num": 2,
                    "security_group": "default"
                },
                "frontend": {
                    "flavor": "1cpu-4ram-hpc",
                    "image_id": "e23f2df2-d68c-4307-ace0-2571f8fdcd1f",
                    "image_userdata": "",
                    "login": "ubuntu",
                    "min_num": 1,
                    "num": 1,
                    "security_group": "default"
                }
            },
            "security_group": "default",
            "setup": {
                "compute_groups": "slurm_worker",
                "frontend_groups": "slurm_master",
                "playbook_path": "/home/rmurri/w/elasticluster/elasticluster/share/playbooks/site.yml",
                "provider": "ansible"
            }
        }
    }
}


def make_cluster(tmpdir, template='example_openstack', config=_CONFIG_KV, cloud=None):
    creator = Creator(config, storage_path=tmpdir.mkdir('storage').strpath)
    cluster = creator.create_cluster(template, cloud=cloud, setup=Mock())
    # for kind, num in nodes.iteritems():
    #     conf_kind = configurator.cluster_conf['mycluster']['nodes'][kind]
    #     cluster.add_nodes(kind, num, conf_kind['image_id'],
    #                       conf_login['image_user'],
    #                       conf_kind['flavor'],
    #                       conf_kind['security_group'])
    return cluster


class Configuration(object):

    def get_config(self, path):
        config = {
            "mycluster": {
                "setup": {
                    "provider": "ansible",
                    "playbook_path": "%(ansible_pb_dir)s/site.yml",
                    "frontend_groups": "slurm_master",
                    "compute_groups": "slurm_worker",
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
                    "setup": "my-slurm-cluster",
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
                    "compute_groups": "slurm_worker",
                    },
                "cloud": {
                    "provider": "openstack",
                    "auth_url": "http://cloud.gc3.uzh.ch:35357",
                    "username": "myusername",
                    "password": "mypassword",
                    "project_domain_name": "Default",
                    "user_domain_name": "Default",
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
                    "setup": "my-slurm-cluster",
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
