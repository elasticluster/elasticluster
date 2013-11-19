#! /usr/bin/env python
#
# Copyright (C) 2013 GC3, University of Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'

# System imports
import os
import urllib
import threading

# External modules
import boto
from boto import ec2
from paramiko import DSSKey, RSAKey, PasswordRequiredException
from paramiko.ssh_exception import SSHException

# Elasticluster imports
from elasticluster import log
from elasticluster.providers import AbstractCloudProvider
from elasticluster.exceptions import SecurityGroupError, KeypairError, \
    ImageError, InstanceError, ClusterError


class BotoCloudProvider(AbstractCloudProvider):
    """
    Uses boto to connect to an ec2 or openstack web service to manage
    the virtual instances
    """
    __node_start_lock = threading.Lock()  # lock used for node startup

    def __init__(self, ec2_url, ec2_region, ec2_access_key, ec2_secret_key,
                 storage_path=None):
        self._url = ec2_url
        self._region_name = ec2_region
        self._access_key = ec2_access_key
        self._secret_key = ec2_secret_key

        # read all parameters from url
        proto, opaqueurl = urllib.splittype(ec2_url)
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
        self._cached_instances = []
        self._images = None

    def _connect(self):
        """
        Connects to the ec2 cloud provider
        """
        # check for existing connection
        if self._connection:
            return self._connection

        try:
            log.debug("Connecting to ec2 host %s", self._ec2host)
            region = ec2.regioninfo.RegionInfo(name=self._region_name,
                                               endpoint=self._ec2host)

            # connect to webservice
            self._connection = boto.connect_ec2(
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                is_secure=self._secure,
                host=self._ec2host, port=self._ec2port,
                path=self._ec2path, region=region)

            # list images to see if the connection works
            log.debug("Connection has been successful.")
            # images = self._connection.get_all_images()
            # log.debug("%d images found on cloud %s",
            #           len(images), self._ec2host)

        except Exception as e:
            log.error("connection to cloud could not be "
                      "established: message=`%s`", str(e))
            raise

        return self._connection

    def start_instance(self, key_name, public_key_path, private_key_path,
                       security_group, flavor, image_id, image_userdata,
                       username=None):
        """
        Starts an instance in the cloud on the specified cloud
        provider (configuration option) and returns the id of the
        started instance.
        """
        connection = self._connect()

        log.debug("Checking keypair `%s`.", key_name)
        # the `_check_keypair` method has to be called within a lock,
        # since it will upload the key if it does not exist and if this
        # happens for every node at the same time ec2 will throw an error
        # message (see issue #79)
        with BotoCloudProvider.__node_start_lock:
            self._check_keypair(key_name, public_key_path, private_key_path)

        log.debug("Checking security group `%s`.", security_group)
        self._check_security_group(security_group)
        # image_id = self._find_image_id(image_id)

        try:
            reservation = connection.run_instances(
                image_id, key_name=key_name, security_groups=[security_group],
                instance_type=flavor, user_data=image_userdata)
        except Exception, ex:
            log.error("Error starting instance: %s", ex)
            if "TooManyInstances" in ex:
                raise ClusterError(ex)
            else:
                raise InstanceError(ex)

        vm = reservation.instances[-1]

        # cache instance object locally for faster access later on
        self._instances[vm.id] = vm

        return vm.id

    def stop_instance(self, instance_id):
        """
        Terminates the given instance.
        """
        instance = self._load_instance(instance_id)
        instance.terminate()

    def get_ips(self, instance_id):
        self._load_instance(instance_id)
        instance = self._load_instance(instance_id)

        return instance.private_ip_address, instance.ip_address

    def is_instance_running(self, instance_id):
        """
        Checks if an instance with the given id is up and running.
        """
        self._load_instance(instance_id)

        instance = self._load_instance(instance_id)

        if instance.update() == "running":
            return True
        else:
            return False

    def _load_instance(self, instance_id):
        """
        Checks if an instance with the given id is cached. If not it
        will connect to the cloud and put it into the local cache
        _instances. An InstanceError is returned if the instance can't
        be found in the local cache or in the cloud.
        """
        connection = self._connect()
        if instance_id in self._instances:
            return self._instances[instance_id]

        # Instance not in the internal dictionary.
        # First, check the internal cache:
        if instance_id not in [i.id for i in self._cached_instances]:
            # Refresh the cache, just in case
            self._cached_instances = []
            reservations = connection.get_all_instances()
            for res in reservations:
                self._cached_instances.extend(res.instances)

        for inst in self._cached_instances:
            if inst.id == instance_id:
                self._instances[instance_id] = inst
                return inst

        # If we reached this point, the instance was not found neither
        # in the cache or on the website.
        raise InstanceError("the given instance `%s` was not found "
                            "on the coud" % instance_id)

    def _check_keypair(self, name, public_key_path, private_key_path):
        connection = self._connect()
        keypairs = connection.get_all_key_pairs()
        keypairs = dict((k.name, k) for k in keypairs)

        # decide if dsa or rsa key is provided
        pkey = None
        is_dsa_key = False
        try:
            pkey = DSSKey.from_private_key_file(private_key_path)
            is_dsa_key = True
        except PasswordRequiredException:
            log.warning(
                "Unable to check key file `%s` because it is encrypted with a "
                "password. Please, ensure that you added it to the SSH agent "
                "with `ssh-add %s`", private_key_path, private_key_path)
        except SSHException:
            try:
                pkey = RSAKey.from_private_key_file(private_key_path)
            except PasswordRequiredException:
                log.warning(
                    "Unable to check key file `%s` because it is encrypted with a "
                    "password. Please, ensure that you added it to the SSH agent "
                    "with `ssh-add %s`", private_key_path, private_key_path)
            except SSHException:
                raise KeypairError('File `%s` is neither a valid DSA key '
                                   'or RSA key.' % private_key_path)

        # create keys that don't exist yet
        if name not in keypairs:
            log.warning(
                "Keypair `%s` not found on resource `%s`, Creating a new one",
                name, self._url)
            with open(os.path.expanduser(public_key_path)) as f:
                key_material = f.read()
                try:
                    # check for DSA on amazon
                    if "amazon" in self._ec2host and is_dsa_key:
                        log.error(
                            "Apparently, amazon does not support DSA keys. "
                            "Please specify a valid RSA key.")
                        raise KeypairError(
                            "Apparently, amazon does not support DSA keys."
                            "Please specify a valid RSA key.")

                    connection.import_key_pair(name, key_material)
                except Exception, ex:
                    log.error(
                        "Could not import key `%s` with name `%s` to `%s`",
                        name, public_key_path, self._url)
                    raise KeypairError(
                        "could not create keypair `%s`: %s" % (name, ex))
        else:
            # check fingerprint
            cloud_keypair = keypairs[name]

            if pkey:
                fingerprint = str.join(
                    ':', (i.encode('hex') for i in pkey.get_fingerprint()))

                if fingerprint != cloud_keypair.fingerprint:
                    if "amazon" in self._ec2host:
                        log.error(
                            "Apparently, Amazon does not compute the RSA key "
                            "fingerprint as we do! We cannot check if the "
                            "uploaded keypair is correct!")
                    else:
                        raise KeypairError(
                            "Keypair `%s` is present but has "
                            "different fingerprint. Aborting!" % name)

    def _check_security_group(self, name):
        """
        Checks if the security group exists.
        TODO: if the configuration file specify some rules, ensure
              that the security group has those rules, and if the security
              group does not exists, create it.
        """
        connection = self._connect()
        security_groups = connection.get_all_security_groups()
        if not security_groups:
            raise SecurityGroupError(
                "the specified security group %s does not exist" % name)

        security_groups = dict((s.name, s) for s in security_groups)

        if name not in security_groups:
            raise SecurityGroupError(
                "the specified security group %s does not exist" % name)

    def _find_image_id(self, image_id):
        """
        Finds an image id to a given id or name.
        """
        if not self._images:
            connection = self._connect()
            self._images = connection.get_all_images()

        image_id_cloud = None
        for i in self._images:
            if i.id == image_id or i.name == image_id:
                image_id_cloud = i.id
                break

        if image_id_cloud:
            return image_id_cloud
        else:
            raise ImageError(
                "Could not find given image id `%s`" % image_id)
