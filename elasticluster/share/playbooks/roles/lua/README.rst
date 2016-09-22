Lua
===

Install Lua together with all the needed dependencies to run Lmod_.

In contrast to other Lua roles, this playbook tries first to install through the
OS-provided packages but falls back to downloading the Lua sources (from the
Lmod archive) and compiling them if the OS packages cannot satisfy all
dependencies of Lmod_.


Requirements
------------

A working set of default UNIX development tools: C compiler, `make` utility,
etc.  They will be installed by the playbook if not already present.


Role Variables
--------------

The following variables may be set to alter the role behavior:

``LUA_VERSION``
  The version of Lua to install. Interpolated into the (default)
  source archive name.

``lua_add_to_path``
  If true, create a file in ``/etc/profile.d`` to add the Lua interpreter
  location to the users' shell ``$PATH``.

``lua_source_dir``
  The directory where to download and extract the source archive.

``lua_install_dir``
  Install Lua under this directory. (Actually, in a subdirectory named after the
  version number.)

``lua_source_url``
  URL of the source archive. The default value downloads the sources from the
  Lmod_ distributed files on SourceForge.net (as they already contain any
  optional packages that are needed for running Lmod_)

``lua_configure_extra_opts``
  Extra arguments to pass to the ``./configure`` script.


Example Playbook
----------------

The following example installs Lua in a directory structure compatible with
EasyBuild's tree layout::

  - hosts: servers
    roles:
      - role: lua
        lua_install_dir: /apps/software/Lua/
        lua_source_dir: /apps/sources/l/Lua/


License
-------

GPLv3


Author Information and Credits
------------------------------

Part of the logic for this playbook was extracted from the
`install-lmod-easybuild.yml`_ written by `Pablo Escobar Lopez
<mailto:pablo.escobarlopez@unibas.ch>`_.

`Riccardo Murri <mailto:riccardo.murri@gmail.com>`_ reworked it into an
autonomous role to be included in ElastiCluster_ and introduced any bugs you can
see.


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
.. _Lmod: http://lmod.readthedocs.io/en/latest/
.. _`install-lmod-easybuild.yml`: https://github.com/pescobar/ansible-easybuild-lmod
