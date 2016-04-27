.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc

=================
  Configuration
=================

All the information about how to access a cloud provider and how to
setup a cluster is stored in a configuration file. The default
configuration file is stored in your home directory:
``~/.elasticluster/config`` but you can specify a different location
from the command line with the `-c` option.

In case the directory `~/.elasticluster/config.d` exists (or, if you
run with `-c <PATH>`, the directory `<PATH>.d`), all files named
`*.conf` contained in that directory are read and parsed. In this way,
you can handle multiple clusters easily by distributing the
configuration over multiple files, and disable only some of them by
renaming the files.

When `elasticluster` is run for the first time, if no configuration
file is found it will copy a `template configuration file`_ in
``~/.elasticluster/config``. Such template is fully commented and self
documented.

Therefore, after installing `elasticluster` for the first time, we
suggest to run the following command::

    elasticluster list-templates

If you don't already have a configuration file, this command will
create one for you. Of course, the file is not complete, as it does
not contain any authentication information, and you will get an error
similar to the following::

    WARNING:gc3.elasticluster:Deploying default configuration file to /home/antonio/.elasticluster/config.
    WARNING:gc3.elasticluster:Ignoring Cluster `ipython`: required key not provided @ data['image_user']
    WARNING:gc3.elasticluster:Ignoring cluster `ipython`.
    Error validating configuration file '/home/antonio/.elasticluster/config': `required key not provided @ data['image_user']`

In this case, you have to edit the configuration file in
``~/.elasticluster/config`` and update it with the correct values.

Please refer to the following section to understand the syntax of the
configuration file and to know which options you need to set in order
to use `elasticluster`.


Basic syntax of the configuration file
======================================

The file is parsed by ConfigParser module and has a syntax similar
to Microsoft Windows INI files.

It consists of `sections` led by a ``[sectiontype/name]`` header and
followed by lines in the form::

    key=value

Section names are in the form ``[type/name]`` wher `type` must be one of:

``cloud``
    define a cloud provider

``login``
    define a way to access a virtual machine

``setup``
    define a way to setup the cluster

``cluster``
  define the composition of a cluster. It contains references to
  the other sections.

``cluster/<clustername>``
  override configuration for specific group of nodes within a cluster

``storage``
  usually not needed, allow to specify a custom path for the storage
  directory and the default storage type.

You must define at least one for each section types in order to have
a valid configuration file.



Cloud Section
=============

A ``cloud`` section named ``<name>`` starts with::

  [cloud/<name>]

The cloud section defines all properties needed to connect to a
specific cloud provider.

You can define as many cloud sections you want, assuming you have
access to different cloud providers and want to deploy different
clusters in different clouds. The mapping between cluster and cloud
provider is done in the `cluster` section (see later).

Currently three cloud providers are available:

- openstack: supports OpenStack cloud
- boto: supports Amazon EC2 and compatible cloud
- google: supports Google Compute Engine

Therefore the following configuration option needs to be set in the cloud
section:

``provider``

    the driver to use to connect to the cloud provider.
    `ec2_boto`, `openstack` or `google`



Valid configuration keys for `boto`
-----------------------------------

``ec2_url``

    the url of the EC2 endpoint. For Amazon is probably
    something like::

        https://ec2.us-east-1.amazonaws.com

    replace ``us-east-1`` with the zone you want to use
    while for OpenStack you can get it from the web interface

``ec2_access_key``

    the access key (also known as access id) your cloud
    provider gave you to access its cloud resources.

``ec2_secret_key``

    the secret key (also known as secret id) your cloud
    provider gave you to access its cloud resources.

``ec2_region``

    the availability zone you want to use.

``vpc``

    the name or ID of the AWS Virtual Private Cloud to provision
    resources in.

``request_floating_ip``

    request assignment of a floating IP when the instance is
    started. Valid values: `True`, `False`.
    Some cloud providers does not automatically assign a public IP
    to the instances, but this is often needed if you want to connect
    to the VM from outside. Setting ``request_floating_ip`` to `True`
    will force `elasticluster` to request such a floating IP if the
    instance doesn't get one automatically.


Valid configuration keys for `google`
-------------------------------------

``gce_client_id``

    The API client id generated in the Google Developers Console

``gce_client_secret``

    The API client secret generated in the Google Developers Console

``gce_project_id``

    The project id of your Google Compute Engine project

``zone``

    The GCE zone to be used. Default is `us-central1-a`.

``network``

    The GCE network to be used. Default is `default`.


Valid configuration keys for *openstack*
----------------------------------------

``auth_url``:

    The URL of the keystone service (main entry point for OpenStack
    clouds). If an environment variable `OS_AUTH_URL` is set when
    elasticluster starts, the config option will be ignored and the
    value of the variable will be used instead.

``username``

    OpenStack username. If an environment variable `OS_USERNAME` is
    set when elasticluster starts, the config option will be ignored
    and the value of the variable will be used instead.

``password``

    OpenStack password. If an environment variable `OS_PASSWORD` is
    set when elasticluster starts, the config option will be ignored
    and the value of the variable will be used instead.

``project_name``

    OpenStack project to use (also known as `tenant`). If an
    environment variable `OS_TENANT_NAME` is set when elasticluster
    starts, the config option will be ignored and the value of the
    variable will be used instead.

``region_name``

    OpenStack region (optional)

``request_floating_ip``

    request assignment of a floating IP when the instance is
    started. Valid values: `True`, `False`.
    Some cloud providers does not automatically assign a public IP
    to the instances, but this is often needed if you want to connect
    to the VM from outside. Setting ``request_floating_ip`` to `True`
    will force `elasticluster` to request such a floating IP if the
    instance doesn't get one automatically.


Examples
--------

For instance, to connect to the `Hobbes private cloud
<http://hobbes.gc3.uzh.ch>`_ of the `University of Zurich`_ you can
use the following::

    [cloud/hobbes]
    provider=ec2_boto
    ec2_url=http://hobbes.gc3.uzh.ch:8773/services/Cloud
    ec2_access_key=****REPLACE WITH YOUR ACCESS ID****
    ec2_secret_key=****REPLACE WITH YOUR SECRET KEY****
    ec2_region=nova
    auto_ip_assignment=True

For Amazon instead (region us-east-1) you can use::

    [cloud/amazon-us-east-1]
    provider=ec2_boto
    ec2_url=https://ec2.us-east-1.amazonaws.com
    ec2_access_key=****REPLACE WITH YOUR ACCESS ID****
    ec2_secret_key=****REPLACE WITH YOUR SECRET KEY****
    ec2_region=us-east-1
    vpc=vpc-one

For Google Compute Engine you can use::

    [cloud/google]
    provider=google
    gce_client_id=****REPLACE WITH YOUR CLIENT ID****
    gce_client_secret=****REPLACE WITH YOUR SECRET KEY****
    gce_project_id=****REPLACE WITH YOUR PROJECT ID****

OpenStack users
+++++++++++++++

From the horizon web interface you can download a file containing your
EC2 credentials by logging into your provider web interface and
clicking on:

"*settings*"
  => "*EC2 Credentials*"
    => "*Download EC2 Credentials*"

The ``ec2rc.sh`` file will contain some values. Update the
configuration file:

* `ec2_url` using the value of the variable EC2_URL
* `ec2_access_key` using the value of the variable EC2_ACCESS_KEY
* `ec2_secret_key` using the value of the variable EC2_SECRET_KEY

Google Compute Engine users
+++++++++++++++++++++++++++
To generate a client_id and client_secret to access the Google Compute
Engine visit the following page:

  https://console.developers.google.com/project/_/apiui/credential

1. Select the project to be used for your cluster
2. If a "Client ID for native application" is listed on this page,
   skip to step 8
3. Under the OAuth section, click "Create new Client ID"
4. Select "Installed Application"
5. If prompted, click "Configure consent screen" and follow the
   instructions to set a "product name" to identify your Cloud
   project in the consent screen
6. In the Create Client ID dialog, be sure the following are selected::

    Application type: Installed application
    Installed application type: Other

7. Click the "Create Client ID" button
8. You'll see your Client ID and Client secret listed under
   "Client ID for native application"

Login Section
===============

A ``login`` section named ``<name>`` starts with::

    [login/<name>]

This section contains information on how to access the instances
started on the cloud, including the user and the SSH keys to use.

Some of the values depend on the image you specified in the
`cluster` section. Values defined here also can affect the `setup`
section and the way the system is setup.

Mandatory configuration keys
----------------------------

``image_user``

    the remote user you must use to connect to the virtual machine.
    In case you're using Google Compute Engine you have to set your username
    here. So if your gmail address is karl.marx@gmail.com,
    your username is karl.marx

``image_sudo``

    Can be `True` or `False`. `True` means that on the remote machine
    you can execute commands as root by running the `sudo` program.

``image_user_sudo``

    the login name of the administrator. Use `root` unless you know
    what you are doing...

``user_key_name``

    name of the *keypair* to use on the cloud provider. If the keypair
    does not exist it will be created by elasticluster.

``user_key_private``

    file containing a valid RSA or DSA private key to be used to
    connect to the remote machine. Please note that this must match
    the ``user_key_public`` file (RSA and DSA keys go in pairs). Also
    note that Amazon does not accept DSA keys but only RSA ones.

``user_key_public``

    file containing the RSA/DSA public key corresponding to the
    ``user_key_private`` private key. See ``user_key_private`` for more
    details.


Examples
--------

For a typical Ubuntu machine, both on Amazon and most OpenStack
providers, these values should be fine::

    [login/ubuntu]
    image_user=ubuntu
    image_user_sudo=root
    image_sudo=True
    user_key_name=elasticluster
    user_key_private=~/.ssh/id_rsa
    user_key_public=~/.ssh/id_rsa.pub

while for Hobbes appliances you will need to use the `gc3-user`
instead::

    [login/gc3-user]
    image_user=gc3-user
    image_user_sudo=root
    image_sudo=True
    user_key_name=elasticluster
    user_key_private=~/.ssh/id_rsa
    user_key_public=~/.ssh/id_rsa.pub


Setup Section
=============

A ``setup`` section named ``<name>`` starts with::

    [setup/<name>]

This section contain information on *how to setup* a cluster. After
the cluster is started, elasticluster will run a ``setup provider`` in
order to configure it.

Mandatory configuration keys
----------------------------

``provider``

    the type of setup provider. So far, only `ansible` is supported.

Ansible-specific mandatory configuration keys
----------------------------------------------

The following configuration keys are only valid if `provider` is
`ansible`.

``<class>_groups``

    Comma separated list of ansible groups the specific <class> will
    belong to. For each <class>_nodes in a [cluster/] section there
    should be a <class>_groups option to configure that specific class
    of nodes with the ansible groups specified.

    If you are setting up a standard HPC cluster you probably want to
    have only two main groups: `frontend_groups` and `compute_groups`.

    To configure a slurm cluster, for instance, you have the following
    available groups:

    ``slurm_master``
        configure this machine as slurm masternode

    ``slurm_clients``
        compute nodes of a slurm cluster

    ``ganglia_master``
        configure as ganglia web frontend.  On the
        master, you probably want to define `ganglia monitor` as well

    ``ganglia_monitor``
        configure as ganglia monitor.

    You can combine more groups together, but of course not all
    combinations make sense. A common setup is, for instance::

        frontend_groups=slurm_master,ganglia_master,ganglia_monitor
        compute_groups=slurm_clients,ganglia_monitor

    This will configure the frontend node as slurm master and ganglia
    frontend, and the compute nodes as clients for both slurm and
    ganglia frontend.

    A full list of the available groups is available at the
    `playbooks`:ref: page.

``<class>_var_<varname>``

    an entry of this type will define a variable called ``<varname>``
    for the specific ``<class>`` and add it to the ansible inventory
    file. Please refer to the documentation of the playbook
    ot know which variables you can set and its meaning.

``global_var_<varname>``

    An entry of this type will define a variable called ``<varname>``
    for all the nodes in the cluster, and add it to the ansible
    inventory file. Please refer to the documentation of the playbook
    ot know which variables you can set and its meaning.

``playbook_path``

    Path to the playbook to use when configuring the system. The
    default value printed here points to the playbook distributed with
    elasticluster. The default value points to the playbooks
    distributed with elasticluster.

``ansible_command``

    Path name of the ``ansible-playbook`` command; defaults to
    ``ansible-playbook``, i.e., search for the command named
    ``ansible-playbook`` in the shell search path.  Can also include
    arguments that will be *prepended* to other arguments that
    ElastiCluster adds to build the "setup" command invocation.

``ansible_extra_args``

    Arguments to *append* to the "setup" command invocation; can be used
    to override specific parameters or to further influence the
    behavior of the ``ansible-playbook`` command (e.g., skip certain tags).

    The string is split according to POSIX shell parsing rules, so
    quotes can be used to protect arguments with embedded spaces.

    Examples::

      [setup/ansible]
      # do not run any setup action tagged as 'users'
      ansible_extra_args = --skip-tags users

      [setup/ansible]
      # ask for confirmation at each step
      ansible_extra_args = --step

``ansible_<option>``
    Any configuration key starting with the string ``ansible_`` is
    used to set the corresponding (uppercased) environmental
    variable and thus override Ansible configuration.

    For example, the following settings raise the number of concurrent
    Ansible connections to 20 and allow a maximum waiting time of 300
    seconds for a single task to finish::

      [setup/ansible]
      # ...
      ansible_forks=20
      ansible_timeout=300

    The full list of environment variables used by Ansible is available
    from the `Ansible configuration`__ section of the Ansible online documentation.

    .. __: http://docs.ansible.com/ansible/intro_configuration.html#environmental-configuration


Examples
--------

Some (working) examples::

    [setup/ansible-slurm]
    provider=ansible
    frontend_groups=slurm_master
    compute_groups=slurm_clients

    [setup/ansible-gridengine]
    provider=ansible
    frontend_groups=gridengine_master
    compute_groups=gridengine_clients

    [setup/ansible-pbs]
    provider=ansible
    frontend_groups=pbs_master,maui_master
    compute_groups=pbs_clients

    [setup/ansible_matlab]
    # Please note that this setup assumes you already have matlab
    # installed on the image that is being used.
    provider=ansible
    frontend_groups=mdce_master,mdce_worker,ganglia_monitor,ganglia_master
    worker_groups=mdce_worker,ganglia_monitor


Cluster Section
===============

A ``cluster`` section named ``<name>`` starts with::

    [cluster/<name>]

The cluster section defines a `template` for a cluster. This section
has references to each one of the other sections and define the
image to use, the default number of compute nodes and the security
group.

Mandatory configuration keys
-----------------------------

``cloud``

    the name of a valid `cloud` section. For instance `hobbes` or
    `amazon-us-east-1`

``login``

    the name of a valid `login` section. For instance `ubuntu` or
    `gc3-user`

``setup_provider``

    the name of a valid `setup` section. For instance, `ansible-slurm`
    or `ansible-pbs`

``image_id``

    image id in `ami` format. If you are using OpenStack, you need to
    run `euca-describe-images` to get a valid `ami-*` id.

``flavor``

    the image type to use. Different cloud providers call it
    differently, could be `instance type`, `instance size` or
    `flavor`.

``security_group``

    Security group to use when starting the instance.

``<class>_nodes``

    the number of nodes of type ``<class>``. These configuration
    options will define the composition of your cluster. A very common
    configuration will include only two group of nodes:

    ``frontend_nodes``
        the queue manager and frontend of the cluster. You
        probably want only one.

    ``compute_nodes``
        the worker nodes of the cluster.

    Each ``<class>_nodes`` group is configured using the corresponding
    ``<class>_groups`` configuration option in the ``[setup/...]``
    section.

``ssh_to``

    `ssh` and `sftp` nodes will connect to only one node. This is the
    first of the group specified in this configuration option, or the
    first node of the first group in alphabetical order.  For
    instance, if you don't set any value for `ssh_to` and you defined
    two groups: `frontend_nodes` and `compute_nodes`, the ssh and sftp
    command will connect to `compute001` which is the first
    `compute_nodes` node. If you specify `frontend`, instead, it will
    connect to `frontend001` (or the first node of the `frontend`
    group).

Optional configuration keys
---------------------------

``image_userdata``

    shell script to be executed (as root) when the machine
    starts. This is usually not needed because the `ansible` provider
    works on *vanilla* images, but if you are using other setup
    providers you may need to execute some command to bootstrap it.

``network_ids``

    comma separated list of network or subnet IDs the nodes of the cluster
    will be connected to. Only supported when the cloud provider is
    `ec2_boto` or `openstack`

``<class>_min_nodes``

    Define the minimum amount of nodes of type `<class>` that must be
    up&running to configure the cluster. When starting a cluster,
    creation of some instances may fail. If at least min_nodes are
    started correctly (i.e. are not in error state), the cluster is
    configured anyway, otherwise creation of the cluster will fail.

``thread_pool_max_size``

    The maximum number of process to be created when virtual machines
    are started. Default is 10.

``boot_disk_type``
    Define the type of boot disk to use.
    Only supported when the cloud provider is `google`.
    Supported values are `pd-standard` and `pd-ssd`.
    Default value is `pd-standard`.

``boot_disk_size``
    Define the size of boot disk to use.
    Only supported when the cloud provider is `google`.
    Values are specified in gigabytes.
    Default value is 10.

``tags``
    Comma-separated list of instance tags.
    Only supported when the cloud provider is `google`.

``scheduling``
    Define the type of instance scheduling.
    Only supported when the cloud provider is `google`.
    Only supported value is `preemptible`.


Examples
--------

Some (working) examples::

    [cluster/slurm]
    cloud=hobbes
    login=gc3-user
    setup_provider=ansible-slurm
    security_group=default
    # Ubuntu image
    image_id=ami-00000048
    flavor=m1.small
    frontend_nodes=1
    compute_nodes=2
    frontend_class=frontend
    network_ids=subnet-one

    [cluster/torque]
    cloud=hobbes
    frontend_nodes=1
    compute_nodes=2
    frontend_class=frontend
    security_group=default
    # CentOS image
    image_id=ami-0000004f
    flavor=m1.small
    login=gc3-user
    setup_provider=ansible-pbs

    [cluster/aws-slurm]
    cloud=amazon-us-east-1
    login=ubuntu
    setup_provider=ansible-slurm
    security_group=default
    # ubuntu image
    image_id=ami-90a21cf9
    flavor=m1.small
    frontend=1
    compute=2

    [cluster/matlab]
    cloud=hobbes
    setup_provider=ansible_matlab
    security_group=default
    image_id=ami-00000099
    flavor=m1.medium
    frontend_nodes=1
    worker_nodes=10
    image_userdata=
    ssh_to=frontend


Cluster node section
====================

A `cluster node` for the node type ``<nodetype>`` of the cluster
``<name>`` starts with::

    [cluster/<name>/<nodetype>]

This section allows you to override some configuration values for
specific group of nodes. Assume you have a standard slurm cluster
with a frontend which is used as manager node and nfs server for the
home directories, and a set of compute nodes.

You may want to use different flavors for the frontend and the
compute nodes, since for the first you need more space and you don't
need many cores or much memory, while the compute nodes may requires
more memory and more cores but are not eager about disk space.

This is achieved defining, for instance, a `bigdisk` flavor (the
name is just fictional) for the frontend and `8cpu32g` for the
compute nodes. Your configuration will thus look like::

    [cluster/slurm]
    ...
    flavor=8cpu32g
    frontend_nodes=1
    compute_nodes=10

    [cluster/slurm/frontend]
    flavor=bigdisk


.. _`template configuration file`: https://raw.github.com/gc3-uzh-ch/elasticluster/master/docs/config.template

Storage section
===============

This section is used to customize the way elasticluster saves the
state of your clusters on disk.

By default, all persistent data is saved in
``~/.elasticluster/storage``. This include two main files for each cluster:

* ``<cluster>.yaml``: a file containing information about your cluster
* ``<cluster>.known_hosts``: a file containing the ssh host keys of
  the nodes of your cluster.

These files are very important, since if they are broken or missing,
elasticluster will **not** be able to recover any information about
your cluster.

In addition to these two files, the setup provider and the cloud
provider might create other files in the storage directory, but these
are not critical, as they are re-genereted if needed.

To change the default path to the storage directory you can create a
new `storage` section and set the ``storage_path`` value::

    [storage]
    storage_path = /foo/bar


By default the status of the cluster is saved in YAML_ format, but
also Pickle_ and Json_ formats are available. To save the cluster in a
different fromat, add the option ``storage_type``::

    [storage]
    storage_type = json

Please note that only newly created storage will honour this option!

.. _YAML: http://yaml.org/
.. _Pickle: http://en.wikipedia.org/wiki/Pickle_(Python)
.. _Json: http://json.org/
