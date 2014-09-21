========================================================================
    Elasticluster
========================================================================

.. This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information


`Elasticluster`_ aims to provide a user-friendly command line tool to
create, manage and setup computing clusters hosted on cloud
infrastructures (like `Amazon's Elastic Compute Cloud EC2`_ or `Google
Compute Engine`_)
or a private `OpenStack`_ cloud). Its main goal
is to get your own private cluster up and running with just a few commands; a `YouTube video`_
demoes the basic features of elasticluster. 

This project is an effort of the
`Grid Computing Competence Center`_ at the
`University of Zurich`_, licensed under the
`GNU General Public License version 3`_.

Documentation for elasticluster is available on the `Read The Docs
<http://elasticluster.readthedocs.org/>`_ website

Features
========

`Elasticluster`_ is in active development, but the following features at the current state:

* Simple configuration file to define cluster templates
* Can start and manage multiple independent clusters at the same time
* Automated cluster setup:
    * use `Debian GNU/Linux`_, `Ubuntu`_, or `CentOS`_ as a base operating system
    * choose `SLURM`_, `Grid Engine`_ or `TORQUE+MAUI`_ as a batch-queueing system
    * setup your `Hadoop`_ cluster to start your favorite map/reduce job
    * or create your `IPython cluster`_ to run your python code in
      parallel over multiple virtual machines
    * configure a distributed storage like `GlusterFS`_ or `Ceph`_, or a
      parallel filesystem like `OrangeFS`_ (formerly known as PVFS2)
    * add useful tools like `Ganglia`_ for monitoring...
    * ...or anything that you can install with an `Ansible`_ playbook!
* Grow and shrink a running cluster

`Elasticluster`_ is currently in active development: please use the
GitHub issue tracker to `file enhancement requests and ideas`_


Quickstart
==========

Installing from PyPI
--------------------

`Elasticluster`_ is a `Python`_ program; Python
version 2.6 is required to run it.

It's quite easy to install `elasticluster` using
`pip`_; the command below is all you
need to install `elasticluster` on your system::

    pip install elasticluster

If you want to run `elasticluster` from source you have to **install**
`Ansible`_ **first:**

::

    pip install ansible==1.3.3
    python setup.py install

Installing the development version from github
----------------------------------------------

The source code of elasticluster is `github`_, if you want to test the
latest development version you can clone the `github elasticluster repository`_.

You need the ``git`` command in order to be able to clone it, and we
suggest you to use `python virtualenv`_ in order to create a
controlled environment in which you can install elasticluster as
normal user. 

Assuming you already have ``virtualenv`` installed on your machine,
you first need to create a virtualenv and then install elasticluster::

    virtualenv elasticluster
    . elasticluster/bin/activate
    pip install git+https://github.com/gc3-uzh-ch/elasticluster.git

Now this will download and install ``elasticluster`` and all of its prerequisites into the current environtment

.. References

.. _`elasticluster`: http://gc3-uzh-ch.github.io/elasticluster/
.. _`Grid Computing Competence Center`: http://www.gc3.uzh.ch/
.. _`University of Zurich`: http://www.uzh.ch
.. _`GC3 Hobbes cloud`: http://www.gc3.uzh.ch/infrastructure/hobbes
.. _`configuration template`: https://raw.github.com/gc3-uzh-ch/elasticluster/master/docs/config.template.ini
.. _`GNU General Public License version 3`: http://www.gnu.org/licenses/gpl.html
.. _`YouTube video`: http://youtu.be/cR3C7XCSMmA

.. _`Amazon's Elastic Compute Cloud EC2`: http://aws.amazon.com/ec2/
.. _`Google Compute Engine`: https://cloud.google.com/products/compute-engine
.. _`OpenStack`: http://www.openstack.org/

.. _`Debian GNU/Linux`: http://www.debian.org
.. _`Ubuntu`: http://www.ubuntu.com
.. _`CentOS`: http://www.centos.org/
.. _`SLURM`: https://computing.llnl.gov/linux/slurm/
.. _`Grid Engine`: http://gridengine.info
.. _`TORQUE+MAUI`: http://www.adaptivecomputing.com/products/open-source/torque/
.. _`Hadoop`: http://hadoop.apache.org/
.. _`IPython cluster`: http://ipython.org/ipython-doc/dev/parallel/
.. _`Ganglia`: http://ganglia.info
.. _`GlusterFS`: http://www.gluster.org/
.. _`Ceph`: http://ceph.com/
.. _`OrangeFS`: http://orangefs.org/
.. _`Ansible`: http://ansible.cc 
.. _`file enhancement requests and ideas`: https://github.com/gc3-uzh-ch/elasticluster/issues

.. _`Python`: http://www.python.org
.. _`pip`: https://pypi.python.org/pypi/pip
.. _`github`: https://github.com/
.. _`github elasticluster repository`: https://github.com/gc3-uzh-ch/elasticluster
.. _`python virtualenv`: https://pypi.python.org/pypi/virtualenv

.. (for Emacs only)
..
  Local variables:
  mode: rst
  End:
