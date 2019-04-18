environment-modules
===================

Install the TCL-based `environment-modules`_ tool.


Requirements
------------

As the *modules* tool is installed from OS packages, all dependencies
are taken care by the system package manager.


Role Variables
--------------

The following variables may be set to alter the role behavior:

``modules_root``
  Directory containing system-wide module files. Defaults to
  ``/etc/modulefiles``.


Example Playbook
----------------

The following example installs the *modules* tool and uses an
alternate root directory for the module files hierarchy::

  - hosts: frontend
    roles:
      - role: environment-modules
        modules_root: /opt/etc/modulesfiles


License
-------

GPLv3


Author Information and Credits
------------------------------

* `Riccardo Murri <mailto:riccardo.murri@gmail.com>`_


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
.. _`environment-modules`: http://modules.sourceforge.net/
