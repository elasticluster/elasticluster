elasticluster
=============

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

Documentation for elasticluster is available on the `Read The Docs
<http://elasticluster.readthedocs.org/>`_ website

Features
========

`elasticluster` is in active development, but the following features at the current state:

* Simple configuration file to define cluster templates
* Can start and manage multiple independent clusters at the same time
* Automated cluster setup:
    * use `Debian GNU/Linux`_, `Ubuntu`_, or `CentOS`_ as a base operating system
    * choose `SLURM`_, `Grid Engine`_ or `TORQUE+MAUI`_ as a batch-queueing system
    * add useful tools like `Ganglia`_ for monitoring...
    * ...or anything that you can install with an `Ansible`_ playbook!
* Grow and shrink a running cluster

`elasticluster` is currently in active development: please use the
GitHub issue tracker to `file enhancement requests and ideas`_


Quickstart
==========

Installing from PyPI
--------------------

`elasticluster` is a `Python`_ program; Python
version 2.6 is required to run it.

It's quite easy to install `elasticluster` using
`pip`_; the command below is all you
need to install `elasticluster` on your system::

    pip install elasticluster

If you want to run `elasticluster` from source you have to **install**
`Ansible`_ **first:**

::

    pip install ansible
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
you first need to create a virtualenv and install `ansible`, which is
needed by elasticluster::

    virtualenv elasticluster
    . elasticluster/bin/activate
    pip install ansible
    
Then you have to download the software. We suggest you to download it
*within* the created virtualenv::

    cd elasticluster
    git clone git://github.com/gc3-uzh-ch/elasticluster.git src
    cd src
    git submodule init
    git submodule update
    python setup.py install

Now the ``elasticluster`` should be available in your current
environment.

How to...
=========

Start a cluster
---------------

The `start` command performs the following tasks:

1. starts VM instances on the cloud provider specified in the
   configuration file (``[cloud/...]`` section);
2. sets up the instances as specified in the ``[setup/...]``
   configuration section (**warning:** this might take a **long** time);
3. Finally, it prints information about how to connect to the cluster
   frontend node.

The size of the cluster and the software installed on it are taken
from the ``[cluster/...]`` section in the configuration file.  Assuming
you have a Considering the ``cluster/mycluster`` section in the
configuration file, the following command will create a cluster with 1
frontend node and 2 compute nodes, and install the SLURM
batch-queueing system on it::

    elasticluster start mycluster

You can override parts of the configuration using command-line
options.  For example, the following invocation of `elasticluster`
creates a cluster using the ``cluster/mycluster`` configuration template
but with 10 compute nodes (instead of 2).

::

    elasticluster start mycluster --name my-other-cluster --compute-nodes 10

You will be later able to refer to this cluster with name
`my-other-cluster`.  If no `--name` option is given, the cluster gets the
name of its template: if your configuration file has a section
``[cluster/mycluster]`` and do not specify a name, the cluster will be
named `mycluster`.


The started clusters will be automatically configured with the given
`frontend_groups` and `compute_groups` in the ``setup/ansible`` section of
the configuration file. In this example `elasticluster` will configure
your cluster with the SLURM batch-queueing system.

Login into the cluster
----------------------

After a cluster has been started by `elasticluster`, some information
are printed to explain how to connect to the cluster. However, the
easiest way to connect to the frontend of the cluster is using the
`ssh` elasticluster command. The `ssh` command accepts a cluster name
as unique argument and will open an ssh connection to the frontend of
the cluster::

    elasticluster ssh my-other-cluster

Please note that in order this to work you **need** to have a working
version of the `ssh` command in your operating system. 

List your clusters
------------------

Use the following command to show all the running clusters::

    elasticluster list

List templates
--------------

To get a list of all configured cluster templates, run::

    elasticluster list-templates


List all nodes of a cluster
---------------------------

To list all nodes within a cluster `my-other-cluster`, run::

    elasticluster list-nodes my-other-cluster

Note that the cluster name is mandatory, even if you have started only
one cluster.   You can list the started cluster names with
`elasticluster list` (see above).


Grow a cluster
--------------

To grow a cluster by a certain number of compute nodes run::

    elasticluster resize my-other-cluster +10

This starts 10 new compute nodes on the cloud and set the nodes up
with the given configuration (see Section "Start a cluster" above).

Note that the cluster name is mandatory, even if you have started only
one cluster.   You can list the started cluster names with
`elasticluster list` (see above).


Shrink a cluster
----------------

**Shrinking a cluster will destroy the last-started node(s) of it.**
At the moment there is no code to determine what nodes could be safely
stopped.  Use the `shrink` functionality with caution, you have been warned!

The following command removes 1 compute node from cluster `my-other-cluster`::

    elasticluster resize my-other-cluster -1


Stop a cluster
--------------

To stop and destroy a cluster (named `my-other-cluster`), use the following
command::

    elasticluster stop my-other-cluster

This will destory all VMs of cluster `my-other-cluster`.

**After a cluster has been stopped it is lost forever.**  There is no
recovery or undo operation, so think twice before stopping the cluster.

.. _`Grid Computing Competence Center`: http://www.gc3.uzh.ch/
.. _`University of Zurich`: http://www.uzh.ch
.. _`GC3 Hobbes cloud`: http://www.gc3.uzh.ch/infrastructure/hobbes
.. _`configuration template`: https://raw.github.com/gc3-uzh-ch/elasticluster/master/docs/config.template.ini
.. _`GNU General Public License version 3`: http://www.gnu.org/licenses/gpl.html
.. _`YouTube video`: http://youtu.be/cR3C7XCSMmA

.. _`Amazon's Elastic Compute Cloud EC2`: http://aws.amazon.com/ec2/
.. _`OpenStack`: http://www.openstack.org/

.. _`Debian GNU/Linux`: http://www.debian.org
.. _`Ubuntu`: http://www.ubuntu.com
.. _`CentOS`: http://www.centos.org/
.. _`SLURM`: https://computing.llnl.gov/linux/slurm/
.. _`Grid Engine`: http://gridengine.info
.. _`TORQUE+MAUI`: http://www.adaptivecomputing.com/products/open-source/torque/
.. _`Ganglia`: http://ganglia.info
.. _`Ansible`: http://ansible.cc 
.. _`file enhancement requests and ideas`: https://github.com/gc3-uzh-ch/elasticluster/issues

.. _`Python`: http://www.python.org
.. _`pip`: https://pypi.python.org/pypi/pip
.. _`github`: https://github.com/
.. _`github elasticluster page`: https://github.com/gc3-uzh-ch/elasticluster
.. _`python virtualenv`: https://pypi.python.org/pypi/virtualenv
