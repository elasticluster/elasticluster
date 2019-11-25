Docker Engine (Community Edition)
=================================

Install [Docker Engine - Community Edition][1] and allow a designated
sets of users to connect and use the Docker daemon.

[1]: https://docs.docker.com/install/


Requirements
------------

The role is pretty much self-contained; since most of the
configuration is actually done by Docker's setup script, the role can
run on any host that runs a distribution supported by Docker CE --
see: <https://docs.docker.com/install/#supported-platforms>

**Running this role requires `root` access.**


Role Variables
--------------

The following variables may be set to alter the role behavior:

`docker_group_members`
: YAML list of user names; those users will be added to the local UNIX
  group that can connect to the Docker Engine daemon.

`docker_release_channel`
: What repository to download Docker packages from (e.g., stable,
  nightly, etc).  Defaults to `stable`.


Example Playbook
----------------

The following example installs Docker Engine CE and allows users
`admin` and `openbis` to connect to it:

```yaml
- hosts: servers
  roles:
  - role: docker-ce
    docker_group_members:
    - admin
    - openbis
```


License
-------

GPLv3


Author Information and Credits
------------------------------

[Manuele Simi](manuele.simi@gmail.com) originally contributed the role
to the [ElastiCluster][2] playbook collection.

[2]: http://elasticluster.readthedocs.io/
