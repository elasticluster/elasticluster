#! /usr/bin/env python
#
#   Copyright (C) 2013-2017 S3IT, University of Zurich
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

from elasticluster import AbstractCloudProvider
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

    def __init__(self, driver_name, storage_path=None, **options):
        self.storage_path = storage_path
        if 'auth_url' in options and 'ex_force_auth_url' not in options:
            options['ex_force_auth_url'] = options['auth_url'].rsplit('/', 1)[0]

        try:
            driver_name = getattr(Provider, driver_name.upper())
        except AttributeError:
            raise ValueError("No libcloud driver for provider {name}".format(name=driver_name))
        driver_class = get_driver(driver_name)
        log.debug('Using libcloud driver `%s` ...', driver_class.__name__)
        auth_args = self.__pop_driver_auth_args(**options)
        if auth_args:
            self.driver = driver_class(*auth_args, **options)
        else:
            self.driver = driver_class(**options)

    def __get_instance(self, instance_id):
        for node in self.driver.list_nodes():
            if node.id == instance_id:
                return node
        return None

    def start_instance(self, key_name, public_key_path, private_key_path, security_group, flavor, image_id,
                       image_userdata, username=None, node_name=None, **options):
        self.__prepare_key_pair(key_name,
                                private_key_path,
                                public_key_path,
                                options.get('image_user_password'))

        options['name'] = node_name
        options['size'] = flavor
        options['image'] = image_id
        if security_group:
            options['security_groups'] = security_group
        options['ex_userdata'] = image_userdata
        options['username'] = username
        options['networks'] = options.pop('network_ids', None)

        if self.driver.get_key_pair(key_name):
            options['auth'] = NodeAuthSSHKey(self.driver.get_key_pair(key_name).public_key)
        else:
            options['auth'] = NodeAuthPassword(options.get('image_user_password'))

        for key in options.keys():
            try:
                list_fn = self.__get_function_by_pattern('list_{0}'.format(key))
            except AttributeError:
                # skip non-existing
                continue
            populated_list = self.__get_name_or_id(options[key], list_fn())
            if populated_list:
                if key.endswith('s'):
                    options[key] = populated_list
                else:
                    options[key] = populated_list[0]

        node = self.driver.create_node(**options)
        if node:
            return node.id
        return None

    def is_instance_running(self, instance_id):
        instance = self.__get_instance(instance_id)
        if not instance:
            log.warn('could not find instance with id %s', instance_id)
            return False
        return instance.state == NodeState.RUNNING

    def stop_instance(self, instance_id):
        instance = self.__get_instance(instance_id)
        if not instance:
            log.warn('could not find instance with id %s', instance_id)
            return
        log.info('stopping %s', instance.name)
        instance.destroy()

    def get_ips(self, instance_id):
        instance = self.__get_instance(instance_id)
        if not instance:
            log.warn('could not find instance with id %s', instance_id)
            return []
        return instance.public_ips + instance.private_ips

    def __prepare_key_pair(self, key_name, private_key_path, public_key_path, password):
        if not key_name:
            log.warn('user_key_name has not been defined, assuming password based authentication')
            return

        try:
            list_key_pairs = self.__get_function_by_pattern('list_key_pairs')
        except AttributeError:
            raise UnsupportedError('key management not supported by provider')
        try:
            self.__get_function_or_ex_function('import_key_pair_from_file')
        except AttributeError:
            raise UnsupportedError('key import not supported by provider')
        try:
            self.__get_function_or_ex_function('create_key_pair')
        except AttributeError:
            raise UnsupportedError('key creation not supported by provider')

        if key_name in [k.name for k in list_key_pairs()]:
            log.info('Key pair (%s) already exists, skipping import.', key_name)
            return

        if public_key_path:
            log.debug("importing public key from path %s", public_key_path)
            key_import = self.__get_function_or_ex_function('import_key_pair_from_file')
            if not key_import(name=key_name, key_file_path=os.path.expandvars(os.path.expanduser(public_key_path))):
                raise KeypairError('failure during import of public key {p}'.format(p=public_key_path))
        elif private_key_path:
            if not private_key_path.endswith('.pem'):
                raise KeypairError('can only work with .pem private keys, derive public key and set user_key_public')
            log.debug("deriving and importing public key from private key")
            self.__import_pem(key_name, private_key_path, password)
        elif os.path.exists(os.path.join(self.storage_path, '{p}.pem'.format(p=key_name))):
            self.__import_pem(key_name, os.path.join(self.storage_path, '{}.pem'.format(key_name)), password)
        else:
            with open(os.path.join(self.storage_path, '{p}.pem'.format(p=key_name)), 'w') as new_key_file:
                new_key_file.write(self.__get_function_or_ex_function('create_key_pair')(name=key_name))
            self.__import_pem(key_name, os.path.join(self.storage_path, '{p}.pem'.format(p=key_name)), password)

    def __import_pem(self, key_name, pem_file_path, password):
        """
        Import PEM certificate with provider
        :param key_name: name of the key to import
        :param pem_file_path: path to the pem file
        :param password: optional password for the pem file
        """
        key_import = self.__get_function_or_ex_function('import_key_pair_from_file')
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
                key_import(name=key_name, key_file_path=f.name)

    def __get_function_by_pattern(self, pattern):
        """
        Return first function whose name *contains* the string `pattern`.

        :param func: partial function name (ex. key_pair)
        :return: list function that goes with it (ex. list_key_pairs)
        """
        function_names = [name for name in dir(self.driver) if pattern in name]
        if function_names:
            name = function_names[0]
            if len(function_names) > 1:
                log.warn(
                    "Several functions match pattern `%s`: %r -- using first one!",
                    pattern, function_names)
            return getattr(self.driver, name)
        else:
            # no such function
            raise AttributeError(
                "No function name contains `{0}` in class `{1}`"
                .format(pattern, self.__class__.__name__))

    def __get_function_or_ex_function(self, func_name):
        """
        Check if a function (or an 'extended' function) exists for a key on a driver, and if it does, return it.
        :param func_name: name of the function
        :return: a callable or none
        """
        # try function name as given
        try:
            return getattr(self.driver, func_name)
        except AttributeError:
            pass
        # try prefixing name with `ex_`
        try:
            return getattr(self.driver, 'ex_' + func_name)
        except AttributeError:
            pass
        # no such function
        raise AttributeError(
            "No function named `{0}` or `{1}` in class `{2}`"
            .format(func_name, 'ex_'+func_name, self.__class__.__name__))

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

    @staticmethod
    def __pop_driver_auth_args(**kwargs):
        """
        Try to construct the arguments that should be passed as initialization of a driver
        :param kwargs: options passed to the class
        :return: args or none
        """
        if 'username' in kwargs:
            return [kwargs.pop('username'), kwargs.pop('password')]
        elif 'access_token' in kwargs:
            return kwargs.pop('access token')
        elif 'access_id' in kwargs:
            return kwargs.pop('access_id'), kwargs.pop('secret_key')
        elif 'service_account_email' in kwargs:
            return [kwargs.pop('service_account_email'), kwargs.pop('pem_file')]
        elif 'client_id' in kwargs:
            return [kwargs.pop('client_id'), kwargs.pop('client_secret')]
        return None

