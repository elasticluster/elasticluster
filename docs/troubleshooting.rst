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
