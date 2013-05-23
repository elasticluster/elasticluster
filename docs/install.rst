.. Hey, Emacs this is -*- rst -*-

   This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information.

.. include:: global.inc

================
  Installation  
================


`elasticluster` is a `Python`_ program; Python version 2.6 is required
to run it.

The easiest way to install elasticluster is using `pip`_, this will
install the latest **stable** release from the `PyPI`_ website. The
following section: `Installing from PyPI`_ will explain you how to do
it.

If you instead want to test the *development* version, go to the
`Installing from github`_ section.

Installing from PyPI
--------------------

It's quite easy to install `elasticluster` using
`pip`_; the command below is all you
need to install `elasticluster` on your system::

    pip install elasticluster

If you want to run `elasticluster` from source you have to **install**
`Ansible`_ **first:**

::

    pip install ansible
    python setup.py install


Installing from github
----------------------

The source code of elasticluster is `github`_, if you want to test the
latest development version you can clone the `github elasticluster repository`_.

You need the ``git`` command in order to be able to clone it, and we
suggest you to use `python virtualenv`_ in order to create a
controlled environment in which you can install elasticluster as
normal user. 

Assuming you already have ``virtualenv`` installed on your machine,
you first need to create a virtualenv and install `ansible`, which is
needed by elasticluster::

    virtualenv elasticluster
    . elasticluster/bin/activate
    pip install ansible
    
Then you have to download the software. We suggest you to download it
*within* the created virtualenv::

    cd elasticluster
    git clone git://github.com/gc3-uzh-ch/elasticluster.git src
    cd src
    git submodule init
    git submodule update
    python setup.py install

Now the ``elasticluster`` should be available in your current
environment.

.. _`github elasticluster repository`: https://github.com/gc3-uzh-ch/elasticluster
