# elasticluster-local-accounts

Add local accounts and groups.

Also add public ssh keys to the created accounts and configures
ssh server to allow password authentication

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

