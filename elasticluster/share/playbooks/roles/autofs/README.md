AutoFS
======

Install Linux' automounter [AutoFS][1], together with scripts for
mounting of NFS (v3 and v4) and GlusterFS filesystems on the fly in
the `/net` directory hierarchy.

[1]: https://wiki.archlinux.org/index.php/Autofs


Requirements
------------

All major Linux distributions include packages for AutoFS; this role
should be able to run almost everywhere without special requirements.

**Running this role requires `root` access.**


Role Variables
--------------

The following variables may be set to alter the role behavior:

`autofs_home_server`
: *If defined,* then `/home` is made into an auto-mounted directory:
  all accesses to a directory `/home/XXX` will result in an attempt to
  mount directory `/srv/nfs/home/XXX` from the host designated by
  `autofs_home_server`.


Example Playbook
----------------

The following example installs AutoFS and configures it to auto-mount
networked filesystems under the `/net` directory:

```yaml
- hosts: servers
  roles:
  - role: autofs
```

The following example install AutoFS like above, and additionally
makes each `/home/XXX` directory automounted from host
`homeserv.example.org`:

```yaml
- hosts: servers
  roles:
  - role: autofs
    autofs_home_server: homeserv.example.org
```


License
-------

GPLv3


Author Information and Credits
------------------------------

[Riccardo Murri](mailto:riccardo.murri@gmail.com) originally
contributed the role to the [ElastiCluster][2] playbook collection.

[2]: http://elasticluster.readthedocs.io/
