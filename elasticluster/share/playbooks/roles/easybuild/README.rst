EasyBuild
=========

Install EasyBuild_ and its dependencies to provide
a working build environment for HPC clusters.

EasyBuild is configured with the following options:

* use Lmod_ as the "environment modules" tool,
  and generate module files with Lua_ syntax.
* use `minimal toolchains`_ (including the "dummy" / system compiler toolchain)
* use `generic optimization flags`_ for maximum compatibility


.. _`minimal toolchains`: http://easybuild.readthedocs.io/en/latest/Manipulating_dependencies.html#using-minimal-toolchains-for-dependencies
.. _`generic optimization flags`: http://easybuild.readthedocs.io/en/latest/Controlling_compiler_optimization_flags.html#optimizing-for-a-generic-processor-architecture-via-optarch-generic


Requirements
------------

`Officially-stated dependencies of EasyBuild
<http://easybuild.readthedocs.io/en/latest/Installation.html#dependencies>`_
are:

- the Lmod_ "environment modules" tool;
- a Python 2.7 interpreter;
- a few standard GNU utilities: ``tar, ``gunzip``, ``bzip2``, etc.

In addition, a working set of default UNIX development tools: C compiler, `make`
utility, etc. is silently assumed.

All of these will be installed by the playbook if not already present.


Role Variables
--------------

The following variables may be set to alter the role behavior:

``EASYBUILD_VERSION``
  The version of EasyBuild_ to install. Interpolated into the (default)
  source archive name.

``EASYBUILD_PREFIX``
  Root directory of all the EasyBuild-related paths: source archive,
  ``.eb``` files repository, installed software, etc.

``EASYBUILD_INSTALL``
  List of ``.eb`` recipes to build. *Beware:* the initial EasyBuild invocation
  will have to build the entire toolchain, so it can take a couple of hours even
  to install a small and relatively simple package. For this reason, the default
  value of this variable is the empty list (i.e., do not install any software
  through EasyBuild).

``EASYBUILD_OPTARCH``
  Optimization flags for building software, see:
  http://easybuild.readthedocs.io/en/latest/Controlling_compiler_optimization_flags.html#controlling-target-architecture-specific-optimizations-via-optarch
  By default the "GENERIC" value is used which should produce code compatible
  with any x86-64 processor.

``easybuild_bootstrap_url``
  URL of the source ``.tar.bz2`` archive. The version string provided by
  variable ``EASYBUILD_VERSION`` is interpolated into the default value.


Example Playbook
----------------

The following example installs EasyBuild_, configures it to write all software
into directory ``/apps``, and uses it to build the GCC-based "foss/2016b"
toolchain::

  - hosts: servers
    roles:
    - role: easybuild
      EASYBUILD_PREFIX: '/apps'
      EASYBUILD_INSTALL:
        - 'foss-2016b.eb'


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

.. _EasyBuild: http://easybuild.readthedocs.io/
.. _ElastiCluster: http://elasticluster.readthedocs.io/
.. _Lmod: http://lmod.readthedocs.io/en/latest/
.. _Lua: http://www.lua.org/
