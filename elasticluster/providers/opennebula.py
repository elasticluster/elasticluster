#! /usr/bin/env python
#
#   Copyright (C) 2019 ETH Zurich
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Cloud provider for OpenNebula.

See:
- https://opennebula.org/pyone-python-bindings-for-open-nebula/
- https://archives.opennebula.org/documentation:rel4.4:api
"""

# stdlib imports
import os
import re
from tempfile import NamedTemporaryFile
import threading

import pyone

from elasticluster.providers import AbstractCloudProvider
from elasticluster import log
from elasticluster.exceptions import ConfigurationError, InstanceError, KeypairError, UnsupportedError
from elasticluster.utils import setitem_nested


# file metadata, etc.
__author__ = ', '.join([
    'Riccardo Murri <riccardo.murri@gmail.com>'
])


# code
class OpenNebulaCloudProvider(AbstractCloudProvider):
    """
    Manage VMs on an OpenNebula cloud.

    :param str endpoint:
        Endpoint for communicating with the OpenNebula XML-RPC server.
        Must start with ``http://`` or ``https://``.

    :param str username:
    :param str password:
       Authentication information.  If omitted, try to read it from
       the file specified by the environment variable ``ONE_AUTH``,
       or OpenNebula's default ``~/.one/one_auth``.
    """

    _api_lock = threading.Lock()

    # for state values, see: http://docs.opennebula.org/5.6/operation/references/vm_states.html#list-of-states
    VM_STATES = {
        'INIT': 0,
        'PENDING': 1,
        'HOLD': 2,
        'ACTIVE': 3,
        'STOPPED': 4,
        'SUSPENDED': 5,
        'DONE': 6,
        # 7 is unused
        'POWEROFF': 8,
        'UNDEPLOYED': 9,
        'CLONING': 10,
        'CLONING_FAILURE': 11,
    }

    LCM_STATES = {
        'LCM_INIT': 0,  # Internal initialization state, not visible for the end users
        'PROLOG': 1,    # The system is transferring the VM files (disk images and the recovery file) to the host in which the virtual machine will be running.
        'BOOT': 2,      # OpenNebula is waiting for the hypervisor to create the VM
        'RUNNING': 3,   # The VM is running (note that this stage includes the internal virtualized machine booting and shutting down phases). In this state, the virtualization driver will periodically monitor it
        'MIGRATE': 4,   # The VM is migrating from one host to another. This is a hot migration
        'SAVE_STOP': 5, # The system is saving the VM files after a stop operation
        'SAVE_SUSPEND': 6,      # The system is saving the VM files after a suspend operation
        'SAVE_MIGRATE': 7,      # The system is saving the VM files for a cold migration
        'PROLOG_MIGRATE': 8,    # File transfers during a cold migration
        'PROLOG_RESUME': 9,     # File transfers after a resume action (from stopped)
        'EPILOG_STOP': 10,      # File transfers from the Host to the system datastore
        'EPILOG': 11,   # The system cleans up the Host used to virtualize the VM, and additionally disk images to be saved are copied back to their datastores
        'SHUTDOWN': 12, # OpenNebula has sent the VM the shutdown ACPI signal, and is waiting for it to complete the shutdown process. If after a timeout period the VM does not disappear, OpenNebula will assume that the guest OS ignored the ACPI signal and the VM state will be changed to running, instead of done
        'CLEANUP_RESUBMIT': 15, # Cleanup after a delete-recreate action
        'UNKNOWN': 16,  # The VM couldn't be monitored, it is in an unknown state
        'HOTPLUG': 17,  # A disk attach/detach operation is in progress
        'SHUTDOWN_POWEROFF': 18,        # OpenNebula has sent the VM the shutdown ACPI signal, and is waiting for it to complete the shutdown process. If after a timeout period the VM does not disappear, OpenNebula will assume that the guest OS ignored the ACPI signal and the VM state will be changed to running, instead of poweroff
        'BOOT_UNKNOWN': 19,     # OpenNebula is waiting for the hypervisor to create the VM (from UNKNOWN)
        'BOOT_POWEROFF': 20,    # OpenNebula is waiting for the hypervisor to create the VM (from POWEROFF)
        'BOOT_SUSPENDED': 21,   # OpenNebula is waiting for the hypervisor to create the VM (from SUSPENDED)
        'BOOT_STOPPED': 22,     # OpenNebula is waiting for the hypervisor to create the VM (from STOPPED)
        'CLEANUP_DELETE': 23,   # Cleanup after a delete action
        'HOTPLUG_SNAPSHOT': 24, # A system snapshot action is in progress
        'HOTPLUG_NIC': 25,      # A NIC attach/detach operation is in progress
        'HOTPLUG_SAVEAS': 26,   # A disk-saveas operation is in progress
        'HOTPLUG_SAVEAS_POWEROFF': 27,  # A disk-saveas operation (from POWEROFF) is in progress
        'HOTPLUG_SAVEAS_SUSPENDED': 28, # A disk-saveas operation (from SUSPENDED) is in progress
        'SHUTDOWN_UNDEPLOY': 29,        # OpenNebula has sent the VM the shutdown ACPI signal, and is waiting for it to complete the shutdown process. If after a timeout period the VM does not disappear, OpenNebula will assume that the guest OS ignored the ACPI signal and the VM state will be changed to running, instead of undeployed
        'EPILOG_UNDEPLOY': 30,  # The system cleans up the Host used to virtualize the VM, and VM files are transfered to the system datastore
        'PROLOG_UNDEPLOY': 31,  # File transfers after a resume action (from undeployed)
        'BOOT_UNDEPLOY': 32,    # OpenNebula is waiting for the hypervisor to create the VM (from UNDEPLOY)
        'HOTPLUG_PROLOG_POWEROFF': 33,  # File transfers for a disk attach from poweroff
        'HOTPLUG_EPILOG_POWEROFF': 34,  # File transfers for a disk detach from poweroff
        'BOOT_MIGRATE': 35,     # OpenNebula is waiting for the hypervisor to create the VM (from a cold migration)
        'BOOT_FAILURE': 36,     # Failure during a BOOT
        'BOOT_MIGRATE_FAILURE': 37,     # Failure during a BOOT_MIGRATE
        'PROLOG_MIGRATE_FAILURE': 38,   # Failure during a PROLOG_MIGRATE
        'PROLOG_FAILURE': 39,   # Failure during a PROLOG
        'EPILOG_FAILURE': 40,   # Failure during an EPILOG
        'EPILOG_STOP_FAILURE': 41,      # Failure during an EPILOG_STOP
        'EPILOG_UNDEPLOY_FAILURE': 42,  # Failure during an EPILOG_UNDEPLOY
        'PROLOG_MIGRATE_POWEROFF': 43,  # File transfers during a cold migration (from POWEROFF)
        'PROLOG_MIGRATE_POWEROFF_FAILURE': 44,  # Failure during a PROLOG_MIGRATE_POWEROFF
        'PROLOG_MIGRATE_SUSPEND': 45,   # File transfers during a cold migration (from SUSPEND)
        'PROLOG_MIGRATE_SUSPEND_FAILURE': 46,   # Failure during a PROLOG_MIGRATE_SUSPEND
        'BOOT_UNDEPLOY_FAILURE': 47,    # Failure during a BOOT_UNDEPLOY
        'BOOT_STOPPED_FAILURE': 48,     # Failure during a BOOT_STOPPED
        'PROLOG_RESUME_FAILURE': 49,    # Failure during a PROLOG_RESUME
        'PROLOG_UNDEPLOY_FAILURE': 50,  # Failure during a PROLOG_UNDEPLOY
        'DISK_SNAPSHOT_POWEROFF': 51,   # A disk-snapshot-create action (from POWEROFF) is in progress
        'DISK_SNAPSHOT_REVERT_POWEROFF': 52,    # A disk-snapshot-revert action (from POWEROFF) is in progress
        'DISK_SNAPSHOT_DELETE_POWEROFF': 53,    # A disk-snapshot-delete action (from POWEROFF) is in progress
        'DISK_SNAPSHOT_SUSPENDED': 54,  # A disk-snapshot-create action (from SUSPENDED) is in progress
        'DISK_SNAPSHOT_REVERT_SUSPENDED': 55,   # A disk-snapshot-revert action (from SUSPENDED) is in progress
        'DISK_SNAPSHOT_DELETE_SUSPENDED': 56,   # A disk-snapshot-delete action (from SUSPENDED) is in progress
        'DISK_SNAPSHOT': 57,    # A disk-snapshot-create action (from RUNNING) is in progress
        'DISK_SNAPSHOT_DELETE': 59,     # A disk-snapshot-delete action (from RUNNING) is in progress
        'PROLOG_MIGRATE_UNKNOWN': 60,   # File transfers during a cold migration (from UNKNOWN)
        'PROLOG_MIGRATE_UNKNOWN_FAILURE': 61,   # Failure during a PROLOG_MIGRATE_UNKNOWN
    }

    def __init__(self, endpoint, username, password, storage_path=None):
        self._endpoint = endpoint
        if username:
            self._username = username
            self._password = password
        else:
            self._username, self._password = self._read_one_auth()
        self._server = None
        self.storage_path = storage_path

    @staticmethod
    def _read_one_auth():
        """
        Read username and password from the ONE auth file,
        or raise `ConfigurationError` if it cannot be found.
        """
        one_auth_file = os.environ.get(
            'ONE_AUTH', os.path.expanduser('~/.one/one_auth'))
        try:
            with open(one_auth_file) as one_auth:
                auth = one_auth.read().strip()
                username, password = auth.split(':')
            return username, password
        except IOError:
            raise ConfigurationError(
                "Cannot read ONE auth file `{0}`."
                .format(one_auth_file))
        except ValueError:
            raise ConfigurationError(
                "Cannot parse contents of file `{0}` as username:password pair."
                .format(one_auth_file))

    def to_vars_dict(self):
        """
        Return local state which is relevant for the cluster setup process.
        """
        log.warn(
            "ElastiCluster's OpenNebula backend is unable"
            " to export cloud connection information to the setup process."
            " Cloud access (e.g., auto-mounting of storage)"
            " will not be available from within the cluster.")
        return {}

    @property
    def server(self):
        if self._server is None:
            self._server = pyone.OneServer(
                self._endpoint, ':'.join([self._username, self._password]))
        return self._server

    def start_instance(self, key_name, public_key_path, private_key_path,
                       security_group, flavor, image_id, image_userdata,
                       cluster_name, username=None, node_name=None, **options):

        template_id, attributes = self._parse_flavor(flavor)

        if node_name:
            # this only sets the VM name for display purposes
            attributes['NAME'] = node_name

        # boot disk
        attributes.setdefault('OS', {})
        boot = attributes['OS']
        boot.setdefault('BOOT', '') # FIXME: should this be 'disk0'?

        attributes.setdefault('DISK', {})
        disk0 = attributes['DISK']
        try:
            # `image_id` is numeric
            image_id = int(image_id)
            disk0['IMAGE_ID'] = image_id
        except (TypeError, ValueError):
            # `image_id` is the disk image name
            if '/' in image_id:
                img_username, img_id = image_id.split('/')
            else:
                img_username = self._username
                img_id = image_id
            disk0['IMAGE'] = img_id
            disk0['IMAGE_UNAME'] = img_username

        # not attempting to merge flavor attributes into the `NIC`
        # part: network configuration should be part of either the ONE
        # template, or the ElastiCluster configuration
        nics = attributes['NIC'] = []
        network_ids = [
            netid.strip()
            for netid in options.pop('network_ids', '').split(',')
            if netid.strip() != ''
        ]
        if network_ids:
            for netid in network_ids:
                try:
                    # numeric ID?
                    netid = int(netid)
                    nics.append({
                        'NETWORK_ID': netid
                    })
                except (TypeError, ValueError):
                    if '/' in netid:
                        net_username, net_id = netid.split('/')
                    else:
                        net_username = self._username
                        net_id = netid
                    nics.append({
                        'NETWORK': net_id,
                        'NETWORK_UNAME': net_username,
                    })
                if security_group and security_group != 'default':
                    nics[-1]['SECURITY_GROUP'] = security_group

        attributes.setdefault('CONTEXT', {})
        context = attributes['CONTEXT']
        # this is needed to enable networking; having the `NIC`
        # lines in template seems not to be enough in ONE 5.6.1
        context['NETWORK'] = 'YES'
        if node_name:
            context['SET_HOSTNAME'] = node_name
        if username:
            context['USERNAME'] = username
        if public_key_path:
            with open(public_key_path) as pubkey:
                context['SSH_PUBLIC_KEY'] = pubkey.read()
        if image_userdata:
            # FIXME: should be base64-encoded and use `START_SCRIPT_BASE64`
            context['START_SCRIPT'] = image_userdata

        # create VM
        with self._api_lock:
            try:
                if template_id is not None:
                    vm_id = self.server.template.instantiate(
                        template_id, (node_name or ''), False,
                        self._make_template_str(attributes))
                else:
                    vm_id = self.server.vm.allocate(
                        self._make_template_str(attributes), False)
                return { 'instance_id': vm_id }
            except pyone.OneException as err:
                raise InstanceError(
                    "Error creating node `{0}`: {1}"
                    .format(node_name, err))

    @staticmethod
    def _make_template_str(template):
        """
        Convert an attribute dictionary into a ``KEY=value`` ONE template string.
        """
        # check that mandatory parameters are given
        #assert 'CPU' in template
        #assert 'MEMORY' in template
        assert 'OS' in template
        #assert 'ARCH' in template['OS']
        assert 'BOOT' in template['OS']
        assert 'DISK' in template
        assert ('IMAGE' in template['DISK'] or 'IMAGE_ID' in template['DISK'])
        assert 'SIZE' in template['DISK']
        assert 'NIC' in template
        assert len(template['NIC']) > 0
        assert ('NETWORK' in template['NIC'][0] or 'NETWORK_ID' in template['NIC'][0])

        parts = []
        for key, value in template.items():
            if key in ['NIC']:
                # by construction, these items are lists
                for item in template[key]:
                    parts.append(
                        '{KEY}=[ {values} ]'
                        .format(
                            KEY=key.upper(),
                            # recurse into dictionary-valued item
                            values=',\n'.join(
                                '{K}="{v}"'
                                .format(K=k.upper(), v=v)
                                for k,v in item.items())))
            elif isinstance(value, dict):
                parts.append(
                    '{KEY}=[ {values} ]'
                    .format(
                        KEY=key.upper(),
                        # recurse into dictionary-valued item
                        values=',\n'.join(
                            '{K}="{v}"'
                            .format(K=k.upper(), v=v)
                            for k,v in value.items())))
            else:
                parts.append(
                    '{KEY}="{value}"'
                    .format(KEY=key.upper(), value=value))

        return '\n'.join(parts)

    def get_ips(self, vm_id):
        vm = self._get_vm(vm_id)
        if not vm:
            return []
        return [vm.TEMPLATE['NIC']['IP']]

    def _get_vm(self, vm_id):
        for vm in self._list_vms():
            if vm.ID == vm_id:
                return vm
        else:
            log.debug("No VM with ID %s found.", vm_id)
            return None

    def _list_vms(self):
        with self._api_lock:
            vmpool = self.server.vmpool.info(
                -1,  # Connected user's and his group's resources
                -1,  # Range start ID
                -1,  # Range end ID
                -1   # Any VM state, except DONE
            )
        return vmpool.VM

    def is_instance_running(self, vm_id):
        vm = self._get_vm(vm_id)
        if vm is None:
            return False
        return (vm.STATE == self.VM_STATES['ACTIVE']
                and vm.LCM_STATE == self.LCM_STATES['RUNNING'])

    def _parse_flavor(self, flavor):
        """
        Parse a flavor string into OpenNebula's `CPU=...` and `MEMORY=...` values.
        """
        template_id = None
        attributes = {}
        parts = re.split(' *[,+\n] *', flavor, re.MULTILINE)
        for part in parts:
            if ':' not in part:
                if template_id is None:
                    template_id = self._parse_template(part)
                else:
                    raise ConfigurationError(
                        "Template ID or name given twice in flavor spec `{0}`"
                        .format(flavor))
            else:
                key, value = part.split(':')
                key = key.upper()
                if key == 'TEMPLATE':
                    if template_id is None:
                        template_id = self._parse_template(part)
                    else:
                        raise ConfigurationError(
                            "Template ID or name given twice in flavor spec `{0}`"
                            .format(flavor))
                else:
                    keys = key.split('.')
                    setitem_nested(attributes, keys, value)

        # one of the two should have been filled by now
        assert template_id or attributes

        return template_id, attributes

    def _parse_template(self, spec):
        """
        Return ONE template ID associated with `spec`.

        Argument `spec` can be an integer, which is interpreted as a
        template ID and returned unchanged, or an arbitrary string,
        which is looked up as a template name in the configured ONE
        server.
        """
        try:
            # allow e.g. `flavor = 20` to just select the
            # template with ID 20
            return int(spec)
        except (TypeError, ValueError):
            # else interpret value as a template name
            return self._find_template_by_name(spec)

    def _find_template_by_name(self, name):
        """
        Return ID of template whose name is exactly *name*.
        """
        with self._api_lock:
            templates = self.server.templatepool.info(
                -1, # Connected user's and his group's resources
                -1, # range start, use -1 for "no restriction"
                -1, # range end, use -1 for "no restriction"
            )
            # FIXME: I'm unsure whether accessing attributes of
            # `template` can trigger a transparent XML-RPC call... for
            # safety, run this loop while holding the API lock.
            for template in templates.VMTEMPLATE:
                if template.NAME == name:
                    return template.ID
        raise ConfigurationError(
            "No VM template found by the name `{0}`"
            .format(name))

    def stop_instance(self, node):
        """
        Destroy a VM.

        :param Node node: A `Node`:class: instance
        """
        vm = self._get_vm(node.instance_id)
        if not vm:
            return
        log.debug("Stopping VM `%s` (ID: %s) ...", vm.NAME, vm.ID)
        with self._api_lock:
            self.server.vm.action('terminate', vm.ID)
        log.debug("Stopped VM `%s` (ID: %s).", vm.NAME, vm.ID)

    def resume_instance(self, instance_state):
        raise NotImplementedError("This provider does not (yet) support pause / resume logic.")

    def pause_instance(self, instance_id):
        raise NotImplementedError("This provider does not (yet) support pause / resume logic.")
