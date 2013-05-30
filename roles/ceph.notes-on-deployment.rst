Notes on deploying ceph *manually*
==================================

Most of the docs on setting up ceph either use `ceph-deploy` or
`mkcephfs`. However, these tools are not suitable for an automatic
deploying system like Ansible, CFEngie or Puppet, because by hiding
the complexity behind the installation and configuration process, they
don't give you the flexibility you would need to use these tools.

Also, when these automatic installation tools does not work as
expected, you find yourself clueless about what went wrong and how to
fix it, which is something as a system administrator I find very
frustrating...

This is why I wrote few notes on how to *manually* deploy ceph, stuff
I've found out trying to create the ansible playbooks but for which I
haven't found any good documentation on the official website or the
documentation.

This page, therefore, is not intended to be a guide to deploy ceph,
because I am not explaining what ceph is for and how does it work, so
*before* reading this, you are supposed to have already tried to set
up ceph and at least having looked at the official documentation,
including the following links:

* http://ceph.com/docs/master/start/
* http://ceph.com/docs/master/architecture/
* http://ceph.com/docs/next/rados/operations/authentication/

The stuff I am not sure about are marked as **NOT SURE:**. The other
stuff I am pretty confident that, at the time of writing 
(28.05.2013, ceph version 0.61.2), is working as I am saying.

Background
----------

To setup ceph you need:

1) one or more monitor nodes
2) one or more osd nodes
3) *optionally*, one or more mds nodes (they are needed for cephfs,
   but not for rados/rbd)

Unless you are explicitly disabled the ``cephx`` authentication
(http://ceph.com/docs/next/rados/operations/authentication/#disabling-cephx),
one of the things you can find tricky is setting up the monitor node,
especially the keyring.

The easiest way to create a working keyring is to create it on one of
the node and then copying it in the correct locations of the various
nodes. This is what I've done, and it work. I am pretty sure that I'm
copying *more* stuff than the necessary though...

Since a ceph cluster needs at least one monitor node, I am creating
the keyring in the first monitor node and then copying the file to the
other nodes.

Setting up the monitor node
---------------------------

Setting up a monitor (in our case) consists of the following steps:

1) create a keyring. The keyring will have keys and correct
   capabilities for the following services/clients:

   ``mon.`` 
       this is, as far as I understood, the key that will be
       shared among all the monitor nodes. **NOT SURE:** I don't know
       if you need one key for all of them or you may just have one
       key for each one of them and share all of them. However, I have
       both...

   ``client.admin``
       this will be used by the administrative commands,
       and can be used to mount the ``cephfs`` filesystem.

   ``osd.<name>``
       one key for each osd node.

   ``mds.<name>``
       one key for each mds node.

2) Bootstrapping the monitor
   (cfr. also http://ceph.com/docs/master/dev/mon-bootstrap/)

Creating the keyring
++++++++++++++++++++

The first step is quite easy, I use ``/etc/ceph/ceph.mon.keyring`` as
temporary keyring file, and then I will copy this file in the
locations where the various daemons are expecting to find it. I run
all these commands in the first monitor node.

First of all you have to create a shared key with the special name
``mon.`` (it's not a typo, it's exactly: `m`, `o`, `n` and `.` (dot))

This is the command::

  ceph-authtool /etc/ceph/ceph.mon.keyring --create-keyring \
      --gen-key -n mon. \
      --cap mon 'allow *'

Since the file is missing, we use the ``-create-keyring`` option, and
we also have to specify the capabilities with ``--cap mon 'allow *'``.

Then we create a key for the ``client.admin`` user, which is used by
the administrative commands and can be used to mount the cephfs
filesystem::

    ceph-authtool /etc/ceph/ceph.mon.keyring --gen-key \
        -n client.admin \
        --cap mon 'allow *' \
        --cap osd 'allow *' \
        --cap mds 'allow *'

In this case the user will need to access all the various services,
*mon*, *osd* and *mds*.

Then, we need one mds key for each metadata server. They all need to
access also the monitor and the OSDs::

    for mdsname in $mdslist
    do
        ceph-authtool /etc/ceph/ceph.mon.keyring --gen-key \
            -n mds.$mdsname \
            --cap mds 'allow *' \
            --cap osd 'allow *' \
            --cap mon 'allow rwx'
    done

Do the same for the OSDs, but in this case the ``--cap`` options are
different::

    for osdname in $osdlist
    do
        ceph-authtool /etc/ceph/ceph.mon.keyring --gen-key \
            -n osd.$osdname \
            --cap osd 'allow *' \
            --cap mon 'allow rwx'
    done

This file **must** be present in each ``mon data`` directory on each
mon node. Usually, this is ``/var/lib/ceph/mon/ceph-<name>``, but *in
principle* you should be able to change it. For instances, if the
monitor ``mon.0`` has ``mon data`` equals to
``/var/lib/ceph/mon/ceph-0``, you are supposed to copy the
``/etc/ceph/ceph.mon.keyring`` file to
``/var/lib/ceph/mon/ceph-0/keyring``

The same of course applies for *all* the various monitor nodes.

Bootstrapping the monitor
+++++++++++++++++++++++++

This can be done in multiple ways. I used a *monmap* file, which
contains information about the monitors belonging to the cluster (I
will not enter in the discussion of quorum nodes, peers etc, please
read the ceph documentation for that.)

If you use the *monmap* way, you need to:

1) create the *monmap* file
2) run ``ceph-mon --mkfs --monmap <file> ...``

There are a few issues with the *monmap* file, which is generated by
the ``monmaptool``:

* It does not take automatically information from the configuration
  file ``/etc/ceph/ceph.conf``, you have to pass the ``-c`` option.

* If you don't do it, and you use the ``--set-initial-members`` and
  the ``-m`` option, it will use default values which are probably not
  good for you.


Before using the monmap file, I **strongly** suggest you to inspect
its content with the ``monmaptool --print <filename>`` command. For
instance, the following command::

    root@ceph-mon001:~# monmaptool --create --generate -m ceph-mon001 /tmp/monmap.worng
    monmaptool: monmap file /tmp/monmap.worng
    monmaptool: generated fsid 5218f76d-ca8d-4f8d-8599-8802c327e7ae
    monmaptool: writing epoch 0 to /tmp/monmap.worng (1 monitors)

Will create a wrong file. To inspect its content run::

    root@ceph-mon001:~# monmaptool --print /tmp/monmap.worng 
    monmaptool: monmap file /tmp/monmap.worng
    epoch 0
    fsid 5218f76d-ca8d-4f8d-8599-8802c327e7ae
    last_changed 2013-05-28 21:12:58.052174
    created 2013-05-28 21:12:58.052174
    0: 10.10.10.14:6789/0 mon.noname-a

As you can see, the only monitor defined has the correct ip address but
**wrong name**: ``mon.noname-a``.

Also, the ``fsid`` is automatically generated every time you run the
command, which means that if you already defined a ``fsid`` in the
``/etc/ceph/ceph.conf`` configuration file, this *monmap* will **not**
work!

On the other hand, assuming the following snippet from the
``/etc/ceph/ceph.conf``::

    [global]
        auth cluster required = cephx
        auth service required = cephx
        auth client required = cephx

        fsid = 00baac7a-0ad4-4ab7-9d5e-fdaf7d122aee
    [mon.0]
        host = ceph-mon001
        mon addr = 10.10.10.14:6789
        mon data = /var/lib/ceph/mon/ceph-0
    [mon.1]
        host = ceph-mon002
        mon addr = 10.10.10.17:6789
        mon data = /var/lib/ceph/mon/ceph-1
    [mon.2]
        host = ceph-mon003
        mon addr = 10.10.10.20:6789
        mon data = /var/lib/ceph/mon/ceph-2

Running ``monmaptool``::

    root@ceph-mon001:~# monmaptool  --create --generate -c /etc/ceph/ceph.conf /tmp/monmap.right
    monmaptool: monmap file /tmp/monmap.right
    monmaptool: set fsid to 00baac7a-0ad4-4ab7-9d5e-fdaf7d122aee
    monmaptool: writing epoch 0 to /tmp/monmap.right (3 monitors)

Will correctly generate the monmap file::

    root@ceph-mon001:~# monmaptool --print /tmp/monmap.right 
    monmaptool: monmap file /tmp/monmap.right
    epoch 0
    fsid 00baac7a-0ad4-4ab7-9d5e-fdaf7d122aee
    last_changed 2013-05-28 21:20:41.032373
    created 2013-05-28 21:20:41.032373
    0: 10.10.10.14:6789/0 mon.0
    1: 10.10.10.17:6789/0 mon.1
    2: 10.10.10.20:6789/0 mon.2

After creating the *monmap* file you can create the *filesystem* in
the ``mon data`` directory. This command has to be run **on each
monitor node**, and replace ``$monname`` with the correct name (in the
previous configuration, it would be `0`, `1` or `1`)::

    ceph-mon --mkfs -i $monname --monmap /etc/ceph/monmap \
        --keyring /etc/ceph/ceph.mon.keyring

Now you should have a ``store.db`` directory in ``mon data``, and you
should be able to run the mon with ``service ceph start``.

Commands to check the status of the monitor:

``ceph auth list``
    prints the list of keys and their capabilites

``ceph mon dump``
    prints a list of the mon nodes, similar to the output of
    ``monmaptool --print``

``ceph status``
    prints information about the status of the cluster.

If something went wrong, follow the instructions on how to increase
the debugging level at
http://ceph.com/docs/master/rados/troubleshooting/log-and-debug/ and
in case you need to run using strace, all the various ``ceph-mon``,
``ceph-osd`` and ``ceph-mds`` daemon accept a ``-d`` option to run in
foreground and print information on the standard output instaead of
the log file. Unfortunately not all the messages are meaningful...


Setting up the OSD
------------------

Setting up the OSD can be tricky because even though in principle you
don't need to store the ``osd data`` directory on a dedicated
filesystem, this is what you are *supposed* to do, so if you try to
just use a directory on the filesystem as osd data directory, you will
find out that:

* ``/etc/init.d/ceph`` assumes it and tries to mount the filesystem if
  it's not mounted, and fails if no ``devs`` is defined.

* for the same reason, the init script fails if no ``osd mkfs type``
  is defined, because it uses it to know how to mount the device in
  the ``osd data`` directory.

* you need specific features of the filesystem that may not be present
  in the default filesystem.

* I am not sure how ceph deal with the available space if you have a
  promiscuous data directory.

* I think that some other parts of the code is assuming that the data
  directory is on a separate filesystem, so if you don't do it
  something strange could happen...

The following steps assume, therefore, that we are going to use a
whole disk for the osd. The configuration file used for the following
example is as follow::

    [osd.0]
        host = ceph-osd001

        osd journal size = 1000

        osd mkfs type = xfs
        devs = /dev/sdb1
        osd addr = 10.10.10.25:6789
        osd data = /var/lib/ceph/osd/ceph-0


Preparing the data directory
++++++++++++++++++++++++++++

So, the first problem is setting up the filesystem. There is a tool,
``ceph-disk`` that should take care of:

* partitioning the disk (two partitions are required, one for data and
  the other for the journal file)
* formatting them (xfs is the preferred filesystem so far)
* creating the directories the osd daemon is expecting to
  find.

Unfortunately the last step is not done correctly, and if you only use
``ceph-disk`` to format the disk the osd daemon will complain that the
``whoami`` file and the ``current`` directory are not found. However,
the ``ceph-osd`` daemon also accept two options: ``--mkfs`` and
``-mkjournal`` which allows you to create all the missing
directories.

To recap, assuming that you want to use ``/dev/sdb1`` partition for
ceph data directory, and thus you are using the whole ``/dev/sdb``
disk for ceph (data and journal), you have to run::

    ceph-disk-prepare --zap-disk /dev/sdb

The ``--zap-disk`` option will delete all the existing partitions, and
it's not needed if the disk is unpartitioned.

Running ``ceph-disk list`` will show you the various disk available on
the machine and some more information on the ceph partitions::

    ceph-disk list
    /dev/sda :
     /dev/sda1 other, ext4, mounted on /
    /dev/sdb :
     /dev/sdb1 ceph data, prepared, cluster ceph, journal /dev/sdb2
     /dev/sdb2 ceph journal, for /dev/sdb1

As you can see, two partitions have been created. Please note that
only the first partition will be actually mounted, while the second
one will be used *raw*, with a link ``journal`` on the filesystem of
the first device pointing to the raw device.

As stated before, this is not enough to make ``ceph-osd`` happy, so
you have to also run the following command::

    ceph-osd -i $osdname -c /etc/ceph/ceph.conf --mkfs --mkjournal

As usual, replace ``$osdname`` with the name of the osd. In my case,
this was ``0`` for the first osd.

The above command will create on the ``osd data`` directory a file
called ``whoami`` (which only contain the name of the osd) and a
directory ``current`` which will contain the actual objects stored in
the osd.

Now you can copy the keyring on the osd

Copying the keyring
+++++++++++++++++++

Like we did for the monitor node, also the OSDs need a keyring in the
``osd data`` directory. In this case, however, you don't need the
whole keyring, but just the osd key. For semplicity I've copied the
whole keyring file instead in
``/var/lib/ceph/osd/ceph-$osdname/keyring``.


Create the osd also on the monitor node
+++++++++++++++++++++++++++++++++++++++

Apart from the configuration file, the monitor nodes does not know
anything about the osd you just installed, so you have to create
one. This can be done on any machine that can access as administrator
to the monitors, which means that the machine must have:

1) the correct ``/etc/ceph/ceph.conf`` file, with the list of the
   monitor nodes
2) a keyring in ``/etc/ceph/keyring`` with the key named
   ``client.admin``. This key must have the  correct capabilites on
   the monitor nodes; in the section `Setting up the monitor node`_
   section we already created this user.

Assuming the authentication work the command to issue is::

    ceph osd create

This will create *the next* osd. For instance, the first time you run
it it will create the ``osd.0`` osd, the second time it will create
``osd.1`` etc. Don't ask me why it does not accept a name, and what
happen if you call your osd differently. If you named your osd like I
did (osd.0, osd.1, osd.2 ...) it will work.

To display information about the OSDs you can run the following
commands::

    root@ceph-osd001:~# ceph osd dump
     
    epoch 8
    fsid 00baac7a-0ad4-4ab7-9d5e-fdaf7d122aee
    created 2013-05-28 21:34:46.652843
    modified 2013-05-28 21:37:38.239213
    flags 

    pool 0 'data' rep size 2 min_size 1 crush_ruleset 0 object_hash rjenkins pg_num 64 pgp_num 64 last_change 1 owner 0 crash_replay_interval 45
    pool 1 'metadata' rep size 2 min_size 1 crush_ruleset 1 object_hash rjenkins pg_num 64 pgp_num 64 last_change 1 owner 0
    pool 2 'rbd' rep size 2 min_size 1 crush_ruleset 2 object_hash rjenkins pg_num 64 pgp_num 64 last_change 1 owner 0

    max_osd 5
    osd.0 up   in  weight 1 up_from 6 up_thru 7 down_at 0 last_clean_interval [0,0) 10.10.10.25:6800/23196 10.10.10.25:6801/23196 10.10.10.25:6802/23196 exists,up 894de0fa-a274-4d6b-b658-7fe3b193299f
    osd.1 up   in  weight 1 up_from 6 up_thru 7 down_at 0 last_clean_interval [0,0) 10.10.10.29:6800/23309 10.10.10.29:6801/23309 10.10.10.29:6802/23309 exists,up 63cd9719-2028-4c2d-a907-b510bffc4151
    osd.2 up   in  weight 1 up_from 5 up_thru 7 down_at 0 last_clean_interval [0,0) 10.10.10.32:6800/23335 10.10.10.32:6801/23335 10.10.10.32:6802/23335 exists,up 1554a8b7-a202-47d8-b7ed-abe9b715bda4
    osd.3 up   in  weight 1 up_from 6 up_thru 6 down_at 0 last_clean_interval [0,0) 10.10.10.34:6800/23348 10.10.10.34:6801/23348 10.10.10.34:6802/23348 exists,up 3c56ee02-1740-4615-aef3-a0d0f25e09b0
    osd.4 up   in  weight 1 up_from 6 up_thru 7 down_at 0 last_clean_interval [0,0) 10.10.10.36:6800/23410 10.10.10.36:6801/23410 10.10.10.36:6802/23410 exists,up f522dd99-c8b2-411e-88d9-d4bda8b940a1

or::

    root@ceph-osd001:~# ceph osd tree

    # id	weight	type name	up/down	reweight
    -1	0.04997	root default
    -2	0.009995		host ceph-osd003
    2	0.009995			osd.2	up	1	
    -3	0.009995		host ceph-osd005
    4	0.009995			osd.4	up	1	
    -4	0.009995		host ceph-osd002
    1	0.009995			osd.1	up	1	
    -5	0.009995		host ceph-osd001
    0	0.009995			osd.0	up	1	
    -6	0.009995		host ceph-osd004
    3	0.009995			osd.3	up	1	


Setting up the MDS
------------------

This is the easiest step. You only have to copy the related key in
``mds data``. Also for the mds you don't need the whole keyring, but
only the key related to the specific mds. I've copied the whole
keyring though...

Assuming this is the piece of the configuration file related to the
mds::

    [mds.0]
        host = ceph-mds001
        mds addr = 10.10.10.21:6789
        mds data = /var/lib/ceph/mds/ceph-0

you have to copy the keyring in ``/var/lib/ceph/mds/ceph-0/keyring``


Notes on the configuration file
-------------------------------

A few random remarks:

* I had to **remove** the ``mon initial members`` option from the
  configuration file. Apparently, having this option caused the
  monitors to *never* establish the quorum, even when it was the only
  monitor node.

* I put ``osd addr``, ``mon addr`` and ``mds addr`` for all the
  hosts. I had a few problems not putting them in the configuration
  file, not sure which ones though, and I am still not sure they are
  needed.

* **NOT SURE** I am not sure if you can actually use the same
  directory for all the services, or all the osd services. You
  probably can, but I still feel that some parts of the code is
  looking for ``/var/lib/ceph/osd/ceph-<name>``, for instance for
  OSDs, so I followed the same syntax.

* *in principle*, you don't need to dedicate a volume for the osd data
  dir; however, the init script in ``/etc/init.d/ceph`` will file if
  you don't use one, and I think that other parts of the code is
  assuming the the data directory actually resides on an external
  filesystem. This means that **you need** to define ``devs`` and
  ``osd mkfs type`` in the configuration file.

Mounting CephFS
---------------

Assuming everything went well, assuming you have at least *one*
**mds** node, mounting the ceph filesystem is quite easy.

1) First of all, you need to load the ``ceph`` kernel module::

       module load ceph

2) then, you need to use a key of an usre that has the right
   capabilites. **NOT SURE** which these are, but the ``client.admin``
   user we created at the beginning works. Run the command::

       ceph auth list

   and then look for an output similar to::

       client.admin
        key: AQCQH6VRQEAPBxAAro3n7bvA8oYUKt5CevCdDg==

   The base64-encoded string after ``key: `` is the key.

3) mount the filesystem using the key of the ``client.admin`` user::

       mount -t ceph <mon-ip>:6789:/ /mnt -o name=admin,secret=<key>

   where:

   ``<mon-ip>``
       is the ip or the hostname of one of the monitor hosts

   ``name=admin``
       is the user you want to use. In this case, ``name=admin`` means
       that the monitor will check that the following ``secret``
       corresponds to the key of the ``client.admin`` user.

   ``secret=<key>``
       is the key of the ``client.admin`` user (or ``client.<foo>`` if
       you specified the ``name=<foo>`` option)
