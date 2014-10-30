.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc

=========
  Usage  
=========

The syntax of the elasticluster command is::

    elasticluster [-v] [-s PATH] [-c PATH] [subcommand] [subcommand args and opts]

The following options are general and are accepted by any subcommand:

``-h, --help``
    Show an help message and exits.

``-v, --verbose``
    Adding one or more `-v` will increase the verbosity. Usually
    elasticluster creates new VMs in parallel, to speedup the process,
    but if you run it with at least *four* `-v` options, elasticluster
    will not fork and will start the VMs sequentially. Useful for
    debugging.

``-s PATH, --storage PATH``

    Path to the storage folder.  This directory is used to store
    information about the cluster which are running. By default this
    is ``~/.elasticluster/storage`

    **WARNING**: If you delete this directory elasticluster will not
    be able to access the cluster anymore!

``-c PATH, --config PATH``

    Path to the configuration file. By default this is
    ``~/.elasticluster/config``. If a directory named ``<PATH>.d``
    (or, by default, ``~/.elasticluster/config.d``) exists, all files
    contained in that directory and ending in `.conf` are read too.


elasticluster provides multiple `subcommands` to start, stop, resize,
inspect your clusters. The available subcommands are:

**start**
    Create a cluster using one of the configured cluster tmplate.

**stop**
    Stop a cluster and all associated VM instances.

**list**
    List all clusters that are currently running.

**list-nodes**
    Show information about the nodes in a specific started cluster.

**list-templates** 
    Show the available cluster configurations, as defined in the
    configuration file.

**setup**
    Run ansible to configure the cluster.

**resize**
    Resize a cluster by adding or removing nodes.

**ssh** 
    Connect to the frontend of the cluster using the `ssh` command.

**sftp**
    Open an SFTP session to the cluster frontend host.

An help message explaining the available options and subcommand of
`elasticluster` is available by running::

    elasticluster -h

Options and arguments accepted by a specific subcommand `<cmd>` is
available by running::

    elasticluster <cmd> -h


The ``start`` command
---------------------

This command will start a new cluster using a specific cluster
configuration, defined in the configuration file. You can start as
many clusters you want using the same cluster configuration, by
providing different ``--name`` options.

Basic usage of the command is::

   usage: elasticluster start [-h] [-v] [-n CLUSTER_NAME]
                              [--nodes N1:GROUP[,N2:GROUP2,...]] [--no-setup]
                              cluster

``cluster`` is the name of a `cluster` section in the configuration
file. For instance, to start the cluster defined by the section
``[cluster/slurm]`` you must run the command::

    elasticluster start slurm

The following options are available:

``-h, --help``
    Show an help message and exits.

``-v, --verbose``
    Adding one or more `-v` will increase the verbosity accordingly.

``-n CLUSTER_NAME, --name CLUSTER_NAME``
    Name of the cluster. By default this is the same as the cluster
    configuration name.

``--nodes N1:GROUP[,N2:GROUP2,...]``

    This option allow you to override the values stored in the
    configuration file, by starting a different number of hosts fore
    each group.

    Assuming you defined, for instance, a cluster with the following
    type of nodes in the configuration file::

        hadoop-data_nodes=4
        hadoop-task_nodes=4

    and you want to run instead 10 data nodes and 10 task nodes, you
    can run elasticluster with option::

        elasticluster ... --nodes 10:hadoop-data,10:hadoop-task

``--no-setup``
    By default elasticluster will automatically run the **setup**
    command after all the virtual machines are up and running. This
    option prevent the `setup` step to be run and will leave the
    cluster unconfigured.


When you start a new cluster, elasticluster will:

* create the requested/configured number of virtual machines.
* wait until *all* the virtual machines are started.
* wait until `elasticluster` is able to connect to *all* the virtual
  machines using `ssh`.
* run ansible on all the virtual machines (unless ``--no-setup``
  option is given).

This process can take several minutes, depending on the load of the
cloud, the configuration of the cluster and your connection
speed. `Elasticluster` usually print very few information on what's
happening, if you run it with `-v` it will display a more verbose
output (including output of ansible command) to help you understanding
what is actually happening.

After the setup process is done a summary of the created cluster is
printed, similar to the following::

    Cluster name:     slurm
    Cluster template: slurm
    Frontend node: frontend001
    - compute nodes: 2
    - frontend nodes: 1

    To login on the frontend node, run the command:

        elasticluster ssh slurm

    To upload or download files to the cluster, use the command:

        elasticluster sftp slurm

The first line tells you the name of the cluster, which is the one you
are supposed to use with the **stop**, **list-nodes**, **resize**,
**ssh** and **sftp** commands.

The second line specifies the cluster configuration section used to
configure the cluster (in this case, for instance, the section
``[cluster/slurm]`` has been used)

The ``Frontend node`` line shows which node is used for the **ssh**
and **sftp** commands, when connecting to the cluster.

Then a list of how many nodes of each type have been started

The remaining lines describe how to connect to the cluster either
by opening an interactive shell to run commands on it, or an sftp
session to upload and download files.

The ``stop`` command
--------------------

The **stop** command will terminate all the instances running and
delete all information related to the cluster saved on the local disk.

**WARNING**: elasticluster doesn't do any kind of test to check if the
cluster is *used*!

Basic usage of the command is::

    usage: elasticluster stop [-h] [-v] [--force] [--yes] cluster

Like the **start** command, ``cluster`` is the name of a `cluster`
section in the configuration file.

The following options are available:

``-h, --help``
    Show an help message and exits.

``-v, --verbose``
    Adding one or more `-v` will increase the verbosity accordingly.

``--force``

    If some of the virtual machines fail to terminate (for instance
    because they have been terminated already not by elasticluster),
    this command will ignore these errors and will force termination
    of all the other instances.

``--yes``

    Since stopping a cluster is a possibly desruptive action,
    elasticluster will always ask for confirmation before doing any
    modification, unless this option is given.


The ``list`` command
--------------------

The **list** command print a list of all the cluster that have been
started. For each cluster, it will print a few information including
the cloud used and the number of nodes started for each node type::

    $ elasticluster list

    The following clusters have been started.
    Please note that there's no guarantee that they are fully configured:

    centossge 
    ---------
      name:           centossge
      template:       centossge
      cloud:          hobbes 
      - frontend nodes: 1
      - compute nodes: 2

    slurm 
    -----
      name:           slurm
      template:       slurm
      cloud:          hobbes 
      - frontend nodes: 1
      - compute nodes: 2

    slurm13.04 
    ----------
      name:           slurm13.04
      template:       slurm13.04
      cloud:          hobbes 
      - frontend nodes: 1
      - compute nodes: 2


The ``list-nodes`` command
--------------------------

The **list-nodes** command print information on the nodes belonging to
a specific cluster.

Basic usage of the command is::

    usage: elasticluster list-nodes [-h] [-v] [-u] cluster

``cluster`` is the name of a cluster that has been *started* previously.

The following options are available:

``-h, --help``
    Show an help message and exits.

``-v, --verbose``
    Adding one or more `-v` will increase the verbosity accordingly.

``-u, --update``

   By default ``elasticluster list-nodes`` will not contact the EC2
   provider to get up-to-date information, unless `-u` option is
   given.

Example::

    $ elasticluster list-nodes centossge

    Cluster name:     centossge
    Cluster template: centossge
    Frontend node: frontend001
    - frontend nodes: 1
    - compute nodes: 2

    To login on the frontend node, run the command:

        elasticluster ssh centossge

    To upload or download files to the cluster, use the command:

        elasticluster sftp centossge

    frontend nodes:

      - frontend001
        public IP:   130.60.24.61
        private IP:  10.10.10.36
        instance id: i-0000299f
        instance flavor: m1.small

    compute nodes:

      - compute001
        public IP:   130.60.24.44
        private IP:  10.10.10.17
        instance id: i-0000299d
        instance flavor: m1.small

      - compute002
        public IP:   130.60.24.48
        private IP:  10.10.10.29
        instance id: i-0000299e
        instance flavor: m1.small


The ``list-templates`` command
------------------------------

The **list-templates** command print a list of all the available
templates defined in the configuration file with a few information for
each one of them.

Basic usage of the command is::

    usage: elasticluster list-templates [-h] [-v] [clusters [clusters ...]]

`clusters` is used to limit the clusters to be listed and uses a
globbing-like pattern matching. For instance, to show all the cluster
templates that contains the word ``slurm`` in their name you can run
the following::

    $ elasticluster list-templates *slurm*
    11 cluster templates found.

    name:     aws-slurm
    cloud:     aws
    compute nodes: 2
    frontend nodes: 1

    name:     slurm
    cloud:     hobbes
    compute nodes: 2
    frontend nodes: 1

    name:     slurm_xl
    cloud:     hobbes
    compute nodes: 2
    frontend nodes: 1

    name:     slurm13.04
    cloud:     hobbes
    compute nodes: 2
    frontend nodes: 1


The ``setup`` command
---------------------

The **setup** command will run `ansible` on the desired cluster once
again. It is usually needed only when you customize and update your
playbooks, in order to re-configure the cluster, since the **start**
command already run `ansible` when all the machines are started.

Basic usage of the command is::

    usage: elasticluster setup [-h] [-v] cluster

``cluster`` is the name of a cluster that has been *started* previously.

The following options are available:

``-h, --help``
    Show an help message and exits.

``-v, --verbose``
    Adding one or more `-v` will increase the verbosity accordingly.


The ``resize`` command
----------------------

The **resize** command allow you to add or remove nodes from a started
cluster. Please, be warned that **this feature is still experimental**,
and while adding nodes is usually safe, removing nodes can be
desruptive and can leave the cluster in an unknwonw state.

Moreover, there is currently no way to decide *which nodes* can be
removed from a cluster, therefore if you shrink a cluster **you must
ensure** that any node of that type can be removed safely and no job
is running on it.

When adding nodes, you have to specify the *type* of the node and the
number of node you want to add. Then, elasticluster will basically
re-run the `start` and `setup` steps:

* create the requested/configured number of virtual machines.
* wait until *all* the virtual machines are started.
* wait until `elasticluster` is able to connect to *all* the virtual
  machines using `ssh`.
* run ansible on all the virtual machines, including the virtual
  machines already configured (unless ``--no-setup`` option is given).

Growing a cluster (adding nodes to the cluster) should be supported by
all the playbooks included in the elasticluster package.

Basic usage of the command is::

    usage: elasticluster resize [-h] [-a N1:GROUP1[,N2:GROUP2]]
                                [-r N1:GROUP1[,N2:GROUP2]] [-v] [--no-setup]
                                [--yes]
                                cluster

``cluster`` is the name of a cluster that has been *started* previously.

The following options are available:

``-h, --help``
    Show an help message and exits.

``-v, --verbose``
    Adding one or more `-v` will increase the verbosity accordingly.

``-a N1:GROUP1[,N2:GROUP2], --add N1:GROUP1[,N2:GROUP2]``

    This option allow you to specify how many nodes for a specific
    group you want to add. You can specify multiple nodes separated by
    a comma.

    Assuming you started, for instance, a cluster named `hadoop` using
    the default values stored in the configuration file::

        hadoop-data_nodes=4
        hadoop-task_nodes=4

    and assuming you want to *add* 5 more data nodes and 10 more task
    nodes, you can run::

        elasticluster resize -a 5:hadoop-data,10:hadoop-task

``-r N1:GROUP1[,N2:GROUP2], --remove N1:GROUP1[,N2:GROUP2]``

    This option allow you to specify how many nodes you want to remove
    from a specific group. It follows the same syntax as the ``--add``
    option.

    **WARNING**: elasticluster pick the nodes to remove at random, so
    **you have to be sure that any of the nodes can be
    removed**. Moreover, not all the playbooks support shrkinging!

``--no-setup``

    By default elasticluster will automatically run the **setup**
    command after starting and/or stopping the virtual machines. This
    option prevent the `setup` step to be run. **WARNING**: use this
    option wisely: depending on the cluster configuration it is
    impossible to know in advance what the status of the cluster will
    be after resizing it and NOT running the `setup` step.

``--yes``

    Since resizing a cluster, especially shrinking, is a possibly
    desruptive action and is not supported by all the distributed
    playbooks, elasticluster will always ask for confirmation before
    doing any modification, unless this option is given.


The ``ssh`` command
-------------------

After a cluster is started, the easiest way to login on it is by using
the **ssh** command. This command will run the `ssh` command with the
correct options to connect to the cluster using the configured values
for user and ssh key to use.

If no ``ssh_to`` option is specified in the configuration file, the
**ssh** command will connect to the first host belonging to the type
which comes first in alphabetic order, otherwise it will connect to
the first host of the group specified by the ``ssh_to`` option of the
``cluster`` section. However, running the command ``elasticluster
list-nodes <cluster>`` will show which host will be used as frontend
node.

The usage of the `ssh` command is as follow::

    elasticluster ssh <clustername> [ -- ssh arguments]

All the options and arguments following the ``--`` characters will be
passed directly to the ``ssh`` command.

For instance, if you just want to run the ``hostname -f`` command on
the frontend of the cluster you can run::

    elasticluster ssh <clustername> -- hostname -f

Note that elasticluster will save in
`~/.elasticluster/storage/<clustername>.known_hosts` the ssh host keys
of the VM instances after the first connection, and re-use them to
protect you from a Man-In-The-Middle attack. Therefore, the following
options are passed to `ssh` command line:

``-o UserKnownHostsFile=~/.elasticluster/storage/<clustername>.known_hosts``
    Use the generated known hosts file to protect against MIIT attacks.

``-o StrictHostKeyChecking=yes``
    Enable check of the host key of the remote machine.

The ``sftp`` command
-------------------

After a cluster is started, the easiest way to upload or download
files to and from the cluster is by using the **sftp** command. This
command will run the `sftp` command with the correct options to
connect to the cluster using the configured values for user and ssh
key to use.

If no ``ssh_to`` option is specified in the configuration file, the
**sftp** command will connect to the first host belonging to the type
which comes first in alphabetic order, otherwise it will connect to
the first host of the group specified by the ``ssh_to`` option of the
``cluster`` section. However, running the command ``elasticluster
list-nodes <cluster>`` will show which host will be used as frontend
node.

The usage of the `sftp` command is as follow::

    elasticluster sftp <clustername> [ -- sftp arguments]

All the options and arguments following the ``--`` characters will be
passed directly to the ``sftp`` command.

Note that elasticluster will save in
`~/.elasticluster/storage/<clustername>.known_hosts` the ssh host keys
of the VM instances after the first connection, and re-use them to
protect you from a Man-In-The-Middle attack. Therefore, the following
options are passed to `sftp` command line:

``-o UserKnownHostsFile=~/.elasticluster/storage/<clustername>.known_hosts``
    Use the generated known hosts file to protect against MIIT attacks.

``-o StrictHostKeyChecking=yes``
    Enable check of the host key of the remote machine.

