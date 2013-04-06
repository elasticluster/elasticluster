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

from elasticluster.providers.cloud_providers import BotoCloudProvider
from elasticluster.helpers import Singleton
from elasticluster.cluster import Node, ClusterStorage
from elasticluster.exceptions import ConfigurationError
from elasticluster.cluster import Cluster
import ConfigParser

class Configurator(object):
    """
    Responsible to create instances, which need information from the configuration file.
    """
    
    cloud_providers_map = {
                           "ec2_boto": BotoCloudProvider
                           }

    # ANTONIO: No need to define an empty constructor!
    def __init__(self):
        pass
    
    
    def create_cloud_provider(self, cloud_name):
        """
        Creates a new cloud provider with the needed information from the configuration.
        """
        config = Configuration.Instance().read_cloud_section(cloud_name)
        provider = Configurator.cloud_providers_map[config["provider"]]
        
        return provider(config["ec2_url"], config["ec2_region"], config["ec2_access_key"], config["ec2_secret_key"])
        
    def create_cluster(self, name):
        """
        Creates a cluster with the needed information from the configuration.
        """
        config = Configuration.Instance().read_cluster_section(name)
        
        return Cluster(name, config['cloud'], self.create_cloud_provider(config['cloud']), int(config['frontend']), int(config['compute']), self)
        
    
    def create_node(self, cluster_name, node_type):
        """
        Creates a node with the needed information from the configuration file. The information of the node is
        specific to its type (e.g. a frontend node could differ from a compute node).
        """
        # ANTONIO: I don't think a node should have a cloud_provider
        # different from the cluster. Thus, cloud_provider should be
        # in the signature of `create_node` and it should be Cluster's
        # responsability to call `create_node` with its cloud provider
        # as argument. This will avoid having multiple instances of
        # the same cloud provider.
        config = Configuration.Instance().read_node_section(cluster_name, node_type)
        
        cloud_name = Configuration.Instance().read_cluster_section(cluster_name)['cloud']
        
        # TODO: this is quite bad, since every node will have its own instance of a cloud provider..
        return Node(node_type, self.create_cloud_provider(cloud_name), config['user_key'], config['user_key_name'], config['os_user'], config['security_group'], config['image'], config['flavor'])

    def create_cluster_storage(self):
        """
        Creates the storage to manage clusters.
        """
        return ClusterStorage(Configuration.Instance().storage_path)




@Singleton
class Configuration(object):
    """
    Singleton
    The configuration class handles the global configuration file.
    It parses the file and provides the important sections as *datatype undecied*
    """
    
    mandatory_cloud_options = ("provider", "ec2_url", "ec2_access_key", "ec2_secret_key", "ec2_region")
    mandatory_cluster_options = ("cloud", "frontend", "compute")
    mandatory_node_options = ("image", "security_group", "flavor", "user_key", "user_key_name", "os_user")
    
    def __init__(self):
        # will be initialized upon user input from outside
        self.file_path = None
        self.cluster_name = None
        self.storage_path = None
        
        self._config = ConfigParser.ConfigParser()
        
        
    def _read_section(self, name):
        """
        Reads a section from the configuration file and returns a dictionary with its content
        """
        self._config.read(self.file_path)
        if self._config.has_section(name):
            return dict(self._config.items(name))
        else:
            raise ConfigParser.NoSectionError("section %s not found in configuration file" % name)


    def read_cluster_section(self, name):
        """
        Reads the cluster section for a given cluster name from the configuration file and returns
        its properties in a dictionary.
        """
        config = self._read_section("cluster/"+name)
        self._check_mandatory_options(Configuration.Instance().mandatory_cluster_options, config)
        
        return config

    def read_node_section(self, cluster_name, node_type):
        """
        Reads the cluster configuration from the current config file with the given parameters for cluster and node type.
        In this case, the sectoins of the cluster and the specific node types will be merged (node_type is more specific)
        in order to allow easier configuration options.
        """
        
        if node_type == Node.frontend_type:
            node_type = "frontend"
        else:
            node_type = "compute"

        config_name_general = "cluster/" + cluster_name
        config_name_specific = "cluster/" + cluster_name + "/" + node_type
        
        # merge configuration parts from the cluster and compute/frontend section
        if self._config.has_section(config_name_general):
            if self._config.has_section(config_name_specific):
                config = dict(self._read_section(config_name_general).items() + self._read_section(config_name_specific).items())
            else:
                config = self._read_section(config_name_general)
            
            self._check_mandatory_options(Configuration.Instance().mandatory_node_options, config)
            
            return config
            
        else:
            raise ConfigParser.NoSectionError("no configuration secton for cluster `%s` found" % cluster_name) 
            
            
    def read_cloud_section(self, name):
        """
        Reads the cloud section for a given cluster name from the configuraiton file and returns
        its properties in a dictionary.
        """
        config = self._read_section("cloud/"+name)
        
        self._check_mandatory_options(Configuration.Instance().mandatory_cloud_options, config)
        
        return config
    
    
    def _check_mandatory_options(self, options, config):
        for o in options:
            if o not in config:
                raise ConfigurationError("could not find mandatory cloud option `%s` in configuration file" % o)
        
