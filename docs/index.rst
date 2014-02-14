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

`elasticluster` aims to provide a user-friendly command line tool to
create, manage and setup computional clusters hosted on cloud
infrastructures (like `Amazon's Elastic Compute Cloud EC2`_, `Google
Compute Engine`_ or an `OpenStack`_ cloud). Its main goal is to get
your own private cluster up and running with just a few commands; a
`YouTube video`_ demoes the basic features of elasticluster.

This project is an effort of the
`Grid Computing Competence Center`_ at the
`University of Zurich`_, licensed under the
`GNU General Public License version 3`_.

----------
 Features 
----------

`elasticluster` is in active development, but the following features at the current state:

* Simple configuration file to define cluster templates
* Can start and manage multiple independent clusters at the same time
* Automated cluster setup:
    * use `Debian GNU/Linux`_, `Ubuntu`_, or `CentOS`_ as a base operating system
    * supports multiple batch systems, including `SLURM`_, `Grid
      Engine`_ or `Torque/PBS`_
    * supports `Hadoop`_ clusters
    * add useful tools like `Ganglia`_ for monitoring...
    * ...or anything that you can install with an `Ansible`_ playbook!
* Grow a running cluster

`elasticluster` is currently in active development: please use the
GitHub issue tracker to `file enhancement requests and ideas`_

--------------
 Architecture 
--------------

The architecture of elasticluster is quite simple: the configuration
file in ``~/.elasticluster/config`` defines a set of *cluster
configurations* and information on how to access a specific cloud
webservice (including access id and secret keys).

Using the command line (or, very soon, a simple API), you can start a
cluster and override some of the default values, like the number of
nodes you want to fire up. Elasticluster will use the `boto library`_
to connect to the desired cloud, start the virtual machines and wait
until they are accessible via ssh.

After all the virtual machines are up and running, elasticluster will
use `ansible`_ to configure them.

If you do a *resize* of the cluster (currently only growing a cluster
is fully supported) new virtual machines will be created and again
`ansible`_ will run for *all* of the virtual machines, in order to
properly add the new hosts to the cluster.


-------------------
 Table of Contents 
-------------------

.. toctree::  :maxdepth: 2

  install
  configure
  usage
  playbooks
  api/index

--------------------
 Indices and tables 
--------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _`YouTube video`: http://youtu.be/cR3C7XCSMmA
.. _`file enhancement requests and ideas`: https://github.com/gc3-uzh-ch/elasticluster/issues
