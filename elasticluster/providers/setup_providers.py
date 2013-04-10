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


from elasticluster.providers import AbstractSetupProvider
from elasticluster.cluster import Node
import elasticluster

from ansible.playbook import PlayBook
from ansible import callbacks
import ansible.constants as ansible_constants
from ansible.errors import AnsibleError

import os
from tempfile import NamedTemporaryFile


class AnsibleSetupProvider(AbstractSetupProvider):
    """
    """
    
    def __init__(self, private_key_file, remote_user, sudo_user, playbook_path):
        self._private_key_file = private_key_file
        self._remote_user = remote_user
        self._sudo_user = sudo_user
        self._playbook_path = playbook_path
        
        ansible_constants.DEFAULT_PRIVATE_KEY_FILE = self._private_key_file
        ansible_constants.DEFAULT_REMOTE_USER = self._remote_user
        ansible_constants.DEFAULT_SUDO_USER = self._sudo_user
    
    def setup_cluster(self, cluster):
        inventory_path = self._build_inventory(cluster)
        
        # check paths
        if not os.path.exists(inventory_path):
            raise AnsibleError("the inventory: %s could not be found" % inventory_path)
        if not os.path.exists(self._playbook_path):
            raise AnsibleError("the playbook: %s could not be found" % self._playbook_path)
        if not os.path.isfile(self._playbook_path):
            raise AnsibleError("the playbook: %s does not appear to be a file" % self._playbook_path)
        
        stats = callbacks.AggregateStats()
        playbook_cb = callbacks.PlaybookCallbacks(verbose=0)
        runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=0)
        
        # change path, since ansible needs to be in the same path then the playbook
        # TODO: is this a bug in ansible or playbook script?
        os.chdir(os.path.dirname(os.path.realpath(self._playbook_path)))
        print os.getcwd()
        
        pb = PlayBook(
            playbook=self._playbook_path,
            host_list=inventory_path,
            remote_user=self._remote_user,
            callbacks=playbook_cb,
            runner_callbacks=runner_cb,
            stats=stats,
            sudo=True,
            sudo_user=self._sudo_user,
            private_key_file=self._private_key_file,
        )
        
        try:
            pb.run()
        except AnsibleError as e:
            elasticluster.log.error("could not execute ansible playbooks. message=`%s`" % e.message)
            
        
    def _build_inventory(self, cluster):
        """
        Builds the inventory for the given cluster and returns its path
        """
        inventory = dict()
        
        for node in cluster.frontend_nodes + cluster.compute_nodes:
            classes = [x.strip() for x in node.setup_classes.split(',')]
            
            for c in classes:
                # slurm
                if c == AbstractSetupProvider.slurm_class:
                    if node.type == Node.frontend_type:
                        if AbstractSetupProvider.slurm_master not in inventory:
                            inventory[AbstractSetupProvider.slurm_master] = []
                        inventory[AbstractSetupProvider.slurm_master].append(node.ip_public)
                    elif node.type == Node.compute_type:
                        if AbstractSetupProvider.slurm_clients not in inventory:
                            inventory[AbstractSetupProvider.slurm_clients] = []
                        inventory[AbstractSetupProvider.slurm_clients].append(node.ip_public)
                        
                #ganglia
                if c == AbstractSetupProvider.ganglia_class:
                    if node.type == Node.frontend_type:
                        if AbstractSetupProvider.ganglia_master not in inventory:
                            inventory[AbstractSetupProvider.ganglia_master] = []
                        inventory[AbstractSetupProvider.ganglia_master].append(node.ip_public)
                    elif node.type == Node.compute_type:
                        if AbstractSetupProvider.ganglia_clients not in inventory:
                            inventory[AbstractSetupProvider.ganglia_clients] = []
                        inventory[AbstractSetupProvider.ganglia_clients].append(node.ip_public)    
        
        if inventory:
            # create a temporary file to pass to ansible, since the api is not stable...
            inventory_file = NamedTemporaryFile(delete=False)
     
            for section,hosts in inventory.items():
                inventory_file.write("\n["+section+"]\n")
                if hosts:
                    counter = 0
                    for host in hosts:
                        counter = counter + 1
                        inventory_file.write("node" + str(counter) + " ansible_ssh_host="+host+"\n")
                        
            
            inventory_file.close
            
            return inventory_file.name
        
        