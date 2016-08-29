.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc


================
  Installation
================

ElastiCluster_ is a `Python`_ program; Python version 2.6 or 2.7 is
required to run it.

The easiest way to install elasticluster is by using `pip`_, this will
install the latest *stable* code release from the `PyPI`_ package
repository.  Section `Installing released code from PyPI`_ will
explain you how to do it.

If you instead want to test the *development* version, go to the
`Installing development code from GitHub`_ section.

In both cases, it's strongly suggested to install `elasticluster` in a
`python virtualenv`_, so that you can easily uninstall or upgrade
`elasticluster`.


Install required dependencies
-----------------------------

CentOS/RHEL
+++++++++++

To install software prerequisites for building and running ElastiCluster, run
the following commands as the ``root`` admin user::

    yum install gcc git libffi-devel openssl-devel python-devel python-virtualenv pytz

Debian/Ubuntu
+++++++++++++

To install software prerequisites for building and running ElastiCluster, run
the following commands (omit the ``sudo` word if running as the ``root`` admin
user)::

    sudo apt-get install gcc git libc6-dev libffi-dev libssl-dev python-dev python-tz virtualenv

MacOSX
++++++

.. warning::

  Installation and testing of ElastiCluster on MacOSX is not currently part of
  the development or the release cycle. So these notes could be severely out of
  date. Please report issues and seek for solutions on the `elasticluster
  mailing-list`_.

In order to install ElastiCluster, you need to install `Xcode`_.
It's free and you can install it directly from the `AppStore`_.


Installing released code from PyPI
----------------------------------

.. warning::

  The code currently available on PyPI (ElastiCluster 1.2) is quite old and is
  lacking a number of important fixes and updates. Until ElastiCluster 1.3 is
  released, we suggest that you install from GitHub_ instead (see section
  :ref:`Installing development code from GitHub`_ below)

Please follow the instructions in section `Install required dependencies`_
before proceeding.

It's quite easy to install `elasticluster` using `pip`_; the command
below is all you need to install `elasticluster` on your system::

    pip install elasticluster

If you run into any problems, please have a look at the
`troubleshooting`:ref: section; the `mailing-list`_ is also a good
place to get help.


Installing development code from GitHub
---------------------------------------

The source code of ElastiCluster is on `GitHub`_, if you want to test the
latest development version you can clone the `GitHub elasticluster repository`_.

Please follow the instructions in section `Install required dependencies`_
before proceeding.

You will need the ``git`` command in order to be able to clone it, and
we suggest you use a `python virtualenv`_ in order to create a
controlled environment in which you can install ElastiCluster without
conflicting with system files or Python libraries.

Assuming you already have ``virtualenv`` installed on your machine,
you first need to create a virtualenv::

    virtualenv elasticluster
    . elasticluster/bin/activate

Then you have to download the software. We suggest you to download it
*within* the created virtualenv::

    cd elasticluster
    git clone git://github.com/gc3-uzh-ch/elasticluster.git src
    cd src
    pip install -e .

Now the ``elasticluster`` command should be available in your current
environment.

If you run into any problems, please have a look at the
`troubleshooting`:ref: section; the `mailing-list`_ is also a good
place to get help.


Building documentation files
++++++++++++++++++++++++++++

ElastiCluster documentation is available in the `docs/` directory, in
reStructuredText-formatted plain text files.

You can additionally build HTML or PDF documentation; in the directory
in the ElastiCluster virtualenv, type::

  cd docs
  make html

To build PDF documentation, use `make latexpdf` instead.

Note that building documentation files requires that the Python module
Sphinx_ (click on the link for install instructions) is available in
the same virtual environment where ElastiCluster is installed.

.. References:

.. _sphinx: http://sphinx-doc.org/latest/install.html
.. _`github elasticluster repository`: https://github.com/gc3-uzh-ch/elasticluster
.. _`Xcode`: https://developer.apple.com/xcode/
.. _`AppStore`: http://www.apple.com/osx/apps/app-store/
