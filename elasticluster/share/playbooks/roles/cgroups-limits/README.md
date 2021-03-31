cgroups-limits
=========

Set cgroup limit in the ElastiCluster frontend node

This role applies the limits to all the members of the unix group "course". We usually
create this group with the extra role "local-accounts"

This role is not executed by default so you probably want to
use the playbook `after.yml` with something like this:

```
---
#
# This playbook is for site-local customization to ElastiCluster's
# playbooks.  It runs *after* any other playbook distributed with
# ElastiCluster has gotten its chance to run.
#
# An empty playbook is checked into the Git repository.  If you make
# any local modifications, please run `git update-index
# --assume-unchanged after.yml` to avoid committing them accidentally
# into ElastiCluster's main branch.
#
- name: Apply local customizations (after)
  tags:
    - after
    - local
  hosts: all
  # by default these are no-op (empty task list)
  roles:
    - local-accounts
    - cgroups-limits
  tasks: []

```


Role Variables
--------------
```
cgroup_memory_limit_in_bytes: '10G'

to_whom_the_limit_applies: '@course'
```

Example Playbook
----------------

    - hosts: servers
      roles:
         - { role: cgroups-limits }

License
-------

GPLv3

Author Information
------------------

Pablo Escobar
