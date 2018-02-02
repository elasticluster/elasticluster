#! /usr/bin/env python
#
# Copyright (C) 2013-2016, 2018 University of Zurich.
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
Turn ElastiCluster configuration into internal data structures.

Digesting configuration files into data structures ready to be processed by the
rest of ElastiCluster happens in three stages:

1. Read configuration files and create a (nested) key/value store of all the
   configuration items.

2. Arrange the configuration items into sets of properties that are needed to
   create ElastiCluster objects (clusters, cloud providers, etc.) -- the
   outcome of this phase would be a set of dictionaries that can be fed as
   `**kwargs` to class constructors.

3. Instanciate the actual working objects.
"""

from __future__ import (print_function, division, absolute_import)

# stdlib imports
from collections import defaultdict
from ConfigParser import SafeConfigParser
import os
from os.path import expanduser, expandvars
import re
import sys
from urlparse import urlparse
from warnings import warn

# 3rd-party modules
from pkg_resources import resource_filename

from schema import Schema, SchemaError, Optional, Or, Regex, Use

# ElastiCluster imports
from elasticluster import log
from elasticluster.exceptions import ConfigurationError
from elasticluster.providers.ansible_provider import AnsibleSetupProvider
from elasticluster.cluster import Cluster, NodeNamingPolicy
from elasticluster.repository import MultiDiskRepository
from elasticluster.utils import environment
from elasticluster.validate import (
    alert,
    boolean,
    executable_file,
    existing_file,
    hostname,
    nonempty_str,
    nonnegative_int,
    nova_api_version,
    positive_int,
    readable_file,
    url,
)


## defaults and built-in config

KEY_RENAMES = [
    # pylint: disable=bad-whitespace,bad-continuation

    # section   from key          to key          verbose?  supported until...
    ('cluster', 'setup_provider', 'setup',        True,     '2.0'),
    ('cloud',   'tenant_name',    'project_name', True,     '2.0'),
    # working on issue #279 uncovered a conflict between code and
    # docs: the documentation referred to config keys
    # `<class>_min_nodes` but the code actually looked for
    # `<class>_nodes_min`.  Keep this last version as it makes the
    # code simpler, but alert users of the change...
    ('cluster', re.compile(r'([0-9a-z_-]+)_min_nodes'),
                                  r'\1_nodes_min', True,    '2.0'),
    ('setup',   'ssh_pipelining', 'ansible_ssh_pipelining',
                                                   True,    '1.4'),
]


SCHEMA = {
    'cloud': {
        'provider': Or('azure', 'ec2_boto', 'google', 'openstack', 'libcloud'),
        # allow other keys w/out restrictions; each cloud provider has its own
        # set of keys, which are handled separately
        str: str,
    },
    'cluster': {
        'cloud': str,
        'setup': str,
        'login': str,
        'nodes': {
            str: {
                'flavor': nonempty_str,
                'image_id': nonempty_str,
                Optional('image_userdata', default=''): str,
                Optional('security_group', default='default'): str,  ## FIXME: alphanumeric?
                Optional('network_ids'): str,
                # these are auto-generated but already there by the time
                # validation is run
                'login': nonempty_str,
                'num': int,
                'min_num': int,
                # only on Google Cloud
                Optional("accelerator_count", default=0): nonnegative_int,
                Optional("accelerator_type"): nonempty_str,
                Optional("min_cpu_platform"): nonempty_str,
                # allow other keys w/out restrictions
                Optional(str): str,
            },
        },
        Optional("ssh_probe_timeout", default=5): positive_int,
        Optional("ssh_proxy_command", default=''): str,
        Optional("start_timeout", default=600): positive_int,
        # only on Google Cloud
        Optional("accelerator_count", default=0): nonnegative_int,
        Optional("accelerator_type"): nonempty_str,
        Optional("allow_project_ssh_keys", default=True): boolean,
        Optional("min_cpu_platform"): nonempty_str,
        # allow other keys w/out restrictions
        Optional(str): str,
    },
    'login': {
        'image_user': nonempty_str,
        Optional('image_sudo', default=True): boolean,
        Optional('image_user_sudo', default="root"): nonempty_str,
        Optional('image_userdata', default=''): str,
        'user_key_name': str,  # FIXME: are there restrictions? (e.g., alphanumeric)
        'user_key_private': readable_file,
        'user_key_public': readable_file,
    },
    'setup': {
        Optional('provider', default='ansible'): str,
        Optional("playbook_path",
                 default=os.path.join(
                     resource_filename('elasticluster', 'share/playbooks'),
                     'site.yml')): readable_file,
        Optional("ansible_command"): executable_file,
        Optional("ansible_extra_args"): str,
        #Optional("ansible_ssh_pipelining"): boolean,
        # allow other keys w/out restrictions
        str: str,
    },
    'storage': {
        Optional('storage_path', default=os.path.expanduser("~/.elasticluster/storage")): str,
        Optional('storage_type'): ['yaml', 'json', 'pickle'],
    },
}


CLOUD_PROVIDER_SCHEMAS = {
    'azure': {
        "provider": 'azure',
        Optional("subscription_id", default=os.getenv('AZURE_SUBSCRIPTION_ID', '')): nonempty_str,
        Optional("tenant_id", default=os.getenv('AZURE_TENANT_ID', '')): nonempty_str,
        Optional("client_id", default=os.getenv('AZURE_CLIENT_ID', '')): nonempty_str,
        Optional("secret", default=os.getenv('AZURE_CLIENT_SECRET', '')): nonempty_str,
        Optional("location", default="westus"): nonempty_str,
        Optional("certificate"): alert(
            "The `certificate` setting is no longer valid"
            " in the Azure configuration."
            " Please remove it from your configuration file."),
        Optional("wait_timeout"): alert(
            "The `wait_timeout` setting is no longer valid"
            " in the Azure configuration."
            " Please remove it from your configuration file."),
    },

    'ec2_boto': {
        "provider": 'ec2_boto',
        "ec2_url": url,
        Optional("ec2_access_key", default=os.getenv('EC2_ACCESS_KEY', '')): nonempty_str,
        Optional("ec2_secret_key", default=os.getenv('EC2_SECRET_KEY', '')): nonempty_str,
        "ec2_region": nonempty_str,
        Optional("request_floating_ip", default=False): boolean,
        Optional("vpc"): nonempty_str,
        Optional("price", default=0): int,
        Optional("timeout", default=0): int,
        Optional("instance_profile"): nonempty_str,
    },

    'google': {
        "provider": 'google',
        "gce_client_id": nonempty_str,
        "gce_client_secret": nonempty_str,
        "gce_project_id": nonempty_str,
        Optional("network", default="default"): nonempty_str,
        Optional("noauth_local_webserver"): boolean,
        Optional("zone", default="us-central1-a"): nonempty_str,
    },

    'openstack': {
        "provider": 'openstack',
        Optional("auth_url"): url,
        Optional("cacert"): existing_file,
        Optional("username"): nonempty_str,
        Optional("password"): nonempty_str,
        Optional("user_domain_name"): nonempty_str,
        Optional("project_domain_name"): nonempty_str,
        Optional("project_name"): nonempty_str,
        Optional("request_floating_ip"): boolean,
        Optional("region_name"): nonempty_str,
        Optional("compute_api_version"): Or('1.1', '2'),
        Optional("image_api_version"): Or('1', '2'),
        Optional("network_api_version"): Or('2.0'),
        Optional("volume_api_version"): Or('1', '2', '3'),
        Optional("identity_api_version"): Or('3', '2'),  # no default, can auto-detect
        ## DEPRECATED, use `compute_api_version` instead
        Optional("nova_api_version"): nova_api_version,
    },

    'libcloud': {
        "provider": 'libcloud',
        'driver_name': nonempty_str,
        Optional(str): str,
    }
}


CLOUD_PROVIDERS = {
    # pylint: disable=bad-whitespace
    'ec2_boto':  ('elasticluster.providers.ec2_boto',       'BotoCloudProvider'),
    'openstack': ('elasticluster.providers.openstack',      'OpenStackCloudProvider'),
    'google':    ('elasticluster.providers.gce',            'GoogleCloudProvider'),
    'azure':     ('elasticluster.providers.azure_provider', 'AzureCloudProvider'),
    'libcloud': ('elasticluster.providers.libcloud_provider', 'LibCloudProvider'),
}


SETUP_PROVIDERS = {
    # pylint: disable=bad-whitespace
    "ansible": ('elasticluster.providers.ansible_provider', 'AnsibleSetupProvider'),
}



def _get_provider(name, provider_map):
    """
    Return the constructor for provider `name` in mapping `provider_map`.

    Second argument `provider_map` is a Python mapping that translates a
    provider kind name (e.g., ``ec2``) into a pair *(module, class)*;
    `_get_provider` will attempt to import the named module (using Python's
    standard import mechanisms) and return the `class` attribute from that
    module.

    :raise KeyError: If the given `name` is not a valid key in `provider_map`
    :raise ImportError: If the module corresponding to `name`
      in `provider_map` cannot be loaded.
    :raise AttributeError: If the class name corresponding to `name`
      in `provider_map` does not exist in the module.
    """
    modname, clsname = provider_map[name]
    mod = __import__(modname, globals(), locals(), [clsname], -1)
    cls = getattr(mod, clsname)
    log.debug("Using class %r from module %r to instanciate provider '%s'",
              cls, mod, name)
    return cls


def _make_defaults_dict():
    """
    Return mapping from names to be used in `%()s` expansion.
    """
    env = {}
    # default location of Ansible playbooks; make it also available as
    # `%(elasticluster_playbooks)` so one can write `%(elasticluster_playbooks)s/site.yml`
    env['ansible_pb_dir'] = env['elasticluster_playbooks'] \
                             = resource_filename('elasticluster', 'share/playbooks')
    return env


## public API entry point

def make_creator(configfiles, storage_path=None):
    """
    Return a `Creator` instance initialized from given configuration files.

    :param list configfiles: list of paths to the INI-style file(s).
        For each path ``P`` in `configfiles`, if a directory named ``P.d``
        exists, also reads all the `*.conf` files in that directory.

    :param str storage_path:
        path to the storage directory. If defined, a
        :py:class:`repository.DiskRepository` class will be instantiated.

    :return: :py:class:`Creator`
    """
    try:
        # only strings have the `.swapcase()` method; lists and tuples don't
        configfiles.swapcase  # pylint: disable=pointless-statement
        configfiles = [configfiles]
    except AttributeError:
        # `configfiles` is list or tuple
        pass

    # also look for ``path.d/*.conf`` files
    configfiles = _expand_config_file_list(configfiles)
    if not configfiles:
        raise ValueError('Empty list of config files')

    config = load_config_files(configfiles)

    return Creator(config, storage_path=storage_path)


def _expand_config_file_list(paths, ignore_nonexistent=True,
                             expand_user_dir=True, expand_env_vars=False):
    """
    Return list of (existing) configuration files.

    The list of configuration file is built in the following way:

    - any path pointing to an existing file is included in the result;

    - for any path ``P``, if directory ``P.d`` exists, any file
      contained in it and named ``*.conf`` is included in the
      result;

    - if argument `ignore_nonexistent` is ``True`` (default), then non-existing
      paths are silently ignored and omitted from the returned result. Else, if
      `ignore_nonexistent` is ``False``, a `ValueError` exception is raised.

    If keyword arguments `expand_user_dir` and `expand_env_vars` are ``True``
    (default), then each path is expanded with `os.path.expanduser` (resp.
    `os.path.expandvars`).
    """
    configfiles = set()
    for path in paths:
        if expand_user_dir:
            path = os.path.expanduser(path)
        if expand_env_vars:
            path = os.path.expandvars(path)
        if os.path.isfile(path):
            configfiles.add(path)
        elif not ignore_nonexistent:
            raise ValueError(
                "Configuration file `{0}` does not exist"
                .format(path))
        path_d = path + '.d'
        if os.path.isdir(path_d):
            for entry in os.listdir(path_d):
                if entry.endswith('.conf'):
                    cfgfile = os.path.join(path_d, entry)
                    if cfgfile not in configfiles:
                        configfiles.add(cfgfile)
    return list(configfiles)


## loading and parsing

# validation regexps
_CLUSTER_NAME_RE = re.compile('^[a-z0-9+_-]+$', re.I)


def load_config_files(paths):
    """
    Read configuration file(s) and return corresponding data structure.

    :param paths: list of file names to load.
    """
    # I wish there were a "pipelinine" operator in Python, so I could rewrite
    # this as `paths *into* raw_config *into* _arrange_config_tree ...`
    raw_config = _read_config_files(paths)
    tree_config1 = _arrange_config_tree(raw_config)
    tree_config2 = _perform_key_renames(tree_config1)
    complete_config = _build_node_section(tree_config2)
    object_tree = _validate_and_convert(complete_config)
    deref_config = _dereference_config_tree(object_tree)
    final_config = _cross_validate_final_config(deref_config)

    return final_config


def _read_config_files(paths):
    """
    Read configuration data from INI-style file(s).

    Data loaded from the given files is aggregated into a nested 2-level Python
    mapping, where 1st-level keys are config section names (as read from the
    files), and corresponding items are again key/value mappings (configuration
    item name and value).

    :param paths: list of filesystem paths of files to read
    """
    # read given config files
    configparser = SafeConfigParser()
    configparser.read(paths)

    # temporarily modify environment to allow both `${...}` and `%(...)s`
    # variable substitution in config values
    defaults = _make_defaults_dict()
    config = {}
    with environment(**defaults):
        for section in configparser.sections():
            config[section] = {}
            for key in configparser.options(section):
                # `configparser.get()` performs the `%(...)s` substitutions
                value = configparser.get(section, key, vars=defaults)
                # `expandvars()` performs the `${...}` substitutions
                config[section][key] = expandvars(value)

    return config


def _arrange_config_tree(raw_config):
    """
    Group configuration data by section type.

    Given the 'raw configuration data' (as returned by
    `_read_config_files`:func:), create and return a nested mapping:

    * 1st-level keys are strings naming section types (i.e., ``'cluster'``,
      ``'cloud'``, ``'login'``, ``'setup'``);

    * 2nd-level keys are then the names given to such sections. For example,
      the contents of section ``[login/ubuntu]`` would be accessible from the
      return value ``C`` as ``C['login']['ubuntu']``.

    As an exception, subsections of a named cluster (e.g.,
    ``[cluster/gridengine/qmaster]``) will be inserted as items in the
    ``'nodes'`` key of the named cluster. For example, key/value pairs read
    from section ``[cluster/gridengine/qmaster]`` will be accessible as
    ``C['cluster']['gridengine']['nodes']['qmaster']``.
    """
    tree = {}
    for sect_name, sect_items in raw_config.iteritems():
        # skip empty sections
        if not sect_items:
            continue
        path = sect_name.split('/')
        # translate `cluster/foo/bar` -> `cluster/foo/__nodes__/bar`
        if path[0] == 'cluster' and len(path) > 2:
            path.insert(2, 'nodes')
        _update_nested_item(tree, path, sect_items)
    return tree


def _update_nested_item(D, path, items):
    """
    Walk nested mapping `D` and update the last key in `path`.
    For example::

      >>> D = {'b': {'a': {}}}
      >>> updated = _update_nested_item(D, ['b', 'a'], {'x':1, 'y':2})
      >>> D['b']['a'] == {'x':1, 'y':2}
      True

    The 'update' operation leaves key/value pairs which are not in `items`
    unchanged::

      >>> D = {'b': {'a': {'z': 3}}}
      >>> updated = _update_nested_item(D, ['b', 'a'], {'x':1, 'y':2})
      >>> D['b']['a'] == {'x':1, 'y':2, 'z':3}
      True

    In fact, `_update_nested_item` can also be used in the 'degenerate' cases
    where `path` is 1 or 0 elements long, in which case it becomes essentially
    a more verbose syntax for `dict.update`::

      >>> D = {'a': {}}
      >>> updated = _update_nested_item(D, ['a'], {'x':1, 'y':2})
      >>> D['a'] == {'x':1, 'y':2}
      True

      >>> D = {'z': 3}
      >>> updated = _update_nested_item(D, [], {'x':1, 'y':2})
      >>> D == {'x':1, 'y':2, 'z':3}
      True

    Note that the nested dictionaries corresponding to the specified `path`
    will be created if they do not already exist::

      >>> D = {}
      >>> updated = _update_nested_item(D, ['b', 'a'], {'x':1, 'y':2})
      >>> D == {'b': {'a': {'x':1, 'y':2}}}
      True
    """
    target = D
    while path:
        key = path.pop(0)
        if key not in target:
            target[key] = {}
        target = target[key]
    target.update(items)
    return target


# pylint: disable=dangerous-default-value
def _perform_key_renames(tree, changes=KEY_RENAMES):
    """
    Change a configuration "tree" in-place, renaming legacy keys to new names.

    This function chiefly supports two distinct uses:

    - allow old/legacy option names configuration files, but still warn users
      of the new/updated name;
    - allow alternate options names to be used in the configuration file but
      normalize them to a "canonical" spelling before the code sees them.

    Second argument `changes` is a list of items. Each item is a tuple
    describing a single key rename:

    - 1st field names the section type (e.g., ``cluster``) where the key
      renames are going to happen;
    - 2nd field is the old/legacy key name (can be a regular expression);
    - 3rd field is the new/updated key name (or the substitution pattern
      if 2nd field is a regexp);
    - 4th field is a boolean flag: if ``True``, a warning will be emitted
      telling users that the configuration option has been renamed; make this
      ``False`` to just allow option key synonyms;
    - 5th field is the ElastiCluster release until which the automatic rename
      will be supported (only relevant if 4th field "verbose" is ``True``).
    """
    for section, from_key, to_key, verbose, supported in changes:
        if section not in tree:
            # XXX: should this be a configuration error instead?
            log.warning(
                "No section `%s` found in configuration!"
                " This will almost certainly end up causing an error later on.",
                section)
            continue
        for stanza, pairs in tree[section].iteritems():
            # ensure we work on a copy of the keys collection,
            # so we can mutate the tree down below
            for key in list(pairs.keys()):
                substitute = False
                try:
                    # try regexp match
                    match = from_key.match(key)
                    if match:
                        to_key = from_key.sub(key, to_key)
                        substitute = True
                except AttributeError:
                    # plain old string match
                    substitute = (key == from_key)
                if substitute:
                    tree[section][stanza][to_key] = tree[section][stanza][from_key]
                    del tree[section][stanza][from_key]
                    if verbose:
                        warn("Configuration key `{from_key}`"
                             " in section `{section}/{stanza}`"
                             " should be renamed to `{to_key}`"
                             " -- please update configuration file(s)."
                             " Support for automatic renaming will be"
                             " removed in {version} of ElastiCluster."
                             .format(
                                 from_key=from_key,
                                 to_key=to_key,
                                 section=section,
                                 stanza=stanza,
                                 version=(("release {0}".format(supported))
                                          if supported
                                          else "a future release")))
    return tree


def _dereference_config_tree(tree, evict_on_error=True):
    # FIXME: Should allow *three* distinct behaviors on error?
    # - "evict on error": remove the offending section and continue
    # - "raise exception": raise a ConfigurationError at the first error
    # - "just report": log errors but try to return all that makes sense
    """
    Modify `tree` in-place replacing cross-references by section name with the
    actual section content.

    For example, if a cluster section lists a key/value pair
    ``'login': 'ubuntu'``, this will be replaced with ``'login': { ... }``.
    """
    to_evict = []
    for cluster_name, cluster_conf in tree['cluster'].iteritems():
        for key in ['cloud', 'login', 'setup']:
            try:
                refname = cluster_conf[key]
            except KeyError:
                log.error(
                    "Configuration section `cluster/%s`"
                    " is missing a `%s=` section reference."
                    " %s",
                    cluster_name, key,
                    ("Dropping cluster definition." if evict_on_error else ""))
                if evict_on_error:
                    to_evict.append(cluster_name)
                    break
                else:
                    # cannot continue
                    raise ConfigurationError(
                        "Invalid cluster definition `cluster/{0}:"
                        " missing `{1}=` configuration key"
                        .format(cluster_name, key))
            try:
                # dereference
                cluster_conf[key] = tree[key][refname]
            except KeyError:
                log.error(
                    "Configuration section `cluster/%s`"
                    " references non-existing %s section `%s`."
                    " %s",
                    cluster_name, key, refname,
                    ("Dropping cluster definition." if evict_on_error else ""))
                if evict_on_error:
                    to_evict.append(cluster_name)
                    break
    for cluster_name in to_evict:
        del tree['cluster'][cluster_name]
    return tree


def _build_node_section(tree):
    """
    Create or update nested mapping `nodes` into each cluster config.

    Keys in the `nodes` mapping are node kind names (i.e., the first segment of
    `*_nodes` configuration options), and corresponding values are
    configuration key/value pairs that apply to nodes of that kind.

    See also function `_gather_node_kind_info`:func: for more details on how
    the kind-level configuration is built.
    """
    for cluster_name, cluster_conf in tree['cluster'].iteritems():
        node_kind_config = dict((key, value)
                                for key, value in cluster_conf.iteritems()
                                if key.endswith('_nodes'))
        if 'nodes' not in cluster_conf:
            cluster_conf['nodes'] = {}
        for key in node_kind_config.iterkeys():
            kind_name = key[:-len('_nodes')]
            # nodes can inherit the properties of cluster or overwrite them
            kind_values = _gather_node_kind_info(kind_name, cluster_name, cluster_conf)
            cluster_conf['nodes'][kind_name] = kind_values
    return tree


def _gather_node_kind_info(kind_name, cluster_name, cluster_conf):
    """
    Collect key/value configuration for nodes of a given kind.

    Return a mapping of key/value configuration options; the mapping is
    constructed by layering key/value pairs from two sources:

    1. Cluster-level options;
    2. Kind-specific attributes, as set in the ``[cluster/name/kind]`` sections.

    Options from the latter override options set in the former.
    """
    # copy cluster-level config
    kind_values = {}
    for attr in (
            'flavor',
            'image_id',
            #'image_user',       ## from `login/*`
            'image_userdata',
            'login',
            'network_ids',
            'security_group',
            'node_name',
            'ssh_proxy_command',
            # Google Cloud only
            'accelerator_count',
            'accelerator_type',
            'allow_project_ssh_keys',
            'boot_disk_size',
            'boot_disk_type',
            'min_cpu_platform',
            'scheduling',
            'tags'
            #'user_key_name',    ## from `login/*`
            #'user_key_private', ## from `login/*`
            #'user_key_public',  ## from `login/*`
    ):
        if attr in cluster_conf:
            kind_values[attr] = cluster_conf[attr]

    # override with node-specific attrs (if given)
    if kind_name in cluster_conf['nodes']:
        for key, value in cluster_conf['nodes'][kind_name].iteritems():
            kind_values[key] = value

    kind_values['num'], kind_values['min_num'] = \
        _compute_desired_and_minimum_number_of_nodes(kind_name, cluster_name, cluster_conf)

    return kind_values


# pylint: disable=invalid-name
def _compute_desired_and_minimum_number_of_nodes(kind_name, cluster_name, cluster_conf):
    """
    Compute desired and minimum number of nodes of the given kind.
    """
    num = int(cluster_conf[kind_name + '_nodes'])
    if (kind_name + '_nodes_min') not in cluster_conf:
        min_num = num
    else:
        min_num = int(cluster_conf[kind_name + '_nodes_min'])
        if min_num > num:
            raise ValueError(
                " In cluster `{cluster_name}`:"
                " Minimum number of '{kind}' nodes ({min_num})"
                " is larger then the number"
                " of '{kind}' nodes to start ({num})"
                .format(
                    cluster_name=cluster_name,
                    kind=kind_name,
                    min_num=min_num,
                    num=num
                ))
    return num, min_num


## validation and conversion

def _validate_and_convert(cfgtree, evict_on_error=True):
    objtree = {}
    for section, model in SCHEMA.iteritems():
        if section not in cfgtree:
            continue
        stanzas = cfgtree[section]
        objtree[section] = {}
        for name, properties in stanzas.iteritems():
            log.debug("Checking section `%s/%s` ...", section, name)
            try:
                objtree[section][name] = Schema(model).validate(properties)
                # further checks for cloud providers
                if section == 'cloud':
                    objtree[section][name] = _validate_cloud_section(objtree[section][name])
                # check node name pattern in clusters conforms to RFC952
                if section == 'cluster':
                    _validate_node_group_names(objtree[section][name])
            except (SchemaError, ValueError) as err:
                log.error("In section `%s/%s`: %s", section, name, err)
                if evict_on_error:
                    log.error(
                        "Dropping configuration section `%s/%s`"
                        " because of the above errors", section, name)
                    # `objtree[section][name]` exists if the except was raised
                    # by the second validation (line 650)
                    if name in objtree[section]:
                        del objtree[section][name]
    return objtree

def _validate_cloud_section(cloud_section):
    """
    Run provider-specific schema validation.
    """
    provider = cloud_section['provider']
    return Schema(
        CLOUD_PROVIDER_SCHEMAS[provider]).validate(cloud_section)

def _validate_node_group_names(cluster_section):
    """
    Check that node group names conform to RFC 952.
    """
    for nodename in cluster_section['nodes']:
        hostname(nodename)  ## raises ValueError if not conformant
    return cluster_section


def _cross_validate_final_config(objtree, evict_on_error=True):
    """
    Run validation checks that require correlating values from different sections.
    """
    # take a copy of cluster config as we might be modifying it
    for name, cluster in list(objtree['cluster'].items()):
        valid = True
        # ensure all cluster node kinds are defined in the `setup/*` section
        setup_sect = cluster['setup']
        for groupname, properties in cluster['nodes'].items():
            if (groupname + '_groups') not in setup_sect:
                log.error("Cluster `%s` requires nodes of kind `%s`,"
                          " but no such group is defined"
                          " in the referenced setup section.",
                          name, groupname)
                valid = False
                break

        # ensure `ssh_to` has a valid value
        if 'ssh_to' in cluster:
            ssh_to = cluster['ssh_to']
            try:
                # extract node kind if this is a node name (e.g., `master001` => `master`)
                parts = NodeNamingPolicy.parse(ssh_to)
                ssh_to = parts['kind']
            except ValueError:
                pass
            if ssh_to not in cluster['nodes']:
                log.error("Cluster `%s` is configured to SSH into nodes of kind `%s`,"
                          " but no such kind is defined.", name, ssh_to)
                valid = False

        # EC2-specific checks
        if cluster['cloud']['provider'] == 'ec2_boto':
            cluster_uses_vpc = ('vpc' in cluster['cloud'])
            for groupname, properties in cluster['nodes'].items():
                if cluster_uses_vpc and 'network_ids' not in properties:
                    log.error(
                        "Node group `%s/%s` is being used in a VPC,"
                        " so it must specify ``network_ids``.",
                        cluster, groupname)
                    if evict_on_error:
                        valid = False
                        break
                if not cluster_uses_vpc and 'network_ids' in properties:
                    log.error(
                        "Cluster `%s` must specify a VPC"
                        " to place `%s` instances in network `%s`",
                        cluster, groupname, properties['network_ids'])
                    if evict_on_error:
                        valid = False
                        break
        if not valid:
            log.error("Dropping cluster `%s` because of the above errors", name)
            del objtree['cluster'][name]
    return objtree


## general factory

class Creator(object):
    """
    The `Creator` class is responsible for:

    1. keeping track of the configuration, and
    2. offering factory methods to create all kind of objects
       that need information from the configuration, and
    3. loading a cluster from a valid `repository.AbstractClusterRepository`.

    First argument cluster configuration is a nested Python mapping structured
    in the following way::

      'cluster': {  ## this must be literally `cluster`
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
      }

    The actual "property" parameters follow the names and types described in the
    `Configuration` section of the manual. This is indeed nothing more than a
    dereferenced un-dump of the configuration file; use
    `load_config_files`:func: to load a set of configuration files into a data
    structure like the above.

    :param dict cluster_conf: see description above
    :param str storage_path: path to store data

    :raises MultipleInvalid: configuration validation
    """

    DEFAULT_STORAGE_PATH = os.path.expanduser("~/.elasticluster/storage")
    DEFAULT_STORAGE_TYPE = 'yaml'

    def __init__(self, conf, storage_path=None, storage_type=None):
        self.cluster_conf = conf['cluster']

        self.storage_path = (
            os.path.expandvars(os.path.expanduser(storage_path)) if storage_path
            else self.DEFAULT_STORAGE_PATH)

        self.storage_type = storage_type or self.DEFAULT_STORAGE_TYPE


    def load_cluster(self, cluster_name):
        """
        Load a cluster from the configured repository.

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
            self.cluster_conf[cluster.template],
            self.cluster_conf[cluster.template]['login']
        )
        return cluster


    def create_cloud_provider(self, cluster_template):
        """
        Return cloud provider instance for the given cluster template.

        :param str cluster_template: name of cluster template to use
        :return: cloud provider instance that fulfills the contract of
                 :py:class:`elasticluster.providers.AbstractCloudProvider`
        """
        cloud_conf = self.cluster_conf[cluster_template]['cloud']
        provider = cloud_conf['provider']

        try:
            ctor = _get_provider(provider, CLOUD_PROVIDERS)
        except KeyError:
            # this should have been caught during config validation!
            raise ConfigurationError(
                "Unknown cloud provider `{0}` for cluster `{1}`"
                .format(provider, cluster_template))
        except (ImportError, AttributeError) as err:
            raise RuntimeError(
                "Unable to load cloud provider `{0}`: {1}: {2}"
                .format(provider, err.__class__.__name__, err))

        provider_conf = cloud_conf.copy()
        provider_conf.pop('provider')

        # use a single keyword args dictionary for instanciating
        # provider, so we can detect missing arguments in case of error
        provider_conf['storage_path'] = self.storage_path
        try:
            return ctor(**provider_conf)
        except TypeError:
            # check that required parameters are given, and try to
            # give a sensible error message if not; if we do not
            # do this, users only see a message like this::
            #
            #   ERROR Error: __init__() takes at least 5 arguments (4 given)
            #
            # which gives no clue about what to correct!
            import inspect
            args, varargs, keywords, defaults = inspect.getargspec(ctor.__init__)
            if defaults is not None:
                # `defaults` is a list of default values for the last N args
                defaulted = dict((argname, value)
                                 for argname, value in zip(reversed(args),
                                                           reversed(defaults)))
            else:
                # no default values at all
                defaulted = {}
            for argname in args[1:]:  # skip `self`
                if argname not in provider_conf and argname not in defaulted:
                    raise ConfigurationError(
                        "Missing required configuration parameter `{0}`"
                        " in cloud section for cluster `{1}`"
                        .format(argname, cluster_template))



    def create_cluster(self, template, name=None, cloud=None, setup=None):
        """
        Creates a ``Cluster``:class: instance by inspecting the configuration
        properties of the given cluster template.

        :param str template: name of the cluster template
        :param str name: name of the cluster. If not defined, the cluster
                         will be named after the template.
        :param cloud: A `CloudProvider`:py:class: instance to use
                      instead of the configured one. If ``None`` (default)
                      then the configured cloud provider will be used.
        :param setup: A `SetupProvider`:py:class: instance to use
                      instead of the configured one. If ``None`` (default)
                      then the configured setup provider will be used.

        :return: :py:class:`elasticluster.cluster.Cluster` instance:

        :raises ConfigurationError: cluster template not found in config
        """
        if template not in self.cluster_conf:
            raise ConfigurationError(
                "No cluster template configuration by the name `{template}`"
                .format(template=template))

        conf = self.cluster_conf[template]

        extra = conf.copy()
        extra.pop('cloud')
        extra.pop('nodes')
        extra.pop('setup')
        extra['template'] = template

        if cloud is None:
            cloud = self.create_cloud_provider(template)
        if name is None:
            name = template
        if setup is None:
            setup = self.create_setup_provider(template, name=name)

        cluster = Cluster(
            name=(name or template),
            cloud_provider=cloud,
            setup_provider=setup,
            user_key_name=conf['login']['user_key_name'],
            user_key_public=conf['login']['user_key_public'],
            user_key_private=conf['login']["user_key_private"],
            repository=self.create_repository(),
            **extra)

        nodes = conf['nodes']
        for group_name in nodes:
            group_conf = nodes[group_name]
            for varname in ['image_user', 'image_userdata']:
                group_conf.setdefault(varname, conf['login'][varname])
            cluster.add_nodes(group_name, **group_conf)
        return cluster


    def create_setup_provider(self, cluster_template, name=None):
        """Creates the setup provider for the given cluster template.

        :param str cluster_template: template of the cluster
        :param str name: name of the cluster to read configuration properties
        """
        conf = self.cluster_conf[cluster_template]['setup']
        if name:
            conf['cluster_name'] = name
        conf_login = self.cluster_conf[cluster_template]['login']

        provider_name = conf.get('provider', 'ansible')
        if provider_name not in SETUP_PROVIDERS:
            raise ConfigurationError(
                "Invalid value `%s` for `setup_provider` in configuration "
                "file." % provider_name)
        provider = _get_provider(provider_name, SETUP_PROVIDERS)

        storage_path = self.storage_path
        playbook_path = conf.pop('playbook_path', None)

        groups = self._read_node_groups(conf)
        environment_vars = {}
        for node_kind, grps in groups.iteritems():
            if not isinstance(grps, list):
                groups[node_kind] = [grps]

            # Environment variables parsing
            environment_vars[node_kind] = {}
            for key, value in (list(conf.items())
                               + list(self.cluster_conf[cluster_template].items())):
                # Set both group and global variables
                for prefix in [(node_kind + '_var_'), "global_var_"]:
                    if key.startswith(prefix):
                        var = key.replace(prefix, '')
                        environment_vars[node_kind][var] = value
                        log.debug("setting variable %s=%s for node kind %s",
                                  var, value, node_kind)

        return provider(groups, playbook_path=playbook_path,
                        environment_vars=environment_vars,
                        storage_path=storage_path,
                        sudo=conf_login['image_sudo'],
                        sudo_user=conf_login['image_user_sudo'],
                        **conf)

    def _read_node_groups(self, conf):
        """
        Return mapping from node kind names to list of Ansible host group names.
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
                if group_name in self._RENAMED_NODE_GROUPS:
                    old_group_name = group_name
                    group_name, remove_at = self._RENAMED_NODE_GROUPS[group_name]
                    warn(
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

    _RENAMED_NODE_GROUPS = {
        # old name     ->  (new name             will be removed in...
        'condor_workers':  ('condor_worker',     '1.4'),
        'gluster_client':  ('glusterfs_client',  '1.4'),
        'gluster_data' :   ('glusterfs_server',  '1.4'),
        'gridengine_clients': ('gridengine_worker', '2.0'),
        'slurm_clients':   ('slurm_worker',      '2.0'),
        'slurm_workers':   ('slurm_worker',      '1.4'),
    }


    def create_repository(self):
        return MultiDiskRepository(self.storage_path,
                                   self.storage_type)
