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
from elasticluster.exceptions import TimeoutError
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'


import elasticluster
import json
import io
import os
import time
import signal

class Cluster(object):
    """
    Handles all cluster related functionality such as start, setup, load, stop, storage etc.
    """
    startup_timeout = 180

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
        
        # initialize nodes
        for _ in range(self._frontend):
            self.add_node(Node.frontend_type)
        
        for _ in range(self._compute):
            self.add_node(Node.compute_type)

    def add_node(self, node_type):
        """
        Adds a new node, but doesn't start the instance on the cloud.
        Returns the created node instance 
        """
        node = self._configurator.create_node(self.name, node_type, self._cloud_provider)
        if node_type == Node.frontend_type:
            self.frontend_nodes.append(node)
        else:
            self.compute_nodes.append(node)
        
        return node
            
    def remove_node(self, node):
        """
        Removes a node from the cluster, but does not stop it.
        """
        if node.type == Node.compute_type:
            self.compute_nodes.remove(node)
        elif node.type == Node.frontend_type:
            self.frontend_nodes.remove(node)
        
    def start(self):
        """
        Starts the cluster with the properties given in the constructor. It will create the nodes
        through the configurator and delegate all the work to them. After the identifiers of all instances
        are available, it will save the cluster throgh the cluster storage.
        """
                
        # start every node
        for node in self.frontend_nodes + self.compute_nodes:
            node.start()
            
        # dump the cluster here, so we don't loose any knowledge about nodes
        self._storage.dump_cluster(self)
            
        # check if all nodes are running, stop all nodes if the timeout is reached
        def timeout_handler(signum, frame):
            raise TimeoutError("problems occured while starting the nodes, timeout `%i`" % Cluster.startup_timeout)
 
        signal.signal(signal.SIGALRM, timeout_handler) 
        signal.alarm(Cluster.startup_timeout)
        
        try:
            starting_nodes = self.compute_nodes + self.frontend_nodes
            while starting_nodes:
                starting_nodes = [n for n in starting_nodes if not n.is_alive()]
                time.sleep(5)
        except TimeoutError as timeout:
            elasticluster.log.error(timeout.message)
            elasticluster.log.error("timeout error occured: stopping all nodes")
            self.stop()
            
    def stop(self):
        """
        Terminates all instances corresponding to this cluster and deletes the cluster storage.
        """
        for node in self.frontend_nodes + self.compute_nodes:
            node.stop()
        self._storage.delete_cluster(self.name)
            
            
    def load_from_storage(self):
        """
        Fills the cluster with the stored informations such as instance ids, so its possible to resume
        operations on the cloud.
        """
        self._storage.load_cluster(self)
        
        for n in self.frontend_nodes + self.compute_nodes:
            if not n.is_alive():
                # TODO: this is very dangerous..., start a new instance at least
                elasticluster.log.error("instance `%s` is not correclty running anymore, shutting it down." % n.instance_id)
                n.stop()
                
            
class Node(object):
    """
    Handles all the node related funcitonality such as start, stop, configure, etc.
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
        self.ip_public = None
        self.ip_private = None
        
        
    def start(self):
        """
        Starts an instance for this node on the cloud through the clode provider. This method is non-blocking, as soon as the
        node id is returned from the cloud provider, it will return.
        """
        elasticluster.log.info("trying to start a node")
        self.instance_id = self._cloud_provider.start_instance(self.user_key_name, self.user_key, self.security_group, self.flavor, self.image)
        elasticluster.log.info("starting node with id `%s`" % self.instance_id)
        
    def stop(self):
        elasticluster.log.info("shutting down instance `%s`" % self.instance_id)
        try:
            self._cloud_provider.stop_instance(self.instance_id)
        except:
            elasticluster.log.error("could not stop instance `%s`, it might already be down." % self.instance_id)
        
    def is_alive(self):
        """
        Checks if the current node is up and running in the cloud
        """
        running = self._cloud_provider.is_instance_running(self.instance_id)
        
        if running:
            elasticluster.log.info("node `%s` is up and running" % self.instance_id)
            self.update_ips()
        else:
            elasticluster.log.debug("waiting for node `%s` to start")
        
        return running
    
    def update_ips(self):
        """
        Updates the ips of the node through the cloud provider.
        """
        if not self.ip_private and not self.ip_public:
            private, public = self._cloud_provider.get_ips(self.instance_id)
            self.ip_public = public
            self.ip_private = private
            

class ClusterStorage(object):
    """
    Handles the storage to save information about all the clusters managed by this tool.
    """
    
    def __init__(self, storage_dir):
        self._storage_dir = storage_dir
    
    def dump_cluster(self, cluster):
        """
        Saves the information of the cluster to disk in json format to load it later on.
        """
        db = {"name":cluster.name}
        db["frontend"] = [node.instance_id for node in cluster.frontend_nodes]
        db["compute"] = [node.instance_id for node in cluster.compute_nodes]
        
        db_json = json.dumps(db)
        
        db_path = self._get_json_path(cluster.name)
        self._clear_storage(db_path)
        
        # ANTONIO: here you have to check if the storage dir does not
        # exist, and in case create one.
        f = io.open(db_path, 'w')
        f.write(unicode(db_json))
        f.close()
        
        
    def load_cluster(self, cluster):
        """
        Loads a cluster from the local storage and fills the given cluster object with the known information.
        """
        db_path = self._get_json_path(cluster.name)
        
        f = io.open(db_path, 'r')
        db_json = f.readline()
        
        information = json.loads(db_json)
        
        # if a cluster grows the number of nodes in the config is not enough
        while len(cluster.frontend_nodes) > len(information["frontend"]):
            cluster.add_node(Node.frontend_type)
        while len(cluster.compute_nodes) > len(information["compute"]):
            cluster.add_node(Node.compute_type)
        
        # fill the information of the nodes
        for node, cache in zip(cluster.frontend_nodes, information['frontend']):
            node.instance_id = cache
        for node, cache in zip(cluster.compute_nodes, information['compute']):
            node.instance_id = cache
    
    
    def delete_cluster(self, cluster_name):
        """
        Deletes the storage of a cluster.
        """
        db_file = self._get_json_path(cluster_name)
        self._clear_storage(db_file)
    
    
    def get_stored_clusters(self):
        """
        Returns a list of all stored clusters.
        """
        from os import listdir
        from os.path import isfile, join
        db_files = [ f.split(os.extsep, 1)[0] for f in listdir(self._storage_dir) if isfile(join(self._storage_dir,f)) ]
        return db_files
    
    
    def _get_json_path(self, cluster_name):
        """
        Gets the path to the json storage file.
        """
        return self._storage_dir + os.sep + cluster_name + ".json"
        
        
    def _clear_storage(self, db_path):
        """
        Clears a storage file.
        """
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    
    
    
    
    