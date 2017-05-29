.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc


.. _playbooks:

============================================
  Playbooks distributed with elasticluster
============================================

ElastiCluster uses `Ansible`_ to configure the VM cluster based on the
options read from the configuration file.  This chapter describes the
Ansible playbooks bundled [#]_ with ElastiCluster and how to
use them.

In some cases, extra variables can be set to playbooks to modify its
default behavior. In these cases, you can either define a variable
global to the cluster using::

    global_var_<varname>=<value>

or, if the variable must be defined only for a specific group of
hosts::

    <groupname>_var_<varname>=<value>


.. [#]

   The playbooks can be found in the ``elasticluster/share/playbooks``
   directory of the source code. You are free to copy,
   customize and redistribute them under the terms of the `GNU General
   Public License version 3`_ or (at your option) any later version.


Ansible
=======

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


SLURM
=====

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

You can combine the SLURM playbook with the Ganglia one; in this case
the ``setup`` stanza will look like::

    [setup/ansible_slurm]
    frontend_groups=slurm_master,ganglia_master
    compute_groups=slurm_worker,ganglia_monitor
    ...

Extra variables can be set by editing the `setup/` section:

================================== =================== =================================================
Variable name                      Default             Description
================================== =================== =================================================
``slurm_selecttype``               ``select/cons_res`` Value of `SelectType` in `slurm.conf`
``slurm_selecttypeparameters``     ``CR_Core_Memory``  Value of `SelectTypeParameters` in `slurm.conf`
``slurm_maxarraysize``             1000                Maximum size of an array job
``slurm_maxjobcount``              10000               Maximum nr. of jobs actively managed by the
                                                       SLURM controller (i.e., pending and running)
``multiuser_cluster``              yes                 Install NIS/YP
================================== =================== =================================================

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
==========

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


HTCondor
========

Tested on:

* Ubuntu 12.04

+-------------------+----------------------------------+
| ansible groups    | role                             |
+===================+==================================+
|``condor_master``  | Act as scheduler, submission and |
|                   | execution host.                  |
+-------------------+----------------------------------+
|``condor_workers`` | Act as execution host only.      |
+-------------------+----------------------------------+

This playbook will install the `HTCondor`_ workload management system
using the packages provided by the Center for High Throughput
Computing at UW-Madison.

The ``/home`` filesystem is exported *from* the condor master to the
compute nodes.

A *snippet* of a typical configuration for a slurm cluster is::

    [cluster/condor]
    setup_provider=ansible_condor
    frontend_nodes=1
    compute_nodes=2
    ssh_to=frontend
    ...

    [setup/ansible_condor]
    frontend_groups=condor_master
    compute_groups=condor_workers
    ...


Ganglia
=======

Tested on:

* Ubuntu 12.04
* CentOS 6.3
* Debian 7.1 (GCE)
* CentOS 6.2 (GCE)

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
===============

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


Hadoop + Spark
==============

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


GlusterFS
=========

Supported on:

* Ubuntu 14.04 and later
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

By default the volume is neither replicated nor striped, i.e., replica
and stripe number is set to 1.  This can be changed by defining the
following variables in the `setup/` section:

+----------------------+------------+-----------------------------------------+
| variable name        | default    | description                             |
+======================+============+=========================================+
| ``gluster_stripes``  | no stripe  | set the stripe value for default volume |
+----------------------+------------+-----------------------------------------+
| ``gluster_replicas`` | no replica | set replica value for default volume    |
+----------------------+------------+-----------------------------------------+

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

The "GlusterFS" playbook depends on the following Ansible roles being
available:

* `glusterfs-common <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/glusterfs-common>`_
* `glusterfs-client <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/glusterfs-client>`_
* `glusterfs-server <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks/roles/glusterfs-server>`_



OrangeFS/PVFS2
==============

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

Kubernetes
==========

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

SSH into the cluster and execute 'sudo kubectl --kubeconfig /etc/kubernetes/admin.conf get nodes' to view the cluster.
