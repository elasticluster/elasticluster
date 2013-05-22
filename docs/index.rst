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
create, manage and setup computing clusters hosted on cloud
infrastructures (like `Amazon's Elastic Compute Cloud EC2`_)
or a private `OpenStack`_ cloud). Its main goal
is to get your own private cluster up and running with just a few commands; a `YouTube video`_
demoes the basic features of elasticluster. 

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
    * choose `SLURM`_, `Grid Engine`_ or `Torque/PBS`_ as a batch-queueing system
    * add useful tools like `Ganglia`_ for monitoring...
    * ...or anything that you can install with an `Ansible`_ playbook!
* Grow and shrink a running cluster

`elasticluster` is currently in active development: please use the
GitHub issue tracker to `file enhancement requests and ideas`_


-------------------
 Table of Contents
-------------------

.. toctree::  :maxdepth: 2

  install
  configure
  usage
  playbooks
  customize


--------------------
 Indices and tables
--------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _`YouTube video`: http://youtu.be/cR3C7XCSMmA
.. _`file enhancement requests and ideas`: https://github.com/gc3-uzh-ch/elasticluster/issues
