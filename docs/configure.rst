.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc


.. configuration:

=================
  Configuration
=================

All the information about how to access a cloud provider and how to
setup a cluster is stored in a configuration file. The default
configuration file is stored in your home directory:
``~/.elasticluster/config`` but you can specify a different location
from the command line with the `-c` option.

If directory `~/.elasticluster/config.d` exists (or, if you run
``elasticluster`` with option `-c <PATH>`, the directory `<PATH>.d`),
all files named `*.conf`:file: contained in that directory are read and
parsed. In this way, you can handle multiple clusters easily by
distributing the configuration over multiple files, and disable only
some of them by renaming the files.

After installing ElastiCluster for the first time, we suggest you run
the following command::

    elasticluster list-templates

If no configuration file is found, it will copy an `example
configuration file`_ in `~/.elasticluster/config`:file:. The example is
fully commented and self-documenting.

However, the example configuration file is not complete, as it does
not contain any authentication information, so you will get an error
similar to the following::

    WARNING:gc3.elasticluster:Deploying default configuration file to /home/antonio/.elasticluster/config.
    WARNING:gc3.elasticluster:Ignoring Cluster `ipython`: required key not provided @ data['image_user']
    WARNING:gc3.elasticluster:Ignoring cluster `ipython`.
    Error validating configuration file '/home/antonio/.elasticluster/config': `required key not provided @ data['image_user']`

You will have to edit the configuration file in
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

Section names have the form ``[type/name]`` where `type` is one of:

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

A valid configuration file must contain at least one section for each
of the ``cloud``, ``login``, ``cluster``, and ``setup`` sections.


Processing of configuration values
==================================

Within each ``key=value`` assignment, the *value* part undergoes the following
transformations:

* References to enviromental variables of the form ``$VARNAME`` or
  ``${VARNAME}`` are replaced by the content of the named environmental
  variable, wherever they appear in a *value*.

  For instance, the following configuration snippet would set the OpenStack user
  name equal to the Linux user name on the computer where ElastiCluster is
  running::

      [cloud/openstack]
      username = $USER
      # ...

* The following special strings are substituted, wherever they appear in a
  *value*:

  ==============================  ====================================================
  this string ...                 ... expands to:
  ==============================  ====================================================
  ``${elasticluster_playbooks}``  Path to the root directory containing
                                  the Ansible playbooks distributed with ElastiCluster
  ``${ansible_pb_dir}``           Deprecated alias for ``${elasticluster_playbooks}``
  ==============================  ====================================================

* Within values that name a file or path name, a ``~`` character at the
  beginning of the path name is substituted with the path to the user's home
  directory.  (In fact, this is a shorthand for ``$HOME/``)


Cloud Section
=============

A ``cloud`` section named ``<name>`` starts with::

  [cloud/<name>]

The cloud section defines all properties needed to connect to a
specific cloud provider.

You can define as many cloud sections you want, assuming you have
access to different cloud providers and want to deploy different
clusters in different clouds. The mapping between cluster and cloud
provider is done in a ``cluster`` section (see below).

Currently these cloud providers are available:

- ``ec2_boto``: supports Amazon EC2 and compatible clouds
- ``google``: supports Google Compute Engine
- ``libcloud``: support `many cloud providers`__ through `Apache LibCloud`_
- ``openstack``: supports OpenStack-based clouds

.. __: https://libcloud.readthedocs.io/en/latest/supported_providers.html

Therefore the following configuration option needs to be set in the cloud
section:

``provider``

    the driver to use to connect to the cloud provider:
    ``ec2_boto``, ``openstack``, ``google`` or ``libcloud``.

    .. note::

       The LibCloud provider can also provision VMs on EC2, Google Compute
       Engine, and OpenStack. The native drivers can however offer functionality
       that is not available through the generic LibCloud driver. Feedback is
       welcome on the ElastiCluster `mailing-list`_.


Valid configuration keys for `ec2_boto`
---------------------------------------

``ec2_url``
    URL of the EC2 endpoint. For Amazon EC2 it is probably
    something like::

        https://ec2.us-east-1.amazonaws.com

    (replace ``us-east-1`` with the zone you want to use).

``ec2_access_key``
    the access key (also known as *access ID*) your cloud
    provider gave you to access its cloud resources.

``ec2_secret_key``
    the secret key (also known as *secret ID*) your cloud
    provider gave you to access its cloud resources.

``ec2_region``
    the availability zone you want to use.

``vpc``
    name or ID of the AWS Virtual Private Cloud to provision
    resources in.

``request_floating_ip``
    request assignment of a public IPv4 address when the instance is
    started. Valid values are ``yes`` (or ``True`` or ``1``) and
    ``no`` (or ``False`` or ``0``; default).  Please see
    `<http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-instance-addressing.html#concepts-public-addresses>`_
    regarding Amazon EC2's assignment of public IPv4
    addresses. Setting ``request_floating_ip`` to ``yes`` will force
    `elasticluster` to request a public IPv4 address if the instance
    doesn't get one automatically.

``price``
    If set to a non-zero value, ElastiCluster will allocate `spot
    instances`_ with a price less than or equal to the value given
    here.  Note that there is currently no way to specify a currency:
    the amount is expressed in whatever currency_ is default in the
    Boto API (typically, US Dollars).

    .. _`spot instances`: https://aws.amazon.com/ec2/spot/

    .. _`currency`: http://boto.cloudhackers.com/en/latest/ref/mturk.html#module-boto.mturk.price

    Defaults to 0, i.e., use regular non-spot instances.

    This is typically best used in a *compute node* configuration
    section (see an example in the `example configuration file`_); you
    probably do not want to run login, file server or similar central
    services on a spot instance (which can be terminated any time,
    depending on spot price bid).


``timeout``
    Maximum amount of seconds to wait for a spot instance to become
    available; if a request for a spot instance cannot be satisfied in
    the given time, the instance startup process aborts.  If set to 0
    (default), then wait indefinitely.

    **Note:** Ignored if ``price`` is zero (default).


``instance_profile``
     Name of an `IAM instance profile`_ that contains roles allowing
     EC2 instances to have specified privileges. For example, you can
     allow EC2 instances to access S3 without passing credentials in.

     .. _`iam instance profile`: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html


Valid configuration keys for `google`
-------------------------------------

``gce_client_id``
    The API client ID generated in the Google Developers Console

``gce_client_secret``
    The API client secret generated in the Google Developers Console

``gce_project_id``
    The project ID of your Google Compute Engine project

``zone``
    The GCE zone to be used. Default is ``us-central1-a``.

``network``
    The GCE network to be used. Default is ``default``.


Obtaining your ``gce_client_id`` and ``gce_client_secret``
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Find the ``gce_client_id`` and ``gce_client_secret`` values by
following instructions at:
`<http://googlegenomics.readthedocs.io/en/latest/use_cases/setup_gridengine_cluster_on_compute_engine/index.html#index-obtaining-client-id-and-client-secrets>`_


Valid configuration keys for *libcloud*
----------------------------------------

``driver_name``:

  Name of the driver you want to configure (provider you want to connect with);
  it has to be one of the strings listed in column "Provider constant" in
  LibCloud's `Provider Matrix`__ (which see for all supported providers).

  .. __: https://libcloud.readthedocs.io/en/latest/supported_providers.html#provider-matrix

Other configuration keys are provider-dependent; ElastiCluster configuration
items map 1-1 to LibCloud "NodeDriver" instanciation parameters, both in name
and in type.

For example, to configure an Azure connection, go to the page
https://libcloud.readthedocs.io/en/latest/compute/drivers/azure.html and check
what the *Instantiating a driver* section states: you would need to
configure the keys ``subscription_id`` and ``key_file``.

A few examples for providers supported through LibCloud are given in the table
below:

==========  =======================================  ========================
Provider    Additional arguments                     Example
==========  =======================================  ========================
Azure       key_file, subscription_id                \
                                                     ``subscription_id=...``
                                                     ``key_file=/path/to/azure.pem``
CloudSigma  username, password, region, api_version  \
                                                     ``username=user``
                                                     ``password=pass``
                                                     ``region=zrh``
                                                     ``api_version=2.0``
CloudStack  apikey, secretkey, host, path            \
                                                     ``apikey=key``
                                                     ``secretkey=secret``
                                                     ``host=example.com``
                                                     ``path=/path/to/api``
ExoScale    key, secret, host, path                  \
                                                     ``key=key``
                                                     ``secret=secret``
                                                     ``host=example.com``
                                                     ``path=/path/to/api``
LibVirt     uri                                      \
                                                     ``uri=qemu:///system``
RackSpace   username, apikey, region                 \
                                                     ``username=user``
                                                     ``apikey=key``
                                                     ``region=iad``
vSphere     host, username, password                 \
                                                     ``host=192.168.1.100``
                                                     ``username=user``
                                                     ``password=pass``
==========  =======================================  ========================


Valid configuration keys for *openstack*
----------------------------------------

.. _`*openstack* command`: https://docs.openstack.org/python-openstackclient/latest/cli/man/openstack.html#manpage

``auth_url``
  URL of the OpenStack Identity service (aka *Keystone*, main entry
  point for OpenStack clouds), same as option ``--os-auth-url`` of the
  `*openstack* command`_. If the environment variable ``OS_AUTH_URL``
  is set, this option is ignored and the value of the environment
  variable is used instead.

``identity_api_version``
  Force use of the OpenStack Identity ("Keystone") API v2 or v3.  (Use
  the values ``2`` or ``3`` respectively.)  If this configuration item
  is not specified, ElastiCluster will try v3 and then v2.  If
  environment variable ``OS_IDENTITY_API_VERSION`` is set, this option
  is ignored and the value of the environment variable is used
  instead.

``username``
  OpenStack user name, same as option ``--os-username`` of the
  `*openstack* command`_. If an environment variable ``OS_USERNAME`` is
  set, this option is ignored and the value of the environment
  variable is used instead.

``user_domain_name``
  OpenStack user domain.  This is mandatory for
  Identity API v3.  The default value is ``default``. If the
  environment variable ``OS_USER_DOMAIN_NAME`` is set, this option is
  ignored and the value of the environment variable is used instead.

``password``
  OpenStack password, same as option ``--os-password`` of the
  `*openstack* command`_. If an environment variable ``OS_PASSWORD`` is
  set, this option is ignored and the value of the environment
  variable is used instead.

``project_name``
  OpenStack project to use (formerly known as "tenant"), same as
  option ``--os-project-name`` of the `*openstack* command`_. If an
  environment variable ``OS_PROJECT_NAME`` or ``OS_TENANT_NAME`` is
  set, this option is ignored and the value of the environment
  variable is used instead.

``project_domain_name``
  OpenStack project domain.  This is mandatory for Identity API v3.
  The default value is ``default``. If the environment variable
  ``OS_PROJECT_DOMAIN_NAME`` is set, this option is ignored and the
  value of the environment variable is used instead.

``region_name``
  OpenStack region. This is optional; not all OpenStack clouds require
  it and there is no widespread default: region names are arbitrary
  strings set by the OpenStack cloud administrators. Ask your local
  OpenStack support for valid values. If environment variable
  ``OS_REGION_NAME`` is set, this option is ignored and the value of
  the environment variable is used instead.

``request_floating_ip``
  request assignment of a "floating IP" when the instance is
  started. Valid values are ``yes`` (or ``True`` or ``1``) and ``no``
  (or ``False`` or ``0``; default).  Some cloud providers do not
  automatically assign a public IP to the instances, but this is often
  needed if you want to connect to the VM from outside. Setting
  ``request_floating_ip`` to ``yes`` will force `elasticluster` to
  request such a floating IP if the instance doesn't get one
  automatically.


Examples
--------

For instance, to connect to Amazon's EC2 (region ``us-east-1``) you can use::

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

If you would want to use libcloud to connect to openstack using password authentication
you can configure the following::

    [cloud/libcloud]
    provider=libcloud
    driver_name=openstack
    auth_url=**** YOUR AUTH URL ****
    ex_tenant_name=**** YOUR TENANT NAME ****
    ex_force_auth_version=2.0_password
    username=**** YOUR USERNAME ****
    password=**** YOUR PASSWORD ****

A larger set of commented examples can be found at:
`<https://github.com/gc3-uzh-ch/elasticluster/tree/master/examples>`_


Login Section
===============

A ``login`` section named ``<name>`` starts with::

    [login/<name>]

This section contains information on how to access the instances
started on the cloud, including the user and the SSH keys to use.

Some of the values depend on the image you specified in the
`cluster` section. Values defined here also can affect the `setup`
section and the way the system is setup.

Configuration keys
------------------

``image_user``
  login name used to SSH into the virtual machine. In case you're
  using Google Compute Engine you have to set your user name here.  So
  if your GMail address is ``karl.marx@gmail.com``, use ``karl.marx``
  as value of ``image_user``.

``image_sudo``
  Boolean value: ``yes`` (or ``True`` or ``1``; default) means that on
  the remote machine the ``image_user`` can execute commands as root
  by running the ``sudo`` program.

  .. warning::

     ElastiCluster makes the assumption that this value is always true
     and will not work correctly otherwise.  This configuration item
     will be removed in a future version of ElastiCluster (as there is
     really no option).

``image_user_sudo``
  login name of the "super user". This is optional, and defaults to
  `root`.  There is little reason to ever change this value from the
  default.

``user_key_name``
  name of the *keypair* to use on the cloud provider. If the
  (pre-generated) keypair does not exist on the cloud platform, it
  will be added by ElastiCluster, uploading the public SSH key pointed
  to by ``user_key_public`` (see below).

``user_key_private``
  file containing a valid SSH private key to be used to connect
  to the virtual machine. Please note that this must match the
  ``user_key_public`` file (SSH keys always come in pairs).

  .. note::

     Currently ElastiCluster only supports RSA and DSA key types.
     Pull requests to add support for more modern SSH key types are
     very welcome.

``user_key_public``
  file containing the RSA/DSA public key corresponding to the
  ``user_key_private`` private key file. See ``user_key_private`` for
  more details.


Examples
--------

For a typical Ubuntu VM, on either Amazon EC2 or most OpenStack
providers, these values should be fine::

    [login/ubuntu]
    image_user=ubuntu
    image_user_sudo=root
    image_sudo=True
    user_key_name=elasticluster
    # these paths should point to the SSH key file used to log in to VMs
    user_key_private=~/.ssh/id_rsa
    user_key_public=~/.ssh/id_rsa.pub

For Google Compute Engine, something like the following should be
used instead::

    [login/google]
    image_user=****REPLACE WITH YOUR GOOGLE USERID (just the userid, not email)****
    image_sudo=yes
    user_key_name=elasticluster
    # You can generate the keypair with the command: `gcloud compute config-ssh`
    user_key_private=~/.ssh/google_compute_engine
    user_key_public=~/.ssh/google_compute_engine.pub

In contrast to other cloud providers, GCE creates a personal account on each
VM so you effectively re-use the same `[login/google]` section across
different VM images.

A larger set of commented examples can be found at:
`<https://github.com/gc3-uzh-ch/elasticluster/tree/master/examples>`_


Setup Section
=============

A ``setup`` section named ``<name>`` starts with::

    [setup/<name>]

This section contain information on *how to setup* a cluster. After
the cluster is started, elasticluster will run a ``setup provider`` in
order to configure it.

A ``setup`` section is mostly independent of any other, and can be
easily re-used across multiple clouds and base OS images -- that's the
whole point of ElastiCluster!


General configuration keys
--------------------------

``provider``
    Type of the setup provider. So far, ``ansible`` is the only valid value
    (and, obviously, the default)


Controlling what is installed on the nodes
------------------------------------------

``<class>_groups``
    Comma separated list of Ansible groups nodes of kind *class* will
    belong to. For each ``<class>_nodes`` in a ``[cluster/...]``
    section there should be a corresponding ``<class>_groups`` option
    to include that specific class of nodes in the given Ansible
    groups.

    For example, to set up a standard HPC cluster you probably want to
    define only two main kinds of nodes: ``frontend_groups`` (for the
    master/control server) and ``compute_groups`` (for the compute
    nodes).  A common setup for a SLURM cluster is::

        frontend_groups=slurm_master,ganglia_master,ganglia_monitor
        compute_groups=slurm_worker,ganglia_monitor

    This will configure the ``frontend001`` node as SLURM master and
    Ganglia collector and frontend, and the ``computeXXX`` nodes as
    SLURM executors and Ganglia ``gmond`` sources.

    Ansible group names supported by ElastiCluster can be found in the
    Playbooks_ section of this manual.  You can combine more groups
    together, separating the names with a comma (``,``) -- but of
    course not all combinations make sense.

    .. warning::

       Any group name that is not supported by ElastiCluster playbooks
       will (silently) be ignored, so watch out for typos!

``<class>_var_<varname>``
    Define an variable called ``<varname>`` that applies only to the
    given node ``<class>``. See the Playbooks_ section to know which
    variables can be set and their meaning.

``global_var_<varname>``
    Define a variable called ``<varname>`` that applies to all the
    nodes in the cluster.  See the Playbooks_ section to know which
    variables can be set and their meaning.

``playbook_path``
    Path to the Ansible playbook file to use when running
    ``elasticluster setup``.  The default value is to use playbook
    ``site.yml`` in the root directory of the distributed with
    ElastiCluster.


Controlling Ansible invocation
------------------------------

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

``ansible_ssh_pipelining``
    Enable or disable SSH pipelining when setting up the
    cluster. Enabled by default, as it improves connection
    speed. Incompatible with some base OS'es, notoriously CentOS6.
    Setting this to ``no``/``false``/``0`` disables it.

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

    The full list of environment variables used by Ansible is available from the
    `Ansible configuration`__ section of the Ansible online documentation.
    Invoking ``elasticluster setup`` with highest verbosity (e.g., ``-vvv``)
    will dump the entire environment that Ansible is being called with to the
    DEBUG-level log.

    .. __: http://docs.ansible.com/ansible/intro_configuration.html#environmental-configuration

    .. note::

       Any ``ANSIBLE_*`` variables defined in the environment take precedence
       over what is defined in the ``[setup/*]`` section. Care must be taken
       when overriding some variables, particularly ``ANSIBLE_ROLES_PATH``,
       which contain paths and references to parts of ElastiCluster: if those
       paths are missing from the replaced value, a number of fatal errors can
       happen.

``ssh_pipelining``
  **Deprecated.**  Use ``ansible_ssh_pipelining`` instead.


Examples
--------

A ``setup`` section is mostly independent of any other, and can be
easily re-used across multiple clouds and base OS images -- that's the
whole point of ElastiCluster!

The following shows how to set up a simple SoGE_ cluster using the
Playbooks_ distributed with ElastiCluster::

  [setup/gridengine]
  provider=ansible
  frontend_groups=gridengine_master
  compute_groups=gridengine_clients

This example shows how to combine multiple Ansible groups into a class
of nodes; namely, install Ganglia_ alongside with PBS/TORQUE::

  [setup/pbs]
  provider=ansible
  frontend_groups=pbs_master,ganglia_master
  compute_groups=pbs_worker,ganglia_monitor

This final example shows how variables can be used to customize or set
options in the playbooks.  Specifically, the example shows how to
install NIS/YP to easily manage users across the cluster::

  [setup/slurm]
  # provider=ansible is the default
  frontend_groups=slurm_master
  compute_groups=slurm_worker

  # install NIS/YP to manage cluster users
  global_var_multiuser_cluster=yes

A larger set of commented examples can be found at:
`<https://github.com/gc3-uzh-ch/elasticluster/tree/master/examples>`_


Cluster Section
===============

The ``cluster`` section named ``<name>`` starts with::

    [cluster/<name>]

A cluster section defines a "template" for a cluster. This section
has references to each one of the other sections and define the
image to use, the default number of compute nodes and the security
group.

Some configuration keys can be overridden for specific node kinds.
The way to do this is to create a section named like this::

    [cluster/<name>/<kind>]

Any configuration specified in this section would take precedence over
the values given in section ``[cluster/<name>]``, but only for nodes
of class ``<kind>``.

For example: assume you have a standard SLURM cluster with a frontend
which is used as master node and NFS server for the home directories,
and a set of compute nodes.  You may want to use different VM flavors
for the frontend and the compute nodes, since for the first you need
more space and you don't need many cores or much memory, while the
compute nodes may requires more memory and more cores but are not
eager about disk space.  If your cloud provided, e.g., a ``bigdisk``
flavor for VMs with a large root disk space, and a ``hpc`` flavor for
VMs optimized for running computational jobs, you could use the former
for the frontend node and the latter for the compute nodes. Your
configuration will thus look like::

    [cluster/slurm]
    # ...
    flavor=hpc
    frontend_nodes=1
    compute_nodes=10

    [cluster/slurm/frontend]
    flavor=bigdisk

    [cluster/slurm/compute]
    # the following setting is (implicitly) inherited
    # from the `[cluster/slurm]` section
    #flavor=hpc

.. _`template configuration file`: https://raw.github.com/gc3-uzh-ch/elasticluster/master/elasticluster/share/etc/config.template


Cluster-wide configuration keys
-------------------------------

The following configuration keys can only be specified in a top-level
``[cluster/...]`` section (i.e., *not* in node-level
``[cluster/.../node]`` override).

``cloud``
    Name of a valid ``cloud`` section.

``login``
    Name of a valid ``login`` section. For instance ``ubuntu`` or
    ``google-login``.

``setup``
    Name of a valid ``setup`` section.

``<class>_nodes``
   the number of nodes of type ``<class>``. These configuration
   options will define the composition of your cluster.
   Each ``<class>_nodes`` group is configured using the corresponding
   ``<class>_groups`` configuration option in the ``[setup/...]``
   section.

``<class>_min_nodes`` (optional)
    **Deprecated.** Please rename to ``<class>_nodes_min``.

``<class>_nodes_min`` (optional)
    Minimum amount of nodes of type ``<class>`` that must be up &
    running in order to start configuring the cluster.

    When running ``elasticluster start`` to start a cluster, creation
    of some instances may fail; if at least this amount of nodes are
    started correctly (i.e. are not in error state), the cluster is
    configured anyway. Otherwise, the ``start`` command will fail.

``ssh_to``
    Which class of nodes to SSH into, when running
    ``elasticluster ssh`` or ``elasticluster sftp``.

    Commands ``elasticluster ssh`` and ``elasticluster sftp`` need to
    single out one node from the cluster, and connect to it via
    SSH/SFTP.  This parameter can specify:

    * either a node name (e.g., `master001`) which will be the target
      of SSH/SFTP connections, or
    * a node class name (e.g., `frontend`): the first node in that
      class will be the target.

    If ``ssh_to`` is not specified, ElastiCluster will try the class
    names ``ssh``, ``login``, ``frontend``, and ``master`` (in this
    order).  If the cluster has no node in all these classes, then the
    first found node is used.

``thread_pool_max_size`` (optional)
    Maximum number of Python worker threads to create for starting VMs
    in parallel.  Default is 10.


Overridable configuration keys
------------------------------

The following configuration keys can appear in a top-level
``[cluster/...]`` section, as well as in a node-level
``[cluster/.../node]`` override.  Configuration keys specified in a
node-level section take precedence over cluster-wide ones.

``flavor``
   The VM "size" to use. Different cloud providers call it
   differently: could be "instance type", "instance size" or "flavor".
   This setting can be overwritten in the Cluster Node section,
   e.g. to use fewer resources on the frontend nodes than on the
   compute nodes.

``image_id``
   Image ID to use as a base for all VMs in this cluster
   (unless later overridden for a class of nodes, see below).  Actual
   format is cloud specific: OpenStack uses UUIDs
   (e.g. `2bf3baba-35c8-4e20-9cc9-b36808720c9b`), Amazon EC2 uses IDs
   like `ami-123456`. For Google Compute Engine you can also use a
   URL of a private image; run ``gcloud compute images describe
   <your_image_name>``:file: to show the selfLink URL to use.

``image_userdata`` (optional)
    Shell script to be executed (as root) when the machine
    starts. This can happen before ElastiCluster even gets a
    chance to connect to the VM.

``network_ids`` (optional)
    Comma separated list of network or subnet IDs the nodes of the cluster
    will be connected to. Only supported when the cloud provider is
    ``ec2_boto`` or ``openstack``.

``security_group``
    Security group to use when starting the instance.

    .. note::

       On Amazon EC2, the *default* security group only allows network
       communication among hosts in the group and does *not* allow SSH
       connections from the outside.  This will make ElastiCluster
       fail as it cannot connect to the cluster nodes (see, e.g.,
       `issue #490`__).  You will need to add a rule to the *default*
       security group to allow SSH connections from the network where
       you run ElastiCluster, or create a new security group which
       allows SSH and use that.

       .. __: https://github.com/gc3-uzh-ch/elasticluster/issues/490



Additional optional configuration keys for Amazon EC2
-----------------------------------------------------

Options ``price`` and ``timeout`` (see their documentation in the
"ec2_boto" cloud provider section) can be specified here as
well, to place nodes on spot instances.


Additional optional configuration keys for Google Cloud
-------------------------------------------------------

``boot_disk_type``
    Define the type of boot disk to use.  Supported values are
    ``pd-standard`` (default) and ``pd-ssd``.

``boot_disk_size``
    Define the size of boot disk to use; values are specified in gigabytes.
    Default value is 10.

``tags``
    Comma-separated list of instance tags.

``scheduling``
    Define the type of instance scheduling.
    Only supported value is ``preemptible``.


Additional optional configuration keys for OpenStack clouds
-----------------------------------------------------------

``boot_disk_type``
    Define the type of boot disk to use.  Supported values are types
    available in the OpenStack volume ("cinder") configuration.

    When using this option for OpenStack, it creates volumes to be used
    as the root disks for the VM's of the specified size, when terminating
    and instance the volume will be deleted automatically. Always specify
    the ``boot_disk_size`` when using this with OpenStack.

``boot_disk_size``
    Define the size of boot disk to use.  Values are specified in
    gigabytes.  There is no default; this option is mandatory of
    ``boot_disk_type`` is also specified.


Examples
--------

This basic example shows how to set up a SoGE_ cluster on Google
Cloud.  (The example assumes that sections ``[setup/gridengine]``,
``[cloud/google]`` and ``[login/google]`` have been defined elsewhere
in the configuration file.)

::

  [cluster/gridengine-on-gce]
  setup=gridengine
  frontend_nodes=1
  compute_nodes=2

  # this is cloud specific
  cloud=google
  security_group=default
  flavor=n1-standard-1

  image_id=****REPLACE WITH OUTPUT FROM: gcloud compute images list | grep debian | cut -f 1 -d " "****

  # on GCE, all images can use the same `login` section
  login=google

The following slightly more complex example shows how to set up a TORQUE
cluster on a OpenStack cloud, using different VM flavors for the
front-end node (less CPU and larger disk) and compute nodes (more CPU
and memory).

The rationale behind this configuration is as follows: for the
front-end node more space is needed (since it's the NFS server for the
whole cluster) and you don't need many cores or much memory, while the
compute nodes may requires more memory and more cores but are not
eager about disk space.  If your cloud provided, e.g., a "big disk"
flavor for VMs with a large root disk space, and a "hpc" flavor for
VMs optimized for running computational jobs, you could use the former
for the frontend node and the latter for the compute nodes. Your
configuration will thus look like the following::

   [cluster/torque]
   setup=pbs
   frontend_nodes=1
   compute_nodes=8

   # this is cloud-specific info (using OpenStack for the example)
   cloud=openstack
   network_ids=eaf06405-6dc2-43d1-9d5a-18bb266e36a8
   security_group=default

   # CentOS 7.4
   image_id=bab386b3-2c21-4a67-a146-a658668ac096

   # `login` info is -in theory- image-specific
   login=centos

   [cluster/torque/frontend]
   # front-end has less CPU and RAM but more disk
   flavor=2cpu-4ram-largedisk

   [cluster/torque/compute]
   # compute nodes have much CPU power and RAM
   flavor=8cpu-64ram-hpc

The following example shows how to set up a SLURM cluster on AWS which
uses EC2 "spot instances" for the compute nodes, by specifying bidding
price and maximum wait timeout.  The spot instance configuration
applies only to the cluster nodes of class ``compute`` -- the
front-end node runs on a regular instance so it is not terminated
abruptly (which would lead to total job and data loss).  Since compute
nodes are started on "spot instances", which may be not available at
the bid price within the given timeout, you also want to set a
*minimum* number of compute nodes (configuration item
``compute_nodes_min``) that must be available in order to proceed to
cluster setup::

  [cluster/slurm-on-aws]
  setup=slurm
  frontend_nodes=1
  compute_nodes=8
  compute_nodes_min=2

  # this is cloud-specific info
  cloud=amazon-us-east-1
  image_id=ami-90a21cf9
  security_group=default
  flavor=m3.large

  # login info is image-specific
  login=ubuntu

  [cluster/slurm-on-aws/compute]
  # use spot instances for compute
  price=0.08
  timeout=600

A larger set of commented examples can be found at:
`<https://github.com/gc3-uzh-ch/elasticluster/tree/master/examples>`_


Storage section
===============

This section is used to customize the way ElastiCluster saves the
state of your clusters on disk.

By default, all persisted data is saved in
``~/.elasticluster/storage``. This includes two main files for each
cluster:

* ``<cluster>.yaml``: a file containing information about your cluster
* ``<cluster>.known_hosts``: a file containing the ssh host keys of
  the nodes of your cluster.

These files are very important: if they are broken or missing,
ElastiCluster will **not** be able to recover any information about
the cluster.

In addition to these two files, the setup provider and the cloud
provider might create other files in the storage directory, but these
are not critical, as they are re-generated if needed.

To change the default path to the storage directory you can create a
new `storage` section and set the ``storage_path`` value::

    [storage]
    storage_path = $HOME/src/elasticluster/


By default the status of the cluster is saved in YAML_ format, but
also Pickle_ and Json_ formats are available. To save the cluster in a
different fromat, use option ``storage_type``::

    [storage]
    storage_path = $HOME/src/elasticluster/
    storage_type = json

Please note that only newly-created files will honour the
``storage_type`` option!  Existing files will keep their format.


.. _YAML: http://yaml.org/
.. _Pickle: http://en.wikipedia.org/wiki/Pickle_(Python)
.. _Json: http://json.org/
