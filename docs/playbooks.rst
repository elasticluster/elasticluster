.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc


.. _playbooks:

============================================
  Playbooks distributed with ElastiCluster
============================================

ElastiCluster uses `Ansible`_ to configure the VM cluster based on the
options read from the configuration file.  This chapter describes the
Ansible playbooks bundled [#]_ with ElastiCluster and how to
use them.

.. [#]

   ElastiCluster playbooks can be found in the
   ``elasticluster/share/playbooks`` directory of the source code. You
   are free to copy, customize and redistribute them under the terms
   of the `GNU General Public License version 3`_ or (at your option)
   any later version.


.. contents::


Setup variables
===============

In some cases, extra variables can be set to playbooks to modify its
default behavior. In these cases, you can either define a variable
global to the cluster using::

    global_var_<varname>=<value>

or, if the variable must be defined only for a specific group of
hosts::

    <groupname>_var_<varname>=<value>

For example::

  slurm_worker_allow_reboot=yes


General setup variables
-----------------------

The following customization variables apply to all ElastiCluster playbooks.

================================== =================== =================================================
Variable name                      Default             Description
================================== =================== =================================================
``allow_reboot``                   no                  Allow rebooting nodes if needed.  Be careful
                                                       if this is set when resizing clusters, as you
                                                       may lose running jobs.
``insecure_https_downloads``       no                  If ``no`` (default), require that web sites, from
                                                       where software is downloaded, present a valid
                                                       SSL/TLS certificate.  However, it may happen
                                                       that the base OS trusted certificates repository
                                                       is not fully up-to-date and this verification fails.
                                                       (See, for instance, `issue #539 <https://github.com/gc3-uzh-ch/elasticluster/issues/539>`_).
                                                       In these cases, setting this option to ``yes``
                                                       allows the playbooks to continue (at the expense
                                                       of some security).

                                                       .. warning::

                                                          Setting this option to ``yes`` also allows
                                                          installing packages from *unauthenticated*
                                                          sources on Debian/Ubuntu.

``multiuser_cluster``              no                  Install NIS/YP.  The first node in the ``master``
                                                       class will be assigned the role of the YP master
                                                       server; additional nodes in the "master" class
                                                       (if any) will be YP slave servers.
``ssh_password_auth``              yes                 Allow users to log in via SSH by providing a
                                                       password. **Note:** the default in ElastiCluster
                                                       is the opposite of what all major GNU/Linux
                                                       distributions do.
``upgrade_packages``               yes                 Upgrade all installed to the latest available
                                                       version.  Setting this to ``no`` allows speedier
                                                       setup when starting from cluster snapshots.
                                                       *Note:* even when set to ``no``, some packages
                                                       may still be upgraded to satisfy dependencies
                                                       of other packages that need to be installed.
================================== =================== =================================================


Compute clusters
================

The following playbooks are available for installing compute clusters
(batch-queuing or otherwise) with ElastiCluster.


SLURM
-----

Supported on:

* Ubuntu 12.04 and later
* Debian 7 ("wheezy") and 8 ("jessie")
* RHEL/CentOS 6.x and 7.x

This playbook installs the `SLURM`_ batch-queueing system.

You are supposed to only define one ``slurm_master`` and multiple
``slurm_worker``. The first will act as login node, NFS server for
the ``/home`` filesystem, and runs the SLURM scheduler and accounting
database; the workers will only execute the jobs.  A ``slurm_submit``
role allows you to optionally install "SLURM client" nodes, i.e.,
hosts whose only role in the cluster is to submit jobs and query the
queue status.

=================  ==================================================
Ansible group      Action
=================  ==================================================
``slurm_master``   SLURM controller/scheduler node; also runs the
                   accounting storage daemon `slurmdbd` and its
                   MySQL/MariaDB backend.
``slurm_worker``   SLURM execution node: runs the `slurmd` daemon.
``slurm_submit``   SLURM client: has all the submission and query
                   commands installed, but runs no daemon.
=================  ==================================================

The following example configuration sets up a SLURM batch-queuing
cluster using 1 front-end and 4 execution nodes::

    [cluster/slurm]
    master_nodes=1
    worker_nodes=4
    ssh_to=master
    setup_provider=slurm
    # ...

    [setup/slurm]
    master_groups=slurm_master
    worker_groups=slurm_worker
    # ...

You can combine the SLURM playbook with other add-on software.  For
instance, you can install the Ganglia monitoring system alongside with
SLURM; in this case the ``setup`` stanza will look like::

    [setup/slurm+ganglia]
    frontend_groups=slurm_master,ganglia_master
    compute_groups=slurm_worker,ganglia_monitor
    ...

When combined with the CUDA add-on, and if any actual NVIDIA GPU
devices are found on the compute nodes, SLURM will be configured with
the GPU devices are GRES__ resources so that you can request the use
of GPUs in your jobs by passing the ``--gres=gpu:...`` option to
``sbatch``::

  # request 2 GPU devices
  sbatch --gres=gpu:2 my_gpgpu_job.sh

.. __: https://slurm.schedmd.com/gres.html

Note that compute nodes need to be given the `cuda` add-on playbook in
order for CUDA GPU detection and configuration to work.  For eaxmple,
the following configuration will detect and configure NVIDIA GPUs on
all compute nodes (but not on the front-end)::

    [setup/slurm+gpu]
    frontend_groups=slurm_master
    compute_groups=slurm_worker,cuda
    ...

Extra variables can be set by editing the `setup/` section:

.. list-table:: cgroup-related SLURM settings
   :widths: 30 20 50
   :header-rows: 1

   * - Variable
     - Default value
     - Description
   * - ``slurm_allowedramspace``          1
     - 100
     - Max percentage of RAM that can be allocated to a job. If
       ``slurm_constrainramspace`` (see below) is ``yes``, then this
       limit is applied to a job's *real memory* usage; otherwise,
       this limit is summed with ``slurm_allowedswapspace`` to cap the
       *virtual memory* usage (see SLURM's ``VSizeFactor``
       configuration parameter).
   * - ``slurm_allowedswapspace``
     - 1
     - Max percentage of virtual memory (in addition to the real
       memory) that can be allocated to a job.  This value is summed
       with ``slurm_allowedramspace`` to cap a job's total *virtual
       memory* usage.  You might want to set this limit to a much
       higher value when using GPUs, as GPU memory might be accounted
       in the job's virtual memory.
   * - ``slurm_constrainramspace``
     - yes
     - **Only used if ``slurm_taskplugin`` is set to ``task/cgroup``.**
       If set to ``yes`` then SLURM constrains the job's RAM usage by
       setting the memory soft limit to the allocated memory and the
       hard limit to the allocated memory * ``slurm_allowedramspace``
       (see below).  This can add stability to a system when there are
       multiple misbehaving jobs that allocate large amounts of
       memory, but can be problematic with jobs using GPUs (since the
       memory used on the GPU seems to be accounted against the job's
       own CPU RAM consumption).
   * - ``slurm_constrainswapspace``
     - yes
     - **Only used if ``slurm_taskplugin`` is set to ``task/cgroup``.**
       If set to ``yes`` then SLURM kills jobs whose virtual memory
       usage exceeds allocated memory * ``slurm_allowedswapspace``
       (see below).
   * - ``slurm_fastschedule``
     - 1
     - Value of ``FastSchedule`` in ``slurm.conf``
   * - ``slurm_jobacctgatherfrequency``
     - 60
     - Value of ``JobAcctGatherFrequency`` in ``slurm.conf``
   * - ``slurm_jobacctgathertype``
     - ``jobacct_gather/linux``
     - Value of ``JobAcctGratherType`` in ``slurm.conf``
   * - ``slurm_maxarraysize``
     - 1000
     - Maximum size of an array job
   * - ``slurm_maxjobcount``
     - 10000
     - Maximum nr. of jobs actively managed by the SLURM controller (i.e., pending and running)
   * - ``slurm_proctracktype``
     - ``proctrack/linuxproc``
     - Value of ``ProcTrackType`` in ``slurm.conf``
   * - ``slurm_returntoservice``
     - 2
     - Value of ``ReturnToService`` in ``slurm.conf``
   * - ``slurm_selecttype``
     - ``select/cons_res``
     - Value of ``SelectType`` in ``slurm.conf``
   * - ``slurm_selecttypeparameters``
     - ``CR_Core_Memory``
     - Value of ``SelectTypeParameters`` in ``slurm.conf``
   * - ``slurm_taskplugin``
     - ``task/none``
     - Value of ``TaskPlugin`` in ``slurm.conf``

Note that the ``slurm_*`` extra variables need to be set *globally*
(e.g., ``global_var_slurm_selectype``) because the SLURM configuration
file must be identical across the whole cluster.

Global variable ``multiuser_cluster`` controls whether the NIS/YP software is
installed on the cluster (NIS master on the cluster master node, compute nodes
are NIS slaves) to make it easier to add users to the cluster (just run the
``adduser`` command on the master).

The "SLURM" playbook depends on the following Ansible roles being
available:

* `slurm-common <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/slurm-common>`_
* `slurm-client <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/slurm-client>`_
* `slurm-master <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/slurm-master>`_
* `slurm-worker <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/slurm-worker>`_

In order for the NFS exported home directory to be mountable from the cluster's compute nodes,
security groups on OpenStack need to permit all UDP traffic between all cluster nodes.


GridEngine
----------

Tested on:

* CentOS 6.x and 7.x
* Ubuntu 14.04 ("trusty") and 16.04 ("xenial")
* Debian 8 ("jessie")

======================== =======================================
 ansible groups          role
======================== =======================================
``gridengine_master``    Scheduler, admin, and submission host
``gridengine_worker``    Compute (exec) node and submission host
======================== =======================================


This playbook installs `GridEngine`_ using the packages distributed with
Ubuntu, Debian, or CentOS, and creates a basic working configuration.

You are supposed to only define one ``gridengine_master`` and multiple
``gridengine_worker``. The first acts as login node, fileserver, and runs the
master scheduler (SGE ``qmaster``), whereas the others will only execute jobs
(SGE ``execd``).

The ``/home`` filesystem is exported *from* the gridengine "master" to the
worker nodes. The cell directory ``$SGE_ROOT/$SGE_CELL/common`` directory is
shared from the gridengine server to the compute nodes (via NFS).

A *snippet* of a typical configuration for a gridengine cluster is::

    [cluster/gridengine]
    frontend_nodes=1
    compute_nodes=5
    ssh_to=frontend
    setup_provider=ansible_gridengine
    ...

    [setup/ansible_gridengine]
    frontend_groups=gridengine_master
    compute_groups=gridengine_worker
    ...

You can combine the gridengine playbooks with ganglia. In this case the
``setup`` configuration stanza looks like::

    [setup/ansible_gridengine]
    frontend_groups=gridengine_master,ganglia_master
    compute_groups=gridengine_worker,ganglia_monitor
    ...

Global variable ``multiuser_cluster`` controls whether the NIS/YP software is
installed on the cluster (NIS master on the cluster master node, compute nodes
are NIS slaves) to make it easier to add users to the cluster (just run the
``adduser`` command on the master).


Hadoop + Spark
--------------

Supported on:

* Ubuntu 16.04, 14.04
* Debian 8 ("jessie")

This playbook installs a Hadoop_ 2.x cluster with Spark_ and Hive_,
using the packages provided by the Apache Bigtop_ project.  The
cluster comprises the HDFS and YARN services: each worker node acts
both as a HDFS "DataNode" and as a YARN execution node; there is a
single master node, running YARN's "ResourceManager" and "JobHistory",
and Hive's "MetaStore" services.

=================  ==================================================
Ansible group      Action
=================  ==================================================
``hadoop_master``  Install the Hadoop cluster master node: run YARN
                   "ResourceManager" and Hive "MetaStore" server.  In
                   addition, install a PostgreSQL server to host Hive
                   metastore tables.
``hadoop_worker``  Install a YARN+HDFS node: run YARN's "NodeManager"
                   and HDFS' "DataNode" services.  This is the group
                   of nodes that actually provide the storage and
                   execution capacity for the Hadoop cluster.
=================  ==================================================

HDFS is only formatted upon creation; if you want to reformat/zero out
the HDFS filesystem you need to run the ``hdfs namenode -format``
command yourself.  No rebalancing is done when adding or removing data
nodes from the cluster.

**Nota bene:**

  1. Currently ElastiCluster turns off HDFS permission checking:
     therefore Hadoop/HDFS clusters installed with ElastiCluster are
     only suitable for shared usage by *mutually trusting* users.

  2. Currently ElastiCluster has no provision to vacate an HDFS data
     node before removing it.  Be careful when shrinking a cluster, as
     this may lead to data loss!

The following example configuration sets up a Hadoop cluster using 4
storage+execution nodes::

    [cluster/hadoop+spark]
    master_nodes=1
    worker_nodes=4
    ssh_to=master

    setup_provider=hadoop+spark
    # ...

    [setup/hadoop+spark]
    provider=ansible
    master_groups=hadoop_master
    worker_groups=hadoop_worker

Global variable ``multiuser_cluster`` controls whether the NIS/YP software is
installed on the cluster (NIS master on the cluster master node, compute nodes
are NIS slaves) to make it easier to add users to the cluster (just run the
``adduser`` command on the master).

The following variables can be used to control the defaults for
running Spark applications.  (Note that they set a *default*, hence
can be overridden by applications when creating a Spark context; on
the other hand, these defaults are *exactly* what is used when running
``pyspark`` or a Jupyter notebook with Spark support.)

.. list-table:: Spark settings
   :widths: 30 20 50
   :header-rows: 1

   * - Variable
     - Default value
     - Description
   * - ``spark_driver_memory_mb``          1
     - *(Free memory on master node / nr. of CPUs of master node)*
     - Used to set ``spark.driver.memory``: maximum amount of memory
       (counted in MBs) that a Spark "driver" process is allowed to use.
   * - ``spark_driver_maxresultsize_mb``          1
     - *(80% of ``spark_driver_memory_mb``)*
     - Used to set ``spark.driver.maxResultSize``: Limit of total size
       (amount in MBs) of serialized results of all partitions for
       each Spark action (e.g. collect)
   * - ``spark_executor_memory_mb``          1
     - *(Max free memory on worker node / max nr. of CPUs on a node)*
     - Used to set ``spark.executor.memory``: Maximum amount of memory
       (counted in MBs) that a Spark "executor" process is allowed to use.
   * - ``spark_python_worker_memory_mb``          1
     - *(50% of ``spark_executor_memory_mb``)*
     - Used to set ``spark.python.worker.memory``: Maximum amount of
       memory (counted in MBs) to use per Python worker process during
       aggregation.  If the memory used during aggregation goes above
       this amount, Spark starts spilling the data into disks.


HTCondor
--------

Tested on:

* Debian 8.x
* Ubuntu 14.04

+-------------------+----------------------------------+
| ansible groups    | role                             |
+===================+==================================+
|``condor_master``  | Act as scheduler, submission and |
|                   | execution host.                  |
+-------------------+----------------------------------+
|``condor_worker``  | Act as execution host only.      |
+-------------------+----------------------------------+

This playbook will install the `HTCondor`_ workload management system
using the packages provided by the Center for High Throughput
Computing at UW-Madison.

The ``/home`` filesystem is exported *from* the condor master to the
compute nodes.

A *snippet* of a typical configuration for a slurm cluster is::

    [cluster/condor]
    setup_provider=htcondor
    frontend_nodes=1
    compute_nodes=2
    ssh_to=frontend
    # ...

    [setup/htcondor]
    frontend_groups=condor_master
    compute_groups=condor_worker
    # ...


Kubernetes
----------

Supported on:

* Ubuntu 16.04
* RHEL/CentOS 7.x

This playbook installs the `Kubernetes`_ container management system on each host.
It is configured using kubeadm. Currently only 1 master node is supported.

To force the playbook to run, add the Ansible group ``kubernetes``. The
following example configuration sets up a kubernetes cluster using 1
master and 2 worker nodes, and additionally installs flannel for the networking
(canal is also available)::

    [cluster/kubernetes]
    master_nodes=1
    worker_nodes=2
    ssh_to=master
    setup_provider=kubernetes
    # ...

    [setup/kubernetes]
    master_groups=kubernetes_master
    worker_groups=kubernetes_worker
    # ...

SSH into the cluster and execute 'sudo kubectl --kubeconfig
/etc/kubernetes/admin.conf get nodes' to view the cluster.


Filesystems and storage
=======================

The following playbooks are available for installing storage clusters
and distributed filesystems with ElastiCluster.  These can be used
standalone, or mixed with compute clusters to provide additional
storage space or more performant cluster filesystems.


CephFS
------

Supported on:

* Ubuntu 16.04, 14.04
* Debian 8 ("jessie"), 9 ("stretch")
* CentOS 6.x and 7.x

=================  ======================================================
Ansible group      Action
=================  ======================================================
``ceph_mon``       Install Ceph server software and configure this host
                   to run the MON (monitor) service.  There *must* be
                   at least one MON node in any Ceph cluster.
``ceph_osd``       Install Ceph server software and configure this host
                   to run the OSD (object storage device) service.
                   There *must* be at least three OSD nodes in a Ceph
                   cluster.
``ceph_mds``       Install Ceph server software and configure this host
                   to run the MDS (meta-data server) service.  This node
                   is optional but CephFS is only available if at least one
                   MDS is available in the cluster.
``ceph_client``    Install required packages to make usage of Ceph Storage
                   Cluster and CephFS possible.  Any mount point listed in
                   ``CEPH_MOUNTS`` will be created and the corresponding
                   filesystem mounted.
=================  ======================================================

This will install a Ceph Storage Cluster with CephFS. Actual data storage is
done in the OSD nodes, on each node under directory
``/var/lib/ceph/osd/ceph-NNN``. All hosts in group ``ceph_client`` can then
mount this filesystem, using either the `CephFS kernel driver`_ or the `CephFS
FUSE driver`_.

Management of the cluster is possible from any node (incl. ``ceph_client``
nodes) using the ``client.admin`` key (deployed in file
``/etc/ceph/ceph.client.admin.keyring``, by default only readable to the
``root`` user).

.. _`CephFS kernel driver`: http://docs.ceph.com/docs/master/cephfs/kernel/
.. _`CephFS FUSE driver`: http://docs.ceph.com/docs/master/cephfs/fuse/

The Ceph and CephFS behavior can be changed by defining the
following variables in the `setup/` section:

.. list-table:: Ceph/CephFS variables in ElastiCluster
   :widths: 10 15 75
   :header-rows: 1

   * - Variable
     - Default value
     - Description
   * - ``ceph_release``
     - ``luminous``
     - Name of Ceph release to install, e.g. "luminous" or "jewel". Note that
       not all releases are available on all platforms; for instance, selecting
       the "hammer" release on Ubuntu 16.04 will install "jewel" instead.
   * - ``ceph_osd_pool_size``
     - 2
     - Default number of object replicas in a pool.
   * - ``ceph_osd_pg_num``
     - computed according to: `<http://docs.ceph.com/docs/master/rados/operations/placement-groups/#a-preselection-of-pg-num>`_
     - Default number of PGs in a pool.
   * - ``ceph_metadata_pg_num``
     - 1/8 of ``ceph_osd_pool_size``
     - Number of PGs for the CephFS metadata pool.
   * - ``ceph_data_pg_num``
     - 7/8 of ``ceph_osd_pool_size``
     - Number of PGs for the CephFS data pool.

More detailed information can be found in the `ceph role README`_.

.. _`ceph role README`: https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/ceph

.. note::

  * In contrast with similar ElastiCluster playbooks, the CephFS playbook does
    *not* automatically mount CephFS on client nodes.

  * This playbook's defaults differ from Ceph's upstream defaults in the following
    ways:

    - default replication factor for objects in a pool is 2 (Ceph's upstream is 3)
    - the minimum number of copies of an object that a pool should have to continue
      being operational is 1 (Ceph's upstream is 2).

    In both cases, the different default is motivated by the assumption that
    cloud-based storage is "safer" than normal disk-based storage due to redundancy
    and fault-tolerance mechanisms at the cloud IaaS level.

  * The `CephFS kernel driver`_ for the "Luminous" release requires features
    that are only present in the Linux kernel from version 4.5 on. At the time
    of this writing, a >4.5 kernel is only installed by default on Debian 9
    "stretch". To mount a "Luminous" CephFS on any other Linux distribution, you
    will have to either use the `CephFS FUSE driver`_ or tell Ceph not tu use
    tunables v5::

      sudo ceph osd crush tunables hammer


The following example configuration sets up a CephFS cluster using 1 MON+MDS
node, 5 OSD nodes and providing 3 replicas for each object::

    [setup/ceph1]
    mon_groups=ceph_mon,ceph_mds
    osd_groups=ceph_osd
    client_groups=ceph_client

    global_var_ceph_release=luminous
    global_var_ceph_osd_pool_size=3

    [cluster/ceph1]
    setup=ceph1

    mon_nodes=1
    osd_nodes=5
    client_nodes=1
    ssh_to=client

    # .. cloud-specific params ...

This example configuration sets up a CephFS cluster using 3 MON+OSD nodes, 1 MDS
nodes and sets explicitly the number of PGs to use for CephFS metadata and
data::

    [setup/ceph2]
    mon_groups=ceph_mon,ceph_osd
    mds_groups=ceph_mds
    client_groups=ceph_client

    global_var_ceph_release=luminous
    global_var_ceph_metadata_pg_num=1024
    global_var_ceph_data_pg_num=8192

    [cluster/ceph2]
    setup=ceph2

    mon_nodes=3
    mds_nodes=1
    client_nodes=1
    ssh_to=client

    # .. cloud-specific params ...


GlusterFS
---------

Supported on:

* Ubuntu 14.04 and later
* Debian 8 and later
* RHEL/CentOS 6.x, 7.x

+--------------------+----------------------------------------------------+
| ansible groups     | action                                             |
+====================+====================================================+
|``glusterfs_server``| Run a GlusterFS server with a single *brick*       |
+--------------------+----------------------------------------------------+
|``glusterfs_client``| Install gluster client and (optionally) mount      |
|                    | a GlusterFS filesystem.                            |
+--------------------+----------------------------------------------------+

This will install a GlusterFS using all the ``glusterfs_server`` nodes
as servers with a single brick located in directory `/srv/glusterfs`,
and any ``glusterfs_client`` to mount this filesystem over directory
``/glusterfs``.

To manage the GlusterFS filesystem you need to connect to a
``gluster_server`` node.

By default the GlusterFS volume is "pure distributed": i.e., there is
no redundancy in the server setup (if a server goes offline, so does
the data that resides there), and neither is the data replicated nor
striped, i.e., replica and stripe number is set to 1.  This can be
changed by defining the following variables in the `setup/` section:

+----------------------+------------+---------------------------------------------+
| variable name        | default    | description                                 |
+======================+============+=============================================+
|``gluster_stripes``   | no stripe  | set the stripe value for default volume     |
+----------------------+------------+---------------------------------------------+
|``gluster_replicas``  | no replica | set replica value for default volume        |
+----------------------+------------+---------------------------------------------+
|``gluster_redundancy``| 0          | nr. of servers that can fail or be          |
|                      |            | offline without affecting data availability |
+----------------------+------------+---------------------------------------------+

Note that setting ``gluster_redundancy`` to a non-zero value will
force the volume to be "dispersed", which is incompatible with
striping and replication.  In other words, the ``gluster_redundancy``
option is incompatible with ``gluster_stripes`` and/or
``gluster_replicas``.  You can read more about the GlusterFS volume
types and permitted combinations at
`<http://docs.gluster.org/en/latest/Administrator%20Guide/Setting%20Up%20Volumes/>`_.

The following example configuration sets up a GlusterFS cluster using 8 data nodes
and providing 2 replicas for each file::

  [cluster/gluster]
    client_nodes=1
    server_nodes=8
    ssh_to=client

    setup_provider=gluster
    # ... rest of cluster params as usual ...

  [setup/gluster]
    provider=ansible

    client_groups=glusterfs_client
    server_groups=glusterfs_server,glusterfs_client

    # set replica and stripe parameters
    server_var_gluster_replicas=2
    server_var_gluster_stripes=1

The following example configuration sets up a dispersed GlusterFS
volume using 6 data nodes with redundancy 2, i.e., two servers can be
offlined without impacting data availability::

  [cluster/gluster]
    client_nodes=1
    server_nodes=6
    ssh_to=client

    setup_provider=gluster
    # ... rest of cluster params as usual ...

  [setup/gluster]
    provider=ansible

    client_groups=glusterfs_client
    server_groups=glusterfs_server,glusterfs_client

    # set redundancy and force "dispersed" volume
    server_var_gluster_redundancy=2

The "GlusterFS" playbook depends on the following Ansible roles being
available:

* `glusterfs-common <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/glusterfs-common>`_
* `glusterfs-client <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/glusterfs-client>`_
* `glusterfs-server <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/glusterfs-server>`_



OrangeFS/PVFS2
--------------

Tested on:

* Ubuntu 14.04

+-----------------+----------------------------------------------------+
| ansible groups  | role                                               |
+=================+====================================================+
|``pvfs2_meta``   | Run the pvfs2 metadata service                     |
+-----------------+----------------------------------------------------+
|``pvfs2_data``   | Run the pvfs2 data service                         |
+-----------------+----------------------------------------------------+
|``pvfs2_client`` | configure as pvfs2 client and mount the filesystem |
+-----------------+----------------------------------------------------+

The OrangeFS/PVFS2 playbook will configure a pvfs2 cluster. It
downloads the software from the `OrangeFS`_ website, compile and
install it on all the machine, and run the various server and client daemons.

In addiction, it will mount the filesystem in ``/pvfs2`` on all the clients.

You can combine, for instance, a SLURM cluster with a PVFS2 cluster::

    [cluster/slurm+orangefs]
    frontend_nodes=1
    compute_nodes=10
    orangefs_nodes=10
    ssh_to=frontend
    setup_provider=ansible_slurm+orangefs
    ...

    [setup/ansible_slurm+orangefs]
    frontend_groups=slurm_master,pvfs2_client
    compute_groups=slurm_worker,pvfs2_client
    orangefs_groups=pvfs2_meta,pvfs2_data
    ...

This configuration will create a SLURM cluster with 10 compute nodes,
10 data nodes and a frontend, and will mount the ``/pvfs2`` directory
from the data nodes to both the compute nodes and the frontend.


Add-on software
===============

The following playbooks add functionality or software on top of a
cluster (e.g., monitoring with web-based dashboard).  They can also be
used stand-alone (e.g., JupyterHub).


Anaconda
--------

Supported on:

* Ubuntu 14.04 and later
* RHEL/CentOS 6.x and 7.x

==============  =======================================================
Ansible group   Action
==============  =======================================================
``anaconda``    Install the Anaconda_ Python distribution
==============  =======================================================

This playbook installs the `Anaconda`_ Python distribution.  Using
customization variables you can choose whether to install the Python
2.7 or Python 3 version, and whether to make the Anaconda Python
interpreter the default Python interpreter for logged-in users.

The following variables may be set to alter the role behavior:

.. list-table:: Anaconda role variables in ElastiCluster
   :widths: 10 15 75
   :header-rows: 1

   * - Variable
     - Default value
     - Description
   * - ``anaconda_version``
     - ``5.1.0``
     - Version of the Anaconda Python distribution to install
   * - ``anaconda_python_version``
     - ``2``
     - Anaconda comes with either a Python2 or a Python3 interpreter
       -- choose which one you want here.
   * - ``anaconda_in_path``
     - ``yes``
     - whether the Python interpreter from Anaconda should be made the
       first match in users' shell ``$PATH``

For instance, the following configuration snippet requests that
ElastiCluster and Ansible install Anaconda Python3 on a SLURM cluster,
and make it the default interpreter on the frontend node only::

     [setup/slurm+anaconda]
     # ... same as usual SLURM setup, but:
     master_groups=slurm_master,anaconda
     worker_groups=slurm_worker,anaconda

     # use Anaconda Python3 flavor
     global_var_anaconda_python_version=3

     # make it default for logged-in users on master node only
     master_var_anaconda_in_path=yes
     worker_var_anaconda_in_path=no

The code from this role is a minor modification of the
`ansible-anaconda`__ playbook written by Andrew Rothstein, and as
such maintains the original distribution license.  See the
accompanying `LICENSE` file for details.

.. __: https://github.com/andrewrothstein/ansible-anaconda


Ansible
-------

Supported on:

* Ubuntu 12.04 and later
* RHEL/CentOS 6.x and 7.x

This playbook installs the `Ansible`_ orchestration and configuration management
system on each host.  There is not much clustering happening here; this playbook
is provided in case you want to be able to run Ansible playbooks from inside the
cluster (as opposed to always running them from the ElastiCluster host).

To force the playbook to run, add the Ansible group ``ansible`` to any node. The
following example configuration sets up a SLURM batch-queuing cluster using 1
front-end and 4 execution nodes, and additionally installs `Ansible`_ on the
front-end::

    [cluster/slurm]
    master_nodes=1
    worker_nodes=4
    ssh_to=master
    setup_provider=slurm+ansible
    # ...

    [setup/slurm+ansible]
    master_groups=slurm_master,ansible
    worker_groups=slurm_worker
    # ...


CUDA
----

Tested on:

* Ubuntu 14.04, 16.04
* CentOS 6.x, 7.x

+----------------+---------------------------------------+
| ansible groups | role                                  |
+================+=======================================+
|``cuda``        | Install the NVIDIA device drivers and |
|                | the CUDA toolkit and runtime.         |
+----------------+---------------------------------------+

This playbook will detect NVIDIA GPU devices on every host where it is
run, and install the CUDA toolkit and runtime software, thus enabling
the use of GPU accelerators.

Note that in some cases a reboot is necessary in order to correctly
install the NVIDIA GPU device drivers; this is only allowed if the
global variable ``allow_reboot`` is ``true`` -- by default, reboots
are not allowed so the playbook will fail if a reboot is needed.

A variable can be used to control the version of the CUDA toolkit that
will be installed on the nodes:

================ ============= ============================================
Variable name    Default value Description
---------------- ------------- --------------------------------------------
``cuda_version`` 8.0           What version of the CUDA toolkit to install
================ ============= ============================================

The default is to install CUDA tooklit and runtime version 8.0


EasyBuild
---------

Supported on:

* Ubuntu 16.04, 14.04
* Debian 8 ("jessie"), 9 ("stretch")
* CentOS 6.x and 7.x

==============  =======================================================
Ansible group   Action
==============  =======================================================
``easybuild``   Install the EasyBuild_ HPC package manager.
==============  =======================================================

This playbook installs EasyBuild_ and its dependencies to provide
a working build environment for HPC clusters.

EasyBuild is configured with the following options:

* use Lmod_ as the "environment modules" tool,
  and generate module files with Lua_ syntax.
* use `minimal toolchains`_ (including the "dummy" / system compiler toolchain)
* use `generic optimization flags`_ for maximum compatibility

.. _`minimal toolchains`: http://easybuild.readthedocs.io/en/latest/Manipulating_dependencies.html#using-minimal-toolchains-for-dependencies
.. _`generic optimization flags`: http://easybuild.readthedocs.io/en/latest/Controlling_compiler_optimization_flags.html#optimizing-for-a-generic-processor-architecture-via-optarch-generic

The following variables may be set to alter the role behavior:

.. list-table:: EasyBuild role variables in ElastiCluster
   :widths: 10 15 75
   :header-rows: 1

   * - Variable
     - Default value
     - Description
   * - ``EASYBUILD_VERSION``
     - 2.8.2
     - The version of EasyBuild_ to install. Interpolated into the
       (default) source archive name.
   * - ``EASYBUILD_PREFIX``
     - ``/opt/easybuild``
     - Root directory of all the EasyBuild-related paths: source
       archive, ``.eb``` files repository, installed software, etc.
   * - ``EASYBUILD_INSTALL``
     - Build no software during cluster setup.
     - List of ``.eb`` recipes to build.  This is a *YAML list*, i.e.,
       a comma-separated list of recipe names enclosed in square
       brackets; for example::

         global_var_EASYBUILD_INSTALL=[RELION,OpenMPI]

       *Beware:* the initial EasyBuild invocation will have to build
       the entire toolchain, so it can take a couple of hours even to
       install a small and relatively simple package. For this reason,
       the default value of this variable is the empty list (i.e., do
       not install any software through EasyBuild).
   * - ``EASYBUILD_OPTARCH``
     - ``GENERIC``
     - Optimization flags for building software, see:
       `<http://easybuild.readthedocs.io/en/latest/Controlling_compiler_optimization_flags.html#controlling-target-architecture-specific-optimizations-via-optarch>`_
       By default the "GENERIC" value is used which should produce
       code compatible with any x86-64 processor.

It is advised to install EasyBuild on the master/frontend node only,
and export the software directories from there to compute nodes via
NFS, to cut down on build times and to avoid coherency issues.


Ganglia
-------

Tested on:

* Ubuntu 12.04, 14.04, 16.04
* CentOS 6.x, 7.x

+--------------------+---------------------------------+
| ansible groups     | role                            |
+====================+=================================+
|``ganglia_master``  | Run gmetad and web interface.   |
|                    | It also run the monitor daemon. |
+--------------------+---------------------------------+
|``ganglia_monitor`` | Run ganglia monitor daemon.     |
+--------------------+---------------------------------+

This playbook will install `Ganglia`_ monitoring tool using the
packages distributed with Ubuntu or CentOS and will configure frontend
and monitors.

You should run only one ``ganglia_master``. This will install the
``gmetad`` daemon to collect all the metrics from the monitored nodes
and will also run apache.

If the machine in which you installed ``ganglia_master`` has IP
``10.2.3.4``, the ganglia web interface will be available at the
address http://10.2.3.4/ganglia/

This playbook is supposed to be compatible with all the other available playbooks.


IPython cluster
---------------

Tested on:

* Ubuntu 12.04
* CentOS 6.3
* Debian 7.1 (GCE)
* CentOS 6.2 (GCE)

+------------------------+------------------------------------+
| ansible groups         | role                               |
+========================+====================================+
| ``ipython_controller`` | Run an IPython cluster controller  |
+------------------------+------------------------------------+
| ``ipython_engine``     | Run a number of ipython engine for |
|                        | each core                          |
+------------------------+------------------------------------+

This playbook will install an `IPython cluster`_ to run python code in
parallel on multiple machines.

One of the nodes should act as *controller* of the cluster
(``ipython_controller``), running the both the *hub* and the
*scheduler*. Other nodes will act as *engine*, and will run one
"ipython engine" per core. You can use the *controller* node for
computation too by assigning the  ``ipython_engine`` class to it as
well.

A *snippet* of typical configuration for an Hadoop cluster is::

    [cluster/ipython]
    setup_provider=ansible_ipython
    controller_nodes=1
    worker_nodes=4
    ssh_to=controller
    ...

    [setup/ansible_ipython]
    controller_groups=ipython_controller,ipython_engine
    worker_groups=ipython_engine
    ...

In order to use the IPython cluster, using the default configuration,
you are supposed to connect to the controller node via ssh and run
your code from there.


JupyterHub
----------

Supported on:

* Ubuntu 16.04, 14.04
* Debian 8 ("jessie"), 9 ("stretch")
* CentOS 6.x and 7.x

==============  =======================================================
Ansible group   Action
==============  =======================================================
``jupyterhub``  Install Jupyter_ and JupyterHub_ to work with interactive
                computational notebooks.
==============  =======================================================

Install JupyterHub_ to grant multiple users access to Jupyter_
notebooks thorugh a web interface.  Kernels are installed to run code
written in Python 2.7 and 3.x (with Anaconda_ Python), BASH (using
the OS-provided shell), PySpark (in conjunction with the Hadoop+Spark
playbook), `R language`_ (if the R add-on is installed, see below),
and MATLAB (if installed).

.. note::

   JupyterHub is configured to authenticate users with the GNU/Linux
   ``/etc/passwd`` database.  So, in order to log in you need to
   create users first (or set passwords to existing users).

   In order to create a new user, run the following commands at the
   node's shell prompt::

     # replace `user_name` with an actual name (e.g. `jsmith`)
     sudo adduser user_name

   In order to set the password for an existing user, run the
   following commands at the node's shell prompt::

     # replace `user_name` with an actual name (e.g. `jsmith`)
     sudo passwd user_name

To use the JupyterHub server:

1. Note down the IP address of the server VM created by ElastiCluster
2. In your browser, open https://server.ip/
3. Accept the self-signed SSL certificate in the browser
4. Log in using username and password

.. note::

   You must edit the VM security group to allow connections to port
   443!  (ElastiCluster will not do this automatically.)

The JupyterHub role can be combined with other playbooks (it is
advised to add it to the frontend/master node), or can be used to
install a stand-alone server.  A full example of how to install a
JupyterHub stand-alone server can be found at:
`<https://github.com/gc3-uzh-ch/elasticluster/blob/master/examples/jupyterhub-on-google.conf>`_


R language
----------

Supported on:

* Ubuntu 16.04, 14.04
* Debian 8 ("jessie"), 9 ("stretch")
* CentOS 6.x and 7.x

==============  =======================================================
Ansible group   Action
==============  =======================================================
``r``           Install the interpreter and a basic libraries
                for the GNU `R language`_ and statistical system.
==============  =======================================================

This playbook installs the `R language`_ interpreter and a few
additional libraries.  R binaries installed by ElastiCluster come from
3rd-party repositories which (normally) provide more up-to-date
releases compared to the OS packages.

The following extra variables can be set to control installation of
additional R libraries:

===================== ========================== ==============================
Variable name         Default                    Description
===================== ========================== ==============================
``r_libraries``       ``[devtools]``             List of R packages to install
``r_cluster_support`` "yes" if installing R on   Whether to install ``Rmpi``
                      more then 1 node,          and other packages for
                      "no" otherwise             distributing work
                                                 across a computing cluster
===================== ========================== ==============================

By default, the ``devtools`` library is installed so that R packages
can be installed directly from their GitHub location.  Additionally, R
support for MPI and distribution of work across a cluster is available
if R support is being deployed to more than 1 host.

.. note::

   Note that the ``r_libraries`` variable is a *YAML list*.  In order
   to customize its value, you must provide a comma-separated list of
   library names, enclosed in square brackets.

   For instance, the following configuration snippet requests that
   ElastiCluster and Ansible install R libraries ``devtools`` and
   ``doSnow`` on the compute nodes of a SLURM cluster::

       [setup/slurm+r]
       # ...
       compute_groups=slurm_worker,r
       compute_r_libraries=[devtools,doSnow]


SAMBA
-----

Supported on:

* Ubuntu 16.04, 14.04
* Debian 8 ("jessie"), 9 ("stretch")
* CentOS 6.x and 7.x

==============  =======================================================
Ansible group   Action
==============  =======================================================
``samba``       Install and configure the SAMBA suite for serving
                local files over the network with the SMB/CIFS protocol
==============  =======================================================

This playbook installs the `SAMBA`_ server suite, which implements a
server for the SMB/CIFS network filesystem, plus other utilities for
integrating Linux/UNIX systems in a Windows environment.  Note that
ElastiCluster only configures the ``smbd`` daemon for serving files as
a "standalone SMB server" -- no other integration with Windows
services is included here.

The following extra variables can be set to control the way the SMB server is set up:

=================== ========================== =================================================
Variable name       Default                    Description
=================== ========================== =================================================
``smb_workgroup``   ``elasticluster``          NetBIOS workgroup name
``smb_shares``      *(no additional shares)*   Define additional SMB shares (see example below)
=================== ========================== =================================================

By default, ElastiCluster only configures sharing users' home
directories over SMB/CIFS.  Additional shares can be defined by adding
a ``smb_shares`` variable in the ``setup/`` section.  The value of
this variable should be a list (comma-separated, enclosed in ``[`` and
``]``) of share definitions; a share definition is enclosed in ``{``
and ``}`` and is comprised of comma-separated *key:value* pair; the
following *key:value* pair will be acted upon:

``name``
  The SMB share name; the string that clients must use to connect to this share

``path``
  Local path to the root directory being served

``readonly``
  Whether writes are allowed to the share.  If ``no`` (default), then no
  writes are allowed by any client.

``public``
  If ``yes``, any user that can connect to the server can read (and
  also write, depending on the ``readonly`` setting above) files in
  the share.  If ``no`` (default), only authenticated users can access
  the share.

For instance, the following ElastiCluster configuration snippet
configures two *additional* shares, one named ``public`` which serves
files off local path ``/data/public`` to any user who can connect, and
one named ``secret`` which serves files off local path
``/data/secret`` to authenticated users::

  [setup/samba]
  server_groups=samba
  server_smb_shares=[
    { name: 'public', path: '/data/public',  readonly: yes, public: yes },
    { name: 'secret', path: '/data/secret',  readonly: yes, public: no },
    ]
