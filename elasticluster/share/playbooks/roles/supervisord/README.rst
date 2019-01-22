Supervisor(D)
=============

Install Supervisor_ and (optionally) deploy configuration for a
managed program and start it.

This role is designed to be called multiple times with different
programs and configuration snippets, in order to manage multiple
processes with Supervisor_.

The supervisor_ system is installed from the distribution's own
packages and deployed with the default configuration.  The optional
functionality for configuring and starting additional programs depends
on the default OS config including additional configuration snippets
using `Supervisor's [include] mechanism
<http://supervisord.org/configuration.html#include-section-settings>`_
(This works and has been successfully tested with Debian/Ubuntu and
CentOS/RedHat.)

*Note:* The Supervisor_ process control system used to be called
`supervisord` (this can still be seen in the web site domain name);
this role retains the old name.


Requirements
------------

The supervisor_ system is installed from the distribution's own
packages, so there are no special requirements. (Other than having a
`supervisor` package, which is true for both Debian and RedHat-derived
distributions.)


Role Variables
--------------

The following variables may be set to alter the role behavior; all of
them are optional.  If the `config` variable is undefined, then no
additional actions are taken (besides installing Supervisor_ with the
distribution's default configuration).

``svd_config``
  Additional configuration for Supervisor_.  Typically, this should be
  a configuration snippet that configures the program named in
  ``svd_program`` (see below).  *Note:* this variable should contain
  the *actual configuration text*, not the path to a file name! (See
  the example section below.)

``svd_program``
  Name of the program that Supervisor_ should start and manage.


Example Playbook
----------------

You should call this role passing the ``svd_config`` and
``svd_program`` options to have a program managed by Supervisor_.
For example, the following stanza calls the `supervisord` role to
manage JupyterHub::

  - name: Manage JupyterHub with `supervisord`
    import_role:
      name: supervisord
    vars:
      program: jupyterhub
      config: |
        # Control (auto)start of JupyterHub through `supervisor` (http://supervisord.org/)
        #
        # Initial version taken from:
        # https://github.com/jupyterhub/jupyterhub-tutorial/blob/master/supervisor/jupyterhub.conf

        [program:jupyterhub]
        command=/opt/anaconda3/bin/jupyterhub -f /etc/jupyterhub/jupyterhub_config.py
        directory=/var/lib/jupyterhub
        autostart=true
        autorestart=true
        redirect_stderr=true
        stdout_logfile=/var/log/jupyterhub.log
        user=root


The role can be included/imported many times over, with different
values for ``svd_config`` and ``svd_program``, to have multiple
services managed by Supervisor_.

Of course, the role can also be used in Ansible's `roles:` section:

  - hosts: servers
    roles:
      - role: supervisor

If no values for ``svd_config`` is given, then the role just install
Supervisor_ from the OS packages and leaves the default configuration
unchanged.


License
-------

GPLv3


Author Information and Credits
------------------------------

* `Riccardo Murri <mailto:riccardo.murri@gmail.com>`_


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
.. _Supervisor: http://supervisord.org/index.html
