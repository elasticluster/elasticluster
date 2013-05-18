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
"""
Cloud provider for the Google Compute Engine.

See <https://code.google.com/p/google-cloud-platform-samples/source/browse/python-client-library-example/gce.py?repo=compute> for reference.
"""
__author__ = 'Riccardo Murri <riccardo.murri@uzh.ch>'


# stdlib imports
import httplib2
import os
import random
import time
import uuid

# External modules
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run

# Elasticluster imports
from elasticluster.providers import AbstractCloudProvider


# constants and defaults

#: the OAuth scope for the GCE web API
GCE_SCOPE = 'https://www.googleapis.com/auth/compute'
GCE_API_NAME = 'compute'
GCE_API_VERSION = 'v1beta14'
GCE_URL = 'https://www.googleapis.com/%s/%s/projects/' \
    % (GCE_API_NAME, GCE_API_VERSION)
GCE_DEFAULT_ZONE = 'us-central1-a'
GCE_DEFAULT_SERVICE_EMAIL = 'default'
GCE_DEFAULT_SCOPES = [
    'https://www.googleapis.com/auth/devstorage.full_control',
    'https://www.googleapis.com/auth/compute'
]


class GoogleCloudProvider(AbstractCloudProvider):
    """
    Cloud provider for the Google Compute Engine.
    """

    def __init__(self, client_id, client_secret, project_id,
                 zone=GCE_DEFAULT_ZONE, network='default',
                 email=GCE_DEFAULT_SERVICE_EMAIL):
        """
        Initialize a provider for the GCE service.

        :param str client_id:     Client ID to use in OAuth authentication.

        :param str client_secret: Client secret (password) to use in
         OAuth authentication.

        :param str project_id:    Project name to log in to GCE.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._project_id = project_id
        self._zone = zone
        self._network = network

        # will be initialized upon first connect
        self._gce = None
        self._auth_http = None
        self._instances = {}
        self._cached_instances = []
        self._images = None

    def _connect(self):
        """
        Connects to the cloud provider.

        Also initializes the OAuth credential storage, which might in
        turn fire up a browser.
        """
        # check for existing connection
        if self._gce:
            return self._gce

        flow = OAuth2WebServerFlow(self._client_id, self._client_secret,
                                   GCE_SCOPE)
        # The `Storage` object holds the credentials that your
        # application needs to authorize access to the user's
        # data. The name of the credentials file is provided. If the
        # file does not exist, it is created. This object can only
        # hold credentials for a single user,
        storage = Storage(os.path.join(self.Configuration.storage,
                                       self._client_id + '.oauth.dat'))

        credentials = storage.get()
        if credentials is None or credentials.invalid:
            # try to start a browser to have the user authenticate with Google
            # XXX: what kind of exception is raised if the browser
            # cannot be started?
            credentials = run(flow, storage)

        http = httplib2.Http()
        self._auth_http = credentials.authorize(http)

        self._gce = build(GCE_API_NAME, GCE_API_VERSION, http=http)

        return self._gce

    # The following function was adapted from
    # https://developers.google.com/compute/docs/api/python_guide
    # (function _blocking_call)
    def _wait_until_done(self, response, wait=30):
        """
        Blocks until the operation status is done for the given operation.

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

            response = request.execute(self._auth_http)
            if response:
                status = response['status']
        return response

    def start_instance(self,
                       # these are common to any
                       # CloudProvider.start_instance() call
                       key_name, public_key_path, private_key_path,
                       security_group, flavor, image_name, image_userdata,
                       # these params are specific to the
                       # GoogleCloudProvider
                       instance_name=None):
        """
        Starts a new instance with the given properties and returns
        the instance id.

        .. fixme::

          The `key_name` and `key_path` are currently ignored.
          We need to understand how GCE does SSH authorization.

        """
        # construct URLs
        image_url = '%s%s/global/images/%s' % (GCE_URL, 'google', image_name)
        project_url = '%s%s' % (GCE_URL, PROJECT_ID)
        machine_type_url = '%s/global/machineTypes/%s' % (project_url, flavor)
        # it does not make much sense to set different zone and
        # network for each cluster machine, so we set them
        # cloud-wide...
        zone_url = '%s/zones/%s' % (project_url, self._zone)
        network_url = '%s/global/networks/%s' % (project_url, self._network)

        # construct the request body
        if instance_name is None:
            # XXX: it would be nice to have a way to name this
            # <clustername>-<nodetype>-NNN, e.g.,
            # "mycluster-compute-001", but we take an easy path to
            # uniqueness for now.
            instance_name = 'elasticluster-%s' % uuid.uuid4()
        instance = {
            'name': instance_name,
            'machineType': flavor,
            'image': image_url,
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
                 }]
        }

        # create the instance
        gce = self._connect()
        request = gce.instances().insert(
            project=self._project_id, body=instance, zone=self._zone)
        response = request.execute(self._auth_http)
        response = self._wait_until_done(response)
        # XXX: we are likely interested in one specific value from the
        # whole response, but we cannot find out until we can see an
        # actual GCE JSON dump... However, `stop_instance()` works by
        # instance name, so let us return that.
        return instance_name

    def stop_instance(self, instance_id):
        """
        Stops the instance with the given id gracefully.
        """
        gce = self._connect()

        # delete an Instance
        request = gce.instances().delete(
            project=self._project_id, instance=instance_id, zone=self._zone)
        response = request.execute(self._auth_http)
        response = self._wait_until_done(response)
        # XXX: check for errors!

    def list_instances(self, filter=None):
        """
        List instances on GCE, optionally filtering the results.

        :param str filter: Filter specification; see https://developers.google.com/compute/docs/reference/latest/instances/list for details.
        """
        gce = self._connect()
        request = gce.instances().list(
            project=self._project_id, filter=filter, zone=self._zone)
        response = request.execute(self._auth_http)
        if response and 'items' in response:
            return response['items']
        else:
            # return new empty list
            return list()

    def is_instance_running(self, instance_id):
        """
        Return True/False depending on whether the instance with the
        given id is up and running.
        """
        items = self.list_instances(filter=('name eq "%s"' % instance_id))
        for item in items:
            if item['status'] == 'RUNNING':
                return True
        return False
