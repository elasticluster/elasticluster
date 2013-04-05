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


from helpers import Singleton
import ConfigParser

@Singleton
class Configuration(object):
    '''
    Singleton
    The configuration class handles the global configuration file.
    It parses the file and provides the important sections as *datatype undecied*
    '''
    
    def __init__(self):
        # will be initialized upon user input from outside
        self.file_path = None
        self.cluster_name = None
        
        self._config = ConfigParser.ConfigParser()
        
        
    def _read_section(self, name):
        """
        Reads a section from the configuration file and returns a dictionary with its content
        """
        self._config.read(self.file_path)
        if self._config.has_section(name):
            return dict(self._config.items(name))
        else:
            raise ConfigParser.NoSectionError


    def read_cluster_section(self, name):
        """
        Reads the cluster section for a given cluster name from the configuration file and returns
        its properties in a dictionary.
        """
        return self._read_section("cluster/"+name)


    def read_cluster_node_section(self, cluster_name, node_type):
        """
        Reads the cluster configuration from the current config file with the given parameters for cluster and node type.
        In this case, the sectoins of the cluster and the specific node types will be merged (node_type is more specific)
        in order to allow easier configuration options.
        """
        config_name_general = "cluster/" + cluster_name
        config_name_specific = "cluster/" + cluster_name + "/" + node_type
        
        try:
            return dict(self._read_section(config_name_general).items() + self._read_section(config_name_specific).items())
        except Exception as e:
            print e
            try:
                return self._read_section(config_name_general)
            except Exception as e:
                raise ConfigParser.NoSectionError
            
            
    def read_cloud_section(self, name):
        """
        Reads the cloud section for a given cluster name from the configuraiton file and returns
        its properties in a dictionary.
        """
        return self._read_section("cloud/"+name)