Ansible GC3 playbooks
=====================

List of playbooks usable for ansible

SLURM configuration
-------------------

In order to configure a slurm cluster, create an hosts file with::

    [slurm_master]
    hostname ansible_ssh_host=Z.B.C.D
    
    [slurm_clients]
    node1 ansible_ssh_host=Z.B.C.D
    node2 ansible_ssh_host=Z.B.C.D
    node3 ansible_ssh_host=Z.B.C.D

then run::

    ansible-playbook -i <hostfile> slurm.yml


Jenkins
-------

To configure jenkins, use an hostfile containing::

    [jenkins]
    hostname ansible_ssh_host=A.B.C.D

then run::

    ansible-playbook -i <hostfile> jenkins.yml

Please note that by default this will install the configuration for
gc3pie. If you want to modify it, just check the variable `j_jobs` in
`group_vars/jenkins``
