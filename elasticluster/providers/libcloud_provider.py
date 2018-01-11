#! /usr/bin/env python
#
#   Copyright (C) 2013-2018 S3IT, University of Zurich
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
import os
from tempfile import NamedTemporaryFile

import paramiko
from paramiko import SSHException
from libcloud.compute.base import NodeAuthSSHKey, NodeAuthPassword
from libcloud.compute.providers import get_driver
from libcloud.compute.types import NodeState, Provider

from elasticluster.providers import AbstractCloudProvider
from elasticluster import log
from elasticluster.exceptions import KeypairError, UnsupportedError


class LibCloudProvider(AbstractCloudProvider):
    """
        This implementation of
        :py:class:`elasticluster.providers.AbstractCloudProvider` uses
        LibCloud to connect to various clouds and manage instances.

        :param str driver_name: name of the driver to use
        :param str storage_path: path to store temporary data
        :param options: all the configuration items that should
                        be forwarded to the driver
        """

    provider_args = {
        'aliyun_ecs': ['access_key_id', 'access_key_secret'],
        'bsnl': ['username', 'password'],
        'cloudscale': ['token'],
        'cloudsigma': ['username', 'password'],
        'cloudwatt': ['email', 'password', 'tenant_id'],
        'digitalocean': ['access_token'],
        'dimensiondata': ['username', 'password'],
        'ec2': ['access_key', 'secret_key'],
        'exoscale': ['key'],
        'gandi': ['api_key'],
        'gce': ['service_account_email_or_client_id', 'pem_file_or_client_secret'],
        'ikoula': ['key'],
        'indosat': ['username', 'password'],
        'internetsolutions': ['username', 'password'],
        'medone': ['username', 'password'],
        'nimbus': ['key'],
        'ntta': ['username', 'password'],
        'openstack': ['username', 'password'],
        'outscale_inc': ['key'],
        'outscale_sas': ['key'],
        'ovh': ['app_key', 'app_secret', 'project_id', 'consumer_key'],
        'packet': ['key'],
        'rackspace': ['username', 'api_key'],
        'vcloud': ['key'],
        'vultr': ['api_key']
    }

    def __init__(self, driver_name, storage_path=None, **options):
        self.storage_path = storage_path
        driver_name = driver_name.lower()
        try:
            req_args = self.provider_args[driver_name]
            if not set(req_args).issubset(options):
                raise ValueError(
                    'Cloud provider {0} requires all of {1} to be set'
                    .format(driver_name, ' '.join(req_args)))
            args = [options.pop(name) for name in req_args]
        except KeyError:
            # no required args?!
            args = []
        # fix for openstack
        if 'auth_url' in options and 'ex_force_auth_url' not in options:
            options['ex_force_auth_url'] = options['auth_url'].rsplit('/', 1)[0]

        try:
            provider_name = getattr(Provider, driver_name.upper())
        except AttributeError:
            raise ValueError(
                "No libcloud driver for provider {name}"
                .format(name=driver_name))
        driver_class = get_driver(provider_name)
        log.debug(
            "Initializing libcloud driver `%s` ...",
            driver_class.__name__)
        self.driver = driver_class(*args, **options)

    def __get_instance(self, instance_id):
        for node in self.driver.list_nodes():
            if node.id == instance_id:
                return node
        else:
            log.warn('could not find instance with id %s', instance_id)
            return None

    def start_instance(self, key_name, public_key_path, private_key_path,
                       security_group, flavor, image_id, image_userdata,
                       username=None, node_name=None, **options):
        self.__prepare_key_pair(key_name,
                                private_key_path,
                                public_key_path,
                                options.get('image_user_password'))
        options['name'] = node_name
        options['size'] = self._get_flavor_by_name(flavor)
        options['image'] = self.driver.get_image(image_id)
        if security_group:
            options['security_groups'] = security_group
        options['ex_userdata'] = image_userdata
        options['username'] = username

        network_ids = [
            netid.strip()
            for netid in options.pop('network_ids', '').split(',')
            if netid.strip() != ''
        ]
        if network_ids:
            try:
                options['networks'] = [
                    net for net in self.driver.ex_list_networks()
                    if net.id in network_ids
                ]
            except AttributeError:
                raise UnsupportedError(
                    "Cluster specifies `network_ids`"
                    " but the cloud provider does not implement"
                    " the `ex_list_networks()` call.")

        if self.driver.get_key_pair(key_name):
            options['auth'] = NodeAuthSSHKey(self.driver.get_key_pair(key_name).public_key)
            options['ex_keyname'] = key_name
        else:
            options['auth'] = NodeAuthPassword(options.get('image_user_password'))

        node = self.driver.create_node(**options)
        if node:
            return node.id
        return None

    def _get_flavor_by_name(self, name):
        flavors = [
            flavor for flavor in self.driver.list_sizes()
            if (flavor.name == name or flavor.id == name)
        ]
        if flavors:
            flavor = flavors[0]
            if len(flavors) > 1:
                log.warn(
                    "%d flavors with name '%s' found!"
                    " using first returned one: %s",
                    len(flavors), flavor)
            return flavor
        else:
            raise FlavorError("Cannot find flavor `%s`" % name)

    def is_instance_running(self, instance_id):
        instance = self.__get_instance(instance_id)
        if not instance:
            return False
        return instance.state == NodeState.RUNNING

    def stop_instance(self, instance_id):
        instance = self.__get_instance(instance_id)
        if not instance:
            return
        log.info('stopping %s', instance.name)
        instance.destroy()

    def get_ips(self, instance_id):
        instance = self.__get_instance(instance_id)
        if not instance:
            return []
        return instance.public_ips + instance.private_ips

    def __prepare_key_pair(self, key_name, private_key_path, public_key_path, password):
        if not key_name:
            log.warn('user_key_name has not been defined, assuming password-based authentication')
            return

        if key_name in [k.name for k in self.driver.list_key_pairs()]:
            log.info('Key pair `%s` already exists, skipping import.', key_name)
            return

        if public_key_path:
            log.debug("importing public key from file %s ...", public_key_path)
            if not self.driver.import_key_pair_from_file(
                    name=key_name,
                    key_file_path=os.path.expandvars(os.path.expanduser(public_key_path))):
                raise KeypairError(
                    'Could not upload public key {p}'
                    .format(p=public_key_path))
        elif private_key_path:
            if not private_key_path.endswith('.pem'):
                raise KeypairError(
                    'can only work with .pem private keys,'
                    ' derive public key and set user_key_public')
            log.debug("deriving and importing public key from private key")
            self.__import_pem(key_name, private_key_path, password)
        else:
            pem_file_path = os.path.join(self.storage_path, key_name + '.pem')
            if not os.path.exists(pem_file_path):
                with open(pem_file_path, 'w') as new_key_file:
                    new_key_file.write(
                        self.driver.create_key_pair(name=key_name))
            self.__import_pem(key_name, pem_file_path, password)

    def __import_pem(self, key_name, pem_file_path, password):
        """
        Import PEM certificate with provider
        :param key_name: name of the key to import
        :param pem_file_path: path to the pem file
        :param password: optional password for the pem file
        """
        pem_file = os.path.expandvars(os.path.expanduser(pem_file_path))
        try:
            pem = paramiko.RSAKey.from_private_key_file(pem_file, password)
        except SSHException:
            try:
                pem = paramiko.DSSKey.from_private_key_file(pem_file, password)
            except SSHException as e:
                raise KeypairError('could not import {f}, neither as RSA key nor as DSA key: {e}'
                                   .format(f=pem_file_path, e=e))
        if not pem:
            raise KeypairError('could not import {f}'.format(f=pem_file_path))
        else:
            with NamedTemporaryFile('w+t') as f:
                f.write('{n} {p}'.format(n=pem.get_name(), p=pem.get_base64()))
                self.driver.import_key_pair_from_file(
                    name=key_name, key_file_path=f.name)

    @staticmethod
    def __get_name_or_id(values, known):
        """
        Return list of values that match attribute ``.id`` or ``.name`` of any object in list `known`.

        :param str values: comma-separated list (i.e., a Python string) of items
        :param list known: list of libcloud items to filter
        :return: list of the libcloud items that match the given values
        """
        result = list()
        for element in [e.strip() for e in values.split(',')]:
            for item in [i for i in known if i.name == element or i.id == element]:
                result.append(item)
        return result
