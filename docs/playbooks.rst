.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc

.. _playbooks:
  
============================================
  Playbooks distributed with elasticluster  
============================================

After the requested number of Virtual Machines have been started,
elasticluster uses `Ansible`_ to configure them based on the
configuration options defined in the configuration file.

We distribute a few playbooks together with elasticluster to configure
some of the most wanted clusters. The playbooks are available at the
``share/elasticluster/providers/ansible-playbooks/`` directory inside
your virtualenv if you installed using `pip`_, or in the
``elasticluster/providers/ansible-playbooks`` directory of the github
source code. You can copy, customize and redistribute them freely
under the terms of the GPLv3 license.

A list of the most used playbooks distributed with elasticluster and
some explanation on how to use them follows.

In some cases, extra variables can be set to playbooks to modify its
default behavior. In these cases, you can either define a variable
global to the cluster using::

    global_var_<varname>=<value>

or, if the variable must be defined only for a specific group of nodes::

    <groupname>_var_<varname>=<value>


Slurm
=====

Tested on:

* Ubuntu 14.04
* Ubuntu 12.04
* Ubuntu 13.04
* Debian 7.1 (GCE)

+------------------+--------------------------------------+
| ansible groups   | role                                 |
+==================+======================================+
|``slurm_master``  | Act as scheduler and submission host |
+------------------+--------------------------------------+
|``slurm_clients`` | Act as compute node                  |
+------------------+--------------------------------------+

This playbook will install the `SLURM`_ queue manager using the
packages distributed with Ubuntu and will create a basic, working
configuration.

You are supposed to only define one ``slurm_master`` and multiple
``slurm_clients``. The first will act as login node and will run the
scheduler, while the others will only execute the jobs.

The ``/home`` filesystem is exported *from* the slurm server to the compute nodes.

A *snippet* of a typical configuration for a slurm cluster is::

    [cluster/slurm]
    frontend_nodes=1
    compute_nodes=5
    ssh_to=frontend
    setup_provider=ansible_slurm
    ...

    [setup/ansible_slurm]
    frontend_groups=slurm_master
    compute_groups=slurm_clients
    ...

You can combine the slurm playbooks with ganglia. In this case the ``setup`` stanza will look like::

    [setup/ansible_slurm]
    frontend_groups=slurm_master,ganglia_master
    compute_groups=slurm_clients,ganglia_monitor
    ...

Extra variables can be set, by editing the `setup/` section:

+----------------------------------+-----------------+-------------------------------------------------+
| variable name                    | default         | description                                     |
+==================================+=================+=================================================+
| ``slurm_selecttype``             | `select/linear` | Value of `SelectType` in `slurm.conf`           |
+----------------------------------+-----------------+-------------------------------------------------+
| ``slurm_selecttypeparameters``   | `CR_Memory`     | Value of `SelectTypeParameters` in `slurm.conf` |
+----------------------------------+-----------------+-------------------------------------------------+

You may define them globally (e.g.
``global_var_slurm_selecctype=select/cons_res``) or only for a
specific group of nodes (e.g
``frontend_var_slurm_selecttype=select/cons_res``).


Gridengine
==========

Tested on:
 
* Ubuntu 12.04
* CentOS 6.3 (except for GCE images)
* Debian 7.1 (GCE)

+-----------------------+--------------------------------------+
| ansible groups        | role                                 |
+=======================+======================================+
|``gridengine_master``  | Act as scheduler and submission host |
+-----------------------+--------------------------------------+
|``gridengine_clients`` | Act as compute node                  |
+-----------------------+--------------------------------------+

This playbook will install `Grid Engine`_ using the packages
distributed with Ubuntu or CentOS and will create a basic, working
configuration.

You are supposed to only define one ``gridengine_master`` and multiple
``gridengine_clients``. The first will act as login node and will run the
scheduler, while the others will only execute the jobs.

The ``/home`` filesystem is exported *from* the gridengine server to
the compute nodes. If you are running on a CentOS, also the
``/usr/share/gridengine/default/common`` directory is shared from the
gridengine server to the compute nodes.

A *snippet* of a typical configuration for a gridengine cluster is::

    [cluster/gridengine]
    frontend_nodes=1
    compute_nodes=5
    ssh_to=frontend
    setup_provider=ansible_gridengine
    ...

    [setup/ansible_gridengine]
    frontend_groups=gridengine_master
    compute_groups=gridengine_clients
    ...

You can combine the gridengine playbooks with ganglia. In this case the ``setup`` stanza will look like::

    [setup/ansible_gridengine]
    frontend_groups=gridengine_master,ganglia_master
    compute_groups=gridengine_clients,ganglia_monitor
    ...

Please note that Google Compute Engine provides Centos 6.2 images with
a non-standard kernel which is **unsupported** by the gridengine
packages.

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


Hadoop
======

Tested on:

* Ubuntu 12.04
* CentOS 6.3
* Debian 7.1 (GCE)

+----------------------+-----------------------------------+
| ansible groups       | role                              |
+======================+===================================+
|``hadoop_namenode``   | Run the Hadoop NameNode service   |
+----------------------+-----------------------------------+
|``hadoop_jobtracker`` | Run the Hadoop JobTracker service |
+----------------------+-----------------------------------+
|``hadoop_datanode``   | Act as datanode for HDFS          |
+----------------------+-----------------------------------+
|``hadoop_tasktracker``| Act as tasktracker node accepting |
|                      | jobs from the JobTracker          |
+----------------------+-----------------------------------+

Hadoop playbook will install a basic hadoop cluster using the packages
available on the Hadoop website. The only supported version so far is
**1.1.2 x86_64** and it works both on CentOS and Ubuntu.

You must define only one ``hadoop_namenode`` and one
``hadoop_jobtracker``. Configuration in which both roles belong to the
same machines are not tested. You can mix ``hadoop_datanode`` and
``hadoop_tasktracker`` without problems though.

A *snippet* of a typical configuration for an Hadoop cluster is::

    [cluster/hadoop]
    hadoop-name_nodes=1
    hadoop-jobtracker_nodes=1
    hadoop-task-data_nodes=10
    setup_provider=ansible_hadoop
    ssh_to=hadoop-name
    ...

    [setup/ansible_hadoop]
    hadoop-name_groups=hadoop_namenode
    hadoop-jobtracker_groups=hadoop_jobtracker
    hadoop-task-data_groups=hadoop_tasktracker,hadoop_datanode
    ...

GlusterFS
=========

Tested on:

* Ubuntu 12.04
* CentOS 6.3

+--------------------+----------------------------------------------------+
| ansible groups     | role                                               |
+====================+====================================================+
| ``gluster_data``   | Run a gluster *brick*                              |
+--------------------+----------------------------------------------------+
| ``gluster_client`` | Install gluster client and install a gluster       |
|                    | filesystem on ``/glusterfs``                       |
+--------------------+----------------------------------------------------+

This will install a GlusterFS using all the ``gluster_data`` nodes as
*bricks*, and any ``gluster_client`` to mount this filesystem in
``/glusterfs``.

Setup is very basic, and by default no replicas is set.

To manage the gluster filesystem you need to connect to a
``gluster_data`` node.

Extra variables can be set, by editing the `setup/` section:

+----------------------+------------+-----------------------------------------+
| variable name        | default    | description                             |
+======================+============+=========================================+
| ``gluster_stripes``  | no stripe  | set the stripe value for default volume |
+----------------------+------------+-----------------------------------------+
| ``gluster_replicas`` | no replica | set replica value for default volume    |
+----------------------+------------+-----------------------------------------+

OrangeFS/PVFS2
==============

Tested on:

* Ubuntu 12.04

+-----------------+----------------------------------------------------+
| ansible groups  | role                                               |
+=================+====================================================+
|``pvfs2_meta``   | Run the pvfs2 metadata service                     |
+-----------------+----------------------------------------------------+
|``pvfs2_data``   | Run the pvfs2 data node                            |
+-----------------+----------------------------------------------------+
|``pvfs2_client`` | configure as pvfs2 client and mount the filesystem |
+-----------------+----------------------------------------------------+

The OrangeFS/PVFS2 playbook will configure a pvfs2 cluster. It
downloads the software from the `OrangeFS`_ website, compile and
install it on all the machine, and run the various server and client daemons.

In addiction, it will mount the filesystem in ``/pvfs2`` on all the clients.

You can combine, for instance, a SLURM cluster with a PVFS2 cluster::

    [cluster/slurm+pvfs2]
    frontend_nodes=1
    compute_nodes=10
    pvfs2-nodes=10
    ssh_to=frontend
    setup_provider=ansible_slurm+pvfs2
    ...

    [setup/ansible_slurm+pvfs2]
    frontend_groups=slurm_master,pvfs2_client
    compute_groups=slurm_clients,pvfs2_client
    pvfs-nodes_groups=pvfs2_meta,pvfs2_data
    ...

This configuration will create a SLURM cluster with 10 compute nodes,
10 data nodes and a frontend, and will mount the ``/pvfs2`` directory
from the data nodes to both the compute nodes and the frontend.

