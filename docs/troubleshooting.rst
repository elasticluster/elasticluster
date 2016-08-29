.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc


===================
  Troubleshooting
===================

This section lists known problems together with solutions and
workarounds (if available).  Please use the `mailing-list`_ for
further help and for any problem not reported here!

.. contents::


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

To fix the issue, please heed the advice given in the error message and run the
command::

  easy_install -U setuptools

Alternatively, you can run this instead::

  pip install --upgrade setuptools

Then resume the installation procedure of ElastiCluster from where you left off
and run the `pip` step again.


Installation fails with: "fatal error: ffi.h: No such file or directory"
-------------------------------------------------------------------------

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

To fix the issue on Debian/Ubuntu computers, please install package
``gcc`` and ``libc6-dev`` prior to attempting to install ElastiCluster::

        sudo apt-get install gcc libc6-dev

To fix the issue on RHEL/CentOS computers, please install package
``gcc``::

        yum install gcc # run this as root

After installing the GCC packages, repeat the installation steps for ElastiCluster.

(*Note:* this error comes from missing or badly installed dependency software
for ElastiCluster; you might want to repeat the steps in section `Install
required dependencies`:ref: again and be sure they run through successful
completion.)


Installation fails with: "unable to execute gcc: No such file or directory"
-------------------------------------------------------------------------------------

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

        yum install gcc # run this as root

After installing the GCC packages, repeat the installation steps for ElastiCluster.

(*Note:* this error comes from missing or badly installed dependency software
for ElastiCluster; you might want to repeat the steps in section `Install
required dependencies`:ref: again and be sure they run through successful
completion.)


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

The solution is to turn `SSH pipelining`_ off.  There are two ways of
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


Issues when installing from source on MacOSX
--------------------------------------------

.. warning::

  Installation and testing of ElastiCluster on MacOSX is not currently part of
  the development or the release cycle. So these notes could be severely out of
  date. Please report issues and seek for solutions on the `elasticluster
  mailing-list`_.

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
  date. Please report issues and seek for solutions on the `elasticluster
  mailing-list`_.

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
