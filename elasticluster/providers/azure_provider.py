#!/usr/bin/env python
# -*- coding: utf-8 -*-#
#
# Copyright (C) 2018 University of Zurich. All rights reserved.
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
__docformat__ = 'reStructuredText'
__author__ = ', '.join([
    'Riccardo Murri <riccardo.murri@gmail.com>'
])

# System imports
import hashlib
import json
import os
import threading
from warnings import warn
from time import sleep


try:
    from azure.common.credentials import ServicePrincipalCredentials
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.compute.models import DiskCreateOption
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.resource.resources.models import DeploymentMode
    from msrestazure.azure_exceptions import CloudError
except ImportError:
    # handle missing libraries in Python 2.6: delay ImportError until
    # actually used but raise a warning in the meantime
    class _Unavailable(object):
        """
        Delay `ImportError` until actually used.

        Still, raise a warning when instanciated.
        """
        def __init__(self, missing):
            self.__missing = missing
            warn("Trying to initialize `{module}` which is not available."
                 " A placeholder object will be used instead, but it will raise"
                 " `ImportError` later if there is any actual attempt at using it."
                 .format(module=self.__missing), ImportWarning)
            def __call__(self, *args, **kwargs):
                raise ImportError(
                    "Trying to actually use client class from module `{module}`"
                    " which could not be imported. Aborting."
                    .format(module=self.__missing))
    ServicePrincipalCredentials = _Unavailable("azure.common.credentials")
    ResourceManagementClient = _Unavailable("azure.mgmt.resource")
    NetworkManagementClient = _Unavailable("azure.mgmt.network")
    ComputeManagementClient = _Unavailable("azure.mgmt.compute")
    DiskCreateOption = _Unavailable("azure.mgmt.compute.models")
    CloudError = _Unavailable("msrestazure.azure_exceptions")

from paramiko import DSSKey, RSAKey, PasswordRequiredException
from paramiko.ssh_exception import SSHException

from pkg_resources import resource_string


# Elasticluster imports
from elasticluster import log
from elasticluster.utils import memoize
from elasticluster.providers import AbstractCloudProvider
from elasticluster.exceptions import (
    ConfigurationError,
    FlavorError,
    ImageError,
    InstanceNotFoundError,
    KeypairError,
    SecurityGroupError,
)


_VM_TEMPLATE = json.loads(resource_string(
    'elasticluster', 'share/etc/azure_vm_template.json'))
"""
Template description for starting a new VM.

Initially taken from:
https://github.com/Azure-Samples/resource-manager-python-template-deployment/blob/master/templates/template.json
Copyright (c) 2015 Microsoft Corporation
"""


class AzureCloudProvider(AbstractCloudProvider):
    """
    Use the Azure Python SDK to connect to the Azure clouds and
    manage virtual machines.

    An AzureCloudProvider owns a tree of Azure resources, rooted in one or
    more subscriptions and one or more storage accounts.
    """

    __lock = threading.Lock()
    """
    Lock used for node startup.
    """

    def __init__(self, subscription_id, tenant_id, client_id, secret, location, **extra):
        self.subscription_id = subscription_id
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.secret = secret
        self.location = location

        # these will be initialized later by `_init_az_api()`
        self._compute_client = None
        self._network_client = None
        self._resource_client = None

        # local state
        self._inventory = {}
        self._vm_details = {}
        self._resource_groups_created = set()


    def _init_az_api(self):
        """
        Initialise client objects for talking to Azure API.

        This is in a separate function so to be called by ``__init__``
        and ``__setstate__``.
        """
        with self.__lock:
            if self._resource_client is None:
                log.debug("Making Azure `ServicePrincipalcredentials` object"
                          " with tenant=%r, client_id=%r, secret=%r ...",
                          self.tenant_id, self.client_id,
                          ('<redacted>' if self.secret else None))
                credentials = ServicePrincipalCredentials(
                    tenant=self.tenant_id,
                    client_id=self.client_id,
                    secret=self.secret,
                )
                log.debug("Initializing Azure `ComputeManagementclient` ...")
                self._compute_client = ComputeManagementClient(credentials, self.subscription_id)
                log.debug("Initializing Azure `NetworkManagementclient` ...")
                self._network_client = NetworkManagementClient(credentials, self.subscription_id)
                log.debug("Initializing Azure `ResourceManagementclient` ...")
                self._resource_client = ResourceManagementClient(credentials, self.subscription_id)
                log.info("Azure API clients initialized.")


    def start_instance(self, key_name, public_key_path, private_key_path,
                       security_group, flavor, image_id, image_userdata,
                       username='root', node_name=None, **extra):
        """
        Start a new VM using the given properties.

        :param str key_name:
          **unused in Azure**, only present for interface compatibility
        :param str public_key_path:
          path to ssh public key to authorize on the VM (for user `username`, see below)
        :param str private_key_path:
          **unused in Azure**, only present for interface compatibility
        :param str security_group:
          network security group to attach VM to, **currently unused**
        :param str flavor:
          machine type to use for the instance
        :param str image_id:
          disk image to use for the instance;
          has the form *publisher/offer/sku/version*
          (e.g., ``canonical/ubuntuserver/16.04.0-LTS/latest``)
        :param str image_userdata:
          command to execute after startup, **currently unused**
        :param str username:
          username for the given ssh key
          (default is ``root`` as it's always guaranteed to exist,
          but you probably don't want to use that)

        :return: tuple[str, str] -- resource group and node name of the started VM
        """
        self._init_az_api()

        # Warn of unsupported parameters, if set.  We do not warn
        # about `user_key` or `private_key_path` since they come from
        # a `[login/*]` section and those can be shared across
        # different cloud providers.
        if security_group and security_group != 'default':
            warn("Setting `security_group` is currently not supported"
                 " in the Azure cloud; VMs will all be attached to"
                 " a network security group named after the cluster name.")
        if image_userdata:
            warn("Parameter `image_userdata` is currently not supported"
                 " in the Azure cloud and will be ignored.")

        # Use the cluster name to identify the Azure resource group;
        # however, `Node.cluster_name` is not passed down here so
        # extract it from the node name, which always contains it as
        # the substring before the leftmost dash (see `cluster.py`,
        # line 1182)
        cluster_name, _ = node_name.split('-', 1)
        with self.__lock:
            if cluster_name not in self._resource_groups_created:
                self._resource_client.resource_groups.create_or_update(
                    cluster_name, {'location': self.location})
                self._resource_groups_created.add(cluster_name)

        # read public SSH key
        with open(public_key_path, 'r') as public_key_file:
            public_key = public_key_file.read()

        image_publisher, image_offer, \
            image_sku, image_version = self._split_image_id(image_id)

        if not security_group:
            security_group = (cluster_name + '-secgroup')

        parameters = {
            'adminUserName':  { 'value': username },
            'imagePublisher': { 'value': image_publisher },  # e.g., 'canonical'
            'imageOffer':     { 'value': image_offer },      # e.g., ubuntuserver
            'imageSku':       { 'value': image_sku },        # e.g., '16.04.0-LTS'
            'imageVersion':   { 'value': image_version },    # e.g., 'latest'
            'networkSecurityGroupName': {
                'value': security_group,
            },
            'sshKeyData':     { 'value': public_key },
            'storageAccountName': {
                'value': self._make_storage_account_name(
                    cluster_name, node_name)
            },
            'subnetName':     { 'value': cluster_name },
            'vmName':         { 'value': node_name },
            'vmSize':         { 'value': flavor },
        }

        log.debug(
            "Deploying `%s` VM template to Azure ...",
            parameters['vmName']['value'])
        oper = self._resource_client.deployments.create_or_update(
            cluster_name, node_name, {
                'mode':       DeploymentMode.incremental,
                'template':   _VM_TEMPLATE,
                'parameters': parameters,
            })
        oper.wait()

        # the `instance_id` is a composite type since we need both the
        # resource group name and the vm name to uniquely identify a VM
        return (cluster_name, node_name)

    @staticmethod
    def _split_image_id(image_id):
        try:
            publisher, offer, sku, version = image_id.split('/', 3)
            return (publisher, offer, sku, version)
        except (ValueError, TypeError):
            raise ConfigurationError(
                "The 'image_id' parameter in Azure"
                " has the form 'publisher/offer/sku/version'"
                " (e.g., 'canonical/ubuntuserver/16.04.0-LTS/latest');"
                " got '{0}' {1} instead!"
                .format(image_id, type(image_id)))

    @staticmethod
    def _make_storage_account_name(cluster_name, node_name):
        algo = hashlib.md5()
        algo.update(cluster_name)
        algo.update(node_name)
        # the `storageAccountName` parameter must be lowercase
        # alphanumeric and between 3 and 24 characters long... We
        # cannot use base64 encoding, and the full MD5 hash is 32
        # characters -- truncate it and hope for the best.
        return algo.hexdigest()[:24]

    def _init_inventory(self, cluster_name):
        with self.__lock:
            if not self._inventory:
                for obj in self._resource_client.resources.list_by_resource_group(cluster_name):
                    self._inventory[obj.name] = obj.id

    def stop_instance(self, instance_id):
        """
        Stops the instance gracefully.

        :param str instance_id: instance identifier
        """
        self._init_az_api()

        cluster_name, node_name = instance_id
        self._init_inventory(cluster_name)

        for name, api_version in [
                # we must delete resources in a specific order: e.g.,
                # a public IP address cannot be deleted if it's still
                # in use by a NIC...
                (node_name,                '2017-12-01'),
                (node_name + '-nic',       '2018-03-01'),
                (node_name + '-public-ip', '2018-03-01'),
                (self._make_storage_account_name(
                    cluster_name, node_name),
                                           '2017-10-01'),
        ]:
            rsc_id = self._inventory[name]
            log.debug("Deleting resource %s (`%s`) ...", name, rsc_id)
            oper = self._resource_client.resources.delete_by_id(rsc_id, api_version)
            oper.wait()
            del self._inventory[name]

        self._vm_details.pop(node_name, None)

        # if this was the last VM to be deleted, clean up leftover resource group
        with self.__lock:
            if len(self._inventory) == 2:
                log.debug("Cleaning up leftover resource group ...")
                oper = self._resource_client.resource_groups.delete(cluster_name)
                oper.wait()
                self._inventory = {}


    def get_ips(self, instance_id):
        """
        Retrieves all IP addresses associated to a given instance.

        :return: tuple (IPs)
        """
        self._init_az_api()
        cluster_name, node_name = instance_id
        # XXX: keep in sync with contents of `_VM_TEMPLATE`
        ip_name = ('{node_name}-public-ip'.format(node_name=node_name))
        ip = self._network_client.public_ip_addresses.get(cluster_name, ip_name)
        if (ip.provisioning_state == 'Succeeded' and ip.ip_address):
            return [ip.ip_address]
        else:
            return []

    def is_instance_running(self, instance_id):
        """
        Check if the instance is up and running.

        :param str instance_id: instance identifier

        :return: bool - True if running, False otherwise
        """
        self._init_az_api()
        # Here, it's always better if we update the instance.
        vm = self._get_vm(instance_id, force_reload=True)
        # FIXME: should we rather check `vm.instance_view.statuses`
        # and search for `.code == "PowerState/running"`? or
        # `vm.instance_view.vm_agent.statuses` and search for `.code
        # == 'ProvisioningState/suceeded'`?
        return vm.provisioning_state == u'Succeeded'

    def _get_vm(self, instance_id, force_reload=True):
        """
        Return details on the VM with the given name.

        :param str node_name: instance identifier
        :param bool force_reload:
          if ``True``, skip searching caches and reload instance from server
          and immediately reload instance data from cloud provider
        :return: py:class:`novaclient.v1_1.servers.Server` - instance
        :raises: `InstanceError` is returned if the instance can't
                 be found in the local cache or in the cloud.
        """
        self._init_az_api()
        if force_reload:
            # Remove from cache and get from server again
            self._inventory = {}
        cluster_name, node_name = instance_id
        self._init_inventory(cluster_name)

        # if instance is known, return it
        if node_name not in self._vm_details:
            vm_info = self._compute_client.virtual_machines.get(
                cluster_name, node_name, 'instanceView')
            self._vm_details[node_name] = vm_info

        try:
            return self._vm_details[node_name]
        except KeyError:
            raise InstanceNotFoundError(
                "Instance `{instance_id}` not found"
                .format(instance_id=instance_id))

    # Fix pickler
    def __getstate__(self):
        return {
            'subscription_id': self.subscription_id,
            'tenant_id': self.tenant_id,
            'client_id': self.client_id,
            'secret': self.secret,
            'location': self.location,
            '_inventory': self._inventory,
            '_resource_groups_created': self._resource_groups_created,
        }

    def __setstate__(self, state):
        # these will be initialized later by `_init_az_api()`
        self._compute_client = None
        self._network_client = None
        self._resource_client = None

        # local state
        self.subscription_id = state['subscription_id']
        self.tenant_id = state['tenant_id']
        self.client_id = state['client_id']
        self.secret = state['secret']
        self.location = state['location']

        self._inventory = state['_inventory']
        self._resource_groups_created = state['_resource_groups_created']

        self._vm_details = {}
