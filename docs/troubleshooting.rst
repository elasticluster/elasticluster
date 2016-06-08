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
