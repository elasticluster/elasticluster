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



class AbstractCloudProvider:
    """
    Defines the contract for a cloud provider to proper function with elasticluster.
    """
    
    def start_instance(self, key_name, key_path, security_group, flavor, image_name):
        """
        Starts a new instance with the given properties and returns the instance id.
        """
        pass
    
    
    def stop_instance(self, instance_id):
        """
        Stops the instance with the given id gracefully.
        """
        pass
    
    
    
    def is_instance_running(self, instance_id):
        """
        Checks if the instance with the given id is up and running.
        """
        pass
    
    
    
class AbstractSetupProvider:
    """
    TODO: define...
    """
    
    slurm_class = "slurm"
    slurm_master = "slurm_master"
    slurm_clients = "slurm_clients"
    
    ganglia_class = "ganglia"
    ganglia_master = "ganglia_master"
    ganglia_clients = "ganglia_monitor"
    
    def __init__(self):
        pass
    
    def setup_cluster(self, cluster):
        pass
    