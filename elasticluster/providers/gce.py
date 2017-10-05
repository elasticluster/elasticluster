#
# Copyright (C) 2013-2018 University of Zurich
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
"""
Cloud provider for the Google Compute Engine.

See <https://code.google.com/p/google-cloud-platform-samples/source/browse/python-client-library-example/gce.py?repo=compute> for reference.
"""
__author__ = 'Riccardo Murri <riccardo.murri@uzh.ch>, ' \
             'Nicolas Baer <nicolas.baer@gmail.com>, '  \
             'Antonio Messina <antonio.s.messina@gmail.com>'


# stdlib imports
import collections
import copy
import httplib2
import os
import random
import threading
import time
import types
import uuid

# External modules
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run_flow
from oauth2client.tools import argparser

# Elasticluster imports
from elasticluster import log
from elasticluster.providers import AbstractCloudProvider
from elasticluster.exceptions import ImageError, InstanceError, InstanceNotFoundError, CloudProviderError


# constants and defaults

#: the OAuth scope for the GCE web API
GCE_SCOPE = 'https://www.googleapis.com/auth/compute'
GCE_API_NAME = 'compute'
GCE_API_VERSION = 'v1'
GCE_URL = 'https://www.googleapis.com/compute/%s/projects/' % GCE_API_VERSION
GCE_DEFAULT_ZONE = 'us-central1-a'
GCE_DEFAULT_SERVICE_EMAIL = 'default'
GCE_DEFAULT_SCOPES = ['https://www.googleapis.com/auth/devstorage'
                      '.full_control',
                      'https://www.googleapis.com/auth/compute']


class GoogleCloudProvider(AbstractCloudProvider):
    """Cloud provider for the Google Compute Engine.

    :param str gce_client_id: Client ID to use in OAuth authentication.

    :param str gce_client_secret: Client secret (password) to use in
                                  OAuth authentication.

    :param str gce_project_id: Project name to log in to GCE.

    :param noauth_local_webserver: do not pop up a webserver for auth

    :param str zone: gce zone, default is `us-central1-a`

    :param str network: network to use, default is  `default`

    :param str email: service email to use, default is `default`

    :param str storage_path: path to store authentication data (oauth.dat
                             file). If no path is specified, the login data
                             has to be entered after every request.
    """
    __gce_lock = threading.Lock()

    def __init__(self,
                 gce_client_id,
                 gce_client_secret,
                 gce_project_id,
                 email=GCE_DEFAULT_SERVICE_EMAIL,
                 network='default',
                 noauth_local_webserver=False,
                 zone=GCE_DEFAULT_ZONE,
                 storage_path=None):
        self._client_id = gce_client_id
        self._client_secret = gce_client_secret
        self._project_id = gce_project_id

        self._email = email
        self._network = network
        self._noauth_local_webserver = noauth_local_webserver
        self._zone = zone

        self._storage_path = storage_path

        # will be initialized upon first connect
        self._gce = None
        self._auth_http = None
        self._instances = {}
        self._cached_instances = []
        self._images = None

    def _connect(self):
        """Connects to the cloud web services. If this is the first
        authentication, a web browser will be started to authenticate
        against google and provide access to elasticluster.

        :return: A Resource object with methods for interacting with the
                 service.
        """
        # ensure only one thread runs the authentication process, if needed
        with GoogleCloudProvider.__gce_lock:
            # check for existing connection
            if not self._gce:
                flow = OAuth2WebServerFlow(self._client_id, self._client_secret,
                                           GCE_SCOPE)
                # The `Storage` object holds the credentials that your
                # application needs to authorize access to the user's
                # data. The name of the credentials file is provided. If the
                # file does not exist, it is created. This object can only
                # hold credentials for a single user. It stores the access
                # priviledges for the application, so a user only has to grant
                # access through the web interface once.
                storage_path = os.path.join(self._storage_path,
                                            self._client_id + '.oauth.dat')
                storage = Storage(storage_path)

                credentials = storage.get()
                if credentials is None or credentials.invalid:
                    args = argparser.parse_args([])
                    args.noauth_local_webserver = self._noauth_local_webserver
                    # try to start a browser to have the user authenticate with Google
                    # TODO: what kind of exception is raised if the browser
                    #       cannot be started?
                    try:
                        credentials = run_flow(flow, storage, flags=args)
                    except Exception as err:
                        log.error("Could not run authentication flow: %s", err)
                        log.debug("(Original traceback follows.)", exc_info=True)
                        raise

                http = httplib2.Http()
                self._auth_http = credentials.authorize(http)

                self._gce = build(GCE_API_NAME, GCE_API_VERSION, http=http)

        return self._gce

    def _execute_request(self, request):
        """Helper method to execute a request, since a lock should be used
        to not fire up multiple requests at the same time.

        :return: Result of `request.execute`
        """
        with GoogleCloudProvider.__gce_lock:
            return request.execute(http=self._auth_http)

    # The following function was adapted from
    # https://developers.google.com/compute/docs/api/python_guide
    # (function _blocking_call)
    def _wait_until_done(self, response, wait=30):
        """Blocks until the operation status is done for the given operation.

        :param response: The response object used in a previous GCE call.

        :param int wait: Wait up to this number of seconds in between
                         successive polling of the GCE status.
        """

        gce = self._connect()

        status = response['status']
        while status != 'DONE' and response:
            # wait a random amount of time (up to `wait` seconds)
            if wait:
                time.sleep(1 + random.randrange(wait))

            operation_id = response['name']

            # Identify if this is a per-zone resource
            if 'zone' in response:
                zone_name = response['zone'].split('/')[-1]
                request = gce.zoneOperations().get(
                    project=self._project_id, operation=operation_id,
                    zone=zone_name)
            else:
                request = gce.globalOperations().get(
                    project=self._project_id,
                    operation=operation_id)

            response = self._execute_request(request)
            if response:
                status = response['status']
        return response

    def start_instance(self,
                       # these are common to any
                       # CloudProvider.start_instance() call
                       key_name, public_key_path, private_key_path,
                       security_group, flavor, image_id, image_userdata,
                       username=None,
                       # these params are specific to the
                       # GoogleCloudProvider
                       node_name=None,
                       boot_disk_type='pd-standard',
                       boot_disk_size=10,
                       tags=None,
                       scheduling=None,
                       accelerator_count=0,
                       accelerator_type='default',
                       allow_project_ssh_keys=True,
                       min_cpu_platform=None,
                       **kwargs):
        """
        Starts a new instance with the given properties and returns
        the instance id.

        :param str key_name: name of the ssh key to connect
        :param str public_key_path: path to ssh public key
        :param str private_key_path: path to ssh private key
        :param str security_group: firewall rule definition to apply on the
                                   instance
        :param str flavor: machine type to use for the instance
        :param str image_id: image type (os) to use for the instance
        :param str image_userdata: command to execute after startup
        :param str username: username for the given ssh key, default None
        :param str node_name: name of the instance
        :param str|Sequence tags: "Tags" to label the instance.
          Can be either a single string (individual tags are comma-separated),
          or a sequence of strings (each string being a single tag).
        :param str scheduling: scheduling option to use for the instance ("preemptible")
        :param int accelerator_count: Number of accelerators (e.g., GPUs) to make available in instance
        :param str accelerator_type: Type of accelerator to request.  Can be one of:

          * Full URL specifying an accelerator type valid for the zone and project VMs are being created in.  For example, ``https://www.googleapis.com/compute/v1/projects/[PROJECT_ID]/zones/[ZONE]/acceleratorTypes/[ACCELERATOR_TYPE]``
          * An accelerator type name (any string which is not a valid URL).  This is internally prefixed with the string ``https://www.googleapis.com/compute/v1/projects/[PROJECT_ID]/zones/[ZONE]/acceleratorTypes/`` to form a full URL.
        :param bool allow_project_ssh_keys:
          When ``True`` (default), SSH login is allowed to a node
          using any of the project-wide SSH keys (if they are
          defined).  When ``False``, only the SSH key specified by
          ElastiCluster config's ``[login/*]`` section will be allowed
          to log in (instance-level key).
        :param str min_cpu_platform: require CPUs of this type or better (e.g., "Intel Skylake")

          Only used if ``accelerator_count`` is > 0.

        :return: str - instance id of the started instance
        """
        # construct URLs
        project_url = '%s%s' % (GCE_URL, self._project_id)
        machine_type_url = '%s/zones/%s/machineTypes/%s' \
                           % (project_url, self._zone, flavor)
        boot_disk_type_url = '%s/zones/%s/diskTypes/%s' \
                           % (project_url, self._zone, boot_disk_type)
        # FIXME: `conf.py` should ensure that `boot_disk_size` has the right
        # type, so there would be no need to convert here
        boot_disk_size_gb = int(boot_disk_size)
        network_url = '%s/global/networks/%s' % (project_url, self._network)
        if image_id.startswith('http://') or image_id.startswith('https://'):
            image_url = image_id
        else:
            # The image names and full resource URLs for several Google-
            # provided images (debian, centos, etc.) follow a consistent
            # pattern, and so elasticluster supports a short-hand of just
            # an image name, such as
            #   "debian-7-wheezy-v20150526".
            # The cloud project in this case is then "debian-cloud".
            #
            # Several images do not follow this convention, and so are
            # special-cased here:
            #   backports-debian -> debian-cloud
            #   ubuntu           -> ubuntu-os-cloud
            #   containter-vm    -> google-containers
            if image_id.startswith('container-vm-'):
              os_cloud = 'google-containers'
            elif image_id.startswith('backports-debian-'):
              os_cloud = 'debian-cloud'
            elif image_id.startswith('ubuntu-'):
              os_cloud = 'ubuntu-os-cloud'
            else:
              os = image_id.split("-")[0]
              os_cloud = "%s-cloud" % os

            image_url = '%s%s/global/images/%s' % (
                GCE_URL, os_cloud, image_id)

        scheduling_option = {}
        if scheduling == 'preemptible':
            scheduling_option['preemptible'] = True
        elif scheduling is not None:
            raise InstanceError("Unknown scheduling option: '%s'" % scheduling)

        if isinstance(tags, types.StringTypes):
            tags = tags.split(',')
        elif isinstance(tags, collections.Sequence):
            # ok, nothing to do
            pass
        elif tags is not None:
            raise TypeError(
                "The `tags` argument to `gce.start_instance`"
                " should be a string or a list, got {T} instead"
                .format(T=type(tags)))

        compute_metadata = [
            {
                "key": "ssh-keys",
                "value": "%s:%s" % (username, public_key_content),
            },
            {
                "key": "block-project-ssh-keys",
                "value": (not allow_project_ssh_keys),
            },
        ]
        if image_userdata:
            compute_metadata.append({
                "key": "startup-script",
                "value": image_userdata,
            })

        # construct the request body
        if node_name:
            instance_id = node_name.lower().replace('_', '-')  # GCE doesn't allow "_"
        else:
            instance_id = 'elasticluster-%s' % uuid.uuid4()

        with open(public_key_path, 'r') as f:
            public_key_content = f.read()

        instance = {
            'name': instance_id,
            'machineType': machine_type_url,
            'tags': {
              'items': tags,
            },
            'scheduling': scheduling_option,
            'disks': [{
                'autoDelete': 'true',
                'boot': 'true',
                'type': 'PERSISTENT',
                'initializeParams' : {
                    'diskName': "%s-disk" % instance_id,
                    'diskType': boot_disk_type_url,
                    'diskSizeGb': boot_disk_size_gb,
                    'sourceImage': image_url
                    }
                }],
            'networkInterfaces': [
                {'accessConfigs': [
                    {'type': 'ONE_TO_ONE_NAT',
                     'name': 'External NAT'
                    }],
                 'network': network_url
                }],
            'serviceAccounts': [
                {'email': self._email,
                 'scopes': GCE_DEFAULT_SCOPES
                }],
            "metadata": {
                "kind": "compute#metadata",
                "items": compute_metadata,
            }
        }

        if min_cpu_platform is not None:
            instance['minCpuPlatform'] = min_cpu_platform

        # add accelerators/GPUs if requested
        if accelerator_count > 0:
            if (accelerator_type.startswith('https://')
                or accelerator_type.startswith('http://')):
                # use URL as-is
                accelerator_type_url = accelerator_type
            else:
                accelerator_type_url = (
                    'https://www.googleapis.com/compute/{api_version}/'
                    'projects/{project_id}/zones/{zone}/'
                    'acceleratorTypes/{accelerator_type}'
                    .format(
                        api_version=GCE_API_VERSION,
                        project_id=self._project_id,
                        zone=self._zone,
                        accelerator_type=accelerator_type
                    ))
            log.debug(
                "VM instance `%s`:"
                " Requesting %d accelerator%s of type '%s'",
                instance_id, accelerator_count,
                ('s' if accelerator_count > 1 else ''),
                accelerator_type_url)
            instance['guestAccelerators'] = [
             {
                 'acceleratorCount': accelerator_count,
                 'acceleratorType': accelerator_type_url,
             }
            ]
            # no live migration with GPUs,
            # see: https://cloud.google.com/compute/docs/gpus#restrictions
            instance['scheduling']['onHostMaintenance'] = 'TERMINATE'
            instance['scheduling']['automaticRestart'] = True

        # create the instance
        gce = self._connect()
        request = gce.instances().insert(
            project=self._project_id, body=instance, zone=self._zone)
        try:
            response = self._execute_request(request)
            response = self._wait_until_done(response)
            self._check_response(response)
            return instance_id
        except (HttpError, CloudProviderError) as e:
            log.error("Error creating instance `%s`" % e)
            raise InstanceError("Error creating instance `%s`" % e)

    def stop_instance(self, instance_id):
        """Stops the instance gracefully.

        :param str instance_id: instance identifier
        :raises: `InstanceError` if instance can not be stopped
        """
        if not instance_id:
          log.info("Instance to stop has no instance id")
          return

        gce = self._connect()

        try:
            request = gce.instances().delete(project=self._project_id,
                                        instance=instance_id, zone=self._zone)
            response = self._execute_request(request)
            self._check_response(response)
        except HttpError as e:
            # If the instance does not exist, we get a 404
            if e.resp.status == 404:
                raise InstanceNotFoundError(
                    "Instance `{instance_id}` was not found"
                    .format(instance_id=instance_id))
            else:
                raise InstanceError(
                    "Could not stop instance `{instance_id}`: `{e}`"
                    .format(instance_id=instance_id, e=e))
        except CloudProviderError as e:
            raise InstanceError(
                "Could not stop instance `{instance_id}`: `{e}`"
                .format(instance_id=instance_id, e=e))

    def list_instances(self, filter=None):
        """List instances on GCE, optionally filtering the results.

        :param str filter: Filter specification; see https://developers.google.com/compute/docs/reference/latest/instances/list for details.
        :return: list of instances
        """
        gce = self._connect()

        try:
            request = gce.instances().list(
                project=self._project_id, filter=filter, zone=self._zone)
            response = self._execute_request(request)
            self._check_response(response)
        except (HttpError, CloudProviderError) as e:
            raise InstanceError("could not retrieve all instances on the "
                                "cloud: ``" % e)

        if response and 'items' in response:
            return response['items']
        else:
            return list()

    def get_ips(self, instance_id):
        """Retrieves the ip addresses (public) from the cloud
        provider by the given instance id.

        :param str instance_id: id of the instance
        :return: list (ips)
        :raises: InstanceError if the ip could not be retrieved.
        """
        if not instance_id:
          raise InstanceError("could not retrieve the ip address for node: "
                              "no associated instance id")
        gce = self._connect()
        instances = gce.instances()
        try:
            request = instances.get(instance=instance_id,
                                    project=self._project_id, zone=self._zone)
            response = self._execute_request(request)
            ip_public = None

            # If the instance is in status TERMINATED, then there will be
            # no IP addresses.
            if response and response['status'] in ('STOPPING', 'TERMINATED'):
              log.info("node '%s' state is '%s'; no IP address(es)" %
                       (instance_id, response['status']))
              return [None]

            if response and "networkInterfaces" in response:
                interfaces = response['networkInterfaces']
                if interfaces:
                    if "accessConfigs" in interfaces[0]:
                        ip_public = interfaces[0]['accessConfigs'][0]['natIP']

            if ip_public:
                return [ip_public]
            else:
                raise InstanceError("could not retrieve the ip address for "
                                    "node `%s`, please check the node "
                                    "through the cloud provider interface"
                                    % instance_id)

        except (HttpError, CloudProviderError) as e:
            raise InstanceError('could not retrieve the ip address of `%s`: '
                                '`%s`' % (instance_id, e))

    def is_instance_running(self, instance_id):
        """Check whether the instance is up and running.

        :param str instance_id: instance identifier
        :reutrn: True if instance is running, False otherwise
        """
        items = self.list_instances(filter=('name eq "%s"' % instance_id))
        for item in items:
            if item['status'] == 'RUNNING':
                return True
        return False

    def _get_image_url(self, image_id):
        """Gets the url for the specified image. Unfortunatly this only works
        for images uploaded by the user. The images provided by google will
        not be found.

        :param str image_id: image identifier
        :return: str - api url of the image
        """
        gce = self._connect()
        filter = "name eq %s" % image_id
        request = gce.images().list(project=self._project_id, filter=filter)
        response = self._execute_request(request)
        response = self._wait_until_done(response)

        image_url = None
        if "items" in response:
            image_url = response["items"][0]["selfLink"]

        if image_url:
            return image_url
        else:
            raise ImageError("Could not find given image id `%s`" % image_id)

    def _check_response(self, response):
        """Checks the response from GCE for error messages.

        :param response: GCE response
        :return: nothing
        :raises: CloudProviderError with error message from GCE
        """
        if "error" in response:
            error = response['error']['errors'][0]['message']
            raise CloudProviderError("The following error occurred while "
                                     "interacting with the cloud provider "
                                     "`%s`" % error)

    def __getstate__(self):
        """
        Overwrites the default dictionary for pickle. Only the gce connection
        is reset in this method in order to enforce a reconnect.
        """
        pickle_dict = copy.deepcopy(self.__dict__)

        # the gce connection might be lost when unpickling, therefore we just
        # save an empty gce connection to mitigate the problems in the first
        # place.
        pickle_dict['_gce'] = None

        return pickle_dict
