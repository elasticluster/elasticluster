#
# Copyright (C) 2013-2019 University of Zurich
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

from __future__ import division

# compatiblity imports
from future import standard_library
standard_library.install_aliases()

# stdlib imports
from collections import defaultdict
from datetime import datetime
import logging
import os
import platform
import tempfile
import shlex
import shutil
from subprocess import call
from warnings import warn


# 3rd party imports
from pkg_resources import resource_filename
import yaml


# Elasticluster imports
import elasticluster
from elasticluster import log
from elasticluster.exceptions import ConfigurationError, ClusterSizeError
from elasticluster.providers import AbstractSetupProvider
from elasticluster.utils import get_num_processors, parse_ip_address_and_port, temporary_dir


__author__ = ','.join([
    'Nicolas Baer <nicolas.baer@uzh.ch>',
    'Antonio Messina <antonio.s.messina@gmail.com>',
    'Riccardo Murri <riccardo.murri@gmail.com>',
])


class AnsibleSetupProvider(AbstractSetupProvider):
    """
    This implementation uses ansible to configure and manage the cluster
    setup. See https://github.com/ansible/ansible for details.

    :param dict groups: dictionary of node kinds with corresponding
                        ansible groups to install on the node kind.
                        e.g [node_kind] = ['ansible_group1', 'ansible_group2']
                        The group defined here can be references in each
                        node. Therefore groups can make it easier to
                        define multiple groups for one node.

    :param str playbook_path: path to playbook; if empty this will use
                              the shared playbook of elasticluster

    :param dict environment_vars: dictonary to define variables per node
                                  kind, e.g. [node_kind][var] = value

    :param str storage_path: path to store the inventory file. By default
                             the inventory file is saved temporarily in a
                             temporary directory and deleted when the
                             cluster in stopped.

    :param bool sudo: indication whether use sudo to gain root permission

    :param str sudo_user: user with root permission

    :param str ansible_module_dir: comma- or colon-separated
                                   path to additional ansible modules

    :param bool slow_but_safer:
      Avoid using ``eatmydata`` to speed up installation of many
      packages which comprise several smallish files.

    :param extra_conf: tbd.

    :ivar groups: node kind and ansible group mapping dictionary
    :ivar environment: additional environment variables
    """

    #: to identify this provider type in messages
    HUMAN_READABLE_NAME = 'Ansible'

    def __init__(self, groups,
                 playbook_path=None,
                 environment_vars=None,
                 storage_path=None,
                 sudo=True,
                 sudo_user='root',
                 slow_but_safer=False,
                 **extra_conf):
        self.groups = groups
        self._playbook_path = playbook_path
        self.environment = environment_vars or {}
        self.use_eatmydata = not slow_but_safer
        self._storage_path = storage_path
        self._sudo_user = sudo_user
        self._sudo = sudo

        if 'ssh_pipelining' in extra_conf:
            extra_conf['ansible_ssh_pipelining'] = extra_conf.pop('ssh_pipelining')
            warn(
                "Setup configuration option `ssh_pipelining`"
                " has been renamed to `ansible_ssh_pipelining`."
                " Please fix the configuration file(s), as support"
                " for the old spelling will be removed in a future release.",
                DeprecationWarning)
        if 'ansible_module_dir' in extra_conf:
            extra_conf['ansible_library'] = extra_conf.pop('ansible_module_dir')
            warn(
                "Setup configuration option `ansible_module_dir`"
                " has been renamed to `ansible_library`."
                " Please fix the configuration file(s), as support"
                " for the old spelling will be removed in a future release.",
                DeprecationWarning)
        self.extra_conf = extra_conf

        if not self._playbook_path:
            # according to
            # https://pythonhosted.org/setuptools/pkg_resources.html#resource-extraction
            # requesting the filename to a directory causes all the
            # contained files and directories to be extracted as well
            playbook_dir = resource_filename('elasticluster', 'share/playbooks')
            self._playbook_path = os.path.join(playbook_dir, 'main.yml')
        else:
            self._playbook_path = os.path.expanduser(self._playbook_path)
            self._playbook_path = os.path.expandvars(self._playbook_path)
        # sanity check
        if not os.path.exists(self._playbook_path):
            raise ConfigurationError(
                "playbook `{playbook_path}` could not be found"
                .format(playbook_path=self._playbook_path))
        if not os.path.isfile(self._playbook_path):
            raise ConfigurationError(
                "playbook `{playbook_path}` is not a file"
                .format(playbook_path=self._playbook_path))
        potential_resume_playbook = os.path.join(os.path.dirname(self._playbook_path),
                                                 'resume.yml')
        if os.path.exists(potential_resume_playbook):
            self._resume_playbook_path = potential_resume_playbook
        else:
            self._resume_playbook_path = None

        if self._storage_path:
            self._storage_path = os.path.expanduser(self._storage_path)
            self._storage_path = os.path.expandvars(self._storage_path)
            self._storage_path_tmp = False
            if not os.path.exists(self._storage_path):
                os.makedirs(self._storage_path)
        else:
            self._storage_path = tempfile.mkdtemp()
            self._storage_path_tmp = True

    def setup_cluster(self, cluster, extra_args=tuple()):
        """
        Configure the cluster by running an Ansible playbook.

        The ElastiCluster configuration attribute `<kind>_groups`
        determines, for each node kind, what Ansible groups nodes of
        that kind are assigned to.

        :param cluster: cluster to configure
        :type cluster: :py:class:`elasticluster.cluster.Cluster`

        :param list extra_args:
          List of additional command-line arguments
          that are appended to each invocation of the setup program.

        :return: ``True`` on success, ``False`` otherwise. Please note, if nothing
                 has to be configured, then ``True`` is returned.

        :raises: `ConfigurationError` if the playbook can not be found
                 or is corrupt.
        """
        return self._run_playbook(cluster, self._playbook_path, extra_args)

    def resume_cluster(self, cluster, extra_args=tuple()):
        """
        As `setup_cluster`, but prefers to run a resume playbook, if
        one is available.  A resume playbook is a playbook which is
        designed to restart a cluster after it has been paused, and
        can be more efficient than a setup playbook (since it can
        assume that the required software is already installed).
        If no such playbook is available, it will use the standard
        setup playbook and print a warning.

        :param cluster: cluster to configure
        :type cluster: :py:class:`elasticluster.cluster.Cluster`

        :param list extra_args:
          List of additional command-line arguments
          that are appended to each invocation of the setup program.

        :return: ``True`` on success, ``False`` otherwise. Please note, if nothing
                 has to be configured, then ``True`` is returned.

        :raises: `ConfigurationError` if the playbook can not be found
                 or is corrupt.
        """
        if self._resume_playbook_path is not None:
            return self._run_playbook(cluster, self._resume_playbook_path, extra_args)
        else:
            log.warning("No resume playbook is available - falling back to the setup "
                        "playbook, which could be slow.")
            return self.setup_cluster(cluster, extra_args)

    def _run_playbook(self, cluster, playbook, extra_args):
        run_id = (
            'elasticluster.{name}.{date}.{pid}@{host}'
            .format(
                name=cluster.name,
                date=datetime.now().isoformat(),
                pid=os.getpid(),
                host=platform.node(),
            )
        )
        inventory_path = self._build_inventory(cluster)
        if inventory_path is None:
            # no inventory file has been created: this can only happen
            # if no nodes have been started nor can be reached
            raise ClusterSizeError()
        assert os.path.exists(inventory_path), (
                "inventory file `{inventory_path}` does not exist"
                .format(inventory_path=inventory_path))

        # build list of directories to search for roles/include files
        ansible_roles_dirs = [
            # include Ansible default first ...
            '/etc/ansible/roles',
        ]
        for root_path in [
                # ... then ElastiCluster's built-in defaults
                resource_filename('elasticluster', 'share/playbooks'),
                # ... then wherever the playbook is
                os.path.dirname(playbook),
        ]:
            for path in [
                    root_path,
                    os.path.join(root_path, 'roles'),
            ]:
                if path not in ansible_roles_dirs and os.path.exists(path):
                    ansible_roles_dirs.append(path)


        # Use env vars to configure Ansible;
        # see all values in https://github.com/ansible/ansible/blob/devel/lib/ansible/constants.py
        #
        # Ansible does not merge keys in configuration files: rather
        # it uses the first configuration file found.  However,
        # environment variables can be used to selectively override
        # parts of the config; according to [1]: "they are mostly
        # considered to be a legacy system as compared to the config
        # file, but are equally valid."
        #
        # [1]: http://docs.ansible.com/ansible/intro_configuration.html#environmental-configuration
        #
        # Provide default values for important configuration variables...
        ansible_env = {
            'ANSIBLE_FORKS':             ('%d' % 4*get_num_processors()),
            'ANSIBLE_HOST_KEY_CHECKING': 'no',
            'ANSIBLE_RETRY_FILES_ENABLED': 'no',
            'ANSIBLE_ROLES_PATH':        ':'.join(reversed(ansible_roles_dirs)),
            'ANSIBLE_SSH_PIPELINING':    'yes',
            'ANSIBLE_TIMEOUT':           '120',
        }
        try:
            import ara
            ara_location = os.path.dirname(ara.__file__)
            ansible_env['ANSIBLE_CALLBACK_PLUGINS'] = (
                '{ara_location}/plugins/callbacks'
                .format(ara_location=ara_location))
            ansible_env['ANSIBLE_ACTION_PLUGINS'] = (
                '{ara_location}/plugins/actions'
                .format(ara_location=ara_location))
            ansible_env['ANSIBLE_LIBRARY'] = (
                '{ara_location}/plugins/modules'
                .format(ara_location=ara_location))
            ara_dir = os.getcwd()
            ansible_env['ARA_DIR'] = ara_dir
            ansible_env['ARA_DATABASE'] = (
                'sqlite:///{ara_dir}/{run_id}.ara.sqlite'
                .format(ara_dir=ara_dir, run_id=run_id))
            ansible_env['ARA_LOG_CONFIG'] = (
                '{run_id}.ara.yml'
                .format(ara_dir=ara_dir, run_id=run_id))
            ansible_env['ARA_LOG_FILE'] = (
                '{run_id}.ara.log'
                .format(ara_dir=ara_dir, run_id=run_id))
            ansible_env['ARA_LOG_LEVEL'] = 'DEBUG'
            ansible_env['ARA_PLAYBOOK_PER_PAGE'] = '0'
            ansible_env['ARA_RESULT_PER_PAGE'] = '0'
        except ImportError:
            elasticluster.log.info(
                "Could not import module `ara`:"
                " no detailed information about the playbook will be recorded.")
        # ...override them with key/values set in the config file(s)
        for k, v in self.extra_conf.items():
            if k.startswith('ansible_'):
                ansible_env[k.upper()] = str(v)
        # ...finally allow the environment have the final word
        ansible_env.update(os.environ)
        # however, this is needed for correct detection of success/failure...
        ansible_env['ANSIBLE_ANY_ERRORS_FATAL'] = 'yes'
        # ...and this might be needed to connect (see issue #567)
        if cluster.ssh_proxy_command:
            ansible_env['ANSIBLE_SSH_ARGS'] = (
                ansible_env.get('ANSIBLE_SSH_ARGS', '')
                + (" -o ProxyCommand='{proxy_command}'"
                   # NOTE: in contrast to `Node.connect()`, we must
                   # *not* expand %-escapes in the SSH proxy command:
                   # it will be done by the `ssh` client
                   .format(proxy_command=cluster.ssh_proxy_command)))

        # report on calling environment
        if __debug__:
            elasticluster.log.debug(
                "Calling `ansible-playbook` with the following environment:")
            for var, value in sorted(ansible_env.items()):
                # sanity check. Do not print password content....
                if "password" in var.lower() or "secret" in var.lower():
                    elasticluster.log.debug("- %s=******", var)
                else:
                    elasticluster.log.debug("- %s=%r", var, value)

        elasticluster.log.debug("Using playbook file %s.", playbook)

        # build `ansible-playbook` command-line
        cmd = shlex.split(self.extra_conf.get('ansible_command', 'ansible-playbook'))
        cmd += [
            ('--private-key=' + cluster.user_key_private),
            os.path.realpath(playbook),
            ('--inventory=' + inventory_path),
        ]

        if self._sudo:
            cmd.extend([
                # force all plays to use `sudo` (even if not marked as such)
                '--become',
                # desired sudo-to user
                ('--become-user=' + self._sudo_user),
            ])

        # determine Ansible verbosity as a function of ElastiCluster's
        # log level (we cannot read `ElastiCluster().params.verbose`
        # here, still we can access the log configuration since it's
        # global).
        verbosity = int((logging.WARNING - elasticluster.log.getEffectiveLevel()) / 10)
        if verbosity > 0:
            cmd.append('-' + ('v' * verbosity))  # e.g., `-vv`

        # append any additional arguments provided by users in config file
        ansible_extra_args = self.extra_conf.get('ansible_extra_args', None)
        if ansible_extra_args:
            cmd += shlex.split(ansible_extra_args)

        # finally, append any additional arguments provided on command-line
        for arg in extra_args:
            # XXX: since we are going to change working directory,
            # make sure that anything that looks like a path to an
            # existing file is made absolute before appending to
            # Ansible's command line.  (Yes, this is a ugly hack.)
            if os.path.exists(arg):
                arg = os.path.abspath(arg)
            cmd.append(arg)

        with temporary_dir():
            # adjust execution environment, for the part that needs a
            # the current directory path
            cmd += [
                '-e', ('@' + self._write_extra_vars(cluster))
            ]
            # run it!
            cmdline = ' '.join(cmd)
            elasticluster.log.debug(
                "Running Ansible command `%s` ...", cmdline)
            rc = call(cmd, env=ansible_env, bufsize=1, close_fds=True)
            # check outcome
            ok = False  # pessimistic default
            if rc != 0:
                elasticluster.log.error(
                    "Command `%s` failed with exit code %d.", cmdline, rc)
            else:
                # even if Ansible exited with return code 0, the
                # playbook might still have failed -- so explicitly
                # check for a "done" report showing that each node run
                # the playbook until the very last task
                cluster_hosts = set(node.name
                                    for node in cluster.get_all_nodes())
                done_hosts = set()
                for node_name in cluster_hosts:
                    try:
                        with open(node_name + '.log') as stream:
                            status = stream.read().strip()
                        if status == 'done':
                            done_hosts.add(node_name)
                    except (OSError, IOError):
                        # no status file for host, do not add it to
                        # `done_hosts`
                        pass
                if done_hosts == cluster_hosts:
                    # success!
                    ok = True
                elif len(done_hosts) == 0:
                    # total failure
                    elasticluster.log.error(
                        "No host reported successfully running the setup playbook!")
                else:
                    # partial failure
                    elasticluster.log.error(
                        "The following nodes did not report"
                        " successful termination of the setup playbook:"
                        " %s", (', '.join(cluster_hosts - done_hosts)))
        if ok:
            elasticluster.log.info("Cluster correctly configured.")
            return True
        else:
            elasticluster.log.warning(
                "The cluster has likely *not* been configured correctly."
                " You may need to re-run `elasticluster setup`.")
            return False

    def _build_inventory(self, cluster):
        """
        Builds the inventory for the given cluster and returns its path

        :param cluster: cluster to build inventory for
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        inventory_data = defaultdict(list)

        for node in cluster.get_all_nodes():
            if node.preferred_ip is None:
                log.warning(
                    "Ignoring node `{0}`: No IP address."
                    .format(node.name))
                continue
            if node.kind not in self.groups:
                # FIXME: should this raise a `ConfigurationError` instead?
                log.warning(
                    "Ignoring node `{0}`:"
                    " Node kind `{1}` not defined in cluster!"
                    .format(node.name, node.kind))
                continue

            extra_vars = ['ansible_user=%s' % node.image_user]

            ip_addr, port = parse_ip_address_and_port(node.preferred_ip)
            if port != 22:
                extra_vars.append('ansible_port=%s' % port)

            # write additional `ansible_*` variables to inventory;
            # `ansible_python_interpreter` gets special treatment
            # since we need to tell script `install-py2.sh` that
            # it should create a wrapper script for running `eatmydata python`
            extra_conf = self.extra_conf.copy()
            ansible_python_interpreter = extra_conf.pop(
                'ansible_python_interpreter', '/usr/bin/python')
            extra_vars.append('ansible_python_interpreter={python}{eatmydata}'
                              .format(
                                  python=ansible_python_interpreter,
                                  eatmydata=('+eatmydata' if self.use_eatmydata else '')))
            # abuse Python's %r fomat to provide quotes around the
            # value, and \-escape any embedded quote chars
            extra_vars.extend('%s=%r' % (k, str(v)) for k, v in
                              extra_conf.items()
                              if k.startswith('ansible_'))

            if node.kind in self.environment:
                # abuse Python's %r fomat to provide quotes around the
                # value, and \-escape any embedded quote chars
                extra_vars.extend('%s=%r' % (k, str(v)) for k, v in
                                  self.environment[node.kind].items())

            for group in self.groups[node.kind]:
                inventory_data[group].append(
                    (node.name, ip_addr, ' '.join(extra_vars)))

        if not inventory_data:
            log.info("No inventory file was created.")
            return None

        # create a temporary file to pass to ansible, since the
        # api is not stable yet...
        if self._storage_path_tmp:
            if not self._storage_path:
                self._storage_path = tempfile.mkdtemp()
            elasticluster.log.warning(
                "Writing inventory file to tmp dir `%s`", self._storage_path)

        inventory_path = os.path.join(
            self._storage_path, (cluster.name + '.inventory'))
        log.debug("Writing Ansible inventory to file `%s` ...", inventory_path)
        with open(inventory_path, 'w+') as inventory_file:
            for section, hosts in inventory_data.items():
                # Ansible throws an error "argument of type 'NoneType' is not
                # iterable" if a section is empty, so ensure we have something
                # to write in there
                if hosts:
                    inventory_file.write("\n[" + section + "]\n")
                    for host in hosts:
                        hostline = "{0} ansible_host={1} {2}\n".format(*host)
                        inventory_file.write(hostline)
        return inventory_path


    def cleanup(self, cluster):
        """Deletes the inventory file used last recently used.

        :param cluster: cluster to clear up inventory file for
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        if self._storage_path and os.path.exists(self._storage_path):
            filename = (cluster.name + '.inventory')
            inventory_path = os.path.join(self._storage_path, filename)

            if os.path.exists(inventory_path):
                try:
                    os.unlink(inventory_path)
                    if self._storage_path_tmp:
                        if len(os.listdir(self._storage_path)) == 0:
                            shutil.rmtree(self._storage_path)
                except OSError as ex:
                    log.warning(
                        "AnsibileProvider: Ignoring error while deleting "
                        "inventory file %s: %s", inventory_path, ex)


    def __setstate__(self, state):
        self.__dict__ = state
        # Compatibility fix: allow loading clusters created before
        # option `ssh_pipelining` was added.
        if 'ssh_pipelining' not in state:
            self.ssh_pipelining = True


    def _write_extra_vars(self, cluster, filename='extra_vars.yml'):
        # build dict of "extra vars"
        # XXX: we should not repeat here names of attributes that
        # should not be exported... it would be better to use a simple
        # naming convention (e.g., omit whatever starts with `_`)

        extra_vars = cluster.to_vars_dict()
        extra_vars.update(extra_vars.pop('extra', {}))
        extra_vars['cloud'] = cluster.cloud_provider.to_vars_dict()
        nodes = extra_vars.pop('nodes')
        extra_vars['nodes'] = {}
        for kind, instances in nodes.items():
            for node in instances:
                node_vars = node.to_vars_dict()
                node_vars.update(node_vars.pop('extra', {}))
                extra_vars['nodes'][node.name] = node_vars
        extra_vars['output_dir'] = os.getcwd()
        # save it to a YAML file
        log.debug("Writing extra vars %r to file %s", extra_vars, filename)
        with open(filename, 'w') as output:
            # ensure output file is not readable to other users,
            # as it may contain passwords
            os.fchmod(output.fileno(), 0o600)
            # dump variables in YAML format for Ansible to read
            yaml.dump({ 'elasticluster': extra_vars }, output)
        return filename
