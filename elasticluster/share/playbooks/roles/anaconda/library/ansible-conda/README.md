# Conda Ansible Module

Manage [conda][] installations of Python packages in [Ansible][] playbooks.
Put this module somewhere Ansible will find it
(like the `library/` directory next to your top level playbooks).
Usage is much like the built-in Ansible pip module.
This requires `conda` to already be installed somehow.

Examples:

```yaml
- name: install numpy via conda
  conda: name=numpy state=latest

- name: install scipy 0.14 via conda
  conda: name=scipy version="0.14"

- name: remove matplotlib from conda
  conda: name=matplotlib state=absent
```

From `ansible-doc`:

```
> CONDA

  Manage Python libraries via conda. Can install, update, and remove
  packages.

Options (= is mandatory):

- channels
        Extra channels to use when installing packages [Default: None]

- executable
        Full path to the conda executable [Default: None]

- extra_args
        Extra arguments passed to conda [Default: None]

= name
        The name of a Python library to install [Default: None]

- state
        State in which to leave the Python package (Choices: present,
        absent, latest) [Default: present]

- version
        A specific version of a library to install [Default: None]

Notes:  Requires conda to already be installed. Will look under the home
        directory for a conda executable.
```

[conda]: http://conda.pydata.org/
[Ansible]: http://docs.ansible.com/index.html
