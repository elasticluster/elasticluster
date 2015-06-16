#!/usr/bin/env python
# Azure provider for elasticluster

# elasticluster 'azure' package conflicts with azure SDK. This fixes
# it by causing "import azure" to look for a system library module.
from __future__ import absolute_import

# System imports
import os
import pickle
from math import floor, ceil
import base64
import subprocess
import time
import re
import threading
import traceback
import random
import xml.etree.ElementTree as xmltree

# External imports
import azure
import azure.servicemanagement
from azure.servicemanagement._http import HTTPRequest
from azure.servicemanagement._http.httpclient import _HTTPClient
from azure.servicemanagement._common_serialization import _get_request_body
from urllib2 import quote as url_quote

# Elasticluster imports
from elasticluster import log
from elasticluster.providers import AbstractCloudProvider
from elasticluster.exceptions import CloudProviderError

SSH_PORT = 22
PORT_MAP_OFFSET = 1200
DEFAULT_WAIT_TIMEOUT = 600
WAIT_RESULT_SLEEP = 10
VNET_NS = 'http://schemas.microsoft.com/ServiceHosting' \
          '/2011/07/NetworkConfiguration'
# general-purpose retry parameters
RETRIES = 50
RETRY_SLEEP = 20
RETRY_SLEEP_RND = 10
VHD_DELETE_ATTEMPTS = 100
VHD_DELETE_INTERVAL = 10

# resource-management constants
VMS_PER_CLOUD_SERVICE = 20
VMS_PER_STORAGE_ACCOUNT = 40
VMS_PER_VNET = 2000
CLOUD_SERVICES_PER_SUBSCRIPTION = 20

# helper functions


def _retry_sleep():
    return RETRY_SLEEP + random.randint(0, RETRY_SLEEP_RND)


def _run_command(args):
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    return proc.returncode, stdout, stderr


def _check_positive_integer(name, value):
    ret = -1
    try:
        if '.' in value:
            raise ValueError
        ret = int(value)
        if ret < 1:
            raise ValueError
    except Exception:
        err = "invalid value '%s' for %s, must be integer > 0" % (
            value, name)
        log.error(err)
        raise Exception(err)
    return ret


def ceil_div(aaa, bbb):
    return int(ceil(float(aaa) / bbb))


def floor_div(aaa, bbb):
    return int(floor(float(aaa) / bbb))


def _create_fingerprint_and_signature(cert_path):
    rtc, stdout, stderr = _run_command(
        ['openssl', 'x509', '-in', cert_path, '-fingerprint', '-noout'])
    if rtc != 0:
        err = "error getting fingerprint " \
              "from cert %s: %s" % (cert_path, stderr)
        log.error(err)
        raise Exception(err)
    fingerprint = stdout.strip()[17:].replace(':', '')
    rtc, stdout, stderr = _run_command(
        ['openssl', 'pkcs12', '-export', '-in', cert_path,
         '-nokeys', '-password', 'pass:'])
    if rtc != 0:
        err = "error getting pkcs12 signature " \
              "from cert_path %s: %s" % (cert_path, stderr)
        log.error(err)
        raise Exception(err)
    signature = base64.b64encode(stdout.strip())
    return fingerprint, signature


def _create_rsa_fingerprint(key_path):
    rtc, stdout, stderr = _run_command(
        ['ssh-keygen', '-lf', key_path])
    if rtc != 0:
        err = "error getting fingerprint " \
              "from RSA key %s: %s" % (key_path, stderr)
        log.error(err)
        raise Exception(err)
    fingerprint = stdout.strip()[5:52].replace(':', '')
    return fingerprint

def _update_request_uri_query(request):
        '''pulls the query string out of the URI and moves it into
        the query portion of the request object.  If there are already
        query parameters on the request the parameters in the URI will
        appear after the existing parameters'''

        if '?' in request.path:
            request.path, _, query_string = request.path.partition('?')
            if query_string:
                query_params = query_string.split('&')
                for query in query_params:
                    if '=' in query:
                        name, _, value = query.partition('=')
                        request.query.append((name, value))

        request.path = url_quote(request.path, '/()$=\',')

        # add encoded queries to request.path.
        if request.query:
            request.path += '?'
            for name, value in request.query:
                if value is not None:
                    request.path += name + '=' + url_quote(value, '/()$=\',') + '&'
            request.path = request.path[:-1]

        return request.path, request.query


def _rest_put(subscription, path, xml):
    # can't use SDK _perform_put because we need text/plain content-type
    request = HTTPRequest()
    request.method = 'PUT'
    request.host = azure.servicemanagement.constants.MANAGEMENT_HOST
    request.path = path
    request.body = _get_request_body(xml)
    request.path, request.query = _update_request_uri_query(request)

    # request.headers.append(('Content-Length', str(len(request.body))))
    request.headers.append(('Content-Type', 'text/plain'))
    request.headers = subscription._sms._update_management_header(
        request, azure.servicemanagement.X_MS_VERSION)
    response = subscription._sms._perform_request(request)
    return response


def check_response(response):
    if not response:
        raise Exception("empty response")
    if response.status != 200:
        raise Exception("response status %s" % response.status)


# def stats(help_string):
#     log.debug("--->%s: %s %.3f", help_string,
#              threading.current_thread().name, time.time())


class AzureGlobalConfig(object):

    """Manage all the settings for an Azure cluster which are
    global as opposed to node-specific.

    This does not manage resources (which are dynamic), only settings
    (which are static, or at least are determined at cluster startup).
    """

    # we only get a few pieces of information at this point
    def __init__(self, parent, subscription_id, certificate, storage_path):

        self._parent = parent
        # if we got a subscription here, use it. if not,
        # a subscription_file has to be
        # included in the cluster parameters passed to setup().
        if subscription_id:
            self._parent._subscriptions.append(
                AzureSubscription(
                    config=self,
                    subscription_id=subscription_id,
                    certificate=certificate, index=0))
        self._storage_path = storage_path

        self._key_name = None
        self._public_key_path = None
        self._private_key_path = None
        self._location = None
        self._base_name = None
        self._username = None
        self._subscription_file = None
        self._use_public_ips = None
        self._n_cloud_services = None
        self._n_storage_accounts = None
        self._n_vms_requested = None
        self._n_subscriptions = None
        self._cs_per_sub = None
        self._sa_per_sub = None
        self._security_group = None
        self._wait_timeout = None
        self._vm_per_cs = None
        self._vm_per_sub = None
        self._vm_per_sa = None

    # called when the first node is about to be created. this is where
    # we get most of the config info. this is not threadsafe - caller
    # must ensure it isn't called concurrently and that it is only
    # called once.
    def setup(
            self,
            key_name,
            public_key_path,
            private_key_path,
            security_group,
            location=None,
            base_name=None,
            username=None,
            subscription_file=None,
            frontend_nodes=None,
            compute_nodes=None,
            use_public_ips=None,
            wait_timeout=DEFAULT_WAIT_TIMEOUT,
            n_cloud_services=None,
            n_storage_accounts=None,
            **kwargs):
        self._key_name = key_name
        self._public_key_path = public_key_path
        self._private_key_path = private_key_path
        self._security_group = security_group
        self._location = location
        self._base_name = base_name
        self._username = username
        self._subscription_file = subscription_file
        self._wait_timeout = _check_positive_integer(
            'wait_timeout', wait_timeout)

        # elasticluster parser doesn't know about bools
        self._use_public_ips = True if use_public_ips == 'True' else False

        # subscriptions
        self._read_subscriptions()

        # resource names will be generated based on this string.
        if len(self._base_name) < 3 or len(self._base_name) > 15:
            err = 'base_name %s not between 3 and 15 characters' \
                  % self._base_name
            log.error(err)
            raise Exception(err)
        if re.match('[^a-z0-9]', self._base_name):
            err = 'base_name %s is invalid, only lowercase letters and ' \
                  'digits allowed' % self._base_name
            log.error(err)
            raise Exception(err)

        # compute total VMs requested (warn: depends on frontend_nodes and
        # compute_nodes being defined)
        n_frontend_nodes = n_compute_nodes = 0
        if frontend_nodes:
            n_frontend_nodes = _check_positive_integer('frontend_nodes',
                                                       frontend_nodes)
        if compute_nodes:
            n_compute_nodes = _check_positive_integer('compute_nodes',
                                                      compute_nodes)
        self._n_vms_requested = n_frontend_nodes + n_compute_nodes

        # if we got resource counts, read them. otherwise compute them.
        if n_cloud_services:
            self._n_cloud_services = _check_positive_integer(
                'n_cloud_services', n_cloud_services)
        else:
            self._n_cloud_services = ceil_div(self._n_vms_requested,
                                              VMS_PER_CLOUD_SERVICE)

        if n_storage_accounts:
            self._n_storage_accounts = _check_positive_integer(
                'n_storage_accounts', n_storage_accounts)
        else:
            self._n_storage_accounts = ceil_div(self._n_vms_requested,
                                                VMS_PER_STORAGE_ACCOUNT)

        self._n_subscriptions = len(self._parent._subscriptions)
        if self._n_subscriptions > self._n_cloud_services or \
                self._n_subscriptions > self._n_storage_accounts:
            new_subs = min(self._n_cloud_services, self._n_storage_accounts)
            msg = "Can't use all %i subscriptions available. Will only " \
                  "use %i." % (self._n_subscriptions, new_subs)
            log.warn(msg)
            self._parent._subscriptions[new_subs:self._n_subscriptions] = []
            self._n_subscriptions = new_subs

        min_subscriptions = ceil_div(self._n_cloud_services,
                                     CLOUD_SERVICES_PER_SUBSCRIPTION)
        if self._n_subscriptions < min_subscriptions:
            err = 'Not enough subscriptions available to meet resource' \
                  'requirements (have %i, need %i)' % \
                  (len(self._parent._subscriptions), min_subscriptions)
            log.error(err)
            raise Exception(err)
        log.debug('compute nodes: %i. cloud services: %i. storage accounts:'
                  ' %i. subscriptions: %i.', self._n_vms_requested,
                  self._n_cloud_services, self._n_storage_accounts,
                  self._n_subscriptions)

        # store values needed to map vms to resources
        self._vm_per_cs = ceil_div(
            self._n_vms_requested, self._n_cloud_services)
        self._cs_per_sub = ceil_div(
            self._n_cloud_services, self._n_subscriptions)
        self._vm_per_sub = self._vm_per_cs * self._cs_per_sub

        self._vm_per_sa = ceil_div(
            self._n_vms_requested, self._n_storage_accounts)
        self._sa_per_sub = ceil_div(
            self._n_storage_accounts, self._n_subscriptions)
        if self._vm_per_sub != self._vm_per_sa * self._sa_per_sub:
            err = 'inconsistency, %i != %i' % \
                  (self._vm_per_sub, self._vm_per_sa * self._sa_per_sub)
            log.error(err)
            raise Exception(err)

    # there are three ways to designate a node in the cluster:
    # - by its flat index (0..total nodes - 1)
    # - by its node name (we will use basename_vm%i where %i is the flat index)
    # - by its resources - index of its subscription, its cloud service
    #   (or alternatively its storage account), and its index within that
    #   cloud service or storage account.
    # We need all possible conversions amongst these.

    def _vm_name_to_flat(self, vm_name):
        if vm_name and vm_name.startswith(self._base_name + '_vm'):
            start = len(self._base_name) + 3
            end = start + 4
            bare = vm_name[start:end]
            return int(bare)
        err = "_vm_name_to_flat: can't process vm_name %s" % vm_name
        log.error(err)
        raise Exception(err)

    def _vm_flat_to_resources(self, vm_index):
        i_sub = floor_div(vm_index, self._vm_per_sub)
        i_cs = floor_div(vm_index % self._vm_per_sub, self._vm_per_cs)
        i_vm_in_cs = vm_index - (i_sub * self._vm_per_sub) - \
            (i_cs * self._vm_per_cs)
        i_sa = floor_div(vm_index % self._vm_per_sub, self._vm_per_sa)
        i_vm_in_sa = vm_index - (i_sub * self._vm_per_sub) - \
            (i_sa * self._vm_per_sa)
        return i_sub, i_cs, i_vm_in_cs, i_sa, i_vm_in_sa

    def _vm_name_to_resources(self, vm_name):
        return self._vm_flat_to_resources(self._vm_name_to_flat(vm_name))

    def _read_subscriptions(self):
        ids = set()
        if self._subscription_file:
            if self._parent._subscriptions:
                log.debug(
                    'subscription was passed in cloud section, and '
                    'subscription_file was '
                    'also passed in cluster section. using both.')
                ids.add(self._parent._subscriptions[0]._subscription_id)
            try:
                pattern = re.compile(
                    r'subscription_id=(\S*)\s+certificate=(.*)')
                with open(self._subscription_file) as fhl:
                    for line in fhl:
                        match = pattern.match(line)
                        if match:
                            if match.group(1) in ids:
                                log.debug('subscription_id %s has already been'
                                          ' read. ignoring.', match.group(1))
                            else:
                                ids.add(match.group(1))
                                index = len(self._parent._subscriptions)
                                self._parent._subscriptions.append(
                                    AzureSubscription(
                                        config=self,
                                        subscription_id=match.group(1),
                                        certificate=os.path.expanduser(
                                            match.group(2)),
                                        index=index))
                        else:
                            log.debug(
                                'ignoring line in subscription_file %s: %s',
                                self._subscription_file, line)
            except Exception as exc:
                log.error('error parsing subscription file %s: %s',
                          self._subscription_file, exc)


class AzureSubscription(object):

    def __init__(self, config, subscription_id, certificate, index):
        self._do_cleanup = False    # never delete a subscription
        self._config = config
        self._subscription_id = subscription_id
        self._certificate = certificate
        self._index = index
        self._sms_internal = None
        self._resource_lock_internal = None
        self._storage_accounts = list()
        self._cloud_services = list()
        self._vnet = None

        # create fingerprint and signature from subscription cert, to
        # be added to cloud services/vms
        fingerprint, signature = _create_fingerprint_and_signature(
            self._certificate)
        self._fingerprint = fingerprint
        self._pkcs12_base64 = signature

        # initialize properties
        _ = self._resource_lock  # force instantiation
        if self._sms_internal is None:
            try:
                self._sms_internal = \
                    azure.servicemanagement.ServiceManagementService(
                        self._subscription_id, self._certificate)
            except Exception as exc:
                log.error('error initializing azure serice: %s', exc)
                raise

    @property
    def _resource_lock(self):
        if self._resource_lock_internal is None:
            self._resource_lock_internal = threading.RLock()
        return self._resource_lock_internal

    @property
    def _sms(self):
        if self._sms_internal is None:
            try:
                self._sms_internal = \
                    azure.servicemanagement.ServiceManagementService(
                        self._subscription_id, self._certificate)
            except Exception as exc:
                log.error('error initializing azure serice: %s', exc)
                raise
        return self._sms_internal

    @property
    def _n_instances(self):
        ret = 0
        with self._resource_lock:
            for cloud_service in self._cloud_services:
                ret = ret + cloud_service._n_instances
            return ret

    # this needs to be in here because sms is per-subscription
    def _wait_result(self, req, timeout=None):
        if not timeout:
            timeout = self._config._wait_timeout
        if not req:
            return  # sometimes this happens, seems to mean success
        giveup_time = time.time() + timeout
        while giveup_time > time.time():
            operation_result = self._sms.get_operation_status(req.request_id)
            if operation_result.status == "InProgress":
                time.sleep(WAIT_RESULT_SLEEP)
                continue
            if operation_result.status == "Succeeded":
                return
            if operation_result.status == "Failed":
                err = 'async operation failed: %s' \
                      % operation_result.error.message
                log.error(err)
                raise CloudProviderError(err)
        err = 'async operation timed out'
        log.error(err)
        raise CloudProviderError(err)

    def __getstate__(self):
        dct = self.__dict__.copy()
        del dct['_resource_lock_internal']
        del dct['_sms_internal']
        return dct

    def __setstate__(self, state):
        self.__dict__ = state
        self._resource_lock_internal = None
        self._sms_internal = None

    def _find_os_disks(self):
        # associate disk names of os vhd's with their nodes.
        try:
            disks = self._sms.list_disks()
            for disk in disks:
                for cloud_service in self._cloud_services:
                    for vm_name, v_m in cloud_service._instances.iteritems():
                        if v_m._os_vhd_name:
                            continue
                        if vm_name in disk.name and \
                                self._config._base_name in disk.name:
                            v_m._os_vhd_name = disk.name
        except Exception as exc:
            log.error('error in _find_os_disks: %s', exc)
            raise


class AzureCloudService(object):

    def __init__(self, config, subscription, index):
        self._do_cleanup = False
        self._config = config
        self._subscription = subscription
        self._location = config._location
        self._index = index
        self._name = "%ssu%ics%i" % (
            self._config._base_name, self._subscription._index, self._index)
        # treat deployment as sub-item of cloud service
        # deployment has same name as cloud service
        # only instances owned by this cloud service:
        self._instances = {}
        self._resource_lock_internal = None
        self._deployment_created = False

    @property
    def _resource_lock(self):
        if self._resource_lock_internal is None:
            self._resource_lock_internal = threading.RLock()
        return self._resource_lock_internal

    @property
    def _n_instances(self):
        with self._resource_lock:
            return len(self._instances)

    @property
    def _exists(self):
        try:
            self._subscription._sms.get_hosted_service_properties(
                service_name=self._name)
            log.debug("cloud service %s exists", self._name)
            return True
        except Exception as exc:
            if not str(exc).startswith('Not Found'):
                log.error('error checking for cloud service %s: %s',
                          self._name, str(exc))
                raise
        return False

    def _create(self):
        with self._resource_lock:
            if not self._exists:
                try:
                    result = self._subscription._sms.create_hosted_service(
                        service_name=self._name,
                        label=self._name,
                        location=self._location)
                    self._subscription._wait_result(result)
                except Exception as exc:
                    # this shouldn't happen
                    # if str(e) == 'Conflict (Conflict)':
                    #    return False
                    log.error('error creating cloud service %s: %s',
                              self._name, exc)
                    raise

    def _delete(self):
        with self._resource_lock:
            if self._deployment:
                log.error("can't delete cloud service %s. It contains a "
                          "deployment and at least one node.", self._name)
                return False
            try:
                self._subscription._sms.delete_hosted_service(
                    service_name=self._name)
            except Exception as exc:
                log.error('error deleting cloud service %s: %s',
                          self._name, exc)
                raise
            return True

    # called by _stop_vm when vm is the last node in the deployment.
    def _delete_deployment(self):
        try:
            result = self._subscription._sms.delete_deployment(
                service_name=self._name,
                deployment_name=self._name)
            self._subscription._wait_result(result)
        except Exception as exc:
            log.error('error deleting deployment from cloud service %s: %s',
                      self._name, exc)
            raise

    @property
    def _deployment(self):
        try:
            dep = self._subscription._sms.get_deployment_by_name(
                service_name=self._name, deployment_name=self._name)
            return dep
        except Exception as exc:
            if str(exc).startswith('Not Found'):
                return None
            log.error('error getting deployment %s: %s', self._name, exc)
            raise

    def _add_certificate(self):
        # Add certificate to cloud service
        result = self._subscription._sms.add_service_certificate(
            self._name, self._subscription._pkcs12_base64, 'pfx', '')
        self._subscription._wait_result(result)

    def _start_vm(self, v_m):
        with self._resource_lock:
            if not self._deployment_created:
                # block while we create the deployment and start the vm
                attempt = 1
                sub = self._subscription
                sms = sub._sms
                while attempt < RETRIES:
                    try:
                        result = sms.create_virtual_machine_deployment(
                            service_name=self._name,
                            deployment_name=self._name,
                            deployment_slot='production',
                            label=v_m._node_name,
                            role_name=v_m._qualified_name,
                            system_config=v_m._system_config,
                            network_config=v_m._network_config,
                            os_virtual_hard_disk=v_m._os_virtual_hard_disk,
                            role_size=v_m._flavor,
                            role_type='PersistentVMRole',
                            virtual_network_name=v_m._virtual_network_name)
                        sub._wait_result(result)
                        break
                    except Exception as exc:
                        if str(exc) == 'Conflict (Conflict)':
                            log.error('error creating vm %s (attempt %i of '
                                      '%i): virtual machine already exists.',
                                      v_m._qualified_name, attempt, RETRIES)
                            raise   # this is serialized, so probably a
                            # legit error
                        if 'is invalid' in str(exc):
                            if re.match('value .* for parameter .* '
                                        'is invalid', str(exc)):
                                log.error('error creating vm %s (attempt %i '
                                          'of %i): virtual machine '
                                          'already exists.',
                                          v_m._qualified_name, attempt,
                                          RETRIES)
                                raise   # treat as legit error
                        else:
                            log.error('error creating vm %s (attempt '
                                      '%i of %i): %s', v_m._qualified_name,
                                      attempt, RETRIES, exc)
                    time.sleep(_retry_sleep())
                    attempt += 1
                if attempt >= RETRIES:
                    err = 'AzureVM start %s: giving up after %i attempts' % \
                          (v_m._qualified_name, RETRIES)
                    log.error(err)
                    raise Exception(err)

                # need to find the disk name for the OS disk attached to
                # this vm.
                self._subscription._find_os_disks()
                v_m._created = True
                self._deployment_created = True
                return

        # add the vm to the deployment - can be parallel (?)
        attempt = 1
        sub = self._subscription
        sms = sub._sms
        while attempt < RETRIES:
            try:
                log.debug("attempt %i to start vm node name %s qual name %s",
                          attempt, v_m._node_name, v_m._qualified_name)
                result = sms.add_role(
                    service_name=self._name,
                    deployment_name=self._name,
                    role_name=v_m._qualified_name,
                    system_config=v_m._system_config,
                    network_config=v_m._network_config,
                    os_virtual_hard_disk=v_m._os_virtual_hard_disk,
                    role_size=v_m._flavor,
                    role_type='PersistentVMRole')
                sub._wait_result(result)
                break
            except Exception as exc:
                log.error('error creating vm %s (attempt '
                          '%i of %i): %s', v_m._qualified_name,
                          attempt, RETRIES, exc)
            time.sleep(_retry_sleep())
            attempt += 1
        if attempt >= RETRIES:
            err = 'AzureVM start %s: giving up after %i attempts' % \
                  (v_m._qualified_name, RETRIES)
            log.error(err)
            raise Exception(err)
        # need to find the disk name for the OS disk attached to
        # this vm.
        self._subscription._find_os_disks()
        v_m._created = True

    def _stop_vm(self, v_m):
        attempt = 1
        sub = self._subscription
        sms = sub._sms
        while attempt < RETRIES:
            try:
                log.debug("attempt %i to stop vm node name %s qual name %s",
                          attempt, v_m._node_name, v_m._qualified_name)
                if len(self._instances) == 1:
                    # we are the last node in this cloud service,
                    # so delete deployment
                    self._delete_deployment()
                else:
                    result = sms.delete_role(
                        service_name=self._name,
                        deployment_name=self._name,
                        role_name=v_m._qualified_name)
                    sub._wait_result(result)

                with self._resource_lock:
                    prov = self._config._parent
                    prov._disks_to_delete[v_m._os_vhd_name] = {
                        'SMS': v_m._subscription._sms,
                        'TRIES': 0, 'LATEST_TRY': None}
                    del self._instances[v_m._qualified_name]
                break
            except Exception as exc:
                log.error('error stopping vm %s (attempt '
                          '%i of %i): %s', v_m._qualified_name,
                          attempt, RETRIES, exc)
                if str(exc).startswith('Not Found'):
                    # assume the error is right, and try to clean up the
                    # leftovers of the vm state
                    with self._resource_lock:
                        prov = self._config._parent
                        prov._disks_to_delete[v_m._os_vhd_name] = {
                            'SMS': v_m._subscription._sms,
                            'TRIES': 0, 'LATEST_TRY': None}
                        del self._instances[v_m._qualified_name]
                    break
            time.sleep(_retry_sleep())
            attempt += 1
        if attempt >= RETRIES:
            err = '_stop_vm %s: giving up after %i attempts' % \
                  (v_m._qualified_name, RETRIES)
            log.error(err)
            raise Exception(err)

    def __getstate__(self):
        dct = self.__dict__.copy()
        del dct['_resource_lock_internal']
        return dct

    def __setstate__(self, state):
        self.__dict__ = state
        self._resource_lock_internal = None


class AzureStorageAccount(object):

    def __init__(self, config, subscription, index):
        self._do_cleanup = False
        self._created = False
        self._config = config
        self._subscription = subscription
        self._index = index
        self._name = "%ssu%ist%i" % (
            self._config._base_name, self._subscription._index, self._index)
        self._resource_lock_internal = None

    @property
    def _resource_lock(self):
        if self._resource_lock_internal is None:
            self._resource_lock_internal = threading.Lock()
        return self._resource_lock_internal

    def _exists(self):
        try:
            self._subscription._sms.get_storage_account_properties(
                service_name=self._name)
            # note - this will only find a storage account of the given name
            # within this subscription. Doesn't guarantee the name isn't in
            # use anywhere in Azure, so be cautious with the result from
            # this method.
            log.debug("storage account %s exists", self._name)
            return True
        except Exception as exc:
            if not str(exc).startswith('Not Found'):
                log.error('error checking for storage account %s: %s',
                          self._name, str(exc))
                raise
            return False

    def _create(self):
        if not self._exists():
            try:
                result = self._subscription._sms.create_storage_account(
                    service_name=self._name,
                    description=self._name,
                    label=self._name,
                    location=self._config._location,
                    account_type='Standard_LRS'
                )
                # this seems to be taking much longer than the others...
                self._subscription._wait_result(
                    result, self._config._wait_timeout * 10)
            except Exception as exc:
                # this probably means that there is a storage account with
                # the requested name in Azure, but not in this subscription.
                if str(exc) == 'Conflict (Conflict)':
                    log.error("Storage account %s already exists in Azure (may"
                              " be in some other subscription)", self._name)
                log.error('error creating storage account %s: %s',
                          self._name, str(exc))
                raise

    def _delete(self):
        attempts = 10
        for attempt in range(1, attempts):
            try:
                self._subscription._sms.delete_storage_account(
                    service_name=self._name)
                log.debug('delete storage account %s: success on attempt %i',
                          self._name, attempt)
                return
            except Exception as exc:
                log.error('delete storage account %s: error on attempt '
                          '#%i: %s', self._name, attempt, exc)
                time.sleep(10)
        err = 'delete storage account %s: giving up after %i attempts' % \
              (self._name, attempts)
        log.error(err)
        raise Exception(err)

    def _create_vhd(self, node_name, image_id):
        disk_url = u'http://%s.blob.core.windows.net/vhds/%s.vhd' % (
            self._name, node_name)
        vhd = azure.servicemanagement.OSVirtualHardDisk(image_id, disk_url)
        return vhd, disk_url

    def __getstate__(self):
        dct = self.__dict__.copy()
        del dct['_resource_lock_internal']
        return dct

    def __setstate__(self, state):
        self.__dict__ = state
        self._resource_lock_internal = None


class AzureVNet(object):

    def __init__(self, config, subscription, index):
        self._do_cleanup = False
        self._config = config
        self._subscription = subscription
        self._index = index
        self._name = "%ssu%ivn%i" % (
            self._config._base_name, self._subscription._index, self._index)
        self._resource_lock_internal = None
        # location comes from config

    @property
    def _resource_lock(self):
        if self._resource_lock_internal is None:
            self._resource_lock_internal = threading.Lock()
        return self._resource_lock_internal

    def _exists(self):
        try:
            result = self._subscription._sms.list_virtual_network_sites()
            if len(result):
                for virtual_network_site in result.virtual_network_sites:
                    if virtual_network_site.name == self._name:
                        log.debug("vnet %s exists", self._name)
                        return True
                return False
            else:
                return False    # no vnets
        except Exception as exc:
            log.error('error checking existence of vnet %s: %s',
                      self._name, exc)
            raise

    @property
    def _path(self):
        return "/%s/services/networking/media" % \
               self._subscription._subscription_id

    def _get_xml(self):
        # get the xml defining the current vnet config for the whole
        # subscription.
        attempt = 1
        while attempt < RETRIES:
            try:
                response = self._subscription._sms.perform_get(self._path)
                check_response(response)
                return response.body
            except Exception as exc:
                if str(exc).startswith('Not Found'):
                    return None
                log.error('error in _get_xml for vnet %s '
                          '(attempt %i of %i): %s',
                          self._name, attempt, RETRIES, exc)
            time.sleep(_retry_sleep())
            attempt += 1
        err = "AzureVNet %s _get_xml: giving up after %i attempts" % \
              (self._name, RETRIES)
        log.error(err)
        raise Exception(err)

    def _create(self):
        if self._exists():
            return
        tree = None
        xml = None
        self._register_namespaces()
        try:
            # since we will be rewriting the whole network config, first
            # we need to get the xml for any existing vnets, and if
            # there is any, fold ours in.
            prior_xml = self._get_xml()
            if prior_xml:
                # vnets already defined (possibly including ours, although
                # it shouldn't be - we already checked)
                # search for ours
                tree = xmltree.fromstring(prior_xml)
                config = tree.find(
                    self._deco('VirtualNetworkConfiguration'))
                sites = config.find(self._deco('VirtualNetworkSites'))
                if sites is not None:  # plain "if sites" gets a warning
                    for site in sites.findall(
                            self._deco('VirtualNetworkSite')):
                        if site.get('name') == self._name:
                            if site.get('location') == self._config._location:
                                log.warn("unexpected: found in xml: vnet %s with "
                                         "location %s",
                                         self._name, self._config._location)
                            else:
                                log.warn("vnet %s found in xml, but location "
                                         "is %s (expected %s)", self._name,
                                         site.get('location'),
                                         self._config._location)
                            return
                else:
                    # probably means there is 1+ DNS servers but no vnets
                    sites = xmltree.Element(self._deco('VirtualNetworkSites'))
                    config.append(sites)
            else:
                # no vnets defined. just add ours
                prior_xml = self._empty_network_config_xml()
                tree = xmltree.fromstring(prior_xml)
                config = tree.find(
                    self._deco('VirtualNetworkConfiguration'))
                sites = config.find(self._deco('VirtualNetworkSites'))

            subtree = self._make_vnet_subtree()
            sites.append(subtree)
            xml = xmltree.tostring(tree)
        except Exception as exc:
            err = 'error preparing AzureVNet _create: %s' % exc
            log.error(err)
            raise
        # replace the whole network config,
        attempt = 1
        while attempt < RETRIES:
            try:
                response = _rest_put(self._subscription, self._path, xml)
                result = azure.servicemanagement.AsynchronousOperationResult()
                if response.headers:
                    for name, value in response.headers:
                        if name.lower() == 'x-ms-request-id':
                            result.request_id = value
                            break
                self._subscription._wait_result(
                    result, self._config._wait_timeout)
                log.debug('created vnet %s', self._name)
                return
            except Exception as exc:
                if 'validation error' in str(exc):
                    err = 'fatal error in _create for vnet %s: %s' \
                          % (self._name, exc)
                    log.error(err)
                    raise  # no point retrying
                log.error('error in _create for vnet %s '
                          '(attempt %i of %i): %s',
                          self._name, attempt, RETRIES, exc)
            time.sleep(_retry_sleep())
            attempt += 1
        err = "AzureVNet %s _delete: giving up after %i attempts" % \
              (self._name, RETRIES)
        log.error(err)
        raise Exception(err)

    def _delete(self):
        if not self._exists():
            return
        tree = None
        xml = None
        self._register_namespaces()
        found = None
        try:
            prior_xml = self._get_xml()  # should exist
            # search for ours
            tree = xmltree.fromstring(prior_xml)
            config = tree.find(
                self._deco('VirtualNetworkConfiguration'))
            sites = config.find(self._deco('VirtualNetworkSites'))
            if sites is not None:
                for site in sites.findall(self._deco('VirtualNetworkSite')):
                    if site.get('name') == self._name:
                        if site.get('Location') != self._config._location:
                            log.warn("vnet %s found in xml, but location is %s "
                                     "(expected %s)", self._name,
                                     site.get('location'), self._config._location)
                        sites.remove(site)
                        found = True
                        break
                if not found:
                    raise Exception("AzureVNet _delete: vnet %s exists, but "
                                    "not found in xml" % self._name)
            xml = xmltree.tostring(tree)
        except Exception as exc:
            err = 'error preparing AzureVNet _delete: %s' % exc
            log.error(err)
            raise
        # replace the whole network config,
        attempt = 1
        while attempt < RETRIES:
            try:
                response = _rest_put(self._subscription, self._path, xml)
                result = azure.servicemanagement.AsynchronousOperationResult()
                if response.headers:
                    for name, value in response.headers:
                        if name.lower() == 'x-ms-request-id':
                            result.request_id = value
                self._subscription._wait_result(
                    result, self._config._wait_timeout)
                log.debug('deleted vnet %s', self._name)
                return
            except Exception as exc:
                log.error('error in _delete for vnet %s '
                          '(attempt %i of %i): %s',
                          self._name, attempt, RETRIES, exc)
            time.sleep(_retry_sleep())
            attempt += 1
        err = "AzureVNet %s _delete: giving up after %i attempts" % \
              (self._name, RETRIES)
        log.error(err)
        raise Exception(err)

    @staticmethod
    def _register_namespaces():
        xmltree.register_namespace('', 'http://www.w3.org/2001/XMLSchema')
        xmltree.register_namespace(
            '', 'http://www.w3.org/2001/XMLSchema-instance')
        xmltree.register_namespace('', VNET_NS)

    @staticmethod
    def _deco(strng):
        return '{%s}%s' % (VNET_NS, strng)

    # create a network config with no vnets
    @staticmethod
    def _empty_network_config_xml():
        template = "<NetworkConfiguration xmlns:xsd=\"http://www.w3.org/" \
                   "2001/XMLSchema\" xmlns:xsi=\"http://www.w3.org/2001/" \
                   "XMLSchema-instance\" xmlns=\"http://schemas." \
                   "microsoft.com/ServiceHosting/2011/07/" \
                   "NetworkConfiguration\">"
        template = template + """
  <VirtualNetworkConfiguration>
    <Dns>
      <DnsServers>
      </DnsServers>
    </Dns>
    <VirtualNetworkSites>
    </VirtualNetworkSites>
  </VirtualNetworkConfiguration>
</NetworkConfiguration>"""
        return template

    # create xml subtree for a vnet with our name and location
    def _make_vnet_subtree(self):
        subtree = xmltree.Element(self._deco('VirtualNetworkSite'))
        subtree.set('name', self._name)
        subtree.set('Location', self._config._location)
        addrspace = xmltree.SubElement(subtree, self._deco('AddressSpace'))
        prefix = xmltree.SubElement(addrspace, self._deco('AddressPrefix'))
        prefix.text = '10.0.0.0/8'
        subnets = xmltree.SubElement(subtree, self._deco('Subnets'))
        subnet = xmltree.SubElement(subnets, self._deco('Subnet'))
        subnet.set('name', 'subnet1')
        subprefix = xmltree.SubElement(subnet, self._deco('AddressPrefix'))
        subprefix.text = '10.0.0.0/11'
        return subtree

    # return info on all vnets currently defined in a subscription
    @staticmethod
    def _get_list(subscription, strng):
        try:
            ret = list()
            result = subscription._sms.list_virtual_network_sites()
            if len(result):
                for virtual_network_site in result.virtual_network_sites:
                    ret.append(virtual_network_site.name)
            return ret
        except Exception as exc:
            log.error('error getting list of vnets for subscription %s: %s',
                      subscription._name, exc)
            raise

    def __getstate__(self):
        dct = self.__dict__.copy()
        del dct['_resource_lock_internal']
        return dct

    def __setstate__(self, state):
        self.__dict__ = state
        self._resource_lock_internal = None


class AzureVM(object):

    def __init__(
            self,
            config,
            node_index,
            cloud_service=None,
            storage_account=None,
            subscription=None,
            flavor=None,
            image=None,
            node_name=None,
            host_name=None,
            image_userdata=None):
        self._do_cleanup = False
        self._config = config
        self._node_index = node_index
        self._cloud_service = cloud_service
        self._storage_account = storage_account
        self._subscription = subscription
        self._flavor = flavor
        self._image = image
        self._node_name = node_name
        self._host_name = host_name
        self._image_userdata = image_userdata

        # figure out what sub, cloud serv, stor acct to use if not specified
        if not self._cloud_service:
            parent = self._config._parent
            (i_subscription, i_cloud_service, _, i_storage_account, _) = \
                self._config._vm_flat_to_resources(self._node_index)
            self._subscription = parent._subscriptions[i_subscription]
            self._cloud_service = \
                self._subscription._cloud_services[i_cloud_service]
            self._storage_account = \
                self._subscription._storage_accounts[i_storage_account]

        self._qualified_name = '{0}_vm{1:04d}_{2}'.format(
            self._config._base_name, self._node_index, self._node_name)
        self._public_ip_internal = None
        self._ssh_port = None
        self._os_virtual_hard_disk = None
        self._os_vhd_name = None
        self._created = False
        self._paused = False
        self._system_config = None
        self._network_config = None
        self._virtual_network_name = None

        try:
            self._create_network_config()

            (self._os_virtual_hard_disk, _) = \
                self._storage_account._create_vhd(self._node_name, self._image)
            self._virtual_network_name = \
                self._subscription._vnet._name
        except Exception as exc:
            log.error('error creating reqs for vm %s: %s',
                      self._qualified_name, exc)
            raise

    def pause(self, instance_id, keep_provisioned=True):
        """shuts down the instance without destroying it.

        The AbstractCloudProvider class uses 'stop' to refer to destroying
        a VM, so use 'pause' to mean powering it down while leaving it
        allocated.

        :param str instance_id: instance identifier

        :return: None
        """
        try:
            if self._paused:
                log.debug("node %s is already paused", instance_id)
                return
            self._paused = True
            post_shutdown_action = 'Stopped' if keep_provisioned else \
                'StoppedDeallocated'
            result = self._subscription._sms.shutdown_role(
                service_name=self._cloud_service._name,
                deployment_name=self._cloud_service._name,
                role_name=self._qualified_name,
                post_shutdown_action=post_shutdown_action)
            self._subscription._wait_result(result)
        except Exception as exc:
            log.error("error pausing instance %s: %s", instance_id, exc)
            raise
        log.debug('paused instance(instance_id=%s)', instance_id)

    def restart(self, instance_id):
        """restarts a paused instance.

        :param str instance_id: instance identifier

        :return: None
        """
        try:
            if not self._paused:
                log.debug("node %s is not paused, can't restart", instance_id)
                return
            self._paused = False
            result = self._subscription._sms.start_role(
                service_name=self._cloud_service._name,
                deployment_name=self._cloud_service._name,
                role_name=instance_id)
            self._subscription._wait_result(result)
        except Exception as exc:
            log.error('error restarting instance %s: %s', instance_id, exc)
            raise
        log.debug('restarted instance(instance_id=%s)', instance_id)

    def _create_network_config(self):
        # Create linux configuration
        self._system_config = azure.servicemanagement.LinuxConfigurationSet(
            self._node_name,
            self._config._username,
            None,
            disable_ssh_password_authentication=True)
        ssh_config = azure.servicemanagement.SSH()
        ssh_config.public_keys = azure.servicemanagement.PublicKeys()
        authorized_keys_path = u'/home/%s/.ssh/authorized_keys' \
                               % self._config._username
        ssh_config.public_keys.public_keys.append(
            azure.servicemanagement.PublicKey(
                path=authorized_keys_path,
                fingerprint=self._subscription._fingerprint))
        self._system_config.ssh = ssh_config

        # Create network configuration
        self._network_config = azure.servicemanagement.ConfigurationSet()
        self._network_config.configuration_set_type = 'NetworkConfiguration'
        if self._config._use_public_ips:
            public_ip = azure.servicemanagement.PublicIP(
                u'pip-%s' % self._node_name)
            # allowed range is 4-30 mins
            public_ip.idle_timeout_in_minutes = 30
            public_ips = azure.servicemanagement.PublicIPs()
            public_ips.public_ips.append(public_ip)
            self._network_config.public_ips = public_ips
            self._ssh_port = SSH_PORT
        else:
            # create endpoints for ssh (22). Map to an offset + instance
            # index + port # for the public side
            self._ssh_port = PORT_MAP_OFFSET + self._node_index + SSH_PORT

        endpoints = azure.servicemanagement.ConfigurationSetInputEndpoints()
        endpoints.subnet_names = []
        endpoints.input_endpoints.append(
            azure.servicemanagement.ConfigurationSetInputEndpoint(
                name='TCP-%s' %
                self._ssh_port,
                protocol='TCP',
                port=self._ssh_port,
                local_port=SSH_PORT))
        self._network_config.input_endpoints = endpoints

    @property
    def _power_state(self):
        instances = self._cloud_service._deployment.role_instance_list
        for instance in instances:
            if instance.instance_name == self._qualified_name:
                # cache IP since it will be asked for soon
                if self._config._use_public_ips:
                    self._public_ip_internal = instance.public_ips[0].address
                else:
                    self._public_ip_internal = instance.instance_endpoints[
                        0].vip
                return instance.power_state
        raise Exception("could not get power_state for instance %s"
                        % self._qualified_name)

    @property
    def _public_ip(self):
        if not self._public_ip_internal:
            # not cached, so look it up
            instances = self._cloud_service._deployment.role_instance_list
            for instance in instances:
                if instance.instance_name == self._qualified_name:
                    if self._config._use_public_ips:
                        self._public_ip_internal = instance.public_ips[
                            0].address
                    else:
                        self._public_ip_internal = instance.instance_endpoints[
                            0].vip
                    return self._public_ip_internal
            raise Exception("could not get public IP for instance %s"
                            % self._qualified_name)
        return self._public_ip_internal


class AzureCloudProvider(AbstractCloudProvider):

    """This implementation of
    :py:class:`elasticluster.providers.AbstractCloudProvider` uses the
    Azure Python interface connect to the Azure clouds and manage instances.

    An AzureCloudProvider owns a tree of Azure resources, rooted in one or
    more subscriptions and one or more storage accounts.
    """

    def __init__(self,
                 subscription_id,
                 certificate,
                 storage_path=None):
        """The constructor of AzureCloudProvider class is called only
        using keyword arguments.

        Usually these are configuration option of the corresponding
        `setup` section in the configuration file.
        """
        # Paramiko debug level
        # import logging
        # logging.getLogger('paramiko').setLevel(logging.DEBUG)
        # logging.basicConfig(level=logging.DEBUG)

        # Ansible debug level
        # import ansible
        # import ansible.utils
        # ansible.utils.VERBOSITY = 9

        # auto stack tracing
        # import stacktracer
        # stacktracer.trace_start("trace.html",interval=15,auto=True)

        # flag indicating resource creation failed - don't even
        # attempt node operations after this is set
        self._start_failed = None

        # this lock should never be held for long - only for changes to the
        # resource arrays this object owns, and queries about same.
        self._resource_lock_internal = None

        # resources
        self._cluster_prep_done = False
        self._subscriptions = []

        # diagnostics
        self._times = {}

        # cleanup
        self._disks_to_delete = {}

        self._config = AzureGlobalConfig(
            self, subscription_id, os.path.expanduser(certificate),
            storage_path)

    def start_instance(
            self,
            key_name,
            public_key_path,
            private_key_path,
            security_group,
            flavor,
            image,
            image_userdata,
            location=None,
            base_name=None,
            username=None,
            node_name=None,
            host_name=None,
            use_public_ips=None,
            wait_timeout=None,
            use_short_vm_names=None,
            n_cloud_services=None,
            n_storage_accounts=None,
            **kwargs):
        """Starts a new instance on the cloud using the given properties.
        Multiple instances might be started in different threads at the same
        time. The implementation should handle any problems regarding this
        itself.
        :return: str - instance id of the started instance
        """

        if self._start_failed:
            raise Exception('start_instance for node %s: failing due to'
                            ' previous errors.' % node_name)

        index = None
        with self._resource_lock:
            # it'd be nice if elasticluster called something like
            # init_cluster() with all the args that will be the
            # same for every node created. But since it doesn't, handle that on
            # first start_instance call.
            if not self._cluster_prep_done:
                self._times['CLUSTER_START'] = time.time()
                self._config.setup(
                    key_name,
                    public_key_path,
                    private_key_path,
                    security_group,
                    location,
                    base_name=base_name,
                    username=username,
                    use_public_ips=use_public_ips,
                    wait_timeout=wait_timeout,
                    use_short_vm_names=use_short_vm_names,
                    n_cloud_services=n_cloud_services,
                    n_storage_accounts=n_storage_accounts,
                    **kwargs)
                # we know we're starting the first node, so create global
                # requirements now
                self._create_global_reqs()
                if self._start_failed:
                    return None
                # this will allow vms to be created
                self._times['SETUP_DONE'] = time.time()
                self._cluster_prep_done = True

            # absolute node index in cluster (0..n-1) determines what
            # subscription, cloud service, storage
            # account, etc. this VM will use. Create the vm and add it to
            # its cloud service, then try to start it.
            index = self._n_instances

            v_m = AzureVM(
                self._config,
                index,
                flavor=flavor,
                image=image,
                node_name=node_name,
                host_name=host_name,
                image_userdata=image_userdata)
            v_m._cloud_service._instances[v_m._qualified_name] = v_m

        try:
            v_m._cloud_service._start_vm(v_m)
        except Exception:
            log.error(traceback.format_exc())
            log.error("setting start_failed flag. Will not "
                      "try to start further nodes.")
            self._start_failed = True
            return None
        log.debug('started instance %s', v_m._qualified_name)
        if index == self._config._n_vms_requested - 1:
            # all nodes started
            self._times['NODES_STARTED'] = time.time()
            self._times['SETUP_ELAPSED'] = self._times['SETUP_DONE'] - \
                self._times['CLUSTER_START']
            self._times['NODE_START_ELAPSED'] = self._times['NODES_STARTED']\
                - self._times['SETUP_DONE']
            self._times['CLUSTER_START_ELAPSED'] = \
                self._times['SETUP_ELAPSED'] + \
                self._times['NODE_START_ELAPSED']

            log.debug("setup time: %.1f sec", self._times['SETUP_ELAPSED'])
            log.debug("node start time: %.1f sec (%.1f sec per vm)",
                      self._times['NODE_START_ELAPSED'],
                      self._times['NODE_START_ELAPSED'] /
                      self._config._n_vms_requested)
            log.debug("total cluster start time: %.1f sec (%.1f sec per vm)",
                      self._times['CLUSTER_START_ELAPSED'],
                      self._times['CLUSTER_START_ELAPSED'] /
                      self._config._n_vms_requested)
            # pause here to try to address the fact that Ansible setup fails
            # more often on the first try than subsequent tries
            time.sleep(_retry_sleep())
        self._save_or_update()  # store our state
        return v_m._qualified_name

    def stop_instance(self, instance_id):
        """Stops the instance gracefully.

        :param str instance_id: instance identifier

        :return: None
        """
        self._restore_from_storage(instance_id)
        if self._start_failed:
            raise Exception('stop_instance for node %s: failing due to'
                            ' previous errors.' % instance_id)

        with self._resource_lock:
            try:
                v_m = self._qualified_name_to_vm(instance_id)
                if not v_m:
                    err = "stop_instance: can't find instance %s" % instance_id
                    log.error(err)
                    raise Exception(err)
                v_m._cloud_service._stop_vm(v_m)
                # note: self._n_instances is a derived property, doesn't need
                # to be updated
                if self._n_instances == 0:
                    log.debug('last instance deleted, destroying '
                              'global resources')
                    self._delete_global_reqs()
                    self._delete_cloud_provider_storage()
            except Exception as exc:
                log.error(traceback.format_exc())
                log.error("error stopping instance %s: %s", instance_id, exc)
                raise
        log.debug('stopped instance %s', instance_id)

    def get_ips(self, instance_id):
        """Retrieves the private and public ip addresses for a given instance.
        Note: Azure normally provides access to vms from a shared load
        balancer IP and
        mapping of ssh ports on the vms. So by default, the Azure provider
        returns strings
        of the form 'ip:port'. However, 'stock' elasticluster and ansible
        don't support this,
        so _use_public_ips uses Azure PublicIPs to expose each vm on the
        internet with its own IP
        and using the standard SSH port.

        :return: list (IPs)
        """
        self._restore_from_storage(instance_id)
        if self._start_failed:
            raise Exception('get_ips for node %s: failing due to'
                            ' previous errors.' % instance_id)

        ret = list()
        v_m = self._qualified_name_to_vm(instance_id)
        if not v_m:
            raise Exception("Can't find instance_id %s" % instance_id)
        if self._config._use_public_ips:
            ret.append(v_m._public_ip)
        else:
            ret.append("%s:%s" % (v_m._public_ip, v_m._ssh_port))

        log.debug('get_ips (instance %s) returning %s',
                  instance_id, ', '.join(ret))
        return ret

    def is_instance_running(self, instance_id):
        """Checks if the instance is up and running.

        :param str instance_id: instance identifier

        :return: bool - True if running, False otherwise
        """
        self._restore_from_storage(instance_id)
        if self._start_failed:
            raise Exception('is_instance_running for node %s: failing due to'
                            ' previous errors.' % instance_id)
        try:
            v_m = self._qualified_name_to_vm(instance_id)
            if not v_m:
                raise Exception("Can't find instance_id %s" % instance_id)
        except Exception:
            log.error(traceback.format_exc())
            raise
        return v_m._power_state == 'Started'

    # ------------------ add-on methods ---------------------------------
    # (not part of the base class, but useful extensions)

    # -------------------- private members ------------------------------

    @property
    def _resource_lock(self):
        if self._resource_lock_internal is None:
            self._resource_lock_internal = threading.Lock()
        return self._resource_lock_internal

    @property
    def _n_instances(self):
        ret = 0
        for subscription in self._subscriptions:
            ret = ret + subscription._n_instances
        return ret

    def _qualified_name_to_vm(self, qualified_name):
        i_sub, i_cs, _, _, _ = \
            self._config._vm_name_to_resources(qualified_name)
        c_s = self._subscriptions[i_sub]._cloud_services[i_cs]
        with c_s._resource_lock:
            return c_s._instances[qualified_name]

    def _create_global_reqs(self):
        try:
            for index in range(self._config._n_cloud_services):
                i_sub = floor_div(index, self._config._cs_per_sub)
                sub = self._subscriptions[i_sub]
                acs = AzureCloudService(self._config, sub, index)
                acs._create()
                acs._add_certificate()
                log.debug("Created cloud service %i (%s)", index, acs._name)
                sub._cloud_services.append(acs)

            for index in range(self._config._n_storage_accounts):
                i_sub = floor_div(index, self._config._sa_per_sub)
                sub = self._subscriptions[i_sub]
                asa = AzureStorageAccount(self._config, sub, index)
                asa._create()
                log.debug("Created storage account %i (%s)", index, asa._name)
                sub._storage_accounts.append(asa)

            # one vnet should be enough for ~ 1000 vms. Tie it to
            # the first subscription.
            # NOTE: this doesn't work - can't start a vm in sub B
            # that refers to a vnet in sub A.
            # sub = self._subscriptions[0]
            # sub._vnet = AzureVNet(self._config, sub, 0)
            # sub._vnet._create()
            index = 0
            for sub in self._subscriptions:
                sub._vnet = AzureVNet(self._config, sub, index)
                sub._vnet._create()
                index += 1
        except Exception as exc:
            log.error('_create_global_reqs error: %s', exc)
            log.debug("setting start_failed flag. Will not "
                      "try to start further nodes.")
            self._start_failed = True
            raise

    # tear down non-node-specific resources. Current default is to delete
    # everything; this may change.
    #
    def _delete_global_reqs(self):
        try:
            # delete all the OS VHDs
            while self._disks_to_delete:
                for disk_name, disk_info in self._disks_to_delete.items():
                    if disk_info['TRIES'] >= VHD_DELETE_ATTEMPTS:
                        log.error("failed to delete vhd %s after %i attempts. "
                                  "giving up.", disk_name, disk_info['TRIES'])
                        del self._disks_to_delete[disk_name]
                        continue
                    if self._delete_disk(disk_name, disk_info):
                        del self._disks_to_delete[disk_name]
                time.sleep(5)

            for sub in self._subscriptions:
                for c_s in sub._cloud_services:
                    if c_s._instances:
                        err = "cloud service %s can't be destroyed, it " \
                              "still has %i vms." % \
                              (c_s._name, len(c_s._instances))
                        log.error(err)
                        raise Exception(err)
                    c_s._delete()
                    log.debug("Deleted cloud service '%s'", c_s._name)

                for s_a in sub._storage_accounts:
                    s_a._delete()
                    log.debug("Deleted storage account '%s'", s_a._name)

                sub._vnet._delete()
        except Exception as exc:
            log.error('_delete_global_reqs error: %s', exc)
            raise

    def _delete_disk(self, disk_name, disk_info):
        disk_info['TRIES'] += 1
        if disk_info['TRIES'] > VHD_DELETE_ATTEMPTS:
            return False
        sms = disk_info['SMS']
        now = time.time()
        if disk_info['LATEST_TRY'] and \
                (now - disk_info['LATEST_TRY'] < VHD_DELETE_INTERVAL):
            return False
        disk_info['LATEST_TRY'] = now
        try:
            # delete_vhd=False doesn't seem to help if the disk is not
            # ready to be deleted yet
            sms.delete_disk(disk_name=disk_name, delete_vhd=True)
            log.debug('_delete_vhd %s: success on attempt %i',
                      disk_name, disk_info['TRIES'])
            return True
        except Exception as exc:
            if str(exc).startswith('Not Found'):
                log.debug(
                    "_delete_vhd: 'not found' deleting %s, assuming "
                    "success", disk_name)
                return True
            # log.error('_delete_vhd: error on attempt #%i to delete '
            #          'disk %s: %s' % (disk_info['TRIES'], disk_name, exc))
            return False

    # methods to support saving and loading our (i.e. cloud provider's) state

    def _save_or_update(self):
        """Save or update the private state needed by the cloud provider.
        """
        with self._resource_lock:
            if not self._config or not self._config._storage_path:
                raise Exception("self._config._storage path is undefined")
            if not self._config._base_name:
                raise Exception("self._config._base_name is undefined")
            if not os.path.exists(self._config._storage_path):
                os.makedirs(self._config._storage_path)
            path = self._get_cloud_provider_storage_path()
            with open(path, 'wb') as storage:
                pickle.dump(self._config, storage, pickle.HIGHEST_PROTOCOL)
                pickle.dump(self._subscriptions, storage,
                            pickle.HIGHEST_PROTOCOL)

    def _get_cloud_provider_storage_path(self):
        cluster_file = 'azure_%s.pickle' % self._config._base_name
        return os.path.join(self._config._storage_path, cluster_file)

    def _delete_cloud_provider_storage(self):
        full_path = None
        try:
            cluster_file = 'azure_%s.pickle' % self._config._base_name
            full_path = os.path.join(self._config._storage_path, cluster_file)
            if os.path.isfile(full_path):
                os.remove(full_path)
        except Exception as exc:
            log.error("Unable to delete storage file %s: %s", full_path, exc)

    # when cluster provider method called, all we know is an instance name.
    def _restore_from_storage(self, instance_name):
        with self._resource_lock:
            if self._config._base_name:
                return  # our state is intact, don't load
            if not self._config._storage_path:
                raise Exception("self._config._storage_path is undefined")
            self._config._base_name, _, _ = instance_name.partition('_')
            path = self._get_cloud_provider_storage_path()
            if not os.path.exists(path):
                raise Exception("cloud provider storage file %s not "
                                "found" % path)
            with open(path, 'r') as storage:
                self._config = pickle.load(storage)
                self._subscriptions = pickle.load(storage)
                # fix up circular references
                self._config._parent = self
                for sub in self._subscriptions:
                    for clds in sub._cloud_services:
                        clds._config = self._config
                        clds._subscription = sub
                    for stac in sub._storage_accounts:
                        stac._config = self._config
                        stac._subscription = sub

    # methods to support pickling by elasticluster

    def __getstate__(self):
        dct = self.__dict__.copy()
        del dct['_resource_lock_internal']
        del dct['_start_failed']
        return dct

    def __setstate__(self, state):
        self.__dict__ = state
        self._resource_lock_internal = None
        self._start_failed = False
