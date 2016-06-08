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


Installing released code from PyPI
----------------------------------

It's quite easy to install `elasticluster` using `pip`_; the command
below is all you need to install `elasticluster` on your system::

    pip install elasticluster

If you run into any problems, please have a look at the
`troubleshooting`:ref: section; the `mailing-list`_ is also a good
place to get help.


Installing development code from GitHub
---------------------------------------

The source code of elasticluster is `github`_, if you want to test the
latest development version you can clone the `github elasticluster repository`_.

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
    python setup.py install

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

.. _sphinx: http://sphinx-doc.org/latest/install.html


Notes on MacOSX installation
----------------------------

Xcode
+++++

In order to install `elasticluster`, you need to have `Xcode`_
installed in your system. It's free and you can install it directly
from the `AppStore`_.

`pip` issues when installing from source
++++++++++++++++++++++++++++++++++++++++

When installing `elasticluster` on MacOSX operating systems you may
get some errors while running `python setup.py install`, because
`pip`_ is not always able to automatically resolve the
dependencies.

In these cases, you need to find the package that is failing and
install it manually using `pip`.

For instance, if during the installation you get something like::

    Running requests-2.4.3/setup.py -q bdist_egg --dist-dir /var/folders/tZ/tZ2B3RaeGVq7+ptdJIbdj++++TI/-Tmp-/easy_install-CrTFFL/requests-2.4.3/egg-dist-tmp-JZ2MOD
    Adding requests 2.4.3 to easy-install.pth file
    Traceback (most recent call last):
      File "setup.py", line 109, in <module>
        'elasticluster = elasticluster.main:main',
      File "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/distutils/core.py", line 152, in setup
        dist.run_commands()
      File "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/distutils/dist.py", line 975, in run_commands
        self.run_command(cmd)
      File "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/distutils/dist.py", line 995, in run_command
        cmd_obj.run()
      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/install.py", line 65, in run
      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/install.py", line 115, in do_egg_install
      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 360, in run

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 576, in easy_install

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 627, in install_item

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 682, in process_distribution

      File "/Users/michela/elasticluster/build/setuptools/pkg_resources.py", line 631, in resolve
        dist = best[req.key] = env.best_match(req, ws, installer)
      File "/Users/michela/elasticluster/build/setuptools/pkg_resources.py", line 871, in best_match
        return self.obtain(req, installer)
      File "/Users/michela/elasticluster/build/setuptools/pkg_resources.py", line 883, in obtain
        return installer(requirement)
      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 595, in easy_install

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 627, in install_item

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 659, in process_distribution

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 532, in install_egg_scripts

      File "/Users/michela/elasticluster/build/setuptools/setuptools/command/easy_install.py", line 734, in install_wrapper_scripts

      File "/private/var/folders/tZ/tZ2B3RaeGVq7+ptdJIbdj++++TI/-Tmp-/easy_install-qch0dG/python-keystoneclient-0.11.1/pbr-0.10.0-py2.6.egg/pbr/packaging.py", line 512, in override_get_script_args
    AttributeError: 'NoneType' object has no attribute 'get_script_header'

you probably need to install `pbr` manually using::

    pip install pbr

In some MacOSX version, even if the installation *seems* to succeed,
you may get the following error the first time you run `elasticluster`::

    Traceback (most recent call last):
      File "/Users/michela/el2/bin/elasticluster", line 9, in <module>
        load_entry_point('elasticluster==1.1-dev', 'console_scripts', 'elasticluster')()
      File "/Users/michela/el2/build/setuptools/pkg_resources.py", line 356, in load_entry_point
        return get_distribution(dist).load_entry_point(group, name)
      File "/Users/michela/el2/build/setuptools/pkg_resources.py", line 2431, in load_entry_point
        return ep.load()
      File "/Users/michela/el2/build/setuptools/pkg_resources.py", line 2147, in load
        ['__name__'])
      File "build/bdist.macosx-10.6-universal/egg/elasticluster/__init__.py", line 33, in <module>
      File "build/bdist.macosx-10.6-universal/egg/elasticluster/providers/gce.py", line 37, in <module>
      File "build/bdist.macosx-10.6-universal/egg/apiclient/discovery.py", line 52, in <module>
      File "build/bdist.macosx-10.6-universal/egg/apiclient/errors.py", line 27, in <module>
    ImportError: No module named anyjson

In this case, the issue is caused by `google-api-python-client`, and
you should:

1) uninstall it using `pip uninstall`
2) reinstall it using `pip install`
3) re-run elasticluster installation::

    pip uninstall google-api-python-client
    [...]
    pip install google-api-python-client
    [...]
    python setup.py install


.. _`github elasticluster repository`: https://github.com/gc3-uzh-ch/elasticluster
.. _`Xcode`: https://developer.apple.com/xcode/
.. _`AppStore`: http://www.apple.com/osx/apps/app-store/
