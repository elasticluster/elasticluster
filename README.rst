Ansible GC3 playbooks
=====================

This repository contains the modules and playbooks used by the GC3 to
mantain the production infrastructure *and* to configure VM instances
on the `Hobbes` cloud.

The structure of the repository follow this schema::

    |   # Group variables   
    +-- group_vars
    |   +-- foo  # variables automatically set for group `foo`
    |   +-- bar  # variables automatically set for group `bar` 
    |
    |   # Host variables
    +-- host_vars
    |   +-- host1  # variables automatically set for host `host1`
    |
    |   # Private variables. All the files in this directory are
    |   # *encrypted* with the filter specified in ``.gitattributes``
    +-- private_vars
    |   +-- ldap  # variables included by some playbook.
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
    +-- modules
    |   # This directory contains ansible modules developed by GC3
    |
    +-- hosts     # GC3 inventory file
    +-- examples  # directory containing examples and code snippets.
    +-- README.rst


GC3-specific configuration
--------------------------

Some playbooks, like ``roles/gc3.yml``, only work for hosts in the
`gc3` group. You can either assign an host to that group in the
inventory file, or you can set a variable `gc3group` equals to `gc3`
(either from the inventory file or from the command line by using the
`-e` option), and the ``site.yml`` playbook will assign the host to
the `gc3` group.

Extra modules
-------------

Extra modules are defined in the ``modules`` directory. In order to
use them you need to either run ``ansible-playbook`` with option ``-M
modules``, **or** edit your ansible configuration file and update the
`library` option, **or** set the environemnt variable
``ANSIBLE_LIBRARY``.

SLURM configuration
-------------------

In order to configure a slurm cluster, create an hosts file with::

    [slurm_master]
    hostname ansible_ssh_host=A.B.C.D
    
    [slurm_clients]
    node1 ansible_ssh_host=A.B.C.D
    node2 ansible_ssh_host=A.B.C.D
    node3 ansible_ssh_host=A.B.C.D

then run::

    ansible-playbook -i <hostfile> site.yml

Jenkins
-------

To configure jenkins, use an hostfile containing::

    [jenkins]
    hostname ansible_ssh_host=A.B.C.D

then run::

    ansible-playbook -i <hostfile> site.yml

Please note that by default this will create jobs to test gc3pie. If
you want to modify it, just check the variable `j_jobs` in
`group_vars/jenkins``

Ganglia
-------

Hostfile to configure ganglia::

    [ganglia_master]
    ganglia-frontend

    [ganglia_monitor]
    ganglia-frontend
    node01
    node02


`ganglia_master` group will install the ganglia web frontend and the
`gmetad` daemon. 

The `ganglia_monitor` group will install `gmond` and will configure it
in order to send statistics to the `ganglia_master` node.

On a default ganglia installation you are supposed to install the
`gmond` daemon on the frontend as well, but this is not done
automatically by this playbook, therefore you have to add the frontend
also to the `ganglia_monitor` group.
