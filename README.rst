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
 * HPC clusters using SLURM_ or GridEngine_;
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

The 1.3 release is nearing, which has seen quite some changes from the
1.2 code that's on PyPI. For the moment, you are therefore encouraged to run the
`development code from GitHub`__ (click to see installation instructions) and
report on any bugs you find!

.. __: http://elasticluster.readthedocs.io/en/master/install.html#installing-development-code-from-github

**Note:** ElastiCluster_ is a Python_ program; Python version 2.6 or 2.7 is
required to run it. Python 3 is not (yet) supported.

After ElastiCluster is installed, run this command to deploy an `example
configuration file`_::

  elasticluster list-templates

The configuration file is located in `.elasticluster/config`; adjust it
to your liking using the `configuration reference`__.

.. __: http://elasticluster.readthedocs.io/en/master/configure.html


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
