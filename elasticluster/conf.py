#! /usr/bin/env python
#
# Copyright (C) 2013, 2014, 2015 S3IT, University of Zurich
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
__author__ = str.join(', ', [
    'Nicolas Baer <nicolas.baer@uzh.ch>',
    'Antonio Messina <antonio.s.messina@gmail.com>',
    'Riccardo Murri <riccardo.murri@gmail.com>',
])

# System imports
from collections import defaultdict
import os
import re
import sys
try:
    from types import StringTypes
except ImportError:
    # Python 3
    StringTypes = (str,)
import warnings

# External modules
from ConfigParser import RawConfigParser

from pkg_resources import resource_filename

try:
    # Voluptuous version >= 0.8.1
    from voluptuous import message, MultipleInvalid, Invalid, Schema
    from voluptuous import All, Length, Any, Url, Boolean, Optional, Required
except ImportError:
    # Voluptuous version <= 0.7.2
    from voluptuous.voluptuous import message, MultipleInvalid, Invalid
    from voluptuous import Schema, All, Length, Any, Url, Boolean, Optional, Required

# Elasticluster imports
from elasticluster import log
from elasticluster.exceptions import ConfigurationError
from elasticluster.providers.ansible_provider import AnsibleSetupProvider
from elasticluster.cluster import Cluster
from elasticluster.repository import MultiDiskRepository


class Configurator(object):
    """The `Configurator` class is responsible for

    1) keeping track of the configuration and

    2) offer factory methods to create all kind of objects that need
    information from the configuration.

    The cluster configuration dictionary is structured in the
    following way: (see an example @
    https://github.com/gc3-uzh-ch/elasticluster/wiki/Configuration-Module)::

          { "<cluster_template>" : {
              "setup" : { properties of the setup section },
              "cloud" : { properties of the cloud section },
              "login" : { properties of the login section },
              "cluster" : { properties of the cluster section },
              "nodes": {  "<node_kind>" : { properties of the node},
                          "<node_kind>" : { properties of the node},
                      },
              },
           "<cluster_template>" : {
              (see above)
              }
           }


    It is also responsible for loading a cluster from a valid
    `repository.AbstractClusterRepository`.

    :param dict cluster_conf: see description above

    :param str storage_path: path to store data

    :raises MultipleInvalid: configuration validation

    """

    setup_providers_map = {"ansible": AnsibleSetupProvider, }

    default_storage_path = os.path.expanduser(
        "~/.elasticluster/storage")
    default_storage_type = 'yaml'

    def __init__(self, cluster_conf, storage_path=None, storage_type=None):
        self.general_conf = dict()
        self.cluster_conf = cluster_conf

        if storage_path:
            storage_path = os.path.expanduser(storage_path)
            storage_path = os.path.expandvars(storage_path)
            self.general_conf['storage_path'] = storage_path
        else:
            self.general_conf['storage_path'] = Configurator.default_storage_path

        self.general_conf['storage_type'] = storage_type or Configurator.default_storage_type

        validator = ConfigValidator(self.cluster_conf)
        validator.validate()

    @classmethod
    def fromConfig(cls, configfiles, storage_path=None):
        """
        Helper method to initialize Configurator from a `.ini`-format file.

        :param list configfiles: list of paths to the ini file(s).
            For each path ``P`` in `configfiles`, if a directory named ``P.d``
            exists, also reads all the `*.conf` files in that directory.

        :param str storage_path:
            path to the storage directory. If defined, a
            :py:class:`repository.DiskRepository` class will be instantiated.

        :return: :py:class:`Configurator`
        """
        if isinstance(configfiles, StringTypes):
            configfiles = [configfiles]
        config_reader = ConfigReader(configfiles)
        (conf, storage_conf) = config_reader.read_config()

        # FIXME: We shouldn't need this ugly fix
        if storage_path:
            storage_conf['storage_path'] = storage_path
        return Configurator(conf, **storage_conf)

    def create_cloud_provider(self, cluster_template):
        """Creates a cloud provider by inspecting the configuration properties
        of the given cluster template.

        :param str cluster_template: template to use (if not already specified
                                 on init)
        :return: cloud provider that fulfills the contract of
                 :py:class:`elasticluster.providers.AbstractSetupProvider`
        """
        conf = self.cluster_conf[cluster_template]['cloud']

        try:
            if conf['provider'] == 'ec2_boto':
                from elasticluster.providers.ec2_boto import BotoCloudProvider
                provider = BotoCloudProvider
            elif conf['provider'] == 'openstack':
                from elasticluster.providers.openstack import OpenStackCloudProvider
                provider = OpenStackCloudProvider
            elif conf['provider'] == 'google':
                from elasticluster.providers.gce import GoogleCloudProvider
                provider = GoogleCloudProvider
            else:
                raise Invalid("Invalid provider '%s' for cluster '%s'"% (conf['provider'], cluster_template))
        except ImportError as ex:
            raise Invalid("Unable to load provider '%s': %s" % (conf['provider'], ex))

        providerconf = conf.copy()
        providerconf.pop('provider')
        providerconf['storage_path'] = self.general_conf['storage_path']

        return provider(**providerconf)

    def create_cluster(self, template, name=None):
        """Creates a cluster by inspecting the configuration properties of the
        given cluster template.

        :param str template: name of the cluster template

        :param str name: name of the cluster. If not defined, the cluster
                         will be named after the template.

        :return: :py:class:`elasticluster.cluster.cluster` instance:

        :raises ConfigurationError: cluster template not found in config

        """
        if not name:
            name = template

        if template not in self.cluster_conf:
            raise ConfigurationError(
                "Invalid configuration for cluster `%s`: %s"
                "" % (template, name))

        conf = self.cluster_conf[template]
        conf_login = self.cluster_conf[template]['login']

        extra = conf['cluster'].copy()
        extra.pop('cloud')
        extra.pop('setup_provider')
        extra['template'] = template

        cluster = Cluster(name=name,
                          cloud_provider=self.create_cloud_provider(template),
                          setup_provider=self.create_setup_provider(template, name=name),
                          user_key_name=conf_login['user_key_name'],
                          user_key_public=conf_login['user_key_public'],
                          user_key_private=conf_login["user_key_private"],
                          repository=self.create_repository(),
                          **extra)

        nodes = dict(
            (k[:-6], int(v)) for k, v in conf['cluster'].iteritems() if
            k.endswith('_nodes'))

        for kind, num in nodes.iteritems():
            conf_kind = conf['nodes'][kind]
            extra = conf_kind.copy()
            extra.pop('image_id', None)
            extra.pop('flavor', None)
            extra.pop('security_group', None)
            extra.pop('image_userdata', None)
            userdata = conf_kind.get('image_userdata', '')
            cluster.add_nodes(kind,
                              num,
                              conf_kind['image_id'],
                              conf_login['image_user'],
                              conf_kind['flavor'],
                              conf_kind['security_group'],
                              image_userdata=userdata,
                              **extra)
        return cluster

    def load_cluster(self, cluster_name):
        """Loads a cluster from the cluster repository.

        :param str cluster_name: name of the cluster
        :return: :py:class:`elasticluster.cluster.cluster` instance
        """
        repository = self.create_repository()
        cluster = repository.get(cluster_name)
        if not cluster._setup_provider:
            cluster._setup_provider = self.create_setup_provider(cluster.template)
        if not cluster.cloud_provider:
            cluster.cloud_provider = self.create_cloud_provider(cluster.template)
        cluster.update_config(
            self.cluster_conf[cluster.template]['cluster'],
            self.cluster_conf[cluster.template]['login']
        )
        return cluster

    @staticmethod
    def _read_node_groups(conf):
        """
        """
        result = defaultdict(list)
        for key, value in conf.items():
            if not key.endswith('_groups'):
                continue
            node_kind = key[:-len('_groups')]
            group_names = [group_name.strip()
                           for group_name in value.split(',')]
            for group_name in group_names:
                # handle renames
                if group_name in Configurator._renamed_node_groups:
                    old_group_name = group_name
                    group_name, remove_at = Configurator._renamed_node_groups[group_name]
                    warnings.warn(
                        "Group `{0}` was renamed to `{1}`;"
                        " please fix your configuration file."
                        " Support for automatically renaming"
                        " this group will be removed in {2}."
                        .format(old_group_name, group_name,
                                (("ElastiCluster {0}".format(remove_at))
                                 if remove_at
                                 else ("a future version of ElastiCluster"))),
                        DeprecationWarning)
                result[node_kind].append(group_name)
        return result

    _renamed_node_groups = {
        # old name     ->  (new name             will be removed in...
        'gluster_data' :   ('glusterfs_server',  '1.4'),
        'gluster_client':  ('glusterfs_client',  '1.4'),
        'slurm_clients':   ('slurm_workers',     '1.4'),
    }

    def create_setup_provider(self, cluster_template, name=None):
        """Creates the setup provider for the given cluster template.

        :param str cluster_template: template of the cluster
        :param str name: name of the cluster to read configuration properties
        """
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

        storage_path = self.general_conf['storage_path']
        if 'playbook_path' in conf:
            playbook_path = conf['playbook_path']
            del conf['playbook_path']
        else:
            playbook_path = None
        groups = self._read_node_groups(conf)
        environment = dict()
        for nodekind, grps in groups.iteritems():
            if not isinstance(grps, list):
                groups[nodekind] = [grps]

            # Environment variables parsing
            environment[nodekind] = dict()
            for key, value in list(conf.items()) + list(self.cluster_conf[cluster_template]['cluster'].items()):
                # Set both group and global variables
                for prefix in ["%s_var_" % nodekind,
                               "global_var_"]:
                    if key.startswith(prefix):
                        var = key.replace(prefix, '')
                        environment[nodekind][var] = value
                        log.debug("setting variable %s=%s for node kind %s",
                                  var, value, nodekind)

        provider = Configurator.setup_providers_map[provider_name]
        return provider(groups, playbook_path=playbook_path,
                        environment_vars=environment,
                        storage_path=storage_path,
                        sudo=conf_login['image_sudo'],
                        sudo_user=conf_login['image_user_sudo'],
                        **conf)

    def create_repository(self):
        storage_path = self.general_conf['storage_path']
        storage_type = self.general_conf['storage_type']
        return MultiDiskRepository(storage_path, storage_type)


## custom validators
@message("file could not be found")
def file_exists(v):
    f = os.path.expanduser(os.path.expandvars(v))
    if os.access(f, os.F_OK):
        return f
    else:
        raise Invalid("file `{v}` could not be found".format(v=v))

@message("file cannot be read")
def can_read_file(v):
    f = os.path.expanduser(os.path.expandvars(v))
    if os.access(f, os.R_OK):
        return f
    else:
        raise Invalid("cannot read file `{v}`".format(v=v))

@message("cannot execute file")
def can_execute_file(v):
    f = os.path.expanduser(os.path.expandvars(v))
    if os.access(f, os.X_OK):
        return f
    else:
        raise Invalid("cannot execute file `{v}`".format(v=v))

@message("Unsupported nova API version")
def nova_api_version(version):
    try:
        from novaclient import client,exceptions
        client.get_client_class(version)
        return version
    except exceptions.UnsupportedVersion as ex:
        raise Invalid(
            "Invalid value for `nova_api_version`: {0}".format(ex))


class ConfigValidator(object):
    """Validator for the cluster configuration dictionary.

    :param config: dictionary containing cluster configuration properties
    """

    def __init__(self, config):
        self.config = config

    def _pre_validate(self):
        """Handles all pre-validation tasks, such as:

        * reading environment variables
        * interpolating configuration options
        """
        # read cloud provider environment variables (ec2_boto or google, openstack)
        for cluster, props in self.config.iteritems():
            if "cloud" in props and "provider" in props['cloud']:

                for param, value in props['cloud'].iteritems():
                    PARAM = param.upper()
                    if not value and PARAM in os.environ:
                        props['cloud'][param] = os.environ[PARAM]

        # manually interpolate ansible path; configobj does not offer
        # an easy way to do it
        ansible_pb_dir = resource_filename('elasticluster', 'share/playbooks')
        for cluster, props in self.config.iteritems():
            if 'setup' in props and 'playbook_path' in props['setup']:
                if props['setup']['playbook_path'].startswith(
                        "%(ansible_pb_dir)s"):
                    pbpath = props['setup']['playbook_path']
                    pbpath = pbpath.replace("%(ansible_pb_dir)s",
                                            str(ansible_pb_dir))
                    self.config[cluster]['setup']['playbook_path'] = pbpath

    def _post_validate(self):
        """Handles all post-validation tasks, such as:

        * expand file paths
        """
        # expand all paths
        for cluster, values in self.config.iteritems():
            conf = self.config[cluster]
            if 'playbook_path' in values['setup']:
                pbpath = os.path.expanduser(values['setup']['playbook_path'])
                conf['setup']['playbook_path'] = pbpath

            privkey = os.path.expanduser(values['login']['user_key_private'])
            conf['login']['user_key_private'] = privkey

            pubkey = os.path.expanduser(values['login']['user_key_public'])
            conf['login']['user_key_public'] = pubkey

    def validate(self):
        """
        Validate the given configuration,
        converting properties to native Python types.

        The configuration to check must have been given to the
        constructor and stored in :py:attr:`self.config`.

        :raises: :py:class:`voluptuous.Invalid` if one property is invalid
        :raises: :py:class:`voluptuous.MultipleInvalid` if multiple
                 properties are not compliant
        """
        self._pre_validate()

        # schema to validate all cluster properties
        schema = {"cluster": {"cloud": All(str, Length(min=1)),
                              "setup_provider": All(str, Length(min=1)),
                              "login": All(str, Length(min=1)),
                          },
                  "setup": {"provider": All(str, Length(min=1)),
                            Optional("playbook_path"): can_read_file(),
                            Optional("ansible_command"): All(can_read_file(), can_execute_file()),
                            Optional("ansible_extra_args"): All(str, Length(min=1)),
                            Optional("ssh_pipelining"): Boolean(str),
                        },
                  "login": {"image_user": All(str, Length(min=1)),
                            "image_user_sudo": All(str, Length(min=1)),
                            "image_sudo": Boolean(str),
                            "user_key_name": All(str, Length(min=1)),
                            "user_key_private": can_read_file(),
                            "user_key_public": can_read_file(),
                        },
        }

        cloud_schema_ec2 = {"provider": 'ec2_boto',
                            "ec2_url": Url(str),
                            Optional("ec2_access_key"): All(str, Length(min=1)),
                            Optional("ec2_secret_key"): All(str, Length(min=1)),
                            "ec2_region": All(str, Length(min=1)),
                            Optional("request_floating_ip"): Boolean(str),
                            Optional("vpc"): All(str, Length(min=1)),
        }
        cloud_schema_gce = {"provider": 'google',
                            "gce_client_id": All(str, Length(min=1)),
                            "gce_client_secret": All(str, Length(min=1)),
                            "gce_project_id": All(str, Length(min=1)),
                            Optional("noauth_local_webserver"): Boolean(str),
                            Optional("zone"): All(str, Length(min=1)),
                            Optional("network"): All(str, Length(min=1)),
        }

        cloud_schema_openstack = {"provider": 'openstack',
                                  "auth_url": All(str, Length(min=1)),
                                  "username": All(str, Length(min=1)),
                                  "password": All(str, Length(min=1)),
                                  "project_name": All(str, Length(min=1)),
                                  Optional("request_floating_ip"): Boolean(str),
                                  Optional("region_name"): All(str, Length(min=1)),
                                  Optional("nova_api_version"): nova_api_version(),
        }

        node_schema = {
            "flavor": All(str, Length(min=1)),
            "image_id": All(str, Length(min=1)),
            "security_group": All(str, Length(min=1)),
            Optional("network_ids"): All(str, Length(min=1)),
        }

        # validation
        validator = Schema(schema, required=True, extra=True)
        node_validator = Schema(node_schema, required=True, extra=True)
        ec2_validator = Schema(cloud_schema_ec2, required=True, extra=False)
        gce_validator = Schema(cloud_schema_gce, required=True, extra=False)
        openstack_validator = Schema(cloud_schema_openstack, required=True, extra=False)

        if not self.config:
            raise Invalid("No clusters found in configuration.")

        for cluster, properties in self.config.iteritems():
            self.config[cluster] = validator(properties)

            if 'provider' not in properties['cloud']:
                raise Invalid(
                    "Missing `provider` option in cluster `%s`" % cluster)
            try:
                cloud_props = properties['cloud']
                if properties['cloud']['provider'] == "ec2_boto":
                    self.config[cluster]['cloud'] = ec2_validator(cloud_props)
                elif properties['cloud']['provider'] == "google":
                    self.config[cluster]['cloud'] = gce_validator(cloud_props)
                elif properties['cloud']['provider'] == "openstack":
                    self.config[cluster]['cloud'] = openstack_validator(cloud_props)
            except MultipleInvalid as ex:
                raise Invalid("Invalid configuration for cloud section `cloud/%s`: %s" % (properties['cluster']['cloud'], str.join(", ", [str(i) for i in ex.errors])))


            if 'nodes' not in properties or len(properties['nodes']) == 0:
                raise Invalid(
                    "No nodes configured for cluster `%s`" % cluster)

            for node, props in properties['nodes'].iteritems():
                # check name pattern to conform hostnames
                match = re.search(r'^[a-zA-Z0-9-]*$', node)
                if not match:
                    raise Invalid(
                        "Invalid name `%s` for node group. A valid node group"
                        " can only consist of letters, digits or the hyphen"
                        " character (`-`)" % (node,))

                node_validator(props)

                if (properties['cloud']['provider'] == 'ec2_boto'
                    and 'vpc' in self.config[cluster]['cloud']
                    and 'network_ids' not in props):
                    raise Invalid(
                        "Node group `%s/%s` is being used in"
                        " a VPC, so it must specify network_ids."
                        % (cluster, node))

                if (properties['cloud']['provider'] == 'ec2_boto'
                    and 'network_ids' in props
                    and 'vpc' not in self.config[cluster]['cloud']):
                    raise Invalid(
                        "Cluster `%s` must specify a VPC to place"
                        " `%s` instances in %s"
                        % (cluster, node, props['network_ids']))

        self._post_validate()


class ConfigReader(object):
    """Reads the configuration properties from a ini file.

    :param str configfile: path to configfile
    """
    cluster_section = "cluster"
    login_section = "login"
    setup_section = "setup"
    cloud_section = "cloud"
    node_section = "node"

    def __init__(self, paths):
        self.configfiles = self._list_config_files(paths)

        configparser = RawConfigParser()
        config_tmp = configparser.read(self.configfiles)
        self.conf = dict()
        for section in configparser.sections():
            self.conf[section] = dict(configparser.items(section))

        #self.conf = ConfigObj(self.configfile, interpolation=False)

        self.schemas = {
            "storage": Schema(
                {Optional("storage_path"): All(str),
                 Optional("storage_type"): Any('yaml', 'json', 'pickle'),
             }),
            "cloud": Schema(
                {"provider": Any('ec2_boto', 'google', 'openstack'),
                 "ec2_url": Url(str),
                 Optional("ec2_access_key"): All(str, Length(min=1)),
                 Optional("ec2_secret_key"): All(str, Length(min=1)),
                 "ec2_region": All(str, Length(min=1)),
                 "auth_url": All(str, Length(min=1)),
                 "username": All(str, Length(min=1)),
                 "password": All(str, Length(min=1)),
                 "tenant_name": All(str, Length(min=1)),
                 Optional("region_name"): All(str, Length(min=1)),
                 "gce_project_id": All(str, Length(min=1)),
                 "gce_client_id": All(str, Length(min=1)),
                 "gce_client_secret": All(str, Length(min=1)),
                 "nova_client_api": nova_api_version()}, extra=True),
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
                 "user_key_private": can_read_file(),
                 "user_key_public": can_read_file()}, required=True)
        }

    @staticmethod
    def _list_config_files(paths, expand_user_dir=True):
        """
        Return list of (existing) configuration files.

        The list of configuration file is built in the following way:

        - any path pointing to an existing file is included in the result;

        - for any path ``P``, if directory ``P.d`` exists, any file
          contained in it and named ``*.conf`` is included in the
          result;

        - non-existing paths are (silently) ignored and omitted from the
          returned result.

        If keyword argument `expand_user_dir` is true (default), then
        each path is expanded with `os.path.expanduser`.
        """
        configfiles = set()
        if expand_user_dir:
            paths = [os.path.expanduser(cfg) for cfg in paths]
        for path in paths:
            if os.path.isfile(path):
                configfiles.add(path)
            path_d = path + '.d'
            if os.path.isdir(path_d):
                for entry in os.listdir(path_d):
                    if entry.endswith('.conf'):
                        cfgfile = os.path.join(path_d, entry)
                        if cfgfile not in configfiles:
                            configfiles.add(cfgfile)
        return list(configfiles)

    def read_config(self):
        """Reads the configuration properties from the ini file and links the
        section to comply with the cluster config dictionary format.

        :return: tuple of dictionaries (clusters, storage) containing
         all configuration properties from the ini file in compliance
         to the cluster config format, and global configuration options for the storage.

        :raises: :py:class:`voluptuous.MultipleInvalid` if not all sections
                 present or broken links between secitons

        """
        storage_section = self.conf.get('storage', {
            'storage_path': Configurator.default_storage_path,
            'storage_type': Configurator.default_storage_type})

        clusters = dict((key, value) for key, value in self.conf.iteritems() if
                        re.search(ConfigReader.cluster_section + "/(.*)", key)
                        and key.count("/") == 1)

        conf_values = dict()

        errors = MultipleInvalid()
        # FIXME: to be refactored:
        # we should check independently each one of the sections, and raise errors accordingly.

        for cluster in clusters:
            # Get the name of the cluster
            name = re.search(ConfigReader.cluster_section + "/(.*)",
                             cluster).groups()[0]
            if not name:
                errors.add("Invalid section name `%s`" % cluster)
                continue

            cluster_conf = self._make_cluster_conf(self.conf[cluster])

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
            except KeyError as ex:
                errors.add(
                    "cluster `%s` setup section `%s` does not exists" % (
                        cluster, setup_name))
            except MultipleInvalid as ex:
                for error in ex.errors:
                    errors.add(error)

            try:
                values['login'] = dict(self.conf[login_name])
                self.schemas['login'](values['login'])
            except KeyError as ex:
                errors.add(
                    "cluster `%s` login section `%s` does not exists" % (
                        cluster, login_name))
            except MultipleInvalid as ex:
                errors.add(Invalid("Error in login section `%s`: %s" % (
                    login_name, str.join(', ', [str(e) for e in ex.errors]))))

            try:
                values['cloud'] = dict(self.conf[cloud_name])
                self.schemas['cloud'](values['cloud'])
            except KeyError as ex:
                errors.add(
                    "cluster `%s` cloud section `%s` does not exists" % (
                        cluster, cloud_name))
            except MultipleInvalid as ex:
                for error in ex.errors:
                    errors.add(Invalid("section %s: %s" % (cloud_name, error)))

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

                if errors.errors:
                    log.error("Ignoring cluster `%s`: %s" % (
                        name, str.join(", ", [str(e) for e in errors.errors])))
                else:
                    conf_values[name] = values
            except KeyError as ex:
                errors.add("Error in section `%s`" % cluster)

        # FIXME: do we really need to raise an exception if we cannot
        # parse *part* of the configuration files? We should just
        # ignore those with errors and return both the parsed
        # configuration values _and_ a list of errors
        if errors.errors:
            raise errors
        return (conf_values, storage_section)


    def _make_cluster_conf(self, conf):
        """
        Create dictionary of cluster config keys.

        Compatibility changes, renames, deprecation warnings, etc. all
        happen here -- so that the rest of the code can always assume
        the configuration is the latest documented format.
        """
        cfg = dict(conf)

        # working on issue #279 uncovered a conflict between code and
        # docs: the documentation referred to config keys
        # `<class>_min_nodes` but the code actually looked for
        # `<class>_nodes_min`.  Keep this last version as it makes the
        # code simpler, but alert users of the change...
        for k,v in cfg.items():
            if k.endswith('_min_nodes'):
                # replace with correct key name
                new_k = k[:-len('_min_nodes')] + '_nodes_min'
                cfg[new_k] = v
                del cfg[k]
                warnings.warn(
                    "Configuration key '{0}' should be renamed to '{1}'."
                    " Support for automatic renaming will be removed"
                    " in the next major version of ElastiCluster."
                    .format(k, new_k))

        return cfg
