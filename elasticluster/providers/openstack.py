#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)openstack.py
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
from apiclient.mimeparse import best_match

__docformat__ = 'reStructuredText'
__author__ = 'Antonio Messina <antonio.s.messina@gmail.com>'

# System imports
import os
import re
import threading
import base64
import hashlib
import subprocess
import getpass

# External modules
from novaclient import client
from novaclient.exceptions import NotFound
from paramiko import DSSKey, RSAKey, PasswordRequiredException, Agent
from paramiko.ssh_exception import SSHException

# Elasticluster imports
from elasticluster import log
from elasticluster.memoize import memoize
from elasticluster.providers import AbstractCloudProvider
from elasticluster.exceptions import SecurityGroupError, KeypairError, \
    ImageError, InstanceError, ClusterError, KeyNotFound, KeyNotAccessible,\
    SSHAgentError

DEFAULT_OS_NOVA_API_VERSION = "1.1"

class OpenStackCloudProvider(AbstractCloudProvider):
    """
    This implementation of
    :py:class:`elasticluster.providers.AbstractCloudProvider` uses the
    OpenStack native python bindings to connect to OpenStack clouds
    and manage instances.

    :param str username: username of the keystone user
    :param str password: password of the keystone user
    :param str project_name: name of the project to use
    :param str auth_url: url of keystone endpoint
    :param str region: OpenStack region to use
    :param str storage_path: path to store temporary data
    :param bool request_floating_ip: Whether ip are assigned automatically
                                    `True` or floating ips have to be
                                    assigned manually `False`
    
    """
    __node_start_lock = threading.Lock()  # lock used for node startup
    _SSH_KEY_CHECKED = False
    _SSH_KEY_ACCESS_ERROR =False

    def __init__(self, username, password, project_name, auth_url,
                 region_name=None, storage_path=None,
                 request_floating_ip=False,
                 nova_api_version=DEFAULT_OS_NOVA_API_VERSION):
        self._os_auth_url = os.getenv('OS_AUTH_URL', auth_url)
        self._os_username = os.getenv('OS_USERNAME', username)
        self._os_password = os.getenv('OS_PASSWORD', password)
        self._os_tenant_name = os.getenv('OS_TENANT_NAME', project_name)
        self._os_region_name = region_name
        self.request_floating_ip = request_floating_ip
        self.nova_api_version = nova_api_version
        self._instances = {}
        self._cached_instances = []

        self.client = client.Client(self.nova_api_version,
                                    self._os_username, self._os_password, self._os_tenant_name,
                                    self._os_auth_url, region_name=self._os_region_name)
 
    def start_instance(self, key_name, public_key_path, private_key_path,
                       security_group, flavor, image_id, image_userdata,
                       username=None, node_name=None, **kwargs):
        """Starts a new instance on the cloud using the given properties.
        The following tasks are done to start an instance:

        * establish a connection to the cloud web service
        * check ssh keypair and upload it if it does not yet exist. This is
          a locked process, since this function might be called in multiple
          threads and we only want the key to be stored once.
        * check if the security group exists
        * run the instance with the given properties

        :param str key_name: name of the ssh key to connect
        :param str public_key_path: path to ssh public key
        :param str private_key_path: path to ssh private key
        :param str security_group: firewall rule definition to apply on the
                                   instance
        :param str flavor: machine type to use for the instance
        :param str image_id: image type (os) to use for the instance
        :param str image_userdata: command to execute after startup
        :param str username: username for the given ssh key, default None

        :return: str - instance id of the started instance
        """

        log.debug("Checking keypair `%s`.", key_name)
        
        with OpenStackCloudProvider.__node_start_lock:
            # CAtch the exception and continue or avoid raising the exception
            self._check_keypair(key_name, public_key_path, private_key_path)


        log.debug("Checking security group `%s`.", security_group)
        self._check_security_group(security_group)

        # Check if the image id is present.
        images = self._get_images()
        if image_id not in [img.id for img in images]:
            raise ImageError("No image found with id '%s' on cloud "
                             "%s" % (image_id, self._os_auth_url))

        # Check if the flavor exists
        flavors = [fl for fl in self._get_flavors() if fl.name == flavor]
        if not flavors:
            raise FlavorError("No flavor found with name %s on cloud "
                              "%s" % (flavor, self._os_auth_url))
        flavor = flavors[0]

        nics = None
        if 'network_ids' in kwargs:
            nics=[{'net-id': netid.strip(), 'v4-fixed-ip': ''} for netid in kwargs['network_ids'].split(',') ]
            log.debug("Specifying networks for vm %s: %s",
                      node_name, str.join(', ', [nic['net-id'] for nic in nics]))

        vm = self.client.servers.create(
            node_name, image_id, flavor, key_name=key_name,
            security_groups=[security_group], userdata=image_userdata,
            nics=nics)

        self._instances[vm.id] = vm
        
        return vm.id

    def stop_instance(self, instance_id):
        """Stops the instance gracefully.

        :param str instance_id: instance identifier
        """
        instance = self._load_instance(instance_id)
        instance.delete()
        del self._instances[instance_id]

    def get_ips(self, instance_id):
        """Retrieves the private and public ip addresses for a given instance.

        :return: tuple (IPs)
        """
        self._load_instance(instance_id)
        instance = self._load_instance(instance_id)

        IPs = sum(instance.networks.values(), [])

        # We also need to check if there is any floating IP associated
        if self.request_floating_ip:
            # We need to list the floating IPs for this instance
            floating_ips = [ip for ip in self.client.floating_ips.list() if ip.instance_id == instance.id]
            if not floating_ips:
                log.debug("Public ip address has to be assigned through "
                          "elasticluster.")
                ip = self._allocate_address(instance)
                # This is probably the preferred IP we want to use
                IPs.insert(0, ip)
        return IPs

    def is_instance_running(self, instance_id):
        """Checks if the instance is up and running.

        :param str instance_id: instance identifier

        :return: bool - True if running, False otherwise
        """

        # Here, it's always better if we update the instance.        
        instance = self._load_instance(instance_id, force_reload=True)
        return instance.status == 'ACTIVE'
    
    
    @classmethod
    def _check_keypair_from_ssh_agent(cls, ref_fingerprint):
        """Function to check if a certain keypair is included in the ssh-agent
        :param str ref_fingerprint: fingerprint of the specified key
        :raises: `KeyNotFound` if the key is not included in the ssh-agent
        """
        raw_agent_fps=[x.get_fingerprint() for x in Agent().get_keys()]
        agent_fps=[':'.join((part.encode('hex') for part in x)) for x in raw_agent_fps]
        if not ref_fingerprint in agent_fps:
            raise KeyNotFound('Keypair with fingerprint'+ref_fingerprint+'not found in the ssh-agent')
    
    def _check_keypair_from_file(self, ref_fingerprint, private_key_path):
        """Function to check if a certain keypair from a file matches the fingerprint
        from a reference one
        :param str ref_fingerprint: fingerprint to be compared
        :raises: KeypairError: if the keypair is not valid, or if the fingerprint to check
                            and the one computed from the private key is not the same
        :raises: KeyNotAccessible: if the private key is password protected
                            and the password provided is not correct
        """
        
        pkey=None
        
        # This block avoid repetition of checks after it is done for the first instance
        if self._SSH_KEY_CHECKED==True:
            if self._SSH_KEY_ACCESS_ERROR==True: # This avoid user entering the code right the second time
                raise KeyNotAccessible#("Unable to access key file `"+private_key_path+": Invalid password")  
            else:
                return
        try:
            pkey=DSSKey.from_private_key_file(private_key_path)
        except PasswordRequiredException:
            try:
                asked_password = getpass.getpass('Enter passphrase for '+private_key_path+ ':')
                pkey=DSSKey.from_private_key_file(private_key_path,asked_password)
            except SSHException:
                self._SSH_KEY_CHECKED=True
                self._SSH_KEY_ACCESS_ERROR=True # This avoid user entering the code right the second time
                raise KeyNotAccessible#("Unable to access key file `"+private_key_path+": Invalid password")      
        except SSHException:
            try:
                pkey=RSAKey.from_private_key_file(private_key_path)
            except PasswordRequiredException:
                try:
                    asked_password = getpass.getpass('Enter passphrase for '+private_key_path+ ':')
                    pkey=RSAKey.from_private_key_file(private_key_path,asked_password)
                except SSHException:
                    self._SSH_KEY_CHECKED=True
                    self._SSH_KEY_ACCESS_ERROR=True # This avoid user entering the code right the second time
                    raise KeyNotAccessible#("Unable to access key file `"+private_key_path+": Invalid password")  
            except SSHException:
                raise KeypairError('File `%s` is neither a valid DSA key '
                                   'or RSA key' % private_key_path)
        fingerprint = str.join(
                ':', (i.encode('hex') for i in pkey.get_fingerprint()))
        if ref_fingerprint!=fingerprint:
            raise KeypairError(
                "Keypair from "+private_key_path+" is present but has "
                "different fingerprint. Aborting!")
        self._SSH_KEY_CHECKED=True
        return

    def _add_key_to_sshagent(self, private_key_path):
        """Function to add a private key to the ssh-agent
        :param str private_key_path: path to the ssh private key file
        :raises KeyNotAccessible: If the password provided is empty (in other cases the ssh-add
                asks for the password again)
        """
        # This block avoid repetition of checks after it is done for the first instance
        if self._SSH_KEY_ACCESS_ERROR==True:
            raise KeyNotAccessible#("Unable to access key file `"+private_key_path+": Invalid password")      
        return_code=subprocess.call(['ssh-add', private_key_path])
        if return_code==0:
            log.info("Key %s suscessfully added to ssh-agent" % private_key_path)
        else: # This only happens if the password is empty
            self._SSH_KEY_ACCESS_ERROR=True # This avoid user entering the code right the second time
            raise KeyNotAccessible#("Unable to access key file `"+private_key_path+": Invalid password") 
        
    @classmethod
    def _check_fingerprint_from_public_key_file(cls, ref_fingerprint, public_key_path):
        """ Function to check if the keypair matches the one at the cloud 
        by using only the public key file.
        :raises KeypairError: if the keypair is not valid, or if the fingerprint to check
                            and the one computed from the private key is not the same
        """
        try:
            with open(public_key_path, 'r') as fd:
                raw_fp=fd.readline().strip()
            key = base64.b64decode(raw_fp.split()[1].encode('ascii'))
            fp_plain = hashlib.md5(key).hexdigest()
            fingerprint = ':'.join(a+b for a,b in zip(fp_plain[::2], fp_plain[1::2]))
            if fingerprint==ref_fingerprint:
                return
            else:
                raise KeypairError(
                "Keypair in "+public_key_path+" is present but has "
                "different fingerprint. Aborting!")
        except Exception:
            raise KeypairError(
                "Keypair in "+public_key_path+" is present but has "
                "different fingerprint. Aborting!")
    
    @classmethod
    def _ensure_sshagent(cls):
        """Function to start a ssh-agent if it is not running
        :raises SSHAgentError if the process does not succed
        """   
        if 'SSH_AUTH_SOCK' in os.environ.keys():
            return
        else:
            try:
                output=subprocess.check_output(['ssh-agent',])
                for output_line in output.split('\n'):
                    match=re.match('(^.*)\=([^\;]*)\;.*$',output_line)
                    if match:
                        var_name, var_value =match.group(1,2)
                        if var_name=='SSH_AUTH_SOCK' or var_name=='SSH_AGENT_PID':
                            os.environ[str(var_name)]=str(var_value)                 
                log.warning('ssh-agent started')
                return
            except subprocess.CalledProcessError:
                raise SSHAgentError
            
    def _check_keypair(self, name, public_key_path, private_key_path):
        """First checks if the keypair is valid, then checks if the keypair
        is registered with on the cloud. If not the keypair is added to the
        users ssh keys.

        :param str name: name of the ssh key
        :param str public_key_path: path to the ssh public key file
        :param str private_key_path: path to the ssh private key file

        :raises: `KeypairError` if key is not a valid RSA or DSA key,
                 the key could not be uploaded, the fingerprint does not
                 match to the one uploaded to the cloud or the key is neither 
                 accessible nor included in the ssh-agent
        """

        # Read key. We do it as first thing because we need it either
        # way, to check the fingerprint of the remote keypair if it
        # exists already, or to create a new keypair.
        
        # Check if a keypair `name` exists on the cloud.
        try:
            keypair = self.client.keypairs.get(name)
        except NotFound:
            log.warning(
                "Keypair `%s` not found on resource `%s`, Creating a new one",
                name, self._os_auth_url)

            # Create a new keypair
            with open(os.path.expanduser(public_key_path)) as f:
                key_material = f.read()
                try:
                    self.client.keypairs.create(name, key_material)
                except Exception, ex:
                    log.error(
                        "Could not import key `%s` with name `%s` to `%s`",
                        name, public_key_path, self._os_auth_url)
                    raise KeypairError(
                        "could not create keypair `%s`: %s" % (name, ex))
        try: 
            self._ensure_sshagent() # If the ssh-agent is not running, this starts it
            self._check_keypair_from_ssh_agent(keypair.fingerprint) # This checks the keys on it
        except SSHAgentError: # If for some reason the ssh-agent cannot be started
            try: # It checks the key from the private key file
                self._check_keypair_from_file(keypair.fingerprint, private_key_path)
            except KeyNotAccessible: # If it is not accessible it checks the public one (computes fp)
                log.warning('Keypair not accessible. Checking fingerprint from public key.')
                self._check_fingerprint_from_public_key_file(keypair.fingerprint, public_key_path)
                log.warning('Matching fingerprints. Cluster will start but will not be accessed')
            except KeypairError:
                raise

        except KeyNotFound: # If the hey is not found among the keys in the ssh-agent
            try: # It tries to add it
                self._add_key_to_sshagent(private_key_path)
                self._check_keypair_from_ssh_agent(keypair.fingerprint)
            except KeyNotAccessible: # If it is not possible to add it, it checks it from the public one
                log.warning('Keypair not accessible. Checking fingerprint from public key.')
                self._check_fingerprint_from_public_key_file(keypair.fingerprint, public_key_path)
                log.warning('Matching fingerprints. Cluster will start but will not be accessed')
            except KeypairError:
                raise


    def _check_security_group(self, name):
        """Checks if the security group exists.

        :param str name: name of the security group
        :raises: `SecurityGroupError` if group does not exist
        """
        security_groups = self.client.security_groups.list()

        # TODO: We should be able to create the security group if it
        # doesn't exist and at least add a rule to accept ssh access.
        # Also, we should be able to add new rules to a security group
        # if needed.
        if name not in [sg.name for sg in security_groups ]:
            raise SecurityGroupError(
                "the specified security group %s does not exist" % name)

    @memoize(120)
    def _get_images(self):
        """Get available images. We cache the results in order to reduce
        network usage.

        """
        return self.client.images.list()

    @memoize(120)
    def _get_flavors(self):
        """Get available flavors. We cache the results in order to reduce
        network usage.

        """
        return self.client.flavors.list()

    def _load_instance(self, instance_id, force_reload=True):
        """Checks if an instance with the given id is cached. If not it
        will connect to the cloud and put it into the local cache
        _instances.

        :param str instance_id: instance identifier
        :param bool force_reload: reload instance from server
        :return: py:class:`novaclient.v1_1.servers.Server` - instance
        :raises: `InstanceError` is returned if the instance can't
                 be found in the local cache or in the cloud.
        """
        if force_reload:
            try:
                # Remove from cache and get from server again
                vm = self.client.servers.get(instance_id)
                # update cache
                self._instances[instance_id] = vm
                # delete internal cache, just in case
                for i in self._cached_instances:
                    if i.id == instance_id:
                        self._cached_instances.remove(i)
                        self._cached_instances.append(vm)
                        break
                    
            except NotFound:
                raise InstanceError("the given instance `%s` was not found "
                                    "on the coud" % instance_id)
        if instance_id in self._instances:
            return self._instances[instance_id]

        # Instance not in the internal dictionary.
        # First, check the internal cache:
        if instance_id not in [i.id for i in self._cached_instances]:
            # Refresh the cache, just in case
            self._cached_instances = self.client.servers.list()

        for inst in self._cached_instances:
            if inst.id == instance_id:
                self._instances[instance_id] = inst
                return inst

        # If we reached this point, the instance was not found neither
        # in the cache or on the website.
        raise InstanceError("the given instance `%s` was not found "
                            "on the coud" % instance_id)

    def _allocate_address(self, instance):
        """Allocates a free public ip address to the given instance

        :param instance: instance to assign address to
        :type instance: py:class:`novaclient.v1_1.servers.Server`

        :return: public ip address
        """
        with OpenStackCloudProvider.__node_start_lock:
            free_ips = [i for i in self.client.floating_ips.list() if not i.fixed_ip]
            if not free_ips:
                free_ips.append(self.client.floating_ips.create())
            ip = free_ips.pop()
            instance.add_floating_ip(ip)
        return ip.ip

    # Fix pickler
    def __getstate__(self):
        return {'auth_url': self._os_auth_url,
                'username': self._os_username,
                'password': self._os_password,
                'project_name': self._os_tenant_name,
                'region_name': self._os_region_name,
                'request_floating_ip': self.request_floating_ip,
                'instance_ids': self._instances.keys(),
                'nova_api_version': self.nova_api_version,
            }

    def __setstate__(self, state):
        self._os_auth_url = state['auth_url']
        self._os_username = state['username']
        self._os_password = state['password']
        self._os_tenant_name = state['project_name']
        self._os_region_name = state['region_name']
        self.request_floating_ip = state['request_floating_ip']
        self.nova_api_version = state.get('nova_api_version', DEFAULT_OS_NOVA_API_VERSION)
        self.client = client.Client(self.nova_api_version,
                                    self._os_username, self._os_password, self._os_tenant_name,
                                    self._os_auth_url, region_name=self._os_region_name)
        self._instances = {}
        self._cached_instances = []
        # recover instance objects from the cloud.

        # This is Disabled as we don't want to reload the
        # instances also for "list" command
        
        # for vm in self.client.servers.list():
        #     if vm.id in state['instance_ids']:
        #         self._instances[vm.id] = vm

        # for missing_vm in set(state['instance_ids']).difference(self._instances.keys()):
        #     log.warning("VM with id %s not found in cloud "
        #                 "%s" % (missing_vm, self._os_auth_url))

        
