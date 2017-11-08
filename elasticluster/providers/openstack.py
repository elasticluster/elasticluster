#!/usr/bin/env python
# -*- coding: utf-8 -*-#
# @(#)openstack.py
#
#
# Copyright (C) 2013, 2015 S3IT, University of Zurich. All rights reserved.
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
    'Antonio Messina <antonio.s.messina@gmail.com>',
    'Riccardo Murri <riccardo.murri@gmail.com>'
    ])

# System imports
import os
import threading
from warnings import warn
from time import sleep

# External modules

# handle missing OpenStack libraries in Python 2.6: delay ImportError until actually
# used but raise a warning in the meantime; since we pinned the 2.6 dependencies
# to the pre-3.0.0 release, everything *should* work with just the "nova" API.
class _Unavailable(object):
    def __init__(self, missing):
        self.__missing = missing
    def Client(self, *args, **kwargs):
        warn("Trying to initialize `{module}` which is not available."
             " A placeholder object will be used instead, but it will raise"
             " `ImportError` later if there is any actual attempt at using it."
             .format(module=self.__missing),
             ImportWarning)
        class _Unavailable(object):
            def __init__(self, missing):
                self.__missing = missing
            def __getattr__(self, name):
                return self
            def __call__(self, *args, **kwargs):
                raise ImportError(
                    "Trying to actually use client class from module `{module}`"
                    " which could not be imported. Aborting."
                    .format(module=self.__missing))
        return _Unavailable(self.__missing)

import keystoneauth1
try:
    from glanceclient import client as glance_client
except ImportError:
    glance_client = _Unavailable('python-glanceclient')
try:
    from neutronclient.v2_0 import client as neutron_client
    from neutronclient.common.exceptions import BadRequest as BadNeutronRequest
except ImportError:
    neutron_client = _Unavailable('python-neutronclient')
    class BadNeutronRequest(Exception):
        """Placeholder to avoid syntax errors."""
        pass
from cinderclient import client as cinder_client
from novaclient import client as nova_client
from novaclient.exceptions import NotFound

from paramiko import DSSKey, RSAKey, PasswordRequiredException
from paramiko.ssh_exception import SSHException

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


# these defaults should be kept in sync w/ `conf.py`
DEFAULT_OS_COMPUTE_API_VERSION='2'
DEFAULT_OS_IDENTITY_API_VERSION='3'
DEFAULT_OS_IMAGE_API_VERSION='2'
DEFAULT_OS_NETWORK_API_VERSION='2.0'  # no choice as of Aug. 2017
DEFAULT_OS_VOLUME_API_VERSION='2'

_NO_DEFAULT = object()
"""
Special value used in `_get_os_config_value` to indicate that a
value *must* be provided.
"""



class OpenStackCloudProvider(AbstractCloudProvider):
    """
    This implementation of
    :py:class:`elasticluster.providers.AbstractCloudProvider` uses the
    OpenStack native python bindings to connect to OpenStack clouds
    and manage instances.

    :param str username: username of the keystone user
    :param str password: password of the keystone user
    :param str project_name: name of the project to use
    :param str user_domain_name: name of the user domain to use
    :param str project_domain_name: name of the project domain to use
    :param str auth_url: url of keystone endpoint
    :param str region: OpenStack region to use
    :param str storage_path: path to store temporary data
    :param bool request_floating_ip: Whether ip are assigned automatically
                                    `True` or floating ips have to be
                                    assigned manually `False`
    :param identity_api_version: What version of the Keystone API to use.
        Valid values are the strings `"v2"` or `"v3"`,
        or `None` (default, meaning try v3 first and fall-back to v2).
    :param cacert: Path to CA certificate bundle (for verifying HTTPS sessions)
        or ``None`` to use the systems' default.
    """

    __node_start_lock = threading.Lock()
    """
    Lock used for node startup.
    """

    def __init__(self, username, password, project_name, auth_url,
                 user_domain_name="default", project_domain_name="default",
                 region_name=None, storage_path=None,
                 request_floating_ip=False,
                 compute_api_version=DEFAULT_OS_COMPUTE_API_VERSION,
                 image_api_version=DEFAULT_OS_IMAGE_API_VERSION,
                 network_api_version=DEFAULT_OS_NETWORK_API_VERSION,
                 volume_api_version=DEFAULT_OS_VOLUME_API_VERSION,
                 # this can be auto-detected
                 identity_api_version=None,
                 # this is deprecated in favor of `compute_api_version`
                 nova_api_version=None,
                 cacert=None,  # keep in sync w/ default in novaclient.Client()
    ):
        # OpenStack connection params
        self._os_auth_url = self._get_os_config_value('auth URL', auth_url, ['OS_AUTH_URL']).rstrip('/')
        self._os_cacert = self._get_os_config_value('cacert', cacert, ['OS_CACERT'], default=None)
        self._os_username = self._get_os_config_value('user name', username, ['OS_USERNAME'])
        self._os_user_domain_name = self._get_os_config_value('user domain name', user_domain_name, ['OS_USER_DOMAIN_NAME'], 'default')
        self._os_password = self._get_os_config_value('password', password, ['OS_PASSWORD'])
        self._os_tenant_name = self._get_os_config_value('project name', project_name, ['OS_PROJECT_NAME', 'OS_TENANT_NAME'])
        self._os_project_domain_name = self._get_os_config_value('project domain name', project_domain_name, ['OS_PROJECT_DOMAIN_NAME'], 'default')
        self._os_region_name = self._get_os_config_value('region_name', region_name, ['OS_REGION_NAME'], '')

        # the OpenStack versioning mess
        if nova_api_version is not None:
            warn('Deprecated parameter `nova_api_version` given to OpenStackProvider;'
                 ' use `compute_api_version` instead', DeprecationWarning)
            compute_api_version = nova_api_version
        self._compute_api_version = compute_api_version
        self._image_api_version = image_api_version
        self._network_api_version = network_api_version
        os_network_api_version = os.getenv('OS_NETWORK_API_VERSION', None)
        if  (os_network_api_version
             and os_network_api_version != DEFAULT_OS_NETWORK_API_VERSION):
            warn("Environment variable OS_NETWORK_API_VERSION set,"
                 " but ElastiCluster does not support selecting"
                 " the OpenStack Networking API (Neutron) version yet.",
                 UserWarning)
        self._volume_api_version = volume_api_version
        self._identity_api_version = identity_api_version or self.__detect_os_identity_api_version()

        # these will be initialized later by `_init_os_api()`
        self.nova_client = None
        self.neutron_client = None
        self.glance_client = None
        self.cinder_client = None

        # local state
        self.request_floating_ip = request_floating_ip
        self._instances = {}
        self._cached_instances = {}

    @staticmethod
    def _get_os_config_value(thing, value, varnames, default=_NO_DEFAULT):
        assert varnames, "List of env variable names cannot be empty"
        for varname in varnames:
            env_value = os.getenv(varname, None)
            if env_value is not None:
                if value is not None and env_value != value:
                    warn("OpenStack {thing} is present both in the environment"
                         " and the config file. Environment variable {varname}"
                         " takes precedence, but this may change in the future."
                         .format(thing=thing, varname=varname),
                         FutureWarning)
                else:
                    log.debug('OpenStack %s taken from env variable %s',
                              thing, varname)
                return env_value
        if value:
            return value
        elif default is _NO_DEFAULT:
            # first variable name is preferred; others are for backwards-compatibility only
            raise RuntimeError(
                "There is no default value for OpenStack {0};"
                " please specify one in the config file"
                " or using environment variable {1}."
                .format(thing, varnames[0]))
        else:
            return default

    def _init_os_api(self):
        """
        Initialise client objects for talking to OpenStack API.

        This is in a separate function so to be called by ``__init__``
        and ``__setstate__``.
        """
        if not self.nova_client:
            log.debug("Initializing OpenStack API clients:"
                      " OS_AUTH_URL='%s'"
                      " OS_USERNAME='%s'"
                      " OS_USER_DOMAIN_NAME='%s'"
                      " OS_PROJECT_NAME='%s'"
                      " OS_PROJECT_DOMAIN_NAME='%s'"
                      " OS_REGION_NAME='%s'"
                      " OS_CACERT='%s'"
                      "", self._os_auth_url,
                      self._os_username, self._os_user_domain_name,
                      self._os_tenant_name, self._os_project_domain_name,
                      self._os_region_name,
                      self._os_cacert)
            sess = self.__init_keystone_session()
            log.debug("Creating OpenStack Compute API (Nova) v%s client ...", self._compute_api_version)
            self.nova_client = nova_client.Client(
                self._compute_api_version, session=sess,
                region_name=self._os_region_name,
                cacert=self._os_cacert)
            log.debug("Creating OpenStack Network API (Neutron) client ...")
            self.neutron_client = neutron_client.Client(
                #self._network_api_version,  ## doesn't work as of Neutron Client 2 :-(
                session=sess, region_name=self._os_region_name,
                ca_cert=self._os_cacert)
            # FIXME: Glance's `Client` class does not take an explicit
            # `cacert` parameter, instead it relies on the `session`
            # argument being "A keystoneauth1 session that should be
            # used for transport" -- I presume this means that
            # `cacert` only needs to be set there.  Is this true of
            # other OpenStack client classes as well?
            log.debug("Creating OpenStack Image API (Glance) v%s client ...", self._image_api_version)
            self.glance_client = glance_client.Client(
                self._image_api_version, session=sess,
                region_name=self._os_region_name)
            log.debug("Creating OpenStack Volume API (Cinder) v%s client ...", self._volume_api_version)
            self.cinder_client = cinder_client.Client(
                self._volume_api_version, session=sess,
                region_name=self._os_region_name,
                cacert=self._os_cacert)

    def __init_keystone_session(self):
        """Create and return a Keystone session object."""
        api = self._identity_api_version  # for readability
        tried = []
        if api in ['3', None]:
            sess = self.__init_keystone_session_v3(check=(api is None))
            tried.append('v3')
            if sess:
                return sess
        if api in ['2', None]:
            sess = self.__init_keystone_session_v2(check=(api is None))
            tried.append('v2')
            if sess:
                return sess
        raise RuntimeError(
            "Cannot establish Keystone session (tried: {0})."
            .format(', '.join(tried)))

    def __init_keystone_session_v2(self, check=False):
        """Create and return a session object using Keystone API v2."""
        from keystoneauth1 import loading as keystone_v2
        loader = keystone_v2.get_plugin_loader('password')
        auth = loader.load_from_options(
            auth_url=self._os_auth_url,
            username=self._os_username,
            password=self._os_password,
            project_name=self._os_tenant_name,
        )
        sess = keystoneauth1.session.Session(auth=auth, verify=self._os_cacert)
        if check:
            log.debug("Checking that Keystone API v2 session works...")
            try:
                # if session is invalid, the following will raise some exception
                nova = nova_client.Client(self.compute_api_version, session=sess, cacert=self._os_cacert)
                nova.flavors.list()
            except keystoneauth1.exceptions.NotFound as err:
                log.warning("Creating Keystone v2 session failed: %s", err)
                return None
            except keystoneauth1.exceptions.ClientException as err:
                log.error("OpenStack server rejected request (likely configuration error?): %s", err)
                return None  # FIXME: should we be raising an error instead?
        # if we got to this point, v2 session is valid
        log.info("Using Keystone API v2 session to authenticate to OpenStack")
        return sess

    def __init_keystone_session_v3(self, check=False):
        """
        Return a new session object, created using Keystone API v3.

        .. note::

          Note that the only supported authN method is password authentication;
          token or other plug-ins are not currently supported.
        """
        try:
            # may fail on Python 2.6?
            from keystoneauth1.identity import v3 as keystone_v3
        except ImportError:
            log.warning("Cannot load Keystone API v3 library.")
            return None
        auth = keystone_v3.Password(
            auth_url=self._os_auth_url,
            username=self._os_username,
            password=self._os_password,
            user_domain_name=self._os_user_domain_name,
            project_domain_name=self._os_project_domain_name,
            project_name=self._os_tenant_name,
        )
        sess = keystoneauth1.session.Session(auth=auth, verify=self._os_cacert)
        if check:
            log.debug("Checking that Keystone API v3 session works...")
            try:
                # if session is invalid, the following will raise some exception
                nova = nova_client.Client(self.compute_api_version, session=sess)
                nova.flavors.list()
            except keystoneauth1.exceptions.NotFound as err:
                log.warning("Creating Keystone v3 session failed: %s", err)
                return None
            except keystoneauth1.exceptions.ClientException as err:
                log.error("OpenStack server rejected request (likely configuration error?): %s", err)
                return None  # FIXME: should we be raising an error instead?
        # if we got to this point, v3 session is valid
        log.info("Using Keystone API v3 session to authenticate to OpenStack")
        return sess


    def __detect_os_identity_api_version(self):
        """
        Return preferred OpenStack Identity API version (either one of the two strings ``'2'`` or ``'3'``) or ``None``.

        The following auto-detection strategies are tried (in this order):

        #. Read the environmental variable `OS_IDENTITY_API_VERSION` and check if its value is one of the two strings ``'2'`` or ``'3'``;
        #. Check if a version tag like ``/v3`` or ``/v2.0`` ends the OpenStack auth URL.

        If none of the above worked, return ``None``.

        For more information on ``OS_IDENTITY_API_VERSION``, please see
        `<https://docs.openstack.org/developer/python-openstackclient/authentication.html>`_.
        """
        ver = os.getenv('OS_IDENTITY_API_VERSION', '')
        if ver == '3':
            log.debug(
                "Using OpenStack Identity API v3"
                " because of environmental variable setting `OS_IDENTITY_API_VERSION=3`")
            return '3'
        elif ver == '2' or ver.startswith('2.'):
            log.debug(
                "Using OpenStack Identity API v2"
                " because of environmental variable setting `OS_IDENTITY_API_VERSION=2`")
            return '2'
        elif self._os_auth_url.endswith('/v3'):
            log.debug(
                "Using OpenStack Identity API v3 because of `/v3` ending in auth URL;"
                " set environmental variable OS_IDENTITY_API_VERSION to force use of Identity API v2 instead.")
            return '3'
        elif self._os_auth_url.endswith('/v2.0'):
            log.debug(
                "Using OpenStack Identity API v2 because of `/v2.0` ending in auth URL;"
                " set environmental variable OS_IDENTITY_API_VERSION to force use of Identity API v3 instead.")
            return '2'
        else:
            # auto-detection failed, need to probe
            return None


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
        self._init_os_api()

        vm_start_args = {}

        log.debug("Checking keypair `%s` ...", key_name)
        with OpenStackCloudProvider.__node_start_lock:
            self._check_keypair(key_name, public_key_path, private_key_path)
        vm_start_args['key_name'] = key_name

        security_groups = [sg.strip() for sg in security_group.split(',')]
        self._check_security_groups(security_groups)
        vm_start_args['security_groups'] = security_groups


        # Check if the image id is present.
        if image_id not in [img.id for img in self._get_images()]:
            raise ImageError(
                    "No image found with ID `{0}` in project `{1}` of cloud {2}"
                    .format(image_id, self._os_tenant_name, self._os_auth_url))
        vm_start_args['userdata'] = image_userdata

        # Check if the flavor exists
        flavors = [fl for fl in self._get_flavors() if fl.name == flavor]
        if not flavors:
            raise FlavorError(
                "No flavor found with name `{0}` in project `{1}` of cloud {2}"
                .format(flavor, self._os_tenant_name, self._os_auth_url))
        flavor = flavors[0]

        network_ids = [net_id.strip()
                       for net_id in kwargs.pop('network_ids', '').split(',')]
        if network_ids:
            nics = [{'net-id': net_id, 'v4-fixed-ip': ''}
                    for net_id in network_ids ]
            log.debug("Specifying networks for node %s: %s",
                      node_name, ', '.join([nic['net-id'] for nic in nics]))
        else:
            nics = None
        vm_start_args['nics'] = nics

        if 'boot_disk_size' in kwargs:
            # check if the backing volume is already there
            volume_name = '{name}-{id}'.format(name=node_name, id=image_id)
            if volume_name in [v.name for v in self._get_volumes()]:
                raise ImageError(
                    "Volume `{0}` already exists in project `{1}` of cloud {2}"
                    .format(volume_name, self._os_tenant_name, self._os_auth_url))

            log.info('Creating volume `%s` to use as VM disk ...', volume_name)
            try:
                bds = int(kwargs['boot_disk_size'])
                if bds < 1:
                    raise ValueError('non-positive int')
            except (ValueError, TypeError):
                raise ConfigurationError(
                    "Invalid `boot_disk_size` specified:"
                    " should be a positive integer, got {0} instead"
                    .format(kwargs['boot_disk_size']))
            volume = self.cinder_client.volumes.create(
                size=bds, name=volume_name, imageRef=image_id,
                volume_type=kwargs.pop('boot_disk_type'))

            # wait for volume to come up
            volume_available = False
            while not volume_available:
                for v in self._get_volumes():
                    if v.name == volume_name and v.status == 'available':
                        volume_available = True
                        break
                sleep(1)  # FIXME: hard-coded waiting time

            # ok, use volume as VM disk
            vm_start_args['block_device_mapping'] = {
                # FIXME: is it possible that `vda` is not the boot disk? e.g. if
                # a non-paravirtualized kernel is being used?  should we allow
                # to set the boot device as an image parameter?
                'vda': ('{id}:::{delete_on_terminate}'
                        .format(id=volume.id, delete_on_terminate=1)),
            }

        # due to some `nova_client.servers.create()` implementation weirdness,
        # the first three args need to be spelt out explicitly and cannot be
        # conflated into `**vm_start_args`
        vm = self.nova_client.servers.create(node_name, image_id, flavor, **vm_start_args)

        # allocate and attach a floating IP, if requested
        if self.request_floating_ip:
            # We need to list the floating IPs for this instance
            try:
                # python-novaclient <8.0.0
                floating_ips = [ip for ip in self.nova_client.floating_ips.list()
                                if ip.instance_id == vm.id]
            except AttributeError:
                floating_ips = self.neutron_client.list_floatingips(id=vm.id)
            # allocate new floating IP if none given
            if not floating_ips:
                self._allocate_address(vm, network_ids)

        self._instances[vm.id] = vm

        return vm.id

    def stop_instance(self, instance_id):
        """Stops the instance gracefully.

        :param str instance_id: instance identifier
        """
        self._init_os_api()
        instance = self._load_instance(instance_id)
        instance.delete()
        del self._instances[instance_id]

    def get_ips(self, instance_id):
        """Retrieves all IP addresses associated to a given instance.

        :return: tuple (IPs)
        """
        self._init_os_api()
        instance = self._load_instance(instance_id)
        IPs = sum(instance.networks.values(), [])
        return IPs

    def is_instance_running(self, instance_id):
        """Checks if the instance is up and running.

        :param str instance_id: instance identifier

        :return: bool - True if running, False otherwise
        """
        self._init_os_api()
        # Here, it's always better if we update the instance.
        instance = self._load_instance(instance_id, force_reload=True)
        return instance.status == 'ACTIVE'

    # Protected methods

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
        self._init_os_api()
        # Read key. We do it as first thing because we need it either
        # way, to check the fingerprint of the remote keypair if it
        # exists already, or to create a new keypair.
        pkey = None
        try:
            pkey = DSSKey.from_private_key_file(private_key_path)
        except PasswordRequiredException:
            warn("Unable to check key file `{0}` because it is encrypted with a "
                 "password. Please, ensure that you added it to the SSH agent "
                 "with `ssh-add {1}`"
                 .format(private_key_path, private_key_path))
        except SSHException:
            try:
                pkey = RSAKey.from_private_key_file(private_key_path)
            except PasswordRequiredException:
                warn("Unable to check key file `{0}` because it is encrypted with a "
                     "password. Please, ensure that you added it to the SSH agent "
                     "with `ssh-add {1}`"
                     .format(private_key_path, private_key_path))
            except SSHException:
                raise KeypairError('File `%s` is neither a valid DSA key '
                                   'or RSA key.' % private_key_path)

        try:
            # Check if a keypair `name` exists on the cloud.
            keypair = self.nova_client.keypairs.get(name)

            # Check if it has the correct keypair, but only if we can read the local key
            if pkey:
                fingerprint = str.join(
                    ':', (i.encode('hex') for i in pkey.get_fingerprint()))
                if fingerprint != keypair.fingerprint:
                    raise KeypairError(
                        "Keypair `%s` is present but has "
                        "different fingerprint. Aborting!" % name)
            else:
                warn("Unable to check if the keypair is using the correct key.")
        except NotFound:
            log.warning(
                "Keypair `%s` not found on resource `%s`, Creating a new one",
                name, self._os_auth_url)

            # Create a new keypair
            with open(os.path.expanduser(public_key_path)) as f:
                key_material = f.read()
                try:
                    self.nova_client.keypairs.create(name, key_material)
                except Exception as ex:
                    log.error(
                        "Could not import key `%s` with name `%s` to `%s`",
                        name, public_key_path, self._os_auth_url)
                    raise KeypairError(
                        "could not create keypair `%s`: %s" % (name, ex))


    def _check_security_groups(self, names):
        """
        Raise an exception if any of the named security groups does not exist.

        :param List[str] groups: List of security group names
        :raises: `SecurityGroupError` if group does not exist
        """
        self._init_os_api()
        log.debug("Checking existence of security group(s) %s ...", names)
        try:
            # python-novaclient < 8.0.0
            security_groups = self.nova_client.security_groups.list()
            existing = set(sg.name for sg in security_groups)
        except AttributeError:
            security_groups = self.neutron_client.list_security_groups()['security_groups']
            existing = set(sg[u'name'] for sg in security_groups)

        # TODO: We should be able to create the security group if it
        # doesn't exist and at least add a rule to accept ssh access.
        # Also, we should be able to add new rules to a security group
        # if needed.
        nonexisting = set(names) - existing
        if nonexisting:
            raise SecurityGroupError(
                "Security group(s) `{0}` do not exist"
                .format(', '.join(nonexisting)))

        # if we get to this point, all sec groups exist
        return True

    @memoize(120)
    def _get_images(self):
        """Get available images. We cache the results in order to reduce
        network usage.

        """
        self._init_os_api()
        try:
            # python-novaclient < 8.0.0
            return self.nova_client.images.list()
        except AttributeError:
            # ``glance_client.images.list()`` returns a generator, but callers
            # of `._get_images()` expect a Python list
            return list(self.glance_client.images.list())

    def _get_volumes(self):
        """Return list of available volumes."""
        self._init_os_api()
        return self.cinder_client.volumes.list()

    @memoize(120)
    def _get_flavors(self):
        """Get available flavors. We cache the results in order to reduce
        network usage.

        """
        self._init_os_api()
        return self.nova_client.flavors.list()

    def _load_instance(self, instance_id, force_reload=True):
        """
        Return instance with the given id.

        For performance reasons, the instance ID is first searched for in the
        collection of VM instances started by ElastiCluster
        (`self._instances`), then in the list of all instances known to the
        cloud provider at the time of the last update
        (`self._cached_instances`), and finally the cloud provider is directly
        queried.

        :param str instance_id: instance identifier
        :param bool force_reload:
          if ``True``, skip searching caches and reload instance from server
          and immediately reload instance data from cloud provider
        :return: py:class:`novaclient.v1_1.servers.Server` - instance
        :raises: `InstanceError` is returned if the instance can't
                 be found in the local cache or in the cloud.
        """
        self._init_os_api()
        if force_reload:
            try:
                # Remove from cache and get from server again
                vm = self.nova_client.servers.get(instance_id)
            except NotFound:
                raise InstanceNotFoundError(
                    "Instance `{instance_id}` not found"
                    .format(instance_id=instance_id))
            # update caches
            self._instances[instance_id] = vm
            self._cached_instances[instance_id] = vm

        # if instance is known, return it
        if instance_id in self._instances:
            return self._instances[instance_id]

        # else, check (cached) list from provider
        if instance_id not in self._cached_instances:
            # Refresh the cache, just in case
            self._cached_instances = dict(
                (vm.id, vm) for vm in self.nova_client.servers.list())

        if instance_id in self._cached_instances:
            inst = self._cached_instances[instance_id]
            self._instances[instance_id] = inst
            return inst

        # If we reached this point, the instance was not found neither
        # in the caches nor on the website.
        raise InstanceNotFoundError(
            "Instance `{instance_id}` not found"
            .format(instance_id=instance_id))

    def _allocate_address(self, instance, network_ids):
        """
        Allocates a floating/public ip address to the given instance.

        :param instance: instance to assign address to

        :param list network_id: List of IDs (as strings) of networks where to
        request allocation the floating IP.

        :return: public ip address
        """
        self._init_os_api()
        with OpenStackCloudProvider.__node_start_lock:
            try:
                # Use the `novaclient` API (works with python-novaclient <8.0.0)
                free_ips = [ip for ip in self.nova_client.floating_ips.list() if not ip.fixed_ip]
                if not free_ips:
                    free_ips.append(self.nova_client.floating_ips.create())
            except AttributeError:
                # Use the `neutronclient` API
                #
                # for some obscure reason, using `fixed_ip_address=None` in the
                # call to `list_floatingips()` returns *no* results (not even,
                # in fact, those with `fixed_ip_address: None`) whereas
                # `fixed_ip_address=''` acts as a wildcard and lists *all* the
                # addresses... so filter them out with a list comprehension
                free_ips = [ip for ip in
                            self.neutron_client.list_floatingips(fixed_ip_address='')['floatingips']
                            if ip['fixed_ip_address'] is None]
                if not free_ips:
                    # FIXME: OpenStack Network API v2 requires that we specify
                    # a network ID along with the request for a floating IP.
                    # However, ElastiCluster configuration allows for multiple
                    # networks to be connected to a VM, but does not give any
                    # hint as to which one(s) should be used for such requests.
                    # So we try them all, ignoring errors until one request
                    # succeeds and hope that it's the OK. One can imagine
                    # scenarios where this is *not* correct, but: (1) these
                    # scenarios are unlikely, and (2) the old novaclient code
                    # above has not even had the concept of multiple networks
                    # for floating IPs and no-one has complained in 5 years...
                    allocated_ip = None
                    for network_id in network_ids:
                        log.debug(
                            "Trying to allocate floating IP on network %s ...", network_id)
                        try:
                            allocated_ip = self.neutron_client.create_floatingip({
                                'floatingip': {'floating_network_id':network_id}})
                        except BadNeutronRequest as err:
                            log.debug(
                                "Failed allocating floating IP on network %s: %s",
                                network_id, err)
                        if allocated_ip:
                            free_ips.append(allocated_ip)
                            break
                        else:
                            continue  # try next network
            if free_ips:
                ip = free_ips.pop()
            else:
                raise RuntimeError(
                    "Could not allocate floating IP for VM {0}"
                    .format(vm.id))
            instance.add_floating_ip(ip)
        return ip.ip

    # Fix pickler
    def __getstate__(self):
        return {'auth_url': self._os_auth_url,
                'username': self._os_username,
                'password': self._os_password,
                'project_name': self._os_tenant_name,
                'project_domain_name': self._os_project_domain_name,
                'user_domain_name': self._os_user_domain_name,
                'region_name': self._os_region_name,
                'request_floating_ip': self.request_floating_ip,
                'instance_ids': self._instances.keys(),
                'compute_api_version': self.compute_api_version,
            }

    def __setstate__(self, state):
        self._os_auth_url = state['auth_url']
        self._os_username = state['username']
        self._os_password = state['password']
        self._os_tenant_name = state['project_name']
        self._os_user_domain_name = state['user_domain_name']
        self._os_project_domain_name = state['project_domain_name']
        self._os_region_name = state['region_name']
        self.request_floating_ip = state['request_floating_ip']
        self._compute_api_version = state.get('compute_api_version', DEFAULT_COMPUTE_API_VERSION),
        self._identity_api_version = state.get('identity_api_version', DEFAULT_IDENTITY_API_VERSION),
        self._image_api_version = state.get('image_api_version', DEFAULT_IMAGE_API_VERSION),
        self._network_api_version = state.get('network_api_version', DEFAULT_NETWORK_API_VERSION),
        self._volume_api_version = state.get('volume_api_version', DEFAULT_VOLUME_API_VERSION),
        self._instances = {}
        self._cached_instances = {}
        # these will be initialized later by `_init_os_api()`
        self.nova_client = None
        self.neutron_client = None
        self.glance_client = None
        self.cinder_client = None
