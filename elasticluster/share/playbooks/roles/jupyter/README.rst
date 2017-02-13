Jupyter
=======

Install Jupyter_ Notebook with kernels for Python 2 and 3, BASH, R_, PySpark
(if Spark_ is already installed), and MATLAB_ (if already installed).

This role relies on the Jupyter packages included in the Anaconda Python
distribution (on which it depends); especially, it assumes that the `pip` and
`python` executables names are un-versioned and that only the root directory
name determines whether Python 2 or 3 is being used.


Requirements
------------

The Anaconda Python distribution (both Python 2 and 3). It will be installed
using the `anaconda role included in ElastiCluster`_.


Role Variables
--------------

The following variables may be set to alter the role behavior (uppercase names
are used for those that you are more likely to customize):

``MATLAB_EXE``
  Executable to run MATLAB (if not found, the MATLAB kernel will not be
  installed). Default: ``matlab`` (i.e., search for a program named ``matlab``
  in the shell search path)`

``PYTHON2_EXE``
  Executable used to run the Python 2 kernel.  Default:
  ``/opt/anaconda2/bin/python``

``PYTHON3_EXE``
  Executable used to run the Python 2 kernel.  Default:
  ``/opt/anaconda2/bin/python``

``R_EXE``
  Executable used to run the R_ language kernel.
  Default: ``/usr/bin/R``

``jupyter_python``
  Python interpreter used to rune Jupyter/JupyterHub
  Default: the value of ``PYTHON3_EXE`` (see above)


Example Playbook
----------------

The following example installs Jupyter uses the OS-provided Python interpreter
to run Python 2 notebooks::

  - hosts: frontend
    roles:
  - role: jupyter
      PYTHON2_EXE: '/usr/bin/python2.7'

Note however, that Anaconda Python 2 will still be installed albeit not used.


License
-------

GPLv3


Author Information and Credits
------------------------------

Written by `Riccardo Murri <mailto:riccardo.murri@gmail.com>`_ for inclusion
into the ElastiCluster_ playbook collection.


.. References:

.. _ElastiCluster: http://elasticluster.readthedocs.io/
.. _Jupyter: http://jupyter.org/
.. _R: http://www.r-project.org/
.. _PySpark: http://spark.apache.org/docs/latest/api/python/
.. _Spark: http://spark.apache.org/
.. _MATLAB: https://www.mathworks.com/products/matlab.html
