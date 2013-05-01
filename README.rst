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

`elasticluster` is a `Python`_ program; Python
version 2.7 is required to run it.

It's quite easy to install `elasticluster` using
`pip`_; the command below is all you
need to install `elasticluster` on your system::

    pip install elasticluster

If you want to run `elasticluster` from source you have to **install**
`Ansible`_ **first:**

::

    pip install ansible
    python setup.py install


Configuration
-------------

After the software is installed you need to create a configuration
file. A fully-commented `configuration template`_
is available `here
<https://raw.github.com/gc3-uzh-ch/elasticluster/master/docs/config.template.ini>`_.

When `elasticluster` is run for the first time, it will copy the
`configuration template`_ to the default
configuration location ``~/.elasticluster/config.cfg``.

The following shows a basic configuration to connect to the
`GC3 Hobbes cloud`_;
please have a look at the `configuration template`_
for details and further options::

    [cloud/hobbes]
    provider=ec2_boto
    ec2_url=http://cloud.gc3.uzh.ch:8773/services/Cloud
    ec2_access_key=***fill in your data here***
    ec2_secret_key=***fill in your data here***
    ec2_region=nova

    [login/gc3-user]
    image_user=gc3-user
    image_user_sudo=root
    image_sudo=True
    user_key_name=***name of SSH keypair on Hobbes***
    user_key_private=~/.ssh/id_dsa
    user_key_public=~/.ssh/id_dsa.pub

    [cluster/mycluster]
    cloud=hobbes
    login=gc3-user
    setup_provider=my-slurm-cluster
    security_group=default
    image_id=ami-00000048
    flavor=m1.tiny
    frontend_nodes=1
    compute_nodes=2
    frontend_class=frontend
    image_userdata=

    [setup/my-slurm-cluster]
    provider=ansible
    playbook_path=%(ansible_pb_dir)s/site.yml
    frontend_groups=slurm_master
    compute_groups=slurm_clients

`elasticluster` looks for a configuration file named
``~/.elasticluster/config.cfg``; you can specify a different location
with the `-c` option: for example, `elasticluster -c
/path/to/another.cfg ...` makes `elasticluster` read the configuration
file ``/path/to/another.cfg``

When you are done configuring, you can start your first cluster with
`elasticluster`: read the "*Start a cluster*" section below!


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
