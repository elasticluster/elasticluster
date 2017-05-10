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
from libcloud.compute.base import NodeAuthSSHKey, NodeAuthPassword
from libcloud.compute.providers import get_driver
from libcloud.compute.types import NodeState
from libcloud.compute.types import Provider
from paramiko import SSHException

from elasticluster import AbstractCloudProvider
from elasticluster import log
from elasticluster.exceptions import KeypairError

EXPLICIT_CONFIG = [
    # 'floating_ip'
]


class LibCloud(AbstractCloudProvider):
    driver = None
    project_name = None
    floating_ip = False
    rules = None
    auth = None

    def __init__(self, driver_name, storage_path=None, **options):
        self.storage_path = storage_path
        if options.get('auth_url') and not options.get('ex_force_auth_url'):
            options['ex_force_auth_url'] = options.get('auth_url').rsplit('/', 1)[0]
        for provider in dir(Provider):
            drv, name = provider
            if driver_name == name:
                log.debug('selected libcloud driver %s', name)
                driver_class = get_driver(drv)
                self.driver = driver_class(options)
                break

    def __get_instance(self, instance_id):
        for node in self.driver.list_nodes():
            if node.id == instance_id:
                return node
        return None

    def starts_instance(self, key_name, public_key_path, private_key_path, security_group, flavor, image_id,
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

        if self.driver.get_key_pair(key_name):
            options['auth'] = NodeAuthSSHKey(self.driver.get_key_pair(key_name).public_key)
        else:
            options['auth'] = NodeAuthPassword(options.get('image_user_password'))

        for key in [k for k in options.keys() if k not in EXPLICIT_CONFIG]:
            list_function = next(self.__check_list_function(key), None)
            if list_function:
                populated_list = self.__check_name_or_id(options[key], list_function())
                if populated_list and len(populated_list) > 0:
                    if key.endswith('s'):
                        options[key] = populated_list
                    else:
                        options[key] = populated_list[0]

        node = self.driver.create_node(options)
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

        if not next(self.__check_list_function('key_pairs'), None):
            raise KeypairError('key management not supported by provider')
        if not self.__function_or_ex_function('import_key_pair_from_file'):
            raise KeypairError('key import not supported by provider')
        if not self.__function_or_ex_function('create_key_pair'):
            raise KeypairError('key creation not supported by provider')

        if key_name in [k.name for k in next(self.__check_list_function('key_pairs'))()]:
            log.info('Key pair (%s) is already installed.', key_name)
            return

        if public_key_path:
            log.debug("importing public key from path %s", public_key_path)
            key_import = self.__function_or_ex_function('import_key_pair_from_file')
            if not key_import(name=key_name, key_file_path=os.path.expandvars(os.path.expanduser(public_key_path))):
                raise KeypairError('failure during import of public key %s', public_key_path)
        elif private_key_path:
            if not private_key_path.endswith('.pem'):
                raise KeypairError('can only work with .pem private keys, derive public key and set user_key_public')
            log.debug("deriving and importing public key from private key")
            self.__import_pem(key_name, private_key_path, password)
        elif os.path.exists(os.path.join(self.storage_path, '{}.pem'.format(key_name))):
            self.__import_pem(key_name, os.path.join(self.storage_path, '{}.pem'.format(key_name)), password)
        else:
            with open(os.path.join(self.storage_path, '{}.pem'.format(key_name)), 'w') as new_key_file:
                new_key_file.write(self.__function_or_ex_function('create_key_pair')(name=key_name))
            self.__import_pem(key_name, os.path.join(self.storage_path, '{}.pem'.format(key_name)), password)

    """
    Import PEM certificate with provider
    """

    def __import_pem(self, key_name, pem_file_path, password):
        key_import = self.__function_or_ex_function('import_key_pair_from_file')
        try:
            pem = paramiko.RSAKey.from_private_key_file(os.path.expandvars(os.path.expanduser(pem_file_path)), password)
        except SSHException:
            try:
                pem = paramiko.DSSKey.from_private_key_file(os.path.expandvars(os.path.expanduser(pem_file_path)),
                                                            password)
            except SSHException:
                raise KeypairError('could not import %s in rsa or dss format', pem_file_path)
        if not pem:
            raise KeypairError('could not import %s', pem_file_path)
        else:
            f = NamedTemporaryFile('w+t')
            f.write('{} {}'.format(pem.get_name(), pem.get_base64()))
            key_import(name=key_name, key_file_path=f.name)
            f.close()

    """
    Check if a list function exists for a key on a driver
    """

    def __check_list_function(self, func):
        for lf in [getattr(self.driver, c, None) for c in dir(self.driver) if 'list_{}'.format(func) in c]:
            yield lf

    """
    Check if a function exists for a key on a driver, or if it is an 'extended' function.
    :returns a callable or none
    """

    def __function_or_ex_function(self, func):
        if func in dir(self.driver):
            return getattr(self.driver, func, None), func
        elif 'ex_{}'.format(func) in dir(self.driver):
            return getattr(self.driver, 'ex_'.format(func), None)
        return None

    """
    Check if a value chain (ex. 'a,b,c') exists in our list of known items (item.name | item.id)
    """

    @staticmethod
    def __check_name_or_id(values, known):
        result = []
        for element in [e.strip() for e in values.split(',')]:
            for item in [i for i in known if i.name == element or i.id == element]:
                result.append(item)
        return result
