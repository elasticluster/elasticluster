.. Hey Emacs, this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: ../global.inc


`elasticluster`
===============

Overview
--------

Elasticluster offers an API to programmatically manage compute clusters on
cloud infrastructure. This page introduces the basic concepts of the API and
provides sample code to illustrate the usage of the API. While this document
should provide you with the basics, more details can be found in the
respective module documentation

Getting Started
---------------

The following subchapters introduce the basic concepts of Elasticluster.

Cluster
~~~~~~~

This is the heart of elasticluster and handles all cluster relevant
behavior.  You can basically start, setup and stop a cluster. Also it
provides factory methods to add nodes to the cluster. A typical
workflow is as follows (see `slurm code example`_):

1. create a new cluster
2. add nodes to fit your computing needs
3. start cluster; start all instances in the cloud
4. setup cluster; configure all nodes to fit your computing cluster
5. ssh into a node to submit computing jobs
6. eventually stop cluster; destroys all instances in the cloud

See documentation of the :py:class:`~elasticluster.cluster.Cluster`
class for futher details.

Node
~~~~

The node represents an instance in a cluster. It holds all information to
connect to the nodes also manages the cloud instance. It provides the basic
functionality to interact with the cloud instance, such as start, stop,
check if the instance is up and ssh connect.

See the :py:class:`~elasticluster.cluster.Node` api docs for further details.


Cloud Provider
~~~~~~~~~~~~~~

Manages the connection to the cloud webservice and offers all functionality
used by the cluster to provision instances. Elasticluster offers two
different cloud providers at the current state:

* :py:class:`~elasticluster.providers.openstack.OpenStackCloudProvider`
    Cloud provider to connect to an OpenStack cloud.

* :py:class:`~elasticluster.providers.ec2_boto.BotoCloudProvider`
    Cloud provider to connect to EC2 compliant web services (e.g
    Amazon, Openstack, etc.)

* :py:class:`~elasticluster.providers.gce.GoogleCloudProvider` Cloud
    provider to connect to the Google Compute Engine (GCE)

All listed cloud providers above can be used to manage a cluster in the
cloud. If the cloud operator is not supported by the implementations above,
an alternative implementation can be provided by following the
:py:class:`~elasticluster.providers.AbstractCloudProvider` contract.


Setup Provider
~~~~~~~~~~~~~~

The setup provider configures in respect to the specified cluster and
node configuration. The basic implementation
:py:class:`~elasticluster.providers.ansible_provider.AnsibleSetupProvider`
uses ansible_ to configure the nodes. Ansible is a push based
configuration management system in which the configuration is stored
locally and pushed to all the nodes in the cluster.

See the :ref:`playbooks` page for more
details on the cluster setups possible with the ansible implementation
and how the ansible playbooks can be enhanced.

If this implementation does not satisfy the clients needs,
an alternative implementation can be implemented following the
:py:class:`~elasticluster.providers.AbstractSetupProvider` contract.


Cluster Repository
~~~~~~~~~~~~~~~~~~

The cluster repository is responsible to keep track of multiple clusters
over time. Therefore Elasticluster provides two implementations:

    * :py:class:`~elasticluster.repository.MemRepository`
        Stores the clusters in memory. Therefore after stopping a program
        using this repository, all clusters are not recoverable but possibly
        still running.

    * :py:class:`~elasticluster.repository.PickleRepository`
        Stores the cluster on disk persistently. This implementation uses
        pickle to serialize and deserialize the cluster.

If a client wants to store the cluster in a database for example,
an alternative implementation can be provided following the
:py:class:`~elasticluster.repository.AbstractClusterRepository` contract.


Sample Code
-----------

.. _`slurm code example`:

Start and setup a SLURM cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following sample code shows how to start and setup a SLURM cluster on an
OpenStack cloud and provides further information on each step. Other cluster
types on other cloud providers can be setup accordingly.

::

    import elasticluster

    # Initialise an EC2 compatible cloud provider, in this case an OpenStack
    # cloud operator is chosen. To initialise the cloud provider the
    # following parameters are passed:
    #   url:        url to connecto to the cloud operator web service
    #   region:     region to start the nodes on
    #   access_key: access key of the current user to connect
    #   secret_key: secret key of the current user to connect
    cloud_provider = elasticluster.BotoCloudProvider(
                                            'http://uzh.ch/services/Cloud',
                                            'nova', 'access_key', 'secret_key')

    # Initialising the setup provider needs a little more preparation:
    # the groups dictionary specifies the kind of nodes used for this cluster.
    # In this case we want a frontend and a compute kind. The frontend node
    # (s) will be setup as slurm_master, the compute node(s) as slurm_worker.
    # This corresponds to the documentation of the ansible playbooks
    # provided with elasticluster. The kind of the node is a name specified
    # by the user. This name will be used to set a new hostname on the
    # instance, therefore it should meet the requirements of RFC 953
    # groups['kind'] = ['andible_group1', 'ansible_group2']
    groups = dict()
    groups['frontend'] = ['slurm_master']
    groups['compute'] = ['slurm_worker']

    setup_provider = elasticluster.AnsibleSetupProvider(groups)

    # cluster initialisation (note: ssh keys are same for all nodes)
    # After the steps above initialising an empty cluster is a peace of cake.
    # The cluster takes the following arguments:
    # name:           name to identify the cluster
    #   cloud_provider: cloud provider to connect to cloud
    #   setup_provider: setup provider to configure the cluster
    #   ssh_key_name:   name of the ssh key stored (or to be stored) on the
    #                   cloud
    #   ssh_key_pub:    path to public ssh key file
    #   ssh_key_priv:   path to private ssh key file
    #
    # The ssh key files are used for all instances in this cluster.
    cluster = elasticluster.Cluster('my-cluster', cloud_provider,
                                    setup_provider, 'ssh_key_name',
                                    '~/ssh/keys/my_ssh_key.pub',
                                    '~/ssh/keys/my_ssh_key')

    # To add nodes to the cluster we can use the add_node. This
    # only initialises a new node, but does not start it yet.
    # The add node function is basically a factory method to make it easy to
    # add nodes to a cluster. It takes the following arguments:
    #   kind:   kind of the node in this cluster. This corresponds to the
    #           groups defined in the cloud_provider.
    cluster.add_node('frontend', 'ami-00000048', 'gc3-user',
                     'm1.tiny', 'all_tcp_ports')

    # We can also add multiple nodes with the add_nodes method.
    # The following command will add 2 nodes of the kind `compute` to the
    # cluster
    cluster.add_nodes('compute', 2, 'ami-00000048', 'gc3-user', 'm1.tiny',
                      'all_tcp_ports')

    # Since we initialised all the nodes for this computing cluster,
    # we can finally start the cluster.
    # The start method is blocking and does the following tasks:
    #   * call the cloud provider to start an instance for each node in a
    #     seperate thread.
    #   * to make sure elasticluster is not stopped during creation of an
    #     instance, it will overwrite the sigint handler
    #   * waits until all nodes are alive (meaning ssh connection
    #     works)
    #   * If the startup timeout is reached and not all nodes are alive,
    #     the cluster will stop and destroy all instances
    cluster.start()

    # Now, all the nodes are started and we can call the setup method to
    # configure slurm on the nodes.
    cluster.setup()


Asynchronous node start
~~~~~~~~~~~~~~~~~~~~~~~

The :py:meth:`~elasticluster.cluster.Cluster.start()` method of the
:py:meth:`~elasticluster.cluster.Cluster` class is blocking and therefore waits until all nodes
are alive. If a client wants to use this time for other tasks,
the nodes can as well be started asynchronous::

    # retrieve all nodes from the cluster
    nodes = cluster.get_all_nodes()

    # start each node
    # The start method on the node is non blocking and will return as soon
    # as the cloud provider is contacted to start a new instance
    for node in nodes:
        node.start()

    # wait until all nodes are alive
    starting_nodes = nodes[:]
    while starting_nodes:
        starting_nodes = [n for n in starting_nodes if not n.is_alive()]


Storing a cluster on disk
~~~~~~~~~~~~~~~~~~~~~~~~~

By default elasticluster will store the cluster in memory only. Therefore
after a programm shutdown the cluster will not be available anymore in
elasticluster, but might still be running on the cloud. The following
example shows how to store clusters on disk to retrieve after a programm
restart::

    # The cluster repository uses pickle to store clusters each in a
    # seperate file in the provided storage directory.
    repository = elasticluster.PickleRepository('/path/to/storage/dir')

    # On cluster initialisation we can pass the repository as optional
    # argument.
    cluster = elasticluster.Cluster('my-cluster', cloud_provider,
                                    setup_provider, 'ssh_key_name',
                                    '~/ssh/keys/my_ssh_key.pub',
                                    '~/ssh/keys/my_ssh_key',
                                    repository=repository)

    # When starting the cluster, it will safe its state using the repository.
    cluster.start()

After a program shutdown we can therefore fetch the cluster from the
repository again and work with it as expected::

    repository = elasticluster.PickleRepository('/path/to/storage/dir')

    # retrieve the cluster from the repository
    cluster = repository.get('my-cluster')

    # or retrieve all clusters that are stored in the repository
    clusters = repository.get_all()


Logging
~~~~~~~

Elasticluster uses the python `logging` module to log events. A client can
overwrite the settings as illustrated below::

    import logging

    import elasticluster

    log = elasticluster.log
    level = logging.getLevelName('INFO')
    log.setLevel(level)

The current example only shows how to increase the log level,
but any settings can be applied compliant with the logging module of python.

.. automodule:: elasticluster
    :members:
