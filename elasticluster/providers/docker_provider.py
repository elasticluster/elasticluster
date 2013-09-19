#!/usr/bin/env python
# -*- coding: utf-8 -*-#
# @(#)docker_provider.py
#
#
# Copyright (C) 2013, GC3, University of Zurich. All rights reserved.
#
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

__author__ = "Antonio Messina <antonio.s.messina@gmail.com>"
__docformat__ = 'reStructuredText'

import docker

from elasticluster import log
from elasticluster.providers import AbstractCloudProvider

class DockerProvider(AbstractCloudProvider):
    """
    Uses Docker to create LXC containers and connect to it via ssh.
    """

    def __init__(self, docker_url=None, storage_path=None):
        self.docker_url = docker_url if docker_url else "unix://var/run/docker.sock"
        self.storage_path = storage_path
        self._client = None

    def _get_client(self):
        if not self._client:
            self._client = docker.Client(self.docker_url, version="1.4")
        return self._client

    def start_instance(self, hostname, key_name, public_key_path,
                       private_key_path, security_group, flavor, image_name,
                       image_userdata, username=None):
        """
        Starts a new instance with the given properties and returns
        the instance id.
        """
        client = self._get_client()
        container = client.create_container(image_name, None, detach=True, hostname=hostname)
        # container = client.create_container(image_name, None, detach=True)
        client.start(container['Id'])
        return  (container['Id'], {'is_docker_container': True})

    def stop_instance(self, instance_id):
        """
        Stops the instance with the given id gracefully.
        """
        client = self._get_client()
        client.stop(instance_id)

    def get_ips(self, instance_id):
        return ('127.0.0.1', '127.0.0.1')

    def get_ssh_ports(self, instance_id):
        client = self._get_client()
        ssh_port = client.port(instance_id, '22')
        return (ssh_port, '22')

    def is_instance_running(self, instance_id):
        """
        Checks if the instance with the given id is up and running.
        """
        client = self._get_client()
        for container in client.containers():
            if container['Id'].startswith(instance_id):
                if container['Status'].startswith('Up'):
                    return True
                return False
        return False
