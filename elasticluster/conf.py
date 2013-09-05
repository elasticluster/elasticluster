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
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>, Antonio Messina <antonio.s.messina@gmail.com>'

# System imports
import os
import re
import sys

# External modules
from configobj import ConfigObj
try:
    # Voluptuous version >= 0.8.1
    from voluptuous import message, MultipleInvalid, Invalid, Schema
    from voluptuous import All, Length, Any, Url, Boolean
except ImportError:
    # Voluptuous version <= 0.7.2
    from voluptuous.voluptuous import message, MultipleInvalid, Invalid
    from voluptuous import Schema, All, Length, Any, Url, Boolean

# Elasticluster imports
from elasticluster.exceptions import ConfigurationError
from elasticluster.providers.ec2_boto import BotoCloudProvider
from elasticluster.providers.gce import GoogleCloudProvider
from elasticluster.providers.ansible_provider import AnsibleSetupProvider
from elasticluster.cluster import Cluster, ClusterStorage, Node


class Configurator(object):
    """
    The Configurator is responsible for (I) keeping track of the
    configuration and (II) offer factory methods to create all kind of
    objects that need information from the configuration.

    The cluster configuration dictionary is structured in the following way:
    (see an example @
     https://github.com/gc3-uzh-ch/elasticluster/wiki/Configuration-Module)
    { "<cluster_template>" : {
        "setup" : { properties of the setup section },
        "cloud" : { properties of the cloud section },
        "login" : { properties of the login section },
        "cluster" : { properties of the cluster section },
        "nodes": {  "<node_type>" : { properties of the node},
                    "<node_type>" : { properties of the node},
                },
        },
     "<cluster_template>" : {
        (see above)
        }
     }
    """

    cloud_providers_map = {
        "ec2_boto": BotoCloudProvider,
        "google": GoogleCloudProvider,
    }

    setup_providers_map = {"ansible": AnsibleSetupProvider, }

    default_storage_dir = os.path.expanduser(
        "~/.elasticluster/storage")

    def __init__(self, cluster_conf, storage_path=None):
        """
        Default constructor to initialize a Configurator.
        :param cluster_conf: configuration dictionary
        :raises MultipleInvalid: configuration validation
        """
        self.general_conf = dict()
        self.cluster_conf = cluster_conf

        if storage_path:
            self.general_conf['storage'] = storage_path
        else:
            self.general_conf['storage'] = Configurator.default_storage_dir

        validator = ConfigValidator(self.cluster_conf)
        validator.validate()

    @classmethod
    def fromConfig(cls, configfile, storage_path=None):
        """
        Helper method to initialize Configurator from an ini file.
        :param configfile: path to the ini file
        :return: configurator object
        """
        config_reader = ConfigReader(configfile)
        conf = config_reader.read_config()
        return Configurator(conf, storage_path=storage_path)

    def create_cloud_provider(self, cluster_template):
        """
        Creates a cloud provider by inspecting the configuration properties
        of the given cluster template.
        :param cluster_template: template to use (if not already specified
            on init)
        :return: object that fulfills the contract of
            :py:class:`elasticluster.providers.AbstractSetupProvider`
        """
        conf = self.cluster_conf[cluster_template]['cloud']

        provider = Configurator.cloud_providers_map[conf['provider']]
        providerconf = conf.copy()
        providerconf.pop('provider')
        providerconf['storage_path'] = self.general_conf['storage']

        return provider(**providerconf)

    def create_cluster(self, template, name=None):
        """
        Creates a cluster by inspecting the configuration properties of the
            given cluster template.
        :param template: name of the cluster template

        :param name: name of the cluster. If not defined, the cluster
        will be named after the template.

        :return: :py:class:`elasticluster.cluster.cluster` instance

        :raises ConfigurationError: cluster template not found in config
        """
        if not name:
            name = template

        if template not in self.cluster_conf:
            raise ConfigurationError(
                "Invalid configuration for cluster `%s`: %s"
                "" % (template, name))

        conf = self.cluster_conf[template]

        nodes = dict(
            (k[:-6], int(v)) for k, v in conf['cluster'].iteritems() if
            k.endswith('_nodes'))
        min_nodes = dict(
            (k[:-10], int(v)) for k, v in conf['cluster'].iteritems() if
            k.endswith('_nodes_min'))

        extra = conf['cluster'].copy()
        extra.pop('cloud')
        extra.pop('setup_provider')
        return Cluster(template,
                       name,
                       conf['cluster']['cloud'],
                       self.create_cloud_provider(template),
                       self.create_setup_provider(template, name=name),
                       nodes,
                       self, min_nodes=min_nodes, **extra)

    def load_cluster(self, cluster_name):
        """
        Loads a cluster from the local stored information.
        :param cluster_name: name of the cluster
        :return: :py:class:`elasticluster.cluster.cluster` instance
        """
        storage = self.create_cluster_storage()
        information = storage.load_cluster(cluster_name)

        cluster = self.create_cluster(
            information['template'], information['name'])

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

    def create_node(self, cluster_template, node_type, cloud_provider, name):
        """
        :param cluster_template: name of the cluster template
        :param node_type: type of the node, string defining the <group> in
            the configuration
        :param cloud_provider: instance of :py:class:`elasticluster
            .providers.AbstractCloudProvider`
        :param name: name of the node
        :return: :py:class:`elasticluster.cluster.node` instance
        """
        conf = self.cluster_conf[cluster_template]['nodes'][node_type]
        conf_login = self.cluster_conf[cluster_template]['login']

        return Node(name, node_type, cloud_provider,
                    conf_login['user_key_public'],
                    conf_login["user_key_private"],
                    conf_login['user_key_name'],
                    conf_login['image_user'], conf['security_group'],
                    conf['image_id'], conf['flavor'],
                    image_userdata=conf.get('image_userdata', ''))

    def create_cluster_storage(self):
        """
        Creates an instance of :py:class:`elasticluster.cluster.ClusterStorage`
            to safe information about a cluster local.
        """
        return ClusterStorage(self.general_conf['storage'])

    def create_setup_provider(self, cluster_template, name=None):
        conf = self.cluster_conf[cluster_template]['setup']
        conf['general_conf'] = self.general_conf.copy()
        if name:
            conf['cluster_name'] = name
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
    """
    Validator for the cluster configuration dictionary.
    """

    def __init__(self, config):
        """
        :param config: dictionary containing cluster configuration properties
        """
        self.config = config

    def _pre_validate(self):
        """
        Handles all pre validation phase functionality, such as:
        - reading environment variables
        - interpolating configuraiton options
        """
        # read cloud provider environment variables (ec2_boto or google)
        for cluster, props in self.config.iteritems():
            if "cloud" in props and "provider" in props['cloud']:
                for param, value in props['cloud'].iteritems():
                    PARAM = param.upper()
                    if not value and PARAM in os.environ:
                        props['cloud'][param] = os.environ[PARAM]

        # interpolate ansible path manual, since configobj does not offer
        # an easy way to handle this
        ansible_pb_dir = os.path.join(
            sys.prefix,
            'share/elasticluster/providers/ansible-playbooks')
        for cluster, props in self.config.iteritems():
            if 'setup' in props and 'playbook_path' in props['setup']:
                if props['setup']['playbook_path'].startswith(
                        "%(ansible_pb_dir)s"):
                    pbpath = props['setup']['playbook_path']
                    pbpath = pbpath.replace("%(ansible_pb_dir)s",
                                            str(ansible_pb_dir))
                    self.config[cluster]['setup']['playbook_path'] = pbpath

            elif 'setup' in props:
                # set default playbook directory if none specified
                setup_conf = self.config[cluster]['setup']
                setup_conf['playbook_path'] = ansible_pb_dir + os.sep + \
                                              "site.yml"

    def _post_validate(self):
        """
        Handles all post validation phase functionality, such as:
        - expanding file paths
        """
        # expand all paths
        for cluster, values in self.config.iteritems():
            conf = self.config[cluster]
            pbpath = os.path.expanduser(values['setup']['playbook_path'])
            conf['setup']['playbook_path'] = pbpath

            privkey = os.path.expanduser(values['login']['user_key_private'])
            conf['login']['user_key_private'] = privkey

            pubkey = os.path.expanduser(values['login']['user_key_public'])
            conf['login']['user_key_public'] = pubkey

    def validate(self):
        """
        Validates the given configuration :py:attr:`self.config` to comply
        with elasticluster. As well all types are converted to the expected
        format if possible.
        """
        self._pre_validate()
        # custom validators
        @message("file could not be found")
        def check_file(v):
            f = os.path.expanduser(os.path.expanduser(v))
            if os.path.exists(f):
                return f
            else:
                raise Invalid("file could not be found `%s`" % v)

        # schema to validate all cluster properties
        schema = {"cluster": {"cloud": All(str, Length(min=1)),
                              "setup_provider": All(str, Length(min=1)),
                              "login": All(str, Length(min=1)),
                              },
                  "setup": {"provider": All(str, Length(min=1)),
                            "playbook_path": check_file(),
                            },
                  "login": {"image_user": All(str, Length(min=1)),
                            "image_user_sudo": All(str, Length(min=1)),
                            "image_sudo": Boolean(str),
                            "user_key_name": All(str, Length(min=1)),
                            "user_key_private": check_file(),
                            "user_key_public": check_file(),
                            }
                  }

        cloud_schema_ec2 = {"provider": 'ec2_boto',
                            "ec2_url": Url(str),
                            "ec2_access_key": All(str, Length(min=1)),
                            "ec2_secret_key": All(str, Length(min=1)),
                            "ec2_region": All(str, Length(min=1))}
        cloud_schema_gce = {"provider": 'google',
                            "gce_client_id": All(str, Length(min=1)),
                            "gce_client_secret": All(str, Length(min=1)),
                            "gce_project_id": All(str, Length(min=1))}

        node_schema = {
            "flavor": All(str, Length(min=1)),
            "image_id": All(str, Length(min=1)),
            "security_group": All(str, Length(min=1))
        }

        # validation
        validator = Schema(schema, required=True, extra=True)
        validator_node = Schema(node_schema, required=True, extra=True)
        ec2_validator = Schema(cloud_schema_ec2, required=True, extra=False)
        gce_validator = Schema(cloud_schema_gce, required=True, extra=False)

        if not self.config:
            raise Invalid("No clusters found in configuration.")

        for cluster, properties in self.config.iteritems():
            validator(properties)

            if properties['cloud']['provider'] == "ec2":
                ec2_validator(properties['cloud'])
            elif properties['cloud']['provider'] == "google":
                gce_validator(properties['cloud'])

            if 'nodes' not in properties or len(properties['nodes']) == 0:
                raise Invalid(
                    "No nodes configured for cluster `%s`" % cluster)

            for node, props in properties['nodes'].iteritems():
                # check name pattern to conform hostnames
                match = re.search(r'^[a-zA-Z0-9-]*$', node)
                if not match:
                    raise Invalid(
                        "Invalid name `%s` for node group. A valid node group "
                        "can only consist of letters, digits or the hyphens "
                        "character (`-`)" % node)

                validator_node(props)

        self._post_validate()


class ConfigReader(object):
    """
    Reads the configuration properties from a ini file.
    """
    cluster_section = "cluster"
    login_section = "login"
    setup_section = "setup"
    cloud_section = "cloud"
    node_section = "node"

    def __init__(self, configfile):
        """
        :param configfile: path to configfile
        """
        self.configfile = configfile
        self.conf = ConfigObj(self.configfile, interpolation=False)

        @message("file could not be found")
        def check_file(v):
            f = os.path.expanduser(os.path.expanduser(v))
            if os.path.exists(f):
                return f
            else:
                raise Invalid("file could not be found `%s`" % v)

        self.schemas = {
            "cloud": Schema(
                {"provider": Any('ec2_boto', 'google'),
                "ec2_url": Url(str),
                "ec2_access_key": All(str, Length(min=1)),
                "ec2_secret_key": All(str, Length(min=1)),
                "ec2_region": All(str, Length(min=1)),
                "gce_project_id": All(str, Length(min=1)),
                "gce_client_id": All(str, Length(min=1)),
                "gce_client_secret": All(str, Length(min=1)),
                }),
            "cluster": Schema(
                {"cloud": All(str, Length(min=1)),
                 "setup_provider": All(str, Length(min=1)),
                 "login": All(str, Length(min=1)),
                 }, required=True, extra=True),
            "setup": Schema(
                {"provider": All(str, Length(min=1)),
                 }, required=True, extra=True),
            "login": Schema(
                {"image_user": All(str, Length(min=1)),
                 "image_user_sudo": All(str, Length(min=1)),
                 "image_sudo": Boolean(str),
                 "user_key_name": All(str, Length(min=1)),
                 "user_key_private": check_file(),
                 "user_key_public": check_file(),
                 }, required=True)
            }

    def read_config(self):
        """
        Reads the configuration properties from the ini file and links the
        section to comply with the cluster config dictionary format.
        :return: dictionary containing all configuration properties from the
         ini file in compliance to the cluster config format
        :raises MultipleInvalid: not all sections present or broken links
            between secitons
        """
        clusters = dict((key, value) for key, value in self.conf.iteritems() if
                        re.search(ConfigReader.cluster_section + "/(.*)", key)
                        and key.count("/") == 1)

        conf_values = dict()

        errors = MultipleInvalid()

        for cluster in clusters:
            name = re.search(ConfigReader.cluster_section + "/(.*)",
                             cluster).groups()[0]
            if not name:
                errors.add("Invalid section name `%s`" % cluster)
                continue

            cluster_conf = dict(self.conf[cluster])

            try:
                self.schemas['cluster'](cluster_conf)
            except MultipleInvalid as ex:
                for error in ex.errors:
                    errors.add("Section `%s`: %s" % (cluster, error))
                continue

            cloud_name = ConfigReader.cloud_section + "/" + cluster_conf[
                'cloud']
            login_name = ConfigReader.login_section + "/" + cluster_conf[
                'login']
            setup_name = ConfigReader.setup_section + "/" + cluster_conf[
                'setup_provider']

            values = dict()
            values['cluster'] = cluster_conf
            try:
                values['setup'] = dict(self.conf[setup_name])
                self.schemas['setup'](values['setup'])
            except KeyError, ex:
                errors.add("cluster `%s` setup section `%s` does not exists" % (cluster, setup_name))
            except MultipleInvalid, ex:
                for error in ex.errors:
                    errors.add(error)

            try:
                values['login'] = dict(self.conf[login_name])
                self.schemas['login'](values['login'])
            except KeyError, ex:
                errors.add("cluster `%s` login section `%s` does not exists" % (cluster, login_name))
            except MultipleInvalid, ex:
                for error in ex.errors:
                    errors.add(error)

            try:
                values['cloud'] = dict(self.conf[cloud_name])
                self.schemas['cloud'](values['cloud'])
            except KeyError, ex:
                errors.add("cluster `%s` cloud section `%s` does not exists" % (cluster, cloud_name))
            except MultipleInvalid, ex:
                for error in ex.errors:
                    errors.add(error)

            try:
                # nodes can inherit the properties of cluster or overwrite them
                nodes = dict((key, value) for key, value in
                             values['cluster'].items() if
                             key.endswith('_nodes'))
                values['nodes'] = dict()
                for node in nodes.iterkeys():
                    node_name = re.search("(.*)_nodes", node).groups()[0]
                    property_name = "%s/%s/%s" % (ConfigReader.cluster_section,
                                                  name, node_name)
                    if property_name in self.conf:
                        node_values = dict(
                            (key, value.strip("'").strip('"')) for key, value
                            in self.conf[property_name].iteritems())
                        node_values = dict(
                            values['cluster'].items() + node_values.items())
                        values['nodes'][node_name] = node_values
                    else:
                        values['nodes'][node_name] = values['cluster']

                conf_values[name] = values
            except KeyError, ex:
                errors.add("Error in section `%s`" % cluster)

        if errors.errors:
            raise errors
        return conf_values
