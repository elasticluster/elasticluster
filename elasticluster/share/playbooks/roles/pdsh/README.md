PDSH
====

Install [PDSH][1], and configure it to use SSH by default, and mark
all hosts with "genders" that correspond to the Ansible groups they're
in.

[1]: http://www.admin-magazine.com/HPC/Articles/pdsh-Parallel-Shell

Note that PDSH over SSH is only useful if all hosts have been
configured to allow passwordless SSH connections. (Which
[ElastiCluster][2] does by default in the `common` role.)


Requirements
------------

All major Linux distributions include packages for PDSH; this role
should be able to run almost everywhere without special requirements.

**Running this role requires `root` access.**


Role Variables
--------------

The following variables may be set to alter the role behavior:

`hosts`
: If this variable is defined, then it should contain a YAML list of
  host names: the `/etc/genders` file will be populated only with
  these hosts, instead of all hosts in the Ansible inventory
  (default).


Example Playbook
----------------

The following example installs PDSH with the default configuration
(use SSH, tag each host with "genders" coming from the Ansible group
names):

```yaml
- hosts: servers
  roles:
  - role: autofs
```


License
-------

GPLv3


Author Information and Credits
------------------------------

[Riccardo Murri](mailto:riccardo.murri@gmail.com) originally
contributed the role to the [ElastiCluster][2] playbook collection.

[2]: http://elasticluster.readthedocs.io/
