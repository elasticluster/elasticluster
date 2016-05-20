.. elasticluster documentation master file, created by
   sphinx-quickstart on Wed May 22 11:39:55 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc


=============================================
  Welcome to elasticluster's documentation!
=============================================

--------------
 Introduction
--------------

ElastiCluster_ aims to provide a user-friendly command line tool to
create, manage and setup computing clusters hosted on cloud
infrastructures (like `Amazon's Elastic Compute Cloud EC2`_, `Google
Compute Engine`_, or a private OpenStack_ cloud). Its main goal is to
get a private cluster up and running with just a few commands; this
video_ demoes ElastiCluster setting up a computational batch-queueing
cluster.

Complete documentation for ElastiCluster is available on the `Read The
Docs <http://elasticluster.readthedocs.org/>`_ website.  General
discussion over ElastiCluster's usage, features, and bugs takes place
on the `elasticluster@googlegroups.com
<https://groups.google.com/forum/#!forum/elasticluster>`_ mailing-list
(only subscribers can post).

The ElastiCluster_ project is an effort of the `Services and Support
for Science IT`_ (S3IT) unit at the `University of Zurich`_, licensed
under the `GNU General Public License version 3`_.


Features
========

ElastiCluster_ is in active development, and offers the following
features at the moment:

* INI-style configuration file to define cluster templates
* Can start and manage multiple independent clusters at the same time
  * Automated setup of:

  - HPC clusters using SLURM_ or GridEngine_;
  - Spark_ / Hadoop_ clusters with HDFS and Hive/SQL;
  - distributed storage clusters using GlusterFS_, OrangeFS_, or Ceph_;
  - ...or anything that you can install with an Ansible_ playbook!

* Growing and shrinking a running cluster.

ElastiCluster_ is currently in active development: please use the
GitHub issue tracker to `file enhancement requests and ideas`_,
or the `mailing-list`_ for discussion.

We appreciate pull requests for new features and enhancements. Please
use the *master* branch as starting point.


----------
 Overview
----------

The architecture of elasticluster is quite simple: the `configuration
file`_ ``~/.elasticluster/config`` defines a set of *cluster
configurations* and information on how to access a specific cloud
service (including access id and secret keys).

Using the command line or a simple API_, you can start a cluster
(possibly overriding some of the default values, like the number of
nodes you want to fire up) and configure it:

* ElastiCluster_ connects to the cloud provider indicated in the
  cluster configuration file, starts virtual machines, and waits until
  they are accessible via ssh.

* After all the VMs are up and running, ElastiCluster runs `Ansible`_
  to configure the cluster.

Upon *resize* of the cluster [#grow-mostly]_, new virtual machines will
be created and again `Ansible`_ will run on *all* the VMs, in order to
properly add the new hosts to the cluster.

ElastiCluster commands `export`_ and `import`_ allow moving a
running cluster's definition and status data from one machine to the
other, to allow controlling the same cluster from different places.

.. _`api`: http://elasticluster.readthedocs.io/en/master/api/index.html
.. _`configuration file`: http://elasticluster.readthedocs.io/en/master/configure.html
.. _`export`: http://elasticluster.readthedocs.io/en/master/usage.html#the-export-command
.. _`import`: http://elasticluster.readthedocs.io/en/master/usage.html#the-import-command

.. [#grow-mostly] Currently, only growing a cluster is fully
   supported; shrinking a loaded cluster may remove nodes with running
   jobs and cause malfunctionings.  See the ``remove-node`` command
   for a safer, albeit more low-level, way of shrinking clusters.


-------------------
 Table of Contents
-------------------

.. toctree::  :maxdepth: 2

  install
  configure
  usage
  troubleshooting
  playbooks
  api/index


--------------------
 Indices and tables
--------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _`video`: http://youtu.be/cR3C7XCSMmA
.. _`file enhancement requests and ideas`: https://github.com/gc3-uzh-ch/elasticluster/issues
