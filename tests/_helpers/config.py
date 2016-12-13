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

from __future__ import absolute_import

__author__ = ('Nicolas Baer <nicolas.baer@uzh.ch>,'
              ' Riccardo Murri <riccardo.murri@gmail.com>')


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
                    "compute_groups": "slurm_worker",
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
