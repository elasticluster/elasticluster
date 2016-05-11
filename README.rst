========================================================================
    ElastiCluster |trevis-ci-status|
========================================================================

.. This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information

.. |trevis-ci-status| image:: https://travis-ci.org/gc3-uzh-ch/elasticluster.svg?branch=master


ElastiCluster_ aims to provide a user-friendly command line tool to
create, manage and setup computing clusters hosted on cloud
infrastructures (like `Amazon's Elastic Compute Cloud EC2`_, `Google
Compute Engine`_, or a private OpenStack_ cloud). Its main goal is
to get your own private cluster up and running with just a few
commands; this video_ demoes ElastiCluster setting up a
computational batch-queueing cluster.

Documentation for ElastiCluster is available on the `Read The Docs
<http://elasticluster.readthedocs.org/>`_ website.  General discussion
over ElastiCluster's usage, features, and bugs takes also place on the
`elasticluster@googlegroups.com
<https://groups.google.com/forum/#!forum/elasticluster>`_ mailing-list
(only subscribers can post).

This project is an effort of the `Services and Support for Science
IT`_ (S3IT) unit at the `University of Zurich`_, licensed under the
`GNU General Public License version 3`_.


Features
========

ElastiCluster_ is in active development, and offers the following
features at the moment:

* INI-style configuration file to define cluster templates
* Can start and manage multiple independent clusters at the same time
* Automated cluster setup:
    * use `Debian GNU/Linux`_, Ubuntu_, or CentOS_ as a base operating system
    * choose SLURM_, `Grid Engine`_ or `TORQUE+MAUI`_ as a batch-queueing system
    * setup your Hadoop_ cluster to start your favorite map/reduce job
    * or create your `IPython cluster`_ to run your python code in
      parallel over multiple virtual machines
    * configure a distributed storage like GlusterFS_ or Ceph_, or a
      parallel filesystem like OrangeFS_ (formerly known as PVFS2)
    * add useful tools like Ganglia_ for monitoring...
    * ...or anything that you can install with an Ansible_ playbook!
* Grow and shrink a running cluster

ElastiCluster_ is currently in active development: please use the
GitHub issue tracker to `file enhancement requests and ideas`_,
or the `mailing-list`_ for discussion.

We appreciate pull requests for new features and enhancements. Please
use the *develop* branch as starting point.


Quickstart
==========

Installing from PyPI
--------------------

ElastiCluster_ is a Python_ program; Python version 2.6 or 2.7 is
required to run it.

It's quite easy to install ElastiCluster using pip_; the command
below is all you need to install ElastiCluster on your system::

    pip install elasticluster


Installing the development version from GitHub
----------------------------------------------

The source code of elasticluster is on GitHub_, if you want to test
the latest development version you should clone the `github elasticluster
repository`_.

You need the ``git`` command in order to be able to clone it, and we
suggest you to use `python virtualenv`_ in order to create a
controlled environment in which you can install elasticluster as
normal user.

Assuming you already have ``virtualenv`` installed on your machine,
you first need to create a virtualenv::

    virtualenv elasticluster
    . elasticluster/bin/activate

Then you have to download the software. We suggest you to download it
*within* the created virtualenv::

    cd elasticluster
    git clone git://github.com/gc3-uzh-ch/elasticluster.git src
    cd src
    python setup.py install

Now the ``elasticluster`` command should be available in your current
environment.

.. References

.. _`elasticluster`: http://gc3-uzh-ch.github.io/elasticluster/
.. _`Grid Computing Competence Center`: http://www.gc3.uzh.ch/
.. _`Services and Support for Science IT`: http://www.s3it.uzh.ch/
.. _`University of Zurich`: http://www.uzh.ch
.. _`GC3 Hobbes cloud`: http://www.gc3.uzh.ch/infrastructure/hobbes
.. _`configuration template`: https://raw.github.com/gc3-uzh-ch/elasticluster/master/docs/config.template.ini
.. _`GNU General Public License version 3`: http://www.gnu.org/licenses/gpl.html
.. _`video`: http://youtu.be/cR3C7XCSMmA

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
.. _`Ansible`: https://github.com/ansible/ansible
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
