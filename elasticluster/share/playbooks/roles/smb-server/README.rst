SAMBA server
============

Install the SAMBA_ SMB/CIFS file server and configure it to serve
files from home directories and (optionally) from other user-defined
shares.  (Printing services are always disabled.)

The SAMBA_ software will be installed using the OS package manager,
which may not install the latest and most up-to-date version of SAMBA.


Requirements
------------

*At the moment, this playbook has only been tested on Ubuntu 16.04.*

There are no special requirements: all dependencies will be handled
by the OS package manager.


Role Variables
--------------

The following variables may be set to alter the role behavior:

``smb_server_name``
  The NetBIOS name the server should advertise.
  (Default: the internet host name)

``smb_shares``
  List of additional shares to serve.  For each share,
  the following fields must be defined:

  ``name``
    Name of the share, i.e., how the share will be visible to clients
    and in UNC paths.

  ``path``
    Local filesystem path to the directory to be shared.

  ``description``
    An optional human-readable description of the share contents,
    which can be displayed by some listing tools.  If omitted,
    no description will be provided to clients.

  ``public`` (optional, default ``false``)
    If true, allow guest (unathenticated) access to the share.
    Default is false, i.e., access to the share must be authenticated
    by providing username and password.

  ``readonly`` (optional, default ``false``)
    If true, no writes are allowed to the share. Default is false.

``smb_workgroup``
  The NetBIOS workgroup the server should join.
  (default: ``ELASTICLUSTER``)


Example Playbook
----------------

The following example installs SAMBA_ and configures it to serve the
directory tree ``/data/active`` as an additional share named
``active``::

  - hosts: servers
    roles:
    - role: smb-server
      smb_workgroup: 'LAB'
      smb_shares:
        - name: active
          path: /data/active
          comment: Active experiment data


License
-------

GPLv3


Author Information and Credits
------------------------------

* `Riccardo Murri <mailto:riccardo.murri@gmail.com>`_


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
.. _Samba: http://www.samba.org/
