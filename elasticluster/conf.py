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

import os
import re
import sys

from voluptuous.voluptuous import message
from configobj import ConfigObj
from voluptuous import Schema, All, Length, Any, Url, Boolean

from elasticluster.exceptions import ConfigurationError
from elasticluster.providers.ec2_boto import BotoCloudProvider
from elasticluster.providers.gce import GoogleCloudProvider
from elasticluster.providers.ansible_provider import AnsibleSetupProvider
from elasticluster.cluster import Cluster, ClusterStorage, Node


class Configurator(object):
    """
    Responsible to create instances, which need information from the
    configuration file.
    """

    cloud_providers_map = {
        "ec2_boto": BotoCloudProvider,
        "google": GoogleCloudProvider,
    }

    setup_providers_map = {"ansible": AnsibleSetupProvider, }

    default_storage_dir = os.path.expanduser(
        "~/.elasticluster/storage")


    def __init__(self, cluster_conf, cluster_template=None):
        """
        """
        self.general_conf = dict()
        self.general_conf['storage'] = Configurator.default_storage_dir
        self.cluster_conf = cluster_conf
        self.cluster_template = cluster_template

        validator = ConfigValidator(self.cluster_conf)
        validator.validate()

    @classmethod
    def fromConfig(cls, configfile, cluster_template=None):
        """
        """
        config_reader = ConfigReader(configfile)
        conf = config_reader.read_config()
        return Configurator(conf, cluster_template)

    def create_cloud_provider(self, cluster_template=None):
        """
        """
        if not cluster_template:
            cluster_template = self.cluster_template

        conf = self.cluster_conf[cluster_template]['cloud']

        provider = Configurator.cloud_providers_map[conf["provider"]]
        conf.pop('provider')

        return provider(**conf)

    def create_cluster(self, cluster_name, cluster_template=None, **extra_args):
        """

        :param cluster_template:
        :param extra_args:
        :return:
        """
        if not cluster_template:
            cluster_template = self.cluster

        if cluster_template not in self.cluster_conf:
            raise ConfigurationError(
                "Invalid configuration for cluster `%s`: %s"
                "" % (cluster_template, cluster_name))

        conf = self.cluster_conf[cluster_template]

        nodes = dict((k[:-6], int(v)) for k, v in conf['cluster'].iteritems() if k.endswith('_nodes'))

        return Cluster(cluster_template,
                       cluster_name,
                       conf['cluster']['cloud'],
                       self.create_cloud_provider(cluster_template=cluster_template),
                       self.create_setup_provider(cluster_template=cluster_template),
                       nodes,
                       self,
        )

    def load_cluster(self, cluster_name):
        storage = self.create_cluster_storage()
        information = storage.load_cluster(cluster_name)

        cluster = self.create_cluster(
            information['name'], information['template'])

        # Clear cluster nodes.
        cluster.nodes = dict((k, []) for k in cluster.nodes)
        for dnode in information['nodes']:
            if dnode['type'] not in cluster.nodes:
                cluster.nodes[dnode['type']] = []
            node = cluster.add_node(dnode['type'], name=dnode['name'])
            node.instance_id = dnode['instance_id']
            node.ip_public = dnode['ip_public']
            node.ip_private = dnode['ip_private']

        return cluster

    def create_node(self, cluster_name, node_type, cloud_provider, name):
        """
        Creates a node with the needed information from the
        configuration file. The information of the node is specific to
        its type (e.g. a frontend node could differ from a compute
        node).
        """
        conf = self.cluster_conf[cluster_name]['nodes'][node_type]
        conf_login = self.cluster_conf[cluster_name]['login']

        return Node(name, node_type, cloud_provider, conf_login['user_key_public'],
                    conf_login["user_key_private"], conf_login['user_key_name'],
                    conf_login['image_user'], conf['security_group'],
                    conf['image_id'], conf['flavor'],
                    image_userdata=conf.get('image_userdata', ''))

    def create_cluster_storage(self):
        """
        Creates the storage to manage clusters.
        """
        return ClusterStorage(self.general_conf['storage'])

    def create_setup_provider(self, cluster_template=None):
        if not cluster_template:
            cluster_template = self.cluster_template

        conf = self.cluster_conf[cluster_template]['setup']
        conf_login = self.cluster_conf[cluster_template]['login']

        provider_name = conf.get('provider')
        if provider_name not in Configurator.setup_providers_map:
            raise ConfigurationError(
                "Invalid value `%s` for `setup_provider` in configuration "
                "file." % provider_name)

        provider = Configurator.setup_providers_map[provider_name]

        return provider(
            conf_login['user_key_private'], conf_login['image_user'],
            conf_login['image_user_sudo'], conf_login['image_sudo'],
            **conf)


class ConfigValidator(object):
    def __init__(self, config):
        self.config = config


    def _pre_validate(self):
        # read cloud provider environment variables (ec2_boto or google)
        for cluster, property in self.config.iteritems():
            if "cloud" in property and "provider" in property['cloud']:
                for param, value in property['cloud'].iteritems():
                    PARAM = param.upper()
                    if not value and PARAM in os.environ:
                        property['cloud'][param] = os.environ[PARAM]

    def _post_validate(self):
        # expand all paths
        for cluster, values in self.config.iteritems():
            self.config[cluster]['setup']['playbook_path'] = os.path.expanduser(
                os.path.expanduser(values['setup']['playbook_path']))
            self.config[cluster]['login']['user_key_private'] = os.path.expanduser(
                os.path.expanduser(values['login']['user_key_private']))
            self.config[cluster]['login']['user_key_public'] = os.path.expanduser(
                os.path.expanduser(values['login']['user_key_public']))


    def validate(self):
        self._pre_validate()

        # custom validators
        @message("file could not be found")
        def check_file(v):
            f = os.path.expanduser(os.path.expanduser(v))
            if os.path.exists(f):
                return f
            else:
                raise ValueError("file could not be found `%s`" % v)

        # schema to validate all cluster properties
        schema = {"cloud":
                      Any(
                          {
                              "provider": 'ec2_boto',
                              "ec2_url": Url(str),
                              "ec2_access_key": All(str, Length(min=1)),
                              "ec2_secret_key": All(str, Length(min=1)),
                              "ec2_region": All(str, Length(min=1)),
                          },
                          {
                              "provider": 'google',
                              "client_id": All(str, Length(min=1)),
                              "client_secret": All(str, Length(min=1)),
                              "project_id": All(str, Length(min=1)),
                          }
                      ),
                  "cluster": {
                      "cloud": All(str, Length(min=1)),
                      "setup_provider": All(str, Length(min=1)),
                      "login": All(str, Length(min=1)),
                  },
                  "setup": {
                      "provider": All(str, Length(min=1)),
                      "playbook_path": check_file(),
                  },
                  "login": {
                      "image_user": All(str, Length(min=1)),
                      "image_user_sudo": All(str, Length(min=1)),
                      "image_sudo": Boolean(str),
                      "user_key_name": All(str, Length(min=1)),
                      "user_key_private": check_file(),
                      "user_key_public": check_file(),
                  }
        }

        node_schema = {
            "flavor": All(str, Length(min=1)),
            "image_id": All(str, Length(min=1)),
            "security_group": All(str, Length(min=1))
        }

        # validation
        validator = Schema(schema, required=True, extra=True)
        validator_node = Schema(node_schema, required=True, extra=True)
        for cluster, properties in self.config.iteritems():
            validator(properties)

            if 'nodes' not in properties or len(properties['nodes']) == 0:
                raise ValueError("No nodes configured for cluster `%s`" % cluster)

            for node, props in properties['nodes'].iteritems():
                validator_node(props)

        self._post_validate()


class ConfigReader(object):
    """
    
    """
    cluster_section = "cluster"
    login_section = "login"
    setup_section = "setup"
    cloud_section = "cloud"
    node_section = "node"

    # TODO: get the interpolation right!
    config_defaults = {
        'ansible_pb_dir': os.path.join(
            sys.prefix, 'share/elasticluster/providers/ansible-playbooks'),
        'ansible_module_dir': os.path.join(
            sys.prefix,
            'share/elasticluster/providers/ansible-playbooks/modules'),
    }


    def __init__(self, configfile):
        self.configfile = configfile
        self.conf = ConfigObj(self.configfile)

    def read_config(self):
        """

        :return:
        """
        clusters = dict((key, value) for key, value in self.conf.iteritems() if
                        re.search(ConfigReader.cluster_section + "/(.*)", key))

        conf_values = dict()

        for cluster in clusters:
            name = re.search(ConfigReader.cluster_section + "/(.*)", cluster).groups()[0]
            try:
                cluster_conf = dict(self.conf[cluster])
                cloud_name = ConfigReader.cloud_section + "/" + cluster_conf['cloud']
                login_name = ConfigReader.login_section + "/" + cluster_conf['login']
                setup_name = ConfigReader.setup_section + "/" + cluster_conf['setup_provider']

                values = dict()
                values['cluster'] = cluster_conf
                values['setup'] = dict(
                    (key, value.strip("'").strip('"')) for key, value in self.conf[setup_name].iteritems())
                values['login'] = dict(
                    (key, value.strip("'").strip('"')) for key, value in self.conf[login_name].iteritems())
                values['cloud'] = dict(
                    (key, value.strip("'").strip('"')) for key, value in self.conf[cloud_name].iteritems())

                # nodes can inherit the properties of cluster or overwrite them
                nodes = dict((key, value) for key, value in values['cluster'].iteritems() if key.endswith('_nodes'))
                values['nodes'] = dict()
                for node in nodes.iterkeys():
                    node_name = re.search("(.*)_nodes", node).groups()[0]
                    property_name = ConfigReader.node_section + "/" + node
                    if property_name in self.conf:
                        node_values = dict(
                            (key, value.strip("'").strip('"')) for key, value in self.conf[property_name].iteritems())
                        node_values = dict(node_values.items() + values['cluster'].items())
                        values['nodes'][node_name] = node_values
                    else:
                        values['nodes'][node_name] = values['cluster']

                conf_values[name] = values
            except KeyError:
                raise ValueError(
                    "could not find all sections required `cluster`, `setup`, `login`, `cloud` for cluster `%s`" % name)

        return conf_values
