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

import time
import boto
import boto.ec2
import urllib
import unicodedata
from conf import Configuration
from providers import AbstractCloudProvider

debuglevel=0

class BotoCloudProvider(AbstractCloudProvider):
    """
    Uses boto to connect to an ec2 or openstack web service to manage
    the virtual instances
    """
    
    def __init__(self):
        # will be initialized upon first connect
        self._connection = None
        self._region = None
        
        #AbstractCloudProvider.__init__(self)
        
    def _connect(self, cloud_options):
        """
        Connects to the ec2 cloud provider with the given cloud options (dictionary from configuration file)
        """
        # check for existing connection
        if self._connection:
            return
        
        # read all parameters from url
        t, opaqueurl = urllib.splittype(cloud_options['ec2_url'])
        host, ec2path = urllib.splithost(opaqueurl)
        ec2host, port = urllib.splitport(host)
        ec2port = int(port)
        
        # connect to webservice
        region = boto.ec2.regioninfo.RegionInfo(name=cloud_options['region'], endpoint=ec2host)
        self._connection = boto.connect_ec2(aws_access_key_id=cloud_options['ec2_access_key'], aws_secret_access_key=cloud_options['ec2_secret_key'], is_secure=False, port=ec2port, host=ec2host, path=ec2path, region=region, debug=debuglevel)
        
        
    def _find_image_id(self, name):
        """
        Finds an image id to a given name. This only works if a connection is already established and will return
        None otherwise.
        """
        if self._connection:
            images = self._connection.get_all_images()
            images = dict((unicodedata.normalize('NFC', i.name), i) for i in images)
            
            if name in images:
                return images[name].id
            
        
        return None
        
        
    def start_instance(self, cluster_name, node_type):
        """
        Starts an instance in the cloud on the specified cloud provider (configuration option)
        """
        try:
            instance_options = Configuration.Instance().read_cluster_node_section(cluster_name, node_type)            
            cloud_options = Configuration.Instance().read_cloud_section(instance_options['cloud'])
            
            self._connect(cloud_options)
            image_id = self._find_image_id(instance_options['image'])
            
            reservation = self._connection.run_instances(image_id, key_name=cloud_options['key_name'], security_groups=[instance_options['security_group']], instance_type=instance_options['flavor'])
            vm = reservation.instances[-1]
            
            while vm.update() == 'pending':
                print 'Vm in pending state. Sleeping 5 seconds...'
                time.sleep(5)
            
            print "vm started :) "
            
        except Exception as e:
            print e
        