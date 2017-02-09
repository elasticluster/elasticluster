R and CRAN
==========

Install the R statistical computing system together with some recommended
dependecies.

This role uses OS packages provided by the CRAN project (for Debian, Ubuntu, and
CentOS/RHEL) to provide up-to-date versions of R. The names and contents of
these packages closely follows those of the corresponding packages in the base
OS distribution, therefore optional features and behavior details of the
installed software might differ slightly from one base system to the other.


Requirements
------------

All dependencies for the base functionality are handled by the OS-level package
manager.

A working set of default UNIX development tools: C compiler, `make` utility,
etc. is needed to build and install packages using R's `install.packages`
function.  They are currently *not* installed by this role.


Role Variables
--------------

The following variables may be set to alter the role behavior:

``r_cran_mirror_url``
  Base URL for the `CRAN mirror`_ to use. Default is to use the
  `0-Cloud mirror autoselect`_ over HTTP.

  Note that some older distributions might not use up-to-date enough SSL root
  certificates, so that access CRAN mirrors over HTTPS fails. This is notably
  the case with Ubuntu 14.04 "trusty" and the `ETHZ CRAN mirror`_. For this
  reason, ElastiCluster's default is to use HTTP instead of HTTPS.


Example Playbook
----------------

The following example installs R downloading packages from the `ETHZ CRAN
mirror`_::

  - hosts: servers
    roles:
    - role: r
      r_cran_mirror_url: 'http://stat.ethz.ch/CRAN'


License
-------

GPLv3


Author Information and Credits
------------------------------

Written by `Riccardo Murri <mailto:riccardo.murri@gmail.com>`_ for inclusion
into the ElastiCluster_ playbook collection.


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
.. _`0-Cloud mirror autoselect`: http://cloud.r-project.org/
.. _`CRAN mirror`: https://cran.r-project.org/mirrors.html
.. _`ETHZ CRAN mirror`: https://stat.ethz.ch/CRAN/
