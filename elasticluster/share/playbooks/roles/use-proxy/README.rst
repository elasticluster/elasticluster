Use web proxy
=============

Use the a web proxy for accessing any HTTP(S) or FTP URL.  This makes
it possible to download files also from VMs in a non-NATed private IP
addressing range or behind a firewall that blocks outbound access.

.. note::

   Settings may take place only after an SSH connection to the host
   is started again afresh.


Requirements
------------

No special setup is necessary.

**Running this role requires ``root`` access.**


Role Variables
--------------

``proxy_url``
: URL to contact the proxy server; e.g., ``http://proxy.example.com:3128/``


Example Playbook
----------------

The following example shows how to configure hosts in group ``servers``
to use the proxy ``http://proxy.example.com:3128/`` by default::

  - hosts: servers
    roles:
    - role: use-proxy
      proxy_url: http://proxy.example.com:3128/


License
-------

GPLv3


Author Information and Credits
------------------------------


`Riccardo Murri <mailto:riccardo.murri@gmail.com>`_ wrote the role playbook from
scratch, for inclusion in the ElastiCluster_ playbook collection.


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
