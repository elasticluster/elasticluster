
scicore-singularity-install
=========

Install Singularity from sources

Role Variables
--------------
```
singularity_install_prefix: '/usr/local'

singularity_version: "latest"
```

Dependencies
------------

none

Example Playbook
----------------

    - hosts: servers
      roles:
         - { role: scicore-singularity-install, singularity_version: "latest" }

License
-------

GPLv3

Author Information
------------------

Pablo Escobar
