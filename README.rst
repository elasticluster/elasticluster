Ansible GC3 playbooks
=====================

List of playbooks usable for ansible

GC3-specific configuration
--------------------------

Some playbooks, like the one to configure the GC3 repository, only
work for hosts in the `gc3` group. You can either assign an host to
that group, or you can set a variable `gc3group` equals to `gc3`
(either from the inventory file or from the command line by using the
`-e` option), and the ``site.yml`` playbook will assign the host to
the `gc3` group.


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
