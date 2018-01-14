========================================================================
    ElastiCluster |travis-ci-status| |gitter|
========================================================================

.. This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information

.. |travis-ci-status| image:: https://travis-ci.org/gc3-uzh-ch/elasticluster.svg?branch=master

.. |gitter| image:: https://badges.gitter.im/elasticluster/chat.svg
   :alt: Join the chat at https://gitter.im/elasticluster/chat
   :target: https://gitter.im/elasticluster/chat?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

ElastiCluster_ aims to provide a user-friendly command line tool to
create, manage and setup computing clusters hosted on cloud
infrastructures (like `Amazon's Elastic Compute Cloud EC2`_, `Google
Compute Engine`_, or a private OpenStack_ cloud). Its main goal is
to get your own private cluster up and running with just a few
commands; this video_ demoes ElastiCluster setting up a
computational batch-queueing cluster.

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
 * HPC clusters using SLURM_ or GridEngine_ (incl. support for CUDA-enabled GPUs);
 * Spark_ / Hadoop_ clusters with HDFS and Hive/SQL;
 * distributed storage clusters using GlusterFS_, OrangeFS_, or Ceph_;
 * ...or anything that you can install with an Ansible_ playbook!
* Growing and shrinking a running cluster.

ElastiCluster_ is currently in active development: please use the
GitHub issue tracker to file `enhancement requests and ideas`_,
or the `mailing-list`_ for discussion.

We appreciate pull requests for new features and enhancements. Please
use the *master* branch as starting point.


Quickstart
==========

The simplest way to run ElastiCluster is to use the official Docker
image.  If you cannot or want not to use Docker, please see alternate
installation instructions on `ElastiCluster's Read The Docs
<http://elasticluster.readthedocs.io/en/latest/install.html>`_ website.

To install ElastiCluster over Docker: (1) download the `elasticluster.sh`_ script
script into a file `elastiucluster.sh`, then (2) type this at your terminal
prompt::

    chmod +x elasticluster.sh

That's it!  You can now check that ElastiCluster is ready by running::

    elasticluster.sh --help

The first time it is run, the `elasticluster.sh`_ script will check if
Docker is installed, and ask for permission to install it if Docker is
not found. Follow the on-screen instructions; see section `Getting
Help`_ if you're in trouble.

You can also rename file ``elasticluster.sh`` to ``elasticluster``, if
you so like, to be consistent with the rest of the documentation.

.. _`elasticluster.sh`: https://raw.githubusercontent.com/gc3-uzh-ch/elasticluster/master/elasticluster.sh

Alternatively, you can also perform both steps at the terminal prompt::

    # use this if the `wget` command is installed
    wget -O elasticluster.sh https://raw.githubusercontent.com/gc3-uzh-ch/elasticluster/master/elasticluster.sh
    chmod +x elasticluster.sh

    # use this if the `curl` command is installed instead
    curl -O https://raw.githubusercontent.com/gc3-uzh-ch/elasticluster/master/elasticluster.sh
    chmod +x elasticluster.sh

Choose either one of the two methods above, depending on whether
``wget`` or ``curl`` is installed on your system (Linux systems
normally have ``wget``; MacOSX normally uses ``curl``).

After ElastiCluster is installed, run this command to deploy an `example
configuration file`_::

  elasticluster list-templates

The configuration file is located in `.elasticluster/config`; adjust it
to your liking using the `configuration reference`__.

.. __: http://elasticluster.readthedocs.io/en/master/configure.html


Getting help
============

For anything concerning ElastiCluster, including trouble running the
installation script, please send an email to
`elasticluster@googlegroups.com
<mailto:elasticluster@googlegroups.com>`_ or post a message on the web
forum `<https://groups.google.com/forum/#!forum/elasticluster>`_.
Include the full output of the script in your email, in order to help
us to identify the problem.


.. References

   References should be sorted by link name (case-insensitively), to
   make it easy to spot a missing or duplicate reference.

.. _`Amazon's Elastic Compute Cloud EC2`: http://aws.amazon.com/ec2/
.. _`Ansible`: https://ansible.com/
.. _`CentOS`: http://www.centos.org/
.. _`Ceph`: http://ceph.com/
.. _`Debian GNU/Linux`: http://www.debian.org
.. _`elasticluster`: http://gc3-uzh-ch.github.io/elasticluster/
.. _`example configuration file`: https://github.com/gc3-uzh-ch/elasticluster/raw/develop/elasticluster/share/etc/config.template
.. _`enhancement requests and ideas`: https://github.com/gc3-uzh-ch/elasticluster/issues
.. _`Ganglia`: http://ganglia.info
.. _`GC3 Hobbes cloud`: http://www.gc3.uzh.ch/infrastructure/hobbes
.. _`github elasticluster repository`: https://github.com/gc3-uzh-ch/elasticluster
.. _`github`: https://github.com/
.. _`GlusterFS`: http://www.gluster.org/
.. _`GNU General Public License version 3`: http://www.gnu.org/licenses/gpl.html
.. _`Google Compute Engine`: https://cloud.google.com/products/compute-engine
.. _`Grid Computing Competence Center`: http://www.gc3.uzh.ch/
.. _`GridEngine`: http://gridengine.info
.. _`Hadoop`: http://hadoop.apache.org/
.. _`IPython cluster`: http://ipython.org/ipython-doc/dev/parallel/
.. _`mailing-list`: https://groups.google.com/forum/#!forum/elasticluster
.. _`OpenStack`: http://www.openstack.org/
.. _`OrangeFS`: http://orangefs.org/
.. _`pip`: https://pypi.python.org/pypi/pip
.. _`python virtualenv`: https://pypi.python.org/pypi/virtualenv
.. _`Python`: http://www.python.org
.. _`Services and Support for Science IT`: http://www.s3it.uzh.ch/
.. _`Spark`: http://spark.apache.org/
.. _`SLURM`: https://slurm.schedmd.com/
.. _`TORQUE+MAUI`: http://www.adaptivecomputing.com/products/open-source/torque/
.. _`Ubuntu`: http://www.ubuntu.com
.. _`University of Zurich`: http://www.uzh.ch
.. _`video`: http://youtu.be/cR3C7XCSMmA

.. (for Emacs only)
..
  Local variables:
  mode: rst
  End:
