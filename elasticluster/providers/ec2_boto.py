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
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>, Antonio Messina <antonio.s.messina@gmail.com>'

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
from elasticluster.exceptions import VpcError, SecurityGroupError, \
    SubnetError, KeypairError, ImageError, InstanceError, ClusterError


class BotoCloudProvider(AbstractCloudProvider):
    """This implementation of
    :py:class:`elasticluster.providers.AbstractCloudProvider` uses the boto
    ec2 interface to connect to ec2 compliant clouds and manage instances.

    Please check https://github.com/boto/boto for further information about
    the supported cloud platforms.

    :param str ec2_url: url to connect to cloud web service
    :param str ec2_region: region identifier
    :param str ec2_access_key: access key of the user account
    :param str ec2_secret_key: secret key of the user account
    :param str storage_path: path to store temporary data
    :param bool request_floating_ip: Whether ip are assigned automatically
                                    `True` or floating ips have to be
                                    assigned manually `False`
    """
    __node_start_lock = threading.Lock()  # lock used for node startup

    def __init__(self, ec2_url, ec2_region, ec2_access_key, ec2_secret_key,
                 vpc=None, storage_path=None, request_floating_ip=False):
        self._url = ec2_url
        self._region_name = ec2_region
        self._access_key = ec2_access_key
        self._secret_key = ec2_secret_key
        self._vpc = vpc
        self.request_floating_ip = request_floating_ip

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
        self._ec2_connection = None
        self._vpc_connection = None
        self._vpc_id = None
        self._region = None

        self._instances = {}
        self._cached_instances = []
        self._images = None

    def _connect(self):
        """Connects to the ec2 cloud provider

        :return: :py:class:`boto.ec2.connection.EC2Connection`
        :raises: Generic exception on error
        """
        # check for existing connection
        if self._ec2_connection:
            return self._ec2_connection

        if not self._vpc:
            vpc_connection = None

        try:
            log.debug("Connecting to ec2 host %s", self._ec2host)
            region = ec2.regioninfo.RegionInfo(name=self._region_name,
                                               endpoint=self._ec2host)

            # connect to webservice
            ec2_connection = boto.connect_ec2(
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                is_secure=self._secure,
                host=self._ec2host, port=self._ec2port,
                path=self._ec2path, region=region)
            log.debug("EC2 connection has been successful.")

            if self._vpc:
                vpc_connection = boto.connect_vpc(
                    aws_access_key_id=self._access_key,
                    aws_secret_access_key=self._secret_key,
                    is_secure=self._secure,
                    host=self._ec2host, port=self._ec2port,
                    path=self._ec2path, region=region)
                log.debug("VPC connection has been successful.")

                for vpc in vpc_connection.get_all_vpcs():
                    log.debug("Checking whether %s matches %s/%s" %
                        (self._vpc, vpc.tags['Name'], vpc.id))
                    if self._vpc in [vpc.tags['Name'], vpc.id]:
                        self._vpc_id = vpc.id
                        if self._vpc != self._vpc_id:
                            log.debug("VPC %s matches %s" %
                                (self._vpc, self._vpc_id))
                        break
                else:
                    raise VpcError('VPC %s does not exist.' % self._vpc)

            # list images to see if the connection works
            # images = self._ec2_connection.get_all_images()
            # log.debug("%d images found on cloud %s",
            #           len(images), self._ec2host)

        except Exception as e:
            log.error("connection to ec2 could not be "
                      "established: message=`%s`", str(e))
            raise

        self._ec2_connection, self._vpc_connection = (
            ec2_connection, vpc_connection)
        return self._ec2_connection

    def start_instance(self, key_name, public_key_path, private_key_path,
                       security_group, flavor, image_id, image_userdata,
                       username=None, node_name=None, network_ids=None,
                       **kwargs):
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
        connection = self._connect()

        log.debug("Checking keypair `%s`.", key_name)
        # the `_check_keypair` method has to be called within a lock,
        # since it will upload the key if it does not exist and if this
        # happens for every node at the same time ec2 will throw an error
        # message (see issue #79)
        with BotoCloudProvider.__node_start_lock:
            self._check_keypair(key_name, public_key_path, private_key_path)

        log.debug("Checking security group `%s`.", security_group)
        security_group_id = self._check_security_group(security_group)
        # image_id = self._find_image_id(image_id)

        if network_ids:
            interfaces = []
            for subnet in network_ids.split(','):
                subnet_id = self._check_subnet(subnet)

                interfaces.append(ec2.networkinterface.NetworkInterfaceSpecification(
                    subnet_id=subnet_id, groups=[security_group_id],
                    associate_public_ip_address=self.request_floating_ip))
            interfaces = ec2.networkinterface.NetworkInterfaceCollection(*interfaces)

            security_groups = []
        else:
            interfaces = None
            security_groups = [security_group]

        try:
            reservation = connection.run_instances(
                image_id, key_name=key_name, security_groups=security_groups,
                instance_type=flavor, user_data=image_userdata,
                network_interfaces=interfaces)
        except Exception, ex:
            log.error("Error starting instance: %s", ex)
            if "TooManyInstances" in ex:
                raise ClusterError(ex)
            else:
                raise InstanceError(ex)

        vm = reservation.instances[-1]
        vm.add_tag("Name", node_name)

        # cache instance object locally for faster access later on
        self._instances[vm.id] = vm

        return vm.id

    def stop_instance(self, instance_id):
        """Stops the instance gracefully.

        :param str instance_id: instance identifier
        """
        instance = self._load_instance(instance_id)
        instance.terminate()
        del self._instances[instance_id]

    def get_ips(self, instance_id):
        """Retrieves the private and public ip addresses for a given instance.

        :return: list (ips)
        """
        self._load_instance(instance_id)
        instance = self._load_instance(instance_id)
        IPs = [ip for ip in instance.private_ip_address, instance.ip_address if ip]

        # We also need to check if there is any floating IP associated
        if self.request_floating_ip and not self._vpc:
            # We need to list the floating IPs for this instance
            floating_ips = [ip for ip in self._ec2_connection.get_all_addresses() if ip.instance_id == instance.id]
            if not floating_ips:
                log.debug("Public ip address has to be assigned through "
                          "elasticluster.")
                ip = self._allocate_address(instance)
                # This is probably the preferred IP we want to use
                IPs.insert(0, ip)
            else:
                IPs = [ip.public_ip for ip in floating_ips] + IPs

        return list(set(IPs))

    def is_instance_running(self, instance_id):
        """Checks if the instance is up and running.

        :param str instance_id: instance identifier

        :return: bool - True if running, False otherwise
        """
        instance = self._load_instance(instance_id)

        if instance.update() == "running":
            # If the instance is up&running, ensure it has an IP
            # address.
            if not instance.ip_address and self.request_floating_ip:
                log.debug("Public ip address has to be assigned through "
                          "elasticluster.")
                self._allocate_address(instance)
                instance.update()
            return True
        else:
            return False

    def _allocate_address(self, instance):
        """Allocates a free public ip address to the given instance

        :param instance: instance to assign address to
        :type instance: py:class:`boto.ec2.instance.Reservation`

        :return: public ip address
        """
        connection = self._connect()
        free_addresses = [ ip for ip in connection.get_all_addresses() if not ip.instance_id]
        if not free_addresses:
            try:
                address = connection.allocate_address()
            except Exception, ex:
                log.error("Unable to allocate a public IP address to instance `%s`",
                          instance.id)
                return None

        try:
            address = free_addresses.pop()
            instance.use_ip(address)
            return address.public_ip
        except Exception, ex:
            log.error("Unable to associate IP address %s to instance `%s`",
                      address, instance.id)
            return None

    def _load_instance(self, instance_id):
        """Checks if an instance with the given id is cached. If not it
        will connect to the cloud and put it into the local cache
        _instances.

        :param str instance_id: instance identifier
        :return: py:class:`boto.ec2.instance.Reservation` - instance
        :raises: `InstanceError` is returned if the instance can't
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
        """First checks if the keypair is valid, then checks if the keypair
        is registered with on the cloud. If not the keypair is added to the
        users ssh keys.

        :param str name: name of the ssh key
        :param str public_key_path: path to the ssh public key file
        :param str private_key_path: path to the ssh private key file

        :raises: `KeypairError` if key is not a valid RSA or DSA key,
                 the key could not be uploaded or the fingerprint does not
                 match to the one uploaded to the cloud.
        """
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
        """Checks if the security group exists.

        :param str name: name of the security group
        :return: str - security group id of the security group
        :raises: `SecurityGroupError` if group does not exist
        """
        connection = self._connect()

        filters = {}
        if self._vpc:
            filters = {'vpc-id': self._vpc_id}

        security_groups = connection.get_all_security_groups(filters=filters)

        matching_groups = [
            group
            for group
             in security_groups
             if name in [group.name, group.id]
        ]
        if len(matching_groups) == 0:
            raise SecurityGroupError(
                "the specified security group %s does not exist" % name)
        elif len(matching_groups) == 1:
            return matching_groups[0].id
        elif self._vpc and len(matching_groups) > 1:
            raise SecurityGroupError(
                "the specified security group name %s matches "
                "more than one security group" % name)

    def _check_subnet(self, name):
        """Checks if the subnet exists.

        :param str name: name of the subnet
        :return: str - subnet id of the subnet
        :raises: `SubnetError` if group does not exist
        """
        # Subnets only exist in VPCs, so we don't need to worry about
        # the EC2 Classic case here.
        subnets = self._vpc_connection.get_all_subnets(
            filters={'vpcId': self._vpc_id})

        matching_subnets = [
            subnet
            for subnet
             in subnets
             if name in [subnet.tags.get('Name'), subnet.id]
        ]
        if len(matching_subnets) == 0:
            raise SubnetError(
                "the specified subnet %s does not exist" % name)
        elif len(matching_subnets) == 1:
            return matching_subnets[0].id
        else:
            raise SubnetError(
                "the specified subnet name %s matches more than "
                "one subnet" % name)

    def _find_image_id(self, image_id):
        """Finds an image id to a given id or name.

        :param str image_id: name or id of image
        :return: str - identifier of image
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
    
    def __getstate__(self):
        d = self.__dict__.copy()
        del d['_ec2_connection']
        del d['_vpc_connection']
        return d

    def __setstate__(self, state):
        self.__dict__ = state
        self._ec2_connection = None
        self._vpc_connection = None
        
