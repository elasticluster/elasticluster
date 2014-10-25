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

# system imports
import logging
import os
import tempfile
import shutil
import sys

# external imports

# ansible.utils needs to be imported *before* ansible.callbacks!
import ansible.utils
import ansible.callbacks as anscb
import ansible.constants as ansible_constants
from ansible.errors import AnsibleError
from ansible.playbook import PlayBook

# Elasticluster imports
import elasticluster
from elasticluster import log
from elasticluster.providers import AbstractSetupProvider


class ElasticlusterPbCallbacks(anscb.PlaybookCallbacks):
    def on_no_hosts_matched(self):
        anscb.call_callback_module('playbook_on_no_hosts_matched')

    def on_no_hosts_remaining(self):
        anscb.call_callback_module('playbook_on_no_hosts_remaining')

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

        anscb.call_callback_module('playbook_on_task_start', name, is_conditional)

    def on_setup(self):
        anscb.call_callback_module('playbook_on_setup')

    def on_import_for_host(self, host, imported_file):
        anscb.call_callback_module('playbook_on_import_for_host',
                             host, imported_file)

    def on_not_import_for_host(self, host, missing_file):
        anscb.call_callback_module('playbook_on_not_import_for_host',
                             host, missing_file)

    def on_play_start(self, pattern):
        anscb.call_callback_module('playbook_on_play_start', pattern)

    def on_stats(self, stats):
        anscb.call_callback_module('playbook_on_stats', stats)


class AnsibleSetupProvider(AbstractSetupProvider):
    """This implementation uses ansible to configure and manage the cluster
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

    :param str ansible_module_dir: path to addition ansible modules
    :param extra_conf: tbd.

    :ivar groups: node kind and ansible group mapping dictionary
    :ivar environment: additional environment variables
    """
    inventory_file_ending = 'ansible-inventory'

    def __init__(self, groups, playbook_path=None, environment_vars=dict(),
                 storage_path=None, sudo=True, sudo_user='root',
                 ansible_module_dir=None, ssh_pipelining=True, **extra_conf):
        self.groups = groups
        self._playbook_path = playbook_path
        self.environment = environment_vars
        self._storage_path = storage_path
        self._sudo_user = sudo_user
        self._sudo = sudo
        self.ssh_pipelining = ssh_pipelining
        self.extra_conf = extra_conf

        if not self._playbook_path:
            self._playbook_path = os.path.join(sys.prefix,
                                               'share/elasticluster/providers/ansible-playbooks', 'site.yml')
        else:
            self._playbook_path = os.path.expanduser(self._playbook_path)
            self._playbook_path = os.path.expandvars(self._playbook_path)

        if self._storage_path:
            self._storage_path = os.path.expanduser(self._storage_path)
            self._storage_path = os.path.expandvars(self._storage_path)
            self._storage_path_tmp = False
            if not os.path.exists(self._storage_path):
                os.makedirs(self._storage_path)

        else:
            self._storage_path = tempfile.mkdtemp()
            self._storage_path_tmp = True

        if ansible_module_dir:
            for mdir in ansible_module_dir.split(','):
                ansible.utils.module_finder.add_directory(mdir.strip())

    def setup_cluster(self, cluster):
        """Configures the cluster according to the node_kind to ansible
        group matching. This method is idempotent and therefore can be
        called multiple times without corrupting the cluster configuration.

        :param cluster: cluster to configure
        :type cluster: :py:class:`elasticluster.cluster.Cluster`

        :return: True on success, False otherwise. Please note, if nothing
                 has to be configures True is returned

        :raises: `AnsibleError` if the playbook can not be found or playbook
                 is corrupt
        """
        inventory_path = self._build_inventory(cluster)
        private_key_file = cluster.user_key_private

        # update ansible constants
        ansible_constants.HOST_KEY_CHECKING = False
        ansible_constants.DEFAULT_PRIVATE_KEY_FILE = private_key_file
        ansible_constants.DEFAULT_SUDO_USER = self._sudo_user
        ansible_constants.ANSIBLE_SSH_PIPELINING = self.ssh_pipelining

        # check paths
        if not inventory_path:
            # No inventory file has been created, maybe an
            # invalid calss has been specified in config file? Or none?
            # assume it is fine.
            elasticluster.log.info("No setup required for this cluster.")
            return True
        if not os.path.exists(inventory_path):
            raise AnsibleError(
                "inventory file `%s` could not be found" % inventory_path)
        # ANTONIO: These should probably be configuration error
        # instead, and should probably checked inside __init__().
        if not os.path.exists(self._playbook_path):
            raise AnsibleError(
                "playbook `%s` could not be found" % self._playbook_path)
        if not os.path.isfile(self._playbook_path):
            raise AnsibleError(
                "the playbook `%s` is not a file" % self._playbook_path)

        elasticluster.log.debug("Using playbook file %s.", self._playbook_path)

        stats = anscb.AggregateStats()
        playbook_cb = ElasticlusterPbCallbacks(verbose=0)
        runner_cb = anscb.DefaultRunnerCallbacks()

        if elasticluster.log.level <= logging.INFO:
            playbook_cb = anscb.PlaybookCallbacks()
            runner_cb = anscb.PlaybookRunnerCallbacks(stats)

        pb = PlayBook(
            playbook=self._playbook_path,
            host_list=inventory_path,
            callbacks=playbook_cb,
            runner_callbacks=runner_cb,
            forks=10,
            stats=stats,
            sudo=self._sudo,
            sudo_user=self._sudo_user,
            private_key_file=private_key_file,
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
        """Builds the inventory for the given cluster and returns its path

        :param cluster: cluster to build inventory for
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        inventory = dict()
        for node in cluster.get_all_nodes():
            if node.kind in self.groups:
                extra_vars = ['ansible_ssh_user=%s' % node.image_user]
                if node.kind in self.environment:
                    extra_vars.extend('%s=%s' % (k, v) for k, v in
                                      self.environment[node.kind].items())
                for group in self.groups[node.kind]:
                    if group not in inventory:
                        inventory[group] = []
                    public_ip = node.preferred_ip
                    inventory[group].append(
                        (node.name, public_ip, str.join(' ', extra_vars)))

        if inventory:
            # create a temporary file to pass to ansible, since the
            # api is not stable yet...
            if self._storage_path_tmp:
                if not self._storage_path:
                    self._storage_path = tempfile.mkdtemp()
                elasticluster.log.warning("Writing inventory file to tmp dir "
                                          "`%s`", self._storage_path)
            fname = '%s.%s' % (AnsibleSetupProvider.inventory_file_ending,
                               cluster.name)
            inventory_path = os.path.join(self._storage_path, fname)

            inventory_fd = open(inventory_path, 'w+')
            for section, hosts in inventory.items():
                inventory_fd.write("\n[" + section + "]\n")
                if hosts:
                    for host in hosts:
                        hostline = "%s ansible_ssh_host=%s %s\n" \
                                   % host
                        inventory_fd.write(hostline)

            inventory_fd.close()

            return inventory_path
        else:
            elasticluster.log.info("No inventory file was created.")
            return None

    def cleanup(self, cluster):
        """Deletes the inventory file used last recently used.

        :param cluster: cluster to clear up inventory file for
        :type cluster: :py:class:`elasticluster.cluster.Cluster`
        """
        if self._storage_path and os.path.exists(self._storage_path):
            fname = '%s.%s' % (AnsibleSetupProvider.inventory_file_ending,
                               cluster.name)
            inventory_path = os.path.join(self._storage_path, fname)

            if os.path.exists(inventory_path):
                try:
                    os.unlink(inventory_path)
                    if self._storage_path_tmp:
                        if len(os.listdir(self._storage_path)) == 0:
                            shutil.rmtree(self._storage_path)
                except OSError, ex:
                    log.warning(
                        "AnsibileProvider: Ignoring error while deleting "
                        "inventory file %s: %s", inventory_path, ex)

    def __setstate__(self, state):
        self.__dict__ = state
        # Compatibility fix: allow loading clusters created before
        # option `ssh_pipelining` was added.
        if 'ssh_pipelining' not in state:
            self.ssh_pipelining = True
