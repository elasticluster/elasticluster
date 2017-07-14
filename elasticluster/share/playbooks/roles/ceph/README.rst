CephFS
======

Install Ceph_ with CephFS_ to provide
a working shared filesystem for clusters.

In contrast with other playbooks in the ElastiCluster_ collection, there is a
single role for installing all kinds of Ceph server and client nodes: the node
groups a host belongs to determine what services will be running:

=================  ======================================================
Ansible group      Action
=================  ======================================================
``ceph_mon``       Install Ceph server software and configure this host
                   to run the MON (monitor) service.  There *must* be
                   at least one MON node in any Ceph cluster.
``ceph_osd``       Install Ceph server software and configure this host
                   to run the OSD (object storage device) service.
                   There *must* be at least three OSD nodes in a Ceph
                   cluster. OSDs store their data into local directory
                   ``/var/lib/ceph/osd/ceph-NNN``.
``ceph_mds``       Install Ceph server software and configure this host
                   to run the MDS (meta-data server) service.  This node
                   is optional but CephFS can only run if at least one
                   MDS is available in the cluster.
``ceph_client``    Install required packages to make usage of Ceph Storage
                   Cluster and CephFS possible.  Any mount point listed in
                   ``CEPH_MOUNTS`` will be created and the corresponding
                   filesystem mounted.
=================  ======================================================


Requirements
------------

The role should be self-contained with no additional dependencies.

It is recommended that NTP is run on all hosts participating in a Ceph cluster.


Role Variables
--------------

The following variables may be set to alter the role behavior:


``ceph_release`` (default: ``luminous``)
  Name of Ceph release to install, e.g. "luminous" or "jewel".
  Note that not all releases are available on all platforms;
  for instance, selecting the "hammer" release on Ubuntu 16.04
  will install "jewel" instead.

``ceph_osd_pool_size`` (default: 2)
  Default number of object replicas in a pool.

``ceph_osd_pg_num`` (default computed according to: `<http://docs.ceph.com/docs/master/rados/operations/placement-groups/#a-preselection-of-pg-num>`_)
  Default number of PGs in a pool.

``ceph_metadata_pg_num`` (default: 1/8 of ``ceph_osd_pool_size``)
  Number of PGs for the CephFS metadata pool.

``ceph_data_pg_num`` (default: 7/8 of ``ceph_osd_pool_size``)
  Number of PGs for the CephFS data pool.

``CEPH_MOUNTS`` (default: no mount points)
  A list of CephFS filesystems to mount on CephFS clients.

  Each filesystem is defined by a dictionary with the following
  key/value pairs:

  - mountpoint: path to the local mountpoint
  - options: mount options, defaults to `rw` if not given
  - state: see documentation for Ansible module `mount`; the default value here is `mounted`

  For example::

      CEPH_MOUNTS:
        - mountpoint: '/cephfs'
          options: 'rw'

  Note there is no "device" or "source" parameter: the mount device for CephFS
  is always the address of a MON host (which is known by other means and need
  not be repeated here).

  By default, this parameter is the empty list, i.e., no CephFS filesystems are mounted.

``ceph_fsid`` (default: ``00baac7a-0ad4-4ab7-9d5e-fdaf7d122aee``)
  Unique identifier for the cluster.  Only relevant if you are running
  several clusters side-by-side.

``ceph_cluster_name`` (default: ``ceph``)
  Argument to the `--cluster` option for `ceph` commands: a human-readable
  cluster name. There is little need to change it unless you're working with
  multiple clusters at the same time.


Example Playbook
----------------

The following example installs and configures Ceph and CephFS, overriding the
default arguments for the pool replica factor and default PG number, and mounts
the filesystm on directory ``/cephfs`` on the client nodes (mount point is
automatically created)::

  - hosts: ceph_mon:ceph_osd:ceph_mds:ceph_client
    roles:
    - role: ceph
      ceph_osd_pool_size: 3
      ceph_osd_pg_num: 8192
      CEPH_MOUNTS:
        - mountpoint: /cephfs

Note that there is a single role for installing all kinds of Ceph server and
client nodes: the node groups a host belongs to determine what services will be
running, so *node group names must have the fixed values given in the table at
the beginning of this page!*


License
-------

GPLv3


Author Information and Credits
------------------------------

`Antonio Messina <mailto:arcimboldo@gmail.com>`_ wrote the original support for
Ceph in ElastiCluster_.

`Riccardo Murri <mailto:riccardo.murri@gmail.com>`_ rewrote the playbook into an
autonomous role, added CephFS support, and introduced any bugs you can see.


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
.. _Ceph: http://docs.ceph.com/docs/master/start/intro/
.. _CephFS: http://docs.ceph.com/docs/master/cephfs/
