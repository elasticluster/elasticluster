.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc


.. _troubleshooting:

===================
  Troubleshooting
===================

This section lists known problems together with solutions and
workarounds (if available).  Please use the `mailing-list`_ for
further help and for any problem not reported here!

.. contents::


Setup of a cluster fails and stops at task ``nfs-client: add to /etc/fstab``
----------------------------------------------------------------------------

You get this error when starting a new cluster: virtual machines are
started correctly and cluster configuration begins, however at some
point the progress stalls and then after a few minutes' time out, the
Ansible playbook stops running. This error will be the last task
mentioned before the "PLAY RECAP"::

  TASK [nfs-client : add to /etc/fstab] *********************************************************************************************************
  fatal: [compute001]: FAILED! => {"changed": false, "failed": true, "msg": "Error mounting /home: mount.nfs: Connection timed out\n"}

This is due to the security group (also named "direwall rules") not
allowing all traffic across cluster VMs: for NFS to work correctly,
each VM in the cluster must be able to open connections to other VMs
on any TCP *and* UDP port. (TCP and UDP are typically named
"protocols" in security groups / firewall rules context.)

* For AWS EC2, you apply the instuctions given `in page "Security
  Groups for Your VPC", section "Adding, Removing, and Updating Rules"
  <https://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_SecurityGroups.html#AddRemoveRules>`_
  at step 6. -- be sure to apply them to the security group you're
  using with ElastiCluster;

* For Google Cloud, you need to add the rule
  ``default-allow-internal`` -- see
  `<https://cloud.google.com/vpc/docs/firewalls>`_ for details.

* For OpenStack, you can find instructions on how to manipulate
  security groups at
  `<https://help.dreamhost.com/hc/en-us/articles/360000717692-Managing-Security-Groups-using-the-OpenStack-CLI>`_.
  Note that you can also manipulate security groups through the
  Horizon web interface but it's hard to find web documents on its
  usage since every commercial provider seems to have their own
  different reimplementation of the OpenStack web frontend.


Downloading fails with error "Failed to validate the SSL certificate"
---------------------------------------------------------------------

This error may happen at different stages and with different web sites
in the setup phase but the commonality is that the Ansible error
message starts with the words *Failed to validate the SSL
certificate*.  For example::

    TASK [lmod : Download sources] ********************************************************************************************************************************************************
    fatal: [frontend001]: FAILED! => {"changed": false, "failed": true, "msg": "Failed to validate the SSL certificate for github.com:443. Make sure your managed systems have a valid CA certificate installed. You can use validate_certs=False if you do not need to confirm the servers identity but this is unsafe and not recommended. Paths checked for this platform: /etc/ssl/certs, /etc/pki/ca-trust/extracted/pem, /etc/pki/tls/certs, /usr/share/ca-certificates/cacert.org, /etc/ansible. The exception msg was: (\"bad handshake: Error([('SSL routines', 'ssl3_read_bytes', 'tlsv1 alert protocol version')],)\",)."}

This error is typically caused by the "trusted CA repository" on the
host being set up being out of sync with the site (GitHub in the above
example).  The site might have gotten a new SSL/TLS certificate more
recently than the base OS updated its "trusted CA" store, so Ansible
cannot verify that the connection is valid and you're not downloading
software from a rogue site.

The "correct fix" (from a security point of view) would be to ensure
that the base OS from your cluster has an up-to-date "trusted CA
repository" that can validate popular sites like github.com.  However,
providing instructions for how to do this is very much dependent on
the base OS and certainly outside the scope of these short notes.

The *quick workaround* instead is to allow ElastiCluster to skip the
verfication process and download software insecurely.  This can be
accomplished by adding this line to your cluster's ``[setup/...]``
configuration section::

  global_var_insecure_https_downloads=yes


Running any ``elasticluster`` command fails with a version conflict about the ``requests`` package
--------------------------------------------------------------------------------------------------

You can get this error when ElastiCluster installed fine, but attempting to run
*any* command fails with a Python traceback like the following one::

  Traceback (most recent call last):
    File "/home/ec2-user/elasticluster/bin/elasticluster", line 6, in <module>
      from pkg_resources import load_entry_point
    File "/home/ec2-user/elasticluster/lib/python2.7/site-packages/pkg_resources/__init__.py", line 3036, in <module>
      @_call_aside
    File "/home/ec2-user/elasticluster/lib/python2.7/site-packages/pkg_resources/__init__.py", line 3020, in _call_aside
      f(*args, **kwargs)
    File "/home/ec2-user/elasticluster/lib/python2.7/site-packages/pkg_resources/__init__.py", line 3049, in _initialize_master_working_set
      working_set = WorkingSet._build_master()
    File "/home/ec2-user/elasticluster/lib/python2.7/site-packages/pkg_resources/__init__.py", line 656, in _build_master
      return cls._build_from_requirements(__requires__)
    File "/home/ec2-user/elasticluster/lib/python2.7/site-packages/pkg_resources/__init__.py", line 669, in _build_from_requirements
      dists = ws.resolve(reqs, Environment())
    File "/home/ec2-user/elasticluster/lib/python2.7/site-packages/pkg_resources/__init__.py", line 859, in resolve
      raise VersionConflict(dist, req).with_context(dependent_req)
      pkg_resources.ContextualVersionConflict: (requests 2.13.0 (/home/ec2-user/elasticluster/lib/python2.7/site-packages), Requirement.parse('requests!=2.12.2,!=2.13.0,>=2.10.0'), set(['keystoneauth1']))

There is a workaround for this bug in ElastiCluster from `commit 7bf55b8`_
onwards, (to be) included in ElastiCluster 1.3. So, upgrading to the latest
ElastiCluster code should solve the issue. Alternatively, you can solve the
problem by manually resolving the conflict::

  pip install requests==2.12.3

.. _`commit 7bf55b8`: https://github.com/gc3-uzh-ch/elasticluster/commit/7bf55b883db43bbba9802328589ab1dfd4cd85c6

Unfortunately, the root cause of this problem does not lie in ElastiCluster;
instead it stems from the dependency resolution mechanism of the package
installer `pip`. See `ElastiCluster issue #414`__ for more technical details.

.. __: https://github.com/gc3-uzh-ch/elasticluster/issues/414


Running any ``elasticluster`` command fails with a version conflict about the ``pbr`` package
---------------------------------------------------------------------------------------------

You can get this error when ElastiCluster installed fine, but attempting to run
*any* command fails with a Python traceback that ends with a line like the following one::

    pkg_resources.ContextualVersionConflict: (pbr 1.10.0 (...), Requirement.parse('pbr>=2.0.0'), set(['oslo.i18n', 'oslo.serialization', 'oslo.utils', 'debtcollector']))

This means that you have a mixture of older and newer OpenStack libraries in
your ElastiCluster installation: to solve the issue, make a new ElastiCluster
virtual environment and install again from scratch.

The root cause of the issue lies in the interplay between the way `pip` handles
dependencies of dependent packages. There is unfortunately little ElastiCluster
can do about it.


Installation fails with ``ValueError: ('Expected version spec in' [...]``
-------------------------------------------------------------------------

When trying to install ElastiCluster with ``pip install``, you get a long error
report that ends with this Python traceback::

  Traceback (most recent call last):
    File "/opt/python/2.7.9/lib/python2.7/site-packages/pip/basecommand.py", line 232, in main
      status = self.run(options, args)
    File "/opt/python/2.7.9/lib/python2.7/site-packages/pip/commands/install.py", line 339, in run
      requirement_set.prepare_files(finder)
    File "/opt/python/2.7.9/lib/python2.7/site-packages/pip/req/req_set.py", line 436, in prepare_files
      req_to_install.extras):
    File "/opt/python/2.7.9/lib/python2.7/site-packages/pip/_vendor/pkg_resources/__init__.py", line 2496, in requires
      dm = self._dep_map
    File "/opt/python/2.7.9/lib/python2.7/site-packages/pip/_vendor/pkg_resources/__init__.py", line 2491, in _dep_map
      dm.setdefault(extra,[]).extend(parse_requirements(reqs))
    File "/opt/python/2.7.9/lib/python2.7/site-packages/pip/_vendor/pkg_resources/__init__.py", line 2820, in parse_requirements
      "version spec")
    File "/opt/python/2.7.9/lib/python2.7/site-packages/pip/_vendor/pkg_resources/__init__.py", line 2785, in scan_list
      raise ValueError(msg, line, "at", line[p:])
  ValueError: ('Expected version spec in', 'python-novaclient;python_version>="2.7"', 'at', ';python_version>="2.7"')

This means that the ``pip` command is too old to properly parse `Python
environment markers <https://www.python.org/dev/peps/pep-0508/>`_; ``pip``
version 8.1.2 is the first one known to work well but version 9.0.0 improves
support.

To fix the issue, please upgrade ``pip`` to (at least) version 9.0.0::

  pip install --upgrade 'pip>=9.0.0'


Installation fails complaining about version of ``setuptools``
--------------------------------------------------------------

While trying to install ElastiCluster on CentOS/RHEL machines with ``pip
install``, you get a long error report that goes along these lines::

  Obtaining file:///.../elasticluster/src
    Running setup.py egg_info for package from file:///.../elasticluster/src

      The required version of setuptools (>=20.6.8) is not available,
      and can't be installed while this script is running. Please
      install a more recent version first, using
      'easy_install -U setuptools'.

      (Currently using setuptools 0.9.8 (/.../elasticluster/lib/python2.7/site-packages))
      Complete output from command python setup.py egg_info:

  The required version of setuptools (>=20.6.8) is not available,
  and can't be installed while this script is running. Please
  install a more recent version first, using
  'easy_install -U setuptools'.

  (Currently using setuptools 0.9.8 (/.../elasticluster/lib/python2.7/site-packages))

  ----------------------------------------
  Cleaning up...
  Command python setup.py egg_info failed with error code 2 in /.../elasticluster/src
  Storing complete log in /home/hydra/rmurri/.pip/pip.log

To fix the issue, please run these commands instead::

  pip install six packaging appdirs; pip install --upgrade setuptools

Then resume the installation procedure of ElastiCluster from where you left off
and run the ``pip`` step again.

.. warning::

  *Do not* heed the advice given in the error message and run the command
  `easy_install -U setuptools``: it might get you in trouble later on,
  see next section.


Installation fails with ``VersionConflict: ... Requirement.parse('setuptools>=17.1'))``
---------------------------------------------------------------------------------------

When trying to install ElastiCluster with ``pip install``, amid the installation
of dependency packages, you get a long error report that ends with a Python
traceback similar to this one (some parts omitted for clarity)::

      Complete output from command .../bin/python -c "import setuptools;__file__='.../build/funcsigs/setup.py';exec(compile(open(__file__).read().replace('\r\n', '\n'), __file__, 'exec'))" install --record /tmp/pip-P4Xwfz-record/install-record.txt --single-version-externally-managed --install-headers .../include/site/python2.7:
        Traceback (most recent call last):

      File "<string>", line 1, in <module>
      ...
      File ".../lib/python2.7/site-packages/pkg_resources.py", line 630, in resolve

        raise VersionConflict(dist,req) # XXX put more info here

      pkg_resources.VersionConflict: (setuptools 0.9.8 (.../lib/python2.7/site-packages), Requirement.parse('setuptools>=17.1'))

To fix the issue, run this command instead::

  pip install six packaging appdirs; pip install --upgrade setuptools

Then resume the installation procedure of ElastiCluster from where you left off
and run the ``pip`` step again.

This problem has so far only been reported on CentOS 7.x and apparently only
happens when both the following conditions are met:

1. The version of ``setuptools`` initially installed in the virtual environment
   was less than the one required by ElastiCluster (e.g. CentOS' default 0.9.8);
2. The ``setuptools`` Python package was updated by running ``easy_install -U setuptools``.


Upgrading ``setuptools`` fails with ``ImportError: No module named extern``
---------------------------------------------------------------------------

Updating ``setuptools`` by means of the ``easy_install`` command fails with a
traceback like the one below::

  $ easy_install -U setuptools
  Traceback (most recent call last):
    File "/tmp/e/bin/easy_install", line 9, in <module>
      load_entry_point('setuptools==27.3.0', 'console_scripts', 'easy_install')()
    File "/tmp/e/lib/python2.7/site-packages/pkg_resources.py", line 378, in load_entry_point
      return get_distribution(dist).load_entry_point(group, name)
    File "/tmp/e/lib/python2.7/site-packages/pkg_resources.py", line 2566, in load_entry_point
      return ep.load()
    File "/tmp/e/lib/python2.7/site-packages/pkg_resources.py", line 2260, in load
      entry = __import__(self.module_name, globals(),globals(), ['__name__'])
    File "build/bdist.linux-x86_64/egg/setuptools/__init__.py", line 10, in <module>
    File "build/bdist.linux-x86_64/egg/setuptools/extern/__init__.py", line 1, in <module>
  ImportError: No module named extern

To fix the issue, run this command instead::

  pip install six packaging appdirs; pip install --upgrade setuptools

Then resume the installation procedure of ElastiCluster from where you left off
and run the ``pip`` step again.

This problem has so far only been reported on CentOS 7.x platforms.


Installation fails with: "fatal error: ffi.h: No such file or directory"
------------------------------------------------------------------------

While trying to install ElastiCluster with ``pip install``, you get a
long error report that ends with these lines::

        No package 'libffi' found
        c/_cffi_backend.c:15:17: fatal error: ffi.h: No such file or directory
         #include <ffi.h>
                         ^
        compilation terminated.
        error: Setup script exited with error: command 'gcc' failed with exit status 1

To fix the issue on Debian/Ubuntu computers, please install package
``libffi-dev`` prior to attempting to install ElastiCluster::

        sudo apt-get install libffi-dev

To fix the issue on RHEL/CentOS computers, please install package
``libffi-devel``::

        yum install libffi-devel # run this as root

After installing the FFI devel packages, repeat the installation steps for ElastiCluster.

(*Note:* this error comes from missing or badly installed dependency software
for ElastiCluster; you might want to repeat the steps in section `Install
required dependencies`:ref: again and be sure they run through successful
completion.)


Installation fails with: "fatal error: openssl/opensslv.h: No such file or directory"
-------------------------------------------------------------------------------------

While trying to install ElastiCluster with ``pip install``, you get a
long error report that ends with lines like these::

          building '_openssl' extension
        x86_64-linux-gnu-gcc -pthread -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fno-strict-aliasing -Wdate-time -D_FORTIFY_SOURCE=2 -g -fstack-protector-strong -Wformat -Werror=format-security -fPIC -I/usr/include/python2.7 -c build/temp.linux-x86_64-2.7/_openssl.c -o build/temp.linux-x86_64-2.7/build/temp.linux-x86_64-2.7/_openssl.o
        build/temp.linux-x86_64-2.7/_openssl.c:423:30: fatal error: openssl/opensslv.h: No such file or directory
        compilation terminated.
        error: command 'x86_64-linux-gnu-gcc' failed with exit status 1

To fix the issue on Debian/Ubuntu computers, please install package
``libssl-dev`` prior to attempting to install ElastiCluster::

        sudo apt-get install libssl-dev

To fix the issue on RHEL/CentOS computers, please install package
``libffi-devel``::

        yum install openssl-devel # run this as root

After installing the OpenSSL devel packages, repeat the installation steps for ElastiCluster.

(*Note:* this error comes from missing or badly installed dependency software
for ElastiCluster; you might want to repeat the steps in section `Install
required dependencies`:ref: again and be sure they run through successful
completion.)


Installation fails with: "fatal error: Python.h: No such file or directory"
---------------------------------------------------------------------------

While trying to install ElastiCluster with ``pip install``, you get a
long error report that ends with lines like these::

  fatal error: Python.h: No such file or directory
     #include <Python.h>
                        ^
    compilation terminated.
  error: command 'gcc' failed with exit status 1

To fix the issue on Debian/Ubuntu computers, please install packages
``libc6-dev`` and ``python-dev`` prior to attempting to install ElastiCluster::

        sudo apt-get install libc6-dev python-dev

To fix the issue on RHEL/CentOS computers, please install packages
``glibc-devel`` and ``python-devel``::

        yum install glibc-devel python-devel # run this as root

After installing the packages, repeat the installation steps for ElastiCluster.

(*Note:* this error comes from missing or badly installed dependency software
for ElastiCluster; you might want to repeat the steps in section `Install
required dependencies`:ref: again and be sure they run through successful
completion.)


Installation fails with: "unable to execute gcc: No such file or directory"
---------------------------------------------------------------------------

While trying to install ElastiCluster with ``pip install``, you get a
long error report that ends with lines like these::

    Complete output from command python setup.py egg_info:
    unable to execute gcc: No such file or directory
    unable to execute gcc: No such file or directory

    No working compiler found, or bogus compiler options
    passed to the compiler from Python's distutils module.
    See the error messages above.
    (If they are about -mno-fused-madd and you are on OS/X 10.8,
    see http://stackoverflow.com/questions/22313407/ .)

To fix the issue on Debian/Ubuntu computers, please install package
``gcc`` prior to attempting to install ElastiCluster::

        sudo apt-get install gcc libc6-dev

To fix the issue on RHEL/CentOS computers, please install package
``gcc``::

        yum install gcc glibc-devel # run this as root

After installing the GCC packages, repeat the installation steps for ElastiCluster.

(*Note:* this error comes from missing or badly installed dependency software
for ElastiCluster; you might want to repeat the steps in section `Install
required dependencies`:ref: again and be sure they run through successful
completion.)


Installation fails with ``Too many levels of symbolic links``
-------------------------------------------------------------

Running ``pip install`` to install ElastiCluster fails with a Python error like
the one below (some parts omitted for brevity)::

   Cleaning up...
   Exception:
   Traceback (most recent call last):
     ...
     File ".../lib/python2.7/site-packages/pip/download.py", line 420, in unpack_file_url
       shutil.copytree(source, location)
     File "/usr/lib64/python2.7/shutil.py", line 208, in copytree
       raise Error, errors
   Error: [..., "[Errno 40] Too many levels of symbolic links: '/home/centos/elasticluster/elasticluster/share/playbooks/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles/roles'")]

This error only happens because the ``pip`` program is too old.
Upgrade ``pip`` by running the command::

  pip install --upgrade "pip>=7.1.0"


Setup of RHEL/CentOS 7 clusters fails immediately
-------------------------------------------------

While running ``elasticluster setup`` (or in the final part of
``elasticluster start``) an Ansible playbook is run, but it stops as
early as the first task.  A long error message follows, resembling
this one::

    PLAY [Common setup for all hosts] **********************************************

    TASK [setup] *******************************************************************
    fatal: [worker001]: FAILED! => {"changed": false, "failed": true, "invocation": {"module_name": "setup"}, "module_stderr": "sudo: sorry, you must have a tty to run sudo\n", "module_stdout": "", "msg": "MODULE FAILURE", "parsed": false}

The key error message here is ``sudo: sorry, you must have a tty to
run sudo``.  Apparently RHEL and CentOS ship with a default
configuration that requires an interactive terminal to run ``sudo``;
this is not there when ``sudo`` is run remotely from Ansible.

A solution is to use the ElastiCluster configuration key ``image_userdata`` to
alter ``sudo`` behavior to allow TTY-less operation. For example::

        [cluster/sge]
        image_userdata=#!/bin/bash
          echo 'Defaults:centos !requiretty' > /etc/sudoers.d/999-requiretty && chmod 440 /etc/sudoers.d/999-requiretty

Another solution is to turn `SSH pipelining`_ off.  There are two ways of
doing this:

1. Add the line ``ansible_ssh_pipelining=no`` in the cluster
   ``[setup/*]`` section.  For instance::

        [setup/slurm]
        provider=ansible
        ansible_ssh_pipelining=no
        # ...rest of sections is unchanged...

2. Or set the ``ANSIBLE_SSH_PIPELINING`` environment
   variable to the value ``no``.  For example::

        env ANSIBLE_SSH_PIPELINING=no elasticluster setup mycluster

You can read a more complete explanation in the book `Ansible: Up and
Running`__ by Lorin Hochstein.

.. __: https://books.google.ch/books?id=V-e6CAAAQBAJ&pg=PA165&lpg=PA165&dq=sudo:+sorry,+you+must+have+a+tty+to+run+sudo
.. _`ssh pipelining`: http://docs.ansible.com/ansible/intro_configuration.html#pipelining


Setup of Ubuntu 16.04 ("xenial") clusters fails immediately
-----------------------------------------------------------

While running ``elasticluster setup`` (or in the final part of
``elasticluster start``) an Ansible playbook is run, but it stops as
early as the first task.  A long error message follows, resembling
this one::

  PLAY [Common setup for all hosts] **********************************************

  TASK [setup] *******************************************************************
  fatal: [master001]: FAILED! => {"changed": false, "failed": true, "module_stderr": "", "module_stdout": "/bin/sh: 1: /usr/bin/python: not found\r\n", "msg": "MODULE FAILURE", "parsed": false}
  ...

The key part of the error message is: ``/usr/bin/python: not found``; `Ubuntu
16.04 does not install Python 2.x`__ by default.

To fix the issue install package ``python`` on the Ubuntu VMs:

* run ``sudo apt install python`` in a VM started with tha base image;
* make a snapshot;
* use that snmapshot as the base for ElastiCluster.

Additional support will be required in ElastiCluster to automate these steps,
see `issue #304 <https://github.com/gc3-uzh-ch/elasticluster/issues/304>`_

.. __: http://summit.ubuntu.com/uos-1511/meeting/22568/python3-only-on-the-images/


Issues when installing from source on MacOSX
--------------------------------------------

.. warning::

  Installation and testing of ElastiCluster on MacOSX is not currently part of
  the development or the release cycle. So these notes could be severely out of
  date. Please report issues and seek for solutions on the ElastiCluster
  `mailing-list`_.

When installing ElastiCluster on MacOSX you may
get some errors while running `python setup.py install`, because
`pip`_ is not always able to automatically resolve the
dependencies.

In these cases, you need to find the package that is failing and
install it manually using `pip`.

For instance, if during the installation you get something like::

    Running requests-2.4.3/setup.py -q bdist_egg --dist-dir /var/folders/tZ/tZ2B3RaeGVq7+ptdJIbdj++++TI/-Tmp-/easy_install-CrTFFL/requests-2.4.3/egg-dist-tmp-JZ2MOD
    Adding requests 2.4.3 to easy-install.pth file
    Traceback (most recent call last):
      File "setup.py", line 109, in <module>
        'elasticluster = elasticluster.main:main',
      File "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/distutils/core.py", line 152, in setup
        dist.run_commands()
      File "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/distutils/dist.py", line 975, in run_commands
        self.run_command(cmd)
      File "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/distutils/dist.py", line 995, in run_command
        cmd_obj.run()
      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/install.py", line 65, in run
      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/install.py", line 115, in do_egg_install
      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 360, in run

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 576, in easy_install

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 627, in install_item

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 682, in process_distribution

      File "/Users/michela/elasticluster/build/setuptools/pkg_resources.py", line 631, in resolve
        dist = best[req.key] = env.best_match(req, ws, installer)
      File "/Users/michela/elasticluster/build/setuptools/pkg_resources.py", line 871, in best_match
        return self.obtain(req, installer)
      File "/Users/michela/elasticluster/build/setuptools/pkg_resources.py", line 883, in obtain
        return installer(requirement)
      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 595, in easy_install

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 627, in install_item

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 659, in process_distribution

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 532, in install_egg_scripts

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 734, in install_wrapper_scripts

      File "/private/var/folders/tZ/tZ2B3RaeGVq7+ptdJIbdj++++TI/-Tmp-/easy_install-qch0dG/python-keystoneclient-0.11.1/pbr-0.10.0-py2.6.egg/pbr/packaging.py", line 512, in override_get_script_args
    AttributeError: 'NoneType' object has no attribute 'get_script_header'

you probably need to install `pbr` manually using::

    pip install pbr


Error "ImportError: No module named anyjson" on MacOSX
------------------------------------------------------

.. warning::

  Installation and testing of ElastiCluster on MacOSX is not currently part of
  the development or the release cycle. So these notes could be severely out of
  date. Please report issues and seek for solutions on the ElastiCluster
  `mailing-list`_.

In some MacOSX version, even if the installation *seems* to succeed, you may get
the following error the first time you run `elasticluster`::

    Traceback (most recent call last):
      File "/Users/michela/el2/bin/elasticluster", line 9, in <module>
        load_entry_point('elasticluster==1.1-dev', 'console_scripts', 'elasticluster')()
      File "/Users/michela/el2/build/setuptools/pkg_resources.py", line 356, in load_entry_point
        return get_distribution(dist).load_entry_point(group, name)
      File "/Users/michela/el2/build/setuptools/pkg_resources.py", line 2431, in load_entry_point
        return ep.load()
      File "/Users/michela/el2/build/setuptools/pkg_resources.py", line 2147, in load
        ['__name__'])
      File "build/bdist.macosx-10.6-universal/egg/elasticluster/__init__.py", line 33, in <module>
      File "build/bdist.macosx-10.6-universal/egg/elasticluster/providers/gce.py", line 37, in <module>
      File "build/bdist.macosx-10.6-universal/egg/apiclient/discovery.py", line 52, in <module>
      File "build/bdist.macosx-10.6-universal/egg/apiclient/errors.py", line 27, in <module>
    ImportError: No module named anyjson

In this case, the issue is caused by `google-api-python-client`, and
you should:

1) uninstall it using `pip uninstall`
2) reinstall it using `pip install`
3) re-run elasticluster installation::

    pip uninstall google-api-python-client
    [...]
    pip install google-api-python-client
    [...]
    pip install -e .
