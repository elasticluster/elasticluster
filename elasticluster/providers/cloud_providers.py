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
from elasticluster.providers import AbstractCloudProvider
from boto import ec2
import boto
import os
import urllib
from elasticluster.exceptions import SecurityGroupError, KeypairError, InstanceError

class BotoCloudProvider(AbstractCloudProvider):
    """
    Uses boto to connect to an ec2 or openstack web service to manage
    the virtual instances
    """
    
    def __init__(self, url, region_name, access_key, secret_key):
        self._url = url
        self._region_name = region_name
        self._access_key = access_key
        self._secret_key = secret_key
        
        # read all parameters from url
        proto, opaqueurl = urllib.splittype(url)
        self._host, self._ec2path = urllib.splithost(opaqueurl)
        self._ec2host, port = urllib.splitport(self._host)
        
        if port:
            port = int(port)
        self._ec2port = port

        if proto == "https":
            self._secure = True
        else:
            self._secure = False
        
        # will be initialized upon first connect
        self._connection = None
        self._region = None
        self._instances = {}
        
    def _connect(self):
        """
        Connects to the ec2 cloud provider
        """
        # check for existing connection
        if self._connection:
            return self._connection
        
    
        try:
            region = ec2.regioninfo.RegionInfo(name=self._region_name, endpoint=self._ec2host)

            # connect to webservice
            self._connection = boto.connect_ec2(aws_access_key_id=self._access_key, aws_secret_access_key=self._secret_key, is_secure=self._secure, port=self._ec2port, host=self._ec2host, path=self._ec2path, region=region)
            
            # list images to see if the connection works
            self._connection.get_all_images()
        
        except Exception as e:
            elasticluster.log.error("connection to cloud could not be established: message=`%s`" % e.message)
            raise
        
        return self._connection

        
    def start_instance(self, key_name, key_path, security_group, flavor, image_name):
        """
        Starts an instance in the cloud on the specified cloud provider (configuration option)
        and returns the id of the started instance.
        """ 
        connection = self._connect()
         
        self._check_keypair(key_name, key_path)
        self._check_security_group(security_group)
        image_id = self._find_image_id(image_name)
        
        reservation = connection.run_instances(image_id, key_name=key_name, security_groups=[security_group], instance_type=flavor)
        vm = reservation.instances[-1]
        
        # cache instance object locally for faster access later on
        self._instances[vm.id] = vm
        
        return vm.id
    
    def stop_instance(self, instance_id):
        """
        Terminates the given instance.
        """
        instance = self._instances[instance_id]
        instance.terminate()
        
    def get_ips(self, instance_id):
        self._load_instance(instance_id)
        instance = self._instances[instance_id]
        
        return instance.private_ip_address, instance.ip_address
        
    def is_instance_running(self, instance_id):
        """
        Checks if an instance with the given id is up and running.
        """
        self._load_instance(instance_id)
        
        instance = self._instances[instance_id]
        
        if instance.update() == "running":
            return True
        else:
            return False
        
        
    def _load_instance(self, instance_id):
        """
        Checks if an instance with the given id is cached. If not it will connect to the cloud and 
        put it into the local cache _instances. An InstanceError is returned if the instance can't
        be found in the local cache or in the cloud.
        """
        connection = self._connect()
        if instance_id not in self._instances:
            reservations = connection.get_all_instances()
            for res in reservations:
                for instance in res.instances:
                    if instance.id == instance_id:
                        self._instances[instance_id] = instance
                        
        if instance_id not in self._instances:
            raise InstanceError("the given instance `%s` was not found on the coud" % instance_id)
        
        
    def _check_keypair(self, name, path):
        connection = self._connect()
        keypairs = connection.get_all_key_pairs()
        keypairs = dict((k.name, k) for k in keypairs)
        

        # create keys that don't exist yet
        if name not in keypairs:
            # ANTONIO: Better to specify where the keypair was not found, and the name as well.
            # something on the lien "Keypair `%s` not found on resource `%s`. Creating a new one" % (name, ec2endpoint)
            elasticluster.log.warning("keypair not found on cloud, creating a new one")
            with open(os.path.expanduser(path)) as f:
                key_material = f.read()
                try:
                    connection.import_key_pair(name, key_material)
                except Exception, ex:
                    # ANTONIO: This is probably an error:
                    # 
                    # * If you cannot import a *new* key, there is no
                    #   key to delete.
                    #
                    # * However, if you get an error because the key
                    #   already exists (shouldn't but could happen,
                    #   because of a race condition) you are deleting
                    #   a valid key.
                    #
                    # (I know, the example I gave you have the same bug :))
                    # 
                    # Moreover: one of the error you can get here is
                    # that the configuration file defines a *private*
                    # key, while you want to upload a public key. You
                    # should add some check (sooner or later) to work
                    # around this kind of mistake, knowing that
                    # usually the public key has the same name of the
                    # private key but with extension `.pub`.
                    # 
                    # One more thing: change the name of the
                    # configuration file meaningful: `user_key` could
                    # either be the private or the public key. Call it
                    # `public_key` or `private_key`.
                    connection.delete_key_pair(name)
                    raise KeypairError("could not create keypair `%s`: %s" % (name, ex))

        
    def _check_security_group(self, name):
        """
        Checks if the security group exists.
        TODO: if the configuration file specify some rules, ensure
              that the security group has those rules, and if the security
              group does not exists, create it.
        """
        connection = self._connect()
        security_groups = connection.get_all_security_groups()
        security_groups = dict((s.name, s) for s in security_groups)
        
        if name not in security_groups:
            raise SecurityGroupError("the specified security group %s does not exist" % name)
    
    
    def _find_image_id(self, name):
        """
        Finds an image id to a given name.
        """
        connection = self._connect()
        images = connection.get_all_images()
        
        # ANTONIO: this is a method you may want to cache
        for i in images:
            if i.name == name:
                return i.id            
    
        return None
    
    
