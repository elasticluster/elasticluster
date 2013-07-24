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

# system imports
import logging
import os
import tempfile

# external imports
import ansible.callbacks
from ansible.callbacks import call_callback_module
import ansible.constants as ansible_constants
from ansible.errors import AnsibleError
from ansible.playbook import PlayBook
import ansible.utils

# Elasticluster imports
import elasticluster
from elasticluster import log
from elasticluster.providers import AbstractSetupProvider


class ElasticlusterPbCallbacks(ansible.callbacks.PlaybookCallbacks):
    def on_no_hosts_matched(self):
        call_callback_module('playbook_on_no_hosts_matched')

    def on_no_hosts_remaining(self):
        call_callback_module('playbook_on_no_hosts_remaining')

    def on_task_start(self, name, is_conditional):
        if hasattr(self, 'step') and self.step:
            resp = raw_input('Perform task: %s (y/n/c): ' % name)
            if resp.lower() in ['y', 'yes']:
                self.skip_task = False
            elif resp.lower() in ['c', 'continue']:
                self.skip_task = False
                self.step = False
            else:
                self.skip_task = True

        call_callback_module('playbook_on_task_start', name, is_conditional)

    def on_setup(self):
        call_callback_module('playbook_on_setup')

    def on_import_for_host(self, host, imported_file):
        call_callback_module('playbook_on_import_for_host',
                             host, imported_file)

    def on_not_import_for_host(self, host, missing_file):
        call_callback_module('playbook_on_not_import_for_host',
                             host, missing_file)

    def on_play_start(self, pattern):
        call_callback_module('playbook_on_play_start', pattern)

    def on_stats(self, stats):
        call_callback_module('playbook_on_stats', stats)


class AnsibleSetupProvider(AbstractSetupProvider):
    """
    """

    def __init__(self, private_key_file, remote_user,
                 sudo_user, sudo, playbook_path, **extra_conf):
        self._private_key_file = os.path.expanduser(
            os.path.expandvars(private_key_file))
        self._remote_user = remote_user
        self._sudo_user = sudo_user
        self._sudo = sudo
        self._playbook_path = playbook_path
        self.extra_conf = extra_conf
        self.groups = dict((k[:-7], v) for k, v in extra_conf.items() if k.endswith('_groups'))
        self.environment = dict()
        for nodetype, grps in self.groups.iteritems():
            if not isinstance(grps, list):
                self.groups[nodetype] = [grps]

            # Environment variables parsing
            self.environment[nodetype] = dict()
            for key, value in extra_conf.iteritems():
                prefix = "%s_var_" % nodetype
                if key.startswith(prefix):
                    var = key.replace(prefix,'')
                    self.environment[nodetype][var] = value

        self.inventory_path = None
        if ('general_conf' not in extra_conf
            or 'storage' not in extra_conf['general_conf']
            or 'cluster_name' not in extra_conf):
            log.error("Unable to store inventory file in elasticluster storage directory")
        else:
            self.inventory_path = os.path.join(
                extra_conf['general_conf']['storage'],
                "%s.ansible-inventory" % extra_conf['cluster_name'])

        module_dir = extra_conf.get('ansible_module_dir', None)
        if module_dir:
            for mdir in module_dir.split(','):
                ansible.utils.module_finder.add_directory(mdir.strip())

        ansible_constants.DEFAULT_PRIVATE_KEY_FILE = self._private_key_file
        ansible_constants.DEFAULT_REMOTE_USER = self._remote_user
        ansible_constants.DEFAULT_SUDO_USER = self._sudo_user
        ansible_constants.HOST_KEY_CHECKING=False

    def setup_cluster(self, cluster):
        self.inventory_path = self._build_inventory(cluster)

        # check paths
        if not self.inventory_path:
            # No inventory file has been created, maybe an
            # invalid calss has been specified in config file? Or none?
            # assume it is fine.
            elasticluster.log.info("No setup required for this cluster.")
            return True
        if not os.path.exists(self.inventory_path):
            raise AnsibleError(
                "inventory file `%s` could not be found" % self.inventory_path)
        # ANTONIO: These should probably be configuration error
        # instead, and should probably checked inside __init__().
        if not os.path.exists(self._playbook_path):
            raise AnsibleError(
                "playbook `%s` could not be found" % self._playbook_path)
        if not os.path.isfile(self._playbook_path):
            raise AnsibleError(
                "the playbook `%s` is not a file" % self._playbook_path)

        elasticluster.log.debug("Using playbook file %s.", self._playbook_path)

        stats = ansible.callbacks.AggregateStats()
        playbook_cb = ElasticlusterPbCallbacks(verbose=0)
        runner_cb = ansible.callbacks.DefaultRunnerCallbacks()

        if elasticluster.log.level <= logging.INFO:
            playbook_cb = ansible.callbacks.PlaybookCallbacks()
            runner_cb = ansible.callbacks.PlaybookRunnerCallbacks(stats)

        pb = PlayBook(
            playbook=self._playbook_path,
            host_list=self.inventory_path,
            remote_user=self._remote_user,
            callbacks=playbook_cb,
            runner_callbacks=runner_cb,
            forks=10,
            stats=stats,
            sudo=self._sudo,
            sudo_user=self._sudo_user,
            private_key_file=self._private_key_file,
        )

        try:
            status = pb.run()
        except AnsibleError as e:
            elasticluster.log.error(
                "could not execute ansible playbooks. message=`%s`", str(e))
            return False


        # Check ansible status.
        cluster_failures = False
        for host, hoststatus in status.items():
            if hoststatus['unreachable']:
                elasticluster.log.error(
                    "Host `%s` is unreachable, "
                    "please re-run elasticluster setup", host)
                cluster_failures = True
            if hoststatus['failures']:
                elasticluster.log.error(
                    "Host `%s` had %d failures: please re-run elasticluster "
                    "setup or check the Ansible playbook `%s`" % (
                        host, hoststatus['failures'], self._playbook_path))
                cluster_failures = True

        if not cluster_failures:
            elasticluster.log.info("Cluster correctly configured.")
            # ANTONIO: TODO: We should return an object to identify if
            # the cluster was correctly configured, if we had
            # temporary errors or permanent errors.
            return True
        return False

    def _build_inventory(self, cluster):
        """
        Builds the inventory for the given cluster and returns its path
        """
        inventory = dict()
        for node in cluster.get_all_nodes():
            if node.type in self.groups:
                extra_vars = ''
                if node.type in self.environment:
                    extra_vars = ['%s=%s' % (k, v) for k, v in \
                                      self.environment[node.type].items()]
                    extra_vars = str.join(' ', extra_vars)
                for group in self.groups[node.type]:
                    if group not in inventory:
                        inventory[group] = []
                    inventory[group].append((node.name, node.ip_public, extra_vars))

        if inventory:
            # create a temporary file to pass to ansible, since the
            # api is not stable yet...
            fname = self.inventory_path
            if not self.inventory_path:
                (fd, fname) = tempfile.mkstemp()
                fd = os.fdopen(fd, 'w+')
                elasticluster.log.warning(
                    "Not using default storage directory for the inventory file.")
                elasticluster.log.warning(
                    "Writing invenetory file to `%s`", fname)
            else:
                fd = open(self.inventory_path, 'w+')
            for section, hosts in inventory.items():
                fd.write("\n["+section+"]\n")
                if hosts:
                    for host in hosts:
                        hostline = "%s ansible_ssh_host=%s %s\n" \
                            % host
                        fd.write(hostline)

            fd.close()

            return self.inventory_path
        else:
            elasticluster.log.info("No inventory file was created.")
            return None

    def cleanup(self):
        """
        Delete inventory file.
        """
        if self.inventory_path:
            if os.path.exists(self.inventory_path):
                try:
                    os.unlink(self.inventory_path)
                except OSError, ex:
                    log.warning(
                        "AnsibileProvider: Ignoring error while deleting "
                        "inventory file %s: %s", self.inventory_path, ex)
