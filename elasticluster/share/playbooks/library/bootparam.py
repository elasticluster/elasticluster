#!/usr/bin/env python
# -*- coding: utf-8 -*-#
#
# Copyright (C) 2017, 2018 Riccardo Murri <riccardo.murri@gmail.com>
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

## ansible metadata and docs
#

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: bootparam
short_description: |
  Alter parameters passed by the boot loader to the Linux kernel
description: |
  Edit Linux boot loader configuration file: add, set, or remove a
  named Linux boot parameter.

  Tries to auto-detect the installed bootloader and its configuration
  file, but you can explicitly specify both using the I(path) and
  I(bootloader) options.

  Note: Any modification will take effect on the Linux kernel at the
  next reboot!
author: Riccardo Murri <riccardo.murri@gmail.com>
options:
  name:
    description: |
      Boot parameter to add, replace, or remove.
    required: true
  value:
    description: |
      Value to give to the named boot parameter.
      Ignored if C(state=absent).
    required: false
  state:
    description: |
      If C(present): add the named boot parameter or set its value.
      If C(absent): remove the named boot parameter from the kernel command line.
    required: false
    default: "present"
    choices:
      - absent
      - present
  edit_only:
    type: boolean
    description: |
      Only edit the configuration file:
      do *not* run commands to install the modified configuration
      into the bootloader.
  path:
    description: |
      Boot loader configuration file to edit.
      If this is specified, argument I(bootloader) should be as well,
      to ensure that the file is edited using the correct syntax.
    required: false
    default: Try a list of well-known bootloader config files.
  bootloader:
    description: |
      Boot loader program that reads the file at I(path).
      This determines the syntax to use.

      Currently-supported values are:

      - C(grub2): GRUB 2 and GRUB-EFI
      - C(grub1): GRUB 1.x / legacy and PV-GRUB

      *Note:* This is ignored unless I(path) is also given.
    required: false
    default: Depends on ``path``.
  backup:
    type: boolean
    description: |
      Create a backup file including the timestamp information
      so you can get the original file back.
"""

EXAMPLES = """
- name: Ensure `swapaccounting=1` is passed to the Linux kernel
  bootloader:
    name: swapaccounting
    value: 1
    state: present

- name: Same as above, but edit file `/grub/grub.conf` using GRUB1 syntax
  bootloader:
    name: swapaccounting
    value: 1
    state: present
    path: /grub/grub.conf
    bootloader: grub1

- name: Ensure no `crashkernel=` setting is on the kernel command line
  bootloader:
    name: crashkernel
    state: absent
"""

RETURN = """
- path:
    type: str
    description: |
      Path to the actual configuration file that was targeted for editing.
      If the I(path) option was passed, this return field holds its value.

- bootloader:
    type: str
    description: |
      Same as the I(bootloader) option.  If that option was passed,
      this return field holds its value.

- edited:
    type: bool
    description: |
      True if the file at I(path) was actually changed.

- installed:
    type: bool
    description: |
      True if the bootloader will use the changed configuration
      at next reboot.

- backup:
    type: str
    description: |
      If a backup of the original configuration file was taken,
      the backup file name will be stored here.
"""


## stdlib imports
#

from abc import ABCMeta, abstractmethod
from collections import OrderedDict
import os
from os.path import basename, dirname
import re
from tempfile import NamedTemporaryFile


## helper functions
#

def _parse_linux_cmdline(cmdline):
    """
    Parse a Linux boot parameter line into key/value pairs.
    """
    result = OrderedDict()
    for kv in cmdline.strip().split():
        if '=' in kv:
            # limit max split to only 1, to correctly handle cases like
            # `root=UUID=c9d37675-ef02-42f0-8900-a72ec2cd0f56`
            k, v = kv.split('=', 1)
            result[k] = v

        else:
            # represent "boolean" flags like `ro` as a key with value `None`
            result[kv] = None
    return result


def _assemble_linux_cmdline(kv):
    """
    Given a dictionary, assemble a Linux boot command line.
    """
    # try to be compatible with Py2.4
    parts = []
    for k, v in kv.items():
        if v is None:
            parts.append(str(k))
        else:
            parts.append('%s=%s' % (k, v))
    return ' '.join(parts)


def _edit_linux_cmdline(cmdline, state, name, value=None):
    """
    Return a new Linux command line, with parameter `name` added,
    replaced, or removed.
    """
    kv = _parse_linux_cmdline(cmdline)
    if state == 'absent':
        try:
            del kv[name]
        except KeyError:
            pass
    elif state == 'present':
        kv[name] = value
    return _assemble_linux_cmdline(kv)


## bootloader handlers
#

class Bootloader(object):
    """
    Interface that concrete bootloader handlers must conform to.
    """

    __metaclass__ = ABCMeta

    __slots__ = ['module']

    def __init__(self, module):
        # reference Ansible module for e.g. `run_command`
        self.module = module

    @abstractmethod
    def edit(self, config, state, name, value=None):
        """
        Change all occurrences of `name` in a kernel boot line in the
        given `config` text.
        """
        raise NotImplementedError()

    def install(self, path):
        """
        Ensure that changes applied to :file:``path`` will be used next
        time the system boots up.

        Return a dictionary that will be merged to the module global
        JSON result.

        By default, this method does nothing.  It *should* likely be
        overridden in most derived classes.
        """
        return {}


class Grub1(Bootloader):
    """
    Handle editing GRUB 1.x ``menu.lst``:file:
    """

    __slots__ = []

    _GRUB_KERNEL_BOOT_ENTRY = re.compile(r'^ \s* kernel \s+ \S+ \s+', re.X|re.M)

    def edit(self, config, state, name, value=None):
        """
        Change all occurrences of `name` in a kernel boot line in the
        given `config` text.
        """
        config = str(config)  # make a copy so we can alter it
        matches = list(self._GRUB_KERNEL_BOOT_ENTRY.finditer(config))
        # process matches in reverse order, so replacing one match
        # does not alter the start/end positions of other matches
        for match in reversed(matches):
            start = match.end()
            # Linux command line extends up to the newline
            if config[start] == '\n':
                cmdline = ''
            else:
                end = config.find('\n', start)
                cmdline = config[start:end]
            new_cmdline = _assemble_linux_cmdline(cmdline, state, name, value)
            config = config[:start] + new_cmdline + config[end:]
        return config


class Grub2(Bootloader):
    """
    Handle editing and committing the GRUB2 / (U)EFI-GRUB bootloader config.
    """

    __slots__ = []

    _GRUB_CMDLINE_VAR = 'GRUB_CMDLINE_LINUX_DEFAULT='
    "Name of env var to change in :file:``/etc/default/grub``"

    def edit(self, config, state, name, value=None):
        """
        Change all occurrences of `name` in a kernel boot line in the
        given `config` text.

        It is expected that `config` is the contents of a file following
        the syntax of ``/etc/default/grub``:file:.

        .. warning::

          This module only does a very crude textual search and replace:
          it is assumed that input lines in have the form ``KEY="value"``
          (quote characters can be double ``"`` or single ``'``), and that
          the ``value`` string spans a single line and contains all
          relevant kernel boot parameters.

          However, the GRUB docs state that :file:``/etc/default/grub``
          "is sourced by a shell script, and so must be valid POSIX shell
          input; normally, it will just be a sequence of ``KEY=value``
          lines".  In particular, the following cases are valid POSIX
          shell input but will be mishandled by this module:

          - It is assumed that all ``KEY=value`` assignments are on a
            single line.  Multi-line strings will make the module error
            out.

          - Variable substitutions in the ``value`` part will not be detected.

          - Escaped quotes will be treated as regular quotes, i.e., there
            is no way to embed a ``"`` or a ``'`` character in a
            ``KEY=value`` line with this module.

          - String concatenation is not supported: whereas the POSIX shell
            interprets a line ``KEY="foo"'bar'`` as assigning the string
            ``foobar`` to ``KEY``, this module will only operate on the
            ``"foo"`` part.
        """
        config = str(config)  # make a copy so we can alter it
        pos = config.find(self._GRUB_CMDLINE_VAR)
        while pos > -1:
            # quote char can be `'` or `"`
            quote_pos = pos + len(self._GRUB_CMDLINE_VAR)
            quote_char = config[quote_pos]
            start = quote_pos + 1
            # string ends with matching quote
            end = config.index(quote_char, start)
            cmdline = config[start:end]
            new_cmdline = _edit_linux_cmdline(cmdline, state, name, value)
            config = config[:start] + new_cmdline + config[end:]
            delta = len(new_cmdline) - len(cmdline)
            pos = config.find(self._GRUB_CMDLINE_VAR, end + delta)
        return config


    def install(self, path):
        rc, stdout, stderr = self.module.run_command(
            # FIXME: do we need to further customize this?
            'grub-mkconfig -o /boot/grub/grub.cfg'.split(),
            # fail module if this fails
            check_rc=True,
        )
        return {
            'rc': rc, 'stdout': stdout, 'stderr': stderr,
        }


## main
#

# map file location to boot loader name/type
# (preserving order is important here, as GRUB2
# will still provide a `/boot/grub/menu.lst` file
# which we should not mistake for the presence
# of GRUB1 ...)
PATHS = OrderedDict([
    # path                  bootloader name
    ('/etc/default/grub',   'grub2'),
    ('/boot/grub/menu.lst', 'grub1'),
])


# map boot loader name/type to function for changing config file
BOOTLOADERS = {
    'grub2': Grub2,
    'grub1': Grub1,
}


def find_bootloader_config():
    for path, bootloader in PATHS.iteritems():
        if os.path.exists(path):
            return path, bootloader
    raise LookupError(
        "Cannot find any known bootloader configuration file."
        " Please specify one using the `path` and `bootloader` arguments.")



def main():
    from ansible.module_utils.basic import AnsibleModule
    module = AnsibleModule(
        argument_spec = {
            'name': {
                'required': True,
            },
            'state': {
                'required': False,
                'default': 'present',
                'choices': ['absent', 'present'],
            },
            'value': {
                'required': False,
                'default': None,
            },
            'edit_only': {
                'type': 'bool',
                'required': False,
                'default': False,
            },
            'path': {
                'required': False,
                'default': '',
            },
            'bootloader': {
                'required': False,
                'choices': list(BOOTLOADERS.keys()),
            },
            'backup': {
                'type': 'bool',
                'required': False,
                'default': False,
            },
        },
        supports_check_mode=True,
    )

    params = module.params

    path = params['path'].strip()
    bootloader = params['bootloader']
    if path and not bootloader:
        try:
            bootloader = PATHS[path]
        except KeyError:
            module.fail_json(
                msg=("If the `path` argument is given,"
                     " then `bootloader` must also be given."),
                changed=False,
            )
    if not path:
        try:
            path, bootloader = find_bootloader_config()
        except LookupError as err:
            module.fail_json(msg=str(err), changed=False)

    # seed the result dict in the object
    result = {
        'changed': False,
        'path': path,
        'bootloader': bootloader,
        'edited': False,
        'installed': False,
    }

    try:
        handler = BOOTLOADERS[bootloader](module)
    except KeyError:
        module.fail_json(
            msg=("Unknown value for `bootloader` argument: {bootloader}"
                 .format(bootloader=bootloader)),
            **result
        )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        return result

    # read in config file contents
    try:
        with open(path, 'r') as input:
            current_config = input.read()
    except (OSError, IOError) as err:
        module.fail_json(
            msg=("Cannot read file `{path}`: {err}"
                 .format(path=path, err=err)),
            **result
        )

    # apply requested changes
    new_config = handler.edit(
        current_config, params['state'], params['name'], params['value'])

    # exit early if no changes
    if new_config == current_config:
        module.exit_json(**result)

    # make a backup if requested
    if params['backup']:
        result['backup'] = module.backup_local(path)

    # write out changed config
    try:
        with NamedTemporaryFile(
                dir=dirname(path),
                prefix=(basename(path) + '.'),
                suffix='.tmp',
                delete=False) as edited:
            edited.write(new_config)
        module.atomic_move(edited.name, path)
        result['changed'] = True
    except (OSError, IOError) as err:
        module.fail_json(
            msg=("Cannot write back file `{path}`: {err}"
                 .format(path=path, err=err)),
            **result
        )
    finally:
        module.cleanup(edited.name)

    result['edited'] = True

    # ensure new config is used by the bootloader next time
    result['installed'] = False
    if not params['edit_only']:
        try:
            install_result = handler.install(path)
            result.update(install_result)
            result['installed'] = True
            result['changed'] = True
        except Exception as err:
            module.fail_json(
                msg=("Cannot install new config file `{path}`: {err}"
                     .format(path=path, err=err)),
                **result
            )

    # all done
    module.exit_json(**result)


if __name__ == '__main__':
    main()
