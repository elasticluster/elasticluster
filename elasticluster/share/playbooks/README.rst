ElastiCluster Ansible playbooks
===============================

This repository contains the modules and playbooks used by the ElastiCluster
to configure the VMs.  They can however be used independently of ElastiCluster.

The structure of the repository follow this schema::

    |   # Group variables
    +-- group_vars
    |   +-- all  # variables set on all hosts where playbooks run;
    |            # currently mainly used to provide conditionals
    |            # about OS version and features
    |
    |   # Collection of playbooks divided by *role*
    +-- roles
    |  - role-foo.yml  # playbook for role `role-foo`
    |  - role-foo      # directory containing stuff used by `role-foo`
    |    - files       # files to be copied on the managed machine.
    |    - handles     # handlers used by the role
    |    - tasks       # collection of tasks executed by the playbook
    |    - templates   # templates used by the playbook
    |
    +-- site.yml
    |   # This is the main playbook. It includes all the playbooks created
    |   # in `roles` directory. Each role is supposed to be applied only
    |   # to specific group of nodes. For instance, the `ganglia` role
    |   # will configure only hosts in the  `ganglia_monitor` or
    |   # `ganglia_master` groups.
    |
    +-- after.yml
    |   # Playbook executed by `site.yml` after all the other tasks have
    |   # successfully run.  Can be used to add local customizations.
    |
    +-- modules
    |   # This directory contains extra Ansible modules
    |
    +-- examples
    |   # directory containing examples and code snippets.
    |
    +-- README.rst

The playbooks distributed in the ``roles/`` directory are documented in section
`"Playbooks distributed with ElastiCluster"
<http://elasticluster.readthedocs.io/en/latest/playbooks.html>`_ of the
`ElastiCluster manual <http://elasticluster.readthedocs.io/>`_. Some of the
roles are also accompanied by a small "README" file that states purpose and
customization variables.

Extra modules are defined in the ``modules`` directory. In order to
use them you need to either run ``ansible-playbook`` with option ``-M
modules``, **or** edit your ansible configuration file and update the
`library` option, **or** set the environment variable
``ANSIBLE_LIBRARY``.  The latter is what ElastiCluster main code does.
