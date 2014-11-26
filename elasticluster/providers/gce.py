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
"""
Cloud provider for the Google Compute Engine.

See <https://code.google.com/p/google-cloud-platform-samples/source/browse/python-client-library-example/gce.py?repo=compute> for reference.
"""
__author__ = 'Riccardo Murri <riccardo.murri@uzh.ch>, ' \
             'Nicolas Baer <nicolas.baer@gmail.com>, '  \
             'Antonio Messina <antonio.s.messina@gmail.com>'


# stdlib imports
import copy
import httplib2
import os
import random
import threading
import time
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
from elasticluster.exceptions import ImageError, InstanceError, CloudProviderError


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
                 noauth_local_webserver=False,
                 zone=GCE_DEFAULT_ZONE,
                 network='default',
                 email=GCE_DEFAULT_SERVICE_EMAIL,
                 storage_path=None):
        self._client_id = gce_client_id
        self._client_secret = gce_client_secret
        self._project_id = gce_project_id
        self._zone = zone
        self._network = network
        self._email = email
        self._storage_path = storage_path
        self._noauth_local_webserver = noauth_local_webserver

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
        # check for existing connection
        with GoogleCloudProvider.__gce_lock:
            if self._gce:
                return self._gce

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
                except:
                    import sys
                    print "Unexpected error:", sys.exc_info()[0]
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
                       instance_name=None, **kwargs):
        """Starts a new instance with the given properties and returns
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

        :param str instance_name: name of the instance

        :return: str - instance id of the started instance
        """
        # construct URLs
        project_url = '%s%s' % (GCE_URL, self._project_id)
        machine_type_url = '%s/zones/%s/machineTypes/%s' \
                           % (project_url, self._zone, flavor)
        network_url = '%s/global/networks/%s' % (project_url, self._network)
        if image_id.startswith('http://') or image_id.startswith('https://'):
            image_url = image_id
        else:
            os = image_id.split("-")[0]
            os_cloud = "%s-cloud" % os
            image_url = '%s%s/global/images/%s' % (
                GCE_URL, os_cloud, image_id)

        # construct the request body
        if instance_name is None:
            instance_name = 'elasticluster-%s' % uuid.uuid4()

        public_key_content = file(public_key_path).read()

        instance = {
            'name': instance_name,
            'machineType': machine_type_url,
            'disks': [{
                'autoDelete': 'true',
                'boot': 'true',
                'type': 'PERSISTENT',
                'initializeParams' : {
                    'diskName': "%s-disk" % instance_name,
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
                "items": [
                    {
                        "key": "sshKeys",
                        "value": "%s:%s" % (username, public_key_content)
                    }
                ]
            }
        }

        # create the instance
        gce = self._connect()
        request = gce.instances().insert(
            project=self._project_id, body=instance, zone=self._zone)
        try:
            response = self._execute_request(request)
            response = self._wait_until_done(response)
            self._check_response(response)
            return instance_name
        except (HttpError, CloudProviderError) as e:
            log.error("Error creating instance `%s`" % e)
            raise InstanceError("Error creating instance `%s`" % e)

    def stop_instance(self, instance_id):
        """Stops the instance gracefully.

        :param str instance_id: instance identifier
        :raises: `InstanceError` if instance can not be stopped
        """
        gce = self._connect()

        try:
            request = gce.instances().delete(project=self._project_id,
                                        instance=instance_id, zone=self._zone)
            response = self._execute_request(request)
            self._check_response(response)
        except (HttpError, CloudProviderError) as e:
            raise InstanceError("Could not stop instance `%s`: `%s`"
                                % (instance_id, e))

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
        """Retrieves the ip addresses (private and public) from the cloud
        provider by the given instance id.

        :param str instance_id: id of the instance
        :return: list (ips)
        :raises: InstanceError if the ip could not be retrieved.
        """
        gce = self._connect()
        instances = gce.instances()
        try:
            request = instances.get(instance=instance_id,
                                    project=self._project_id, zone=self._zone)
            response = self._execute_request(request)
            ip_private = None
            ip_public = None
            if response and "networkInterfaces" in response:
                interfaces = response['networkInterfaces']
                if interfaces:
                    ip_private = interfaces[0]['networkIP']

                    if "accessConfigs" in interfaces[0]:
                        ip_public = interfaces[0]['accessConfigs'][0]['natIP']

            if ip_private and ip_public:
                return [ip_private, ip_public]
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
