NTPd
====

Install the `NTP daemon`_ to keep all hosts in the cluster agreeing on
timekeeping.


.. _`ntp daemon`:


Requirements
------------

All supported distributions of Linux include NTPd among the provided packages;
no special setup is necessary.


Role Variables
--------------

The following variables may be set to alter the role behavior:

``ntp_servers``
  List of internet hosts to configure a 1-way association with.
  Defaults to 4 randomly-chosen servers in the `pool.ntp.org` domain.

``ntp_peers``
  List of internet hosts to configure a 2-way association with (i.e., both hosts
  can serve time to the other, depending on circumstances). Defaults to the list
  of all hosts in the cluster.




Example Playbook
----------------

The following example installs EasyBuild_, configures it to write all software
into directory ``/apps``, and uses it to build the GCC-based "foss/2016b"
toolchain::

  - hosts: servers
    roles:
    - role: ntp
      ntp_servers:
      - 'master001'
      ntp_peers:
      - 'worker001'
      - 'worker002'


License
-------

GPLv3


Author Information and Credits
------------------------------

`Riccardo Murri <mailto:riccardo.murri@gmail.com>`_ wrote the role playbook from
scratch, for inclusion in the ElastiCluster_ playbook collection.


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
