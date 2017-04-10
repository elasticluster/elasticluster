Apache BigTop
=========

Install BigTop_ and its dependencies to provide the binaries for the Apache Hadoop Component Stack.

Role Variables
--------------

The following variable may be set to alter the role behavior:

``bigtop_experimental``
  This flag enables the deployment of the latest development version of the Hadoop Component Stack.
  The Stack has various dependencies, like java version, scala version, sbt version, zookeeper version, etc.
  All settings for using the experimental flag propagate through the playbooks.


Example Playbook
----------------

The following example installs BigTop_ Stack components::

  - hosts: hadoop_master
    roles:
    - role: yarn-master


License
-------

GPLv3


Author Information and Credits
------------------------------

