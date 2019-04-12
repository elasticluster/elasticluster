Lmod
====

Install Lmod_ and configure it to (optionally) load a set of modules when a new
user shell session is started.


Requirements
------------

A working Lua_ interpreter, with add-on packages:

- `LuaFileSystem <https://keplerproject.github.io/luafilesystem/>`_
- `luaposix <http://luaposix.github.io/luaposix/>`_
- `lua-term <https://github.com/hoelzro/lua-term>`_ *(optional)*

They are all installed by the ``lua`` role distributed with ElastiCluster_.


Role Variables
--------------

The following variables may be set to alter the role behavior:

``lmod_install_from_source``
  If ``yes``, then download, build, and install Lmod from the source
  archive.  If ``no`` (default), then try to install Lmod from the OS
  package and install from source if that fails.

``lmod_force_version``
  If set, require that this version of Lmod be installed; if not
  available in the OS packages, install from source.  The value of
  ``lmod_force_version`` is interpolated into the (default) source
  archive name, so you need to use the exact version number as it
  appears in the source archive name (see the `Lmod GitHub releases
  page`_ for a list).

``lmod_default_modules``
  List of modules to load in any new user shell session. Any valid argument of
  ``module list`` can be used as a list item here.

``modules_root``
  Directory containing system-wide module files. Defaults to
  ``/etc/modulefiles``.

``lua_exe``
  Path to the Lua_ interpreter to use; it must be named ``lua``. Defaults to
  ``/usr/bin/lua``.

``lmod_install_dir``
  Install Lmod under this directory. (Actually, in a subdirectory named after the
  version number.)  Only used when installing from source.

``lmod_source_dir``
  The directory where to download and extract the source archive.
  Only used when installing from source.

``lmod_source_url``
  URL of the ``.tar.bz2`` source archive. The version string is interpolated
  into the default value.  Only used when installing from source.

``lmod_configure_extra_opts``
  Extra arguments to pass to the ``./configure`` script.
  Only used when installing from source.


Example Playbook
----------------

The following example installs Lmod_ in a directory structure compatible with
EasyBuild's tree layout::

  - hosts: servers
    roles:
      - role: lmod
        lmod_install_dir: /apps/software/Lmod/
        lmod_source_dir: /apps/sources/l/Lmod/


License
-------

GPLv3


Author Information and Credits
------------------------------

* `Riccardo Murri <mailto:riccardo.murri@gmail.com>`_


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
.. _Lmod: http://lmod.readthedocs.io/en/latest/
.. _`Lmod GitHub releases page`: https://github.com/TACC/Lmod/releases
.. _Lua: http://www.lua.org/
