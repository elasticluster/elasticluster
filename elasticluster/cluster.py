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


import elasticluster
import json
import io
import os

class Cluster(object):
    """
    TODO: document
    """


    def __init__(self, name, cloud, cloud_provider, frontend, compute, configurator, **extra):
        self.name = name
        self._cloud = cloud
        self._frontend = frontend
        self._compute = compute
        self._cloud_provider = cloud_provider
        
        self._configurator = configurator
        self._storage = configurator.create_cluster_storage()
        
        self.compute_nodes = []
        self.frontend_nodes = []
        
    def start(self):
        """
        TODO: document
        """
        # initialize nodes
        for _ in range(self._frontend):
            node = self._configurator.create_node(self.name, Node.frontend_type)
            self.frontend_nodes.append(node)
        
        for _ in range(self._compute):
            node = self._configurator.create_node(self.name, Node.compute_type)
            self.compute_nodes.append(node)
        
        # start every node
        for node in self.frontend_nodes + self.compute_nodes:
            node.start()
            
        # dump the cluster here, so we don't loose any knowledge about nodes
        self._storage.dump_cluster(self)
            
        # check if the nodes are running
        # TODO: add some sort of timeout here, otherwise you know...
        starting_nodes = self.compute_nodes + self.frontend_nodes
        while starting_nodes:
            # ANTONIO: This is dangerous: the exit condition could never be
            # condition from this loop!
            starting_nodes = [n for n in starting_nodes if not n.is_alive()]
            # ANTONIO: You should put some call to sleep() here...
            
            
class Node(object):
    """
    TODO: document
    """
    frontend_type = 1
    compute_type = 2

    def __init__(self, node_type, cloud_provider, user_key, user_key_name, os_user, security_group, image, flavor):
        self.type = node_type
        self._cloud_provider = cloud_provider
        self.user_key = user_key
        self.user_key_name = user_key_name
        self._os_user = os_user
        self.security_group = security_group
        self.image = image
        self.flavor = flavor
        
        self.instance_id = None
        
        
    def start(self):
        elasticluster.log.info("trying to start a node")
        self.instance_id = self._cloud_provider.start_instance(self.user_key_name, self.user_key, self.security_group, self.flavor, self.image)
        elasticluster.log.info("starting node with id `%s`" % self.instance_id)
        
    def is_alive(self):
        running = self._cloud_provider.is_instance_running(self.instance_id)
        
        if running:
            elasticluster.log.info("node `%s` is up and running" % self.instance_id)
            return True
        else:
            elasticluster.log.debug("waiting for node `%s` to start" % self.instance_id)
            return False
    
        

class ClusterStorage(object):
    """
    TODO: document
    """
    
    def __init__(self, storage_dir):
        self._storage_dir = storage_dir
    
    def dump_cluster(self, cluster):
        db = {"name":cluster.name}
        db["frontend"] = [node.instance_id for node in cluster.frontend_nodes]
        db["backend"] = [node.instance_id for node in cluster.compute_nodes]
        
        db_json = json.dumps(db)
        
        db_path = self._get_json_path(cluster.name)
        self._clear_storage(db_path)

        # ANTONIO: here you have to check if the storage dir does not
        # exist, and in case create one.
        f = io.open(db_path, 'w')
        f.write(unicode(db_json))
        f.close()
        
        
    def load_cluster(self, cluster_name):
        pass
    
    def list_stored_clusters(self):
        pass
    
    
    def _get_json_path(self, cluster_name):
        return self._storage_dir + os.sep + cluster_name + ".json"
        
        
    def _clear_storage(self, db_path):
        if os.path.exists(db_path):
            os.unlink(db_path)
