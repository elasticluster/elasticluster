#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = """
---
module: conda
short_description: Manage Python libraries via conda
description:
  >
    Manage Python libraries via conda.
    Can install, update, and remove packages.
author: Synthicity
notes:
  >
    Requires conda to already be installed.
    Will look under the home directory for a conda executable.
options:
  name:
    description: The name of a Python library to install
    required: true
    default: null
  version:
    description: A specific version of a library to install
    required: false
    default: null
  state:
    description: State in which to leave the Python package
    required: false
    default: present
    choices: [ "present", "absent", "latest" ]
  channels:
    description: Extra channels to use when installing packages
    required: false
    default: null
  executable:
    description: Full path to the conda executable
    required: false
    default: null
  extra_args:
    description: Extra arguments passed to conda
    required: false
    default: null
"""

EXAMPLES = """
- name: install numpy via conda
  conda: name=numpy state=latest

- name: install scipy 0.14 via conda
  conda: name=scipy version="0.14"

- name: remove matplotlib from conda
  conda: name=matplotlib state=absent
"""

from distutils.spawn import find_executable
import os.path


def _find_conda(module, executable):
    """
    If `executable` is not None, checks whether it points to a valid file
    and returns it if this is the case. Otherwise tries to find the `conda`
    executable in the path. Calls `fail_json` if either of these fail.

    """
    if not executable:
        conda = find_executable('conda')
        if conda:
            return conda
    else:
        if os.path.isfile(executable):
            return executable

    module.fail_json(msg="could not find conda executable")


def _add_channels_to_command(command, channels):
    """
    Add extra channels to a conda command by splitting the channels
    and putting "--channel" before each one.

    """
    if channels:
        channels = channels.strip().split()
        dashc = []
        for channel in channels:
            dashc.append('--channel')
            dashc.append(channel)

        return command[:2] + dashc + command[2:]
    else:
        return command


def _add_extras_to_command(command, extras):
    """
    Add extra arguments to a conda command by splitting the arguments
    on white space and inserting them after the second item in the command.

    """
    if extras:
        extras = extras.strip().split()
        return command[:2] + extras + command[2:]
    else:
        return command


def _check_installed(module, conda, name):
    """
    Check whether a package is installed. Returns (bool, version_str).

    """
    command = [
        conda,
        'list',
        '^' + name + '$'  # use regex to get an exact match
    ]
    command = _add_extras_to_command(command, module.params['extra_args'])

    rc, stdout, stderr = module.run_command(command)

    if rc != 0:
        return False, None

    version = stdout.strip().split()[-2]

    return True, version


def _remove_package(module, conda, installed, name):
    """
    Use conda to remove a given package if it is installed.

    """
    if module.check_mode and installed:
        module.exit_json(changed=True)

    if not installed:
        module.exit_json(changed=False)

    command = [
        conda,
        'remove',
        '--yes',
        name
    ]
    command = _add_extras_to_command(command, module.params['extra_args'])

    rc, stdout, stderr = module.run_command(command)

    if rc != 0:
        module.fail_json(msg='failed to remove package ' + name)

    module.exit_json(changed=True, name=name, stdout=stdout, stderr=stderr)


def _install_package(
        module, conda, installed, name, version, installed_version):
    """
    Install a package at a specific version, or install a missing package at
    the latest version if no version is specified.

    """
    if installed and (version is None or installed_version == version):
        module.exit_json(changed=False, name=name, version=version)

    if module.check_mode:
        if not installed or (installed and installed_version != version):
            module.exit_json(changed=True)

    if version:
        install_str = name + '=' + version
    else:
        install_str = name

    command = [
        conda,
        'install',
        '--yes',
        install_str
    ]
    command = _add_channels_to_command(command, module.params['channels'])
    command = _add_extras_to_command(command, module.params['extra_args'])

    rc, stdout, stderr = module.run_command(command)

    if rc != 0:
        module.fail_json(msg='failed to install package ' + name)

    module.exit_json(
        changed=True, name=name, version=version, stdout=stdout, stderr=stderr)


def _update_package(module, conda, installed, name):
    """
    Make sure an installed package is at its latest version.

    """
    if not installed:
        module.fail_json(msg='can\'t update a package that is not installed')

    # see if it's already installed at the latest version
    command = [
        conda,
        'update',
        '--dry-run',
        name
    ]
    command = _add_channels_to_command(command, module.params['channels'])
    command = _add_extras_to_command(command, module.params['extra_args'])

    rc, stdout, stderr = module.run_command(command)

    if rc != 0:
        module.fail_json(msg='can\'t update a package that is not installed')

    if 'requested packages already installed' in stdout:
        module.exit_json(changed=False, name=name)

    # now we're definitely gonna update the package
    if module.check_mode:
        module.exit_json(changed=True, name=name)

    command = [
        conda,
        'update',
        '--yes',
        name
    ]
    command = _add_channels_to_command(command, module.params['channels'])
    command = _add_extras_to_command(command, module.params['extra_args'])

    rc, stdout, stderr = module.run_command(command)

    if rc != 0:
        module.fail_json(msg='failed to update package ' + name)

    module.exit_json(changed=True, name=name, stdout=stdout, stderr=stderr)


def main():
    module = AnsibleModule(
        argument_spec={
            'name': {'required': True, 'type': 'str'},
            'version': {'default': None, 'required': False, 'type': 'str'},
            'state': {
                'default': 'present',
                'required': False,
                'choices': ['present', 'absent', 'latest']
            },
            'channels': {'default': None, 'required': False},
            'executable': {'default': None, 'required': False},
            'extra_args': {'default': None, 'required': False, 'type': 'str'}
        },
        supports_check_mode=True)

    conda = _find_conda(module, module.params['executable'])
    name = module.params['name']
    state = module.params['state']
    version = module.params['version']

    installed, installed_version = _check_installed(module, conda, name)

    if state == 'absent':
        _remove_package(module, conda, installed, name)
    elif state == 'present' or (state == 'latest' and not installed):
        _install_package(
            module, conda, installed, name, version, installed_version)
    elif state == 'latest':
        _update_package(module, conda, installed, name)


# import module snippets
from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
