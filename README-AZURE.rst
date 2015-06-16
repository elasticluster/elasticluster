========================================================================
Testing gridengine + elasticluster + Azure
========================================================================

.. This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information

Note about pip (6/19/15): There is a bug in the Ubuntu version of pip at this time. (see
https://bugs.launchpad.net/ubuntu/+source/python-pip/+bug/1306991) If you encounter this bug, the command ``pip install --pre azure-elasticluster`` will fail.
At that point, if you try to run the ``pip`` command by itself, that will also fail. The solution is as follows:
::

	sudo easy_install -U pip	# this will uninstall and reinstall pip, without the problem
	sudo pip uninstall elasticluster	# note, that's NOT azure-elasticluster, just elasticluster
	sudo pip install --pre azure-elasticluster

In this guide, we'll walk through all the steps to:

	- set up a Linux machine to run a test version of elasticluster that supports Microsoft Azure; 
	- start an Azure compute cluster and provision it to run gridengine; 
	- communicate with the cluster; and 
	- tear down the cluster.

1. Set up a client environment for running elasticluster. Most testing has been done on Ubuntu 14.04. 
On a new machine, install prerequisites:

::

	sudo apt-get update
	sudo apt-get install git python-pip python-dev build-essential \
		libssl-dev libffi-dev nodejs-legacy
	sudo apt-get install npm -y
	sudo apt-get install libxml2-dev libxslt1-dev
	# these two steps are only needed if you want to run in a virtual Python environment:
	sudo apt-get install python-virtualenv
	sudo pip install virtualenvwrapper

2. If you wish, create and enter a virtual Python environment. If installing on a computer that is also used for other purposes, 
this is strongly recommended, since you will be installing a nonstandard fork of elasticluster, and keeping the system Python clean
is a good general practice. If installing on a computer (or virtual machine) that is dedicated to this task, you can skip to step 3:

::

	mkdir ~/.virtualenvs
	export WORKON_HOME=~/.virtualenvs
	source /usr/local/bin/virtualenvwrapper.sh
	mkvirtualenv elasticluster
	workon elasticluster
	cdvirtualenv
	# note that the following command will make the wrapper commands (workon, etc.) available in the future:
	# echo "source /usr/local/bin/virtualenvwrapper.sh" >> $HOME/.bashrc

3. Install the specific Python packages for this test scenario:

This is the forked version of elasticluster that supports Azure (for testing prior to integration with elsticluster).
(NOTE: A previous version of this code required a special version of Ansible. This is no longer the case.)
In spite of the different PyPI name here, the package actually installed will be named ``elasticluster``, so if you also need to run
the standard version of elasticluster on the same computer, you should use a virtual environment for this one. 
The ``--pre`` flag is needed because this is labeled as a "dev" version in PyPI. NOTE: If you are in a virtual environment, 
do NOT specify ``sudo`` in the following command. If not in a virtual environment, you MUST specify ``sudo``.

::

	sudo pip install --pre azure-elasticluster

The Microsoft Azure SDK for Python will be automatically installed by the azure-elasticluster package. For more 
information see: https://github.com/Azure/azure-sdk-for-python/

4. Confirm elasticluster is ready to run:

::

	elasticluster --help

5. You'll need to have an Azure account and know its subscription ID. (see http://azure.microsoft.com/en-us/ to set up a 30-day trial account if necessary.) 
You'll also need to generate a management certificate (.cer) and upload it to Azure. If you haven't done this yet:

::

	mkdir ~/.ssh
	chmod 700 ~/.ssh

Here's one of those things that shouldn't matter, but it apparently does: you should run the following openssl commands from the ``~/.ssh`` 
directory. (Or maybe it's OK if you always use absolute paths instead of "~", but that's unconfirmed at this point.) If you don't do this, 
the resulting keys will not work - Azure will accept them, but Ansible won't, so your VMs will start and then fail to be provisioned.

::

	cd ~/.ssh

The next command will prompt for information. Set the company name as it will make finding the cert in azure portal easier. Everything else 
can be blank. 

::

	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
	-keyout managementCert.pem -out managementCert.pem 

	openssl x509 -outform der -in managementCert.pem -out managementCert.cer

6. You'll need a keypair to access the virtual machines during provisioning, and later via ssh. For now [to be fixed soon], 
you should create a private key file that matches your management cert, like this:

::

	openssl rsa -in managementCert.pem -out managementCert.key

SSH is picky about ownership/permissions on key files. Make sure that yours look like this:

::

	$ ls -l ~/.ssh
	[...]
	-rw------- 1 my_user_name my_user_name  797 May  3 18:00 managementCert.cer

Use these commands if needed on the .pem, .cer, and .key files:

::

	# replace 'my_user_name' with your username - you knew that
	sudo chown my_user_name:my_user_name ~/.ssh/managementCert.pem
	sudo chmod 600 ~/.ssh/managementCert.pem
	# make sure you do this to all 3 files!
    
(Note: access to a specific virtual machine using a keypair that is not also an Azure management keypair doesn't work at present, but
is an open work item.)

7. Upload managementCert.cer to your Azure subscription via the web portal (https://manage.windowsazure.com). (Scroll down to "settings" on the 
left-hand menu, then click "management certificates" at the top, and you'll find an "upload" button at the bottom.)



8. Edit the elasticluster config file. (The default is ``~/.elasticluster/config``. You can optionally specify a different file/path on the 
elasticluster command line.) You can start by copying the file ``azure-sample-config`` from the same directory as this README to 
``~/.elasticluster/config`` on your computer. You'll need to edit the items marked ``**** CHANGE ****``.

For the certificate, specify the .pem file created in step 5 (e.g. ``/home/my_user_name/.ssh/managementCert.pem``).

For user_key_private, specify the .key file created in step 7 (e.g. ``/home/my_user_name/.ssh/managementCert.key``). For user_key_public, specify 
the same .pem file you used for the certificate entry.

Set the basename to a meaningful string of between 3 and 15 characters, digits and lowercase letters only. All Azure resources created will 
include this string.

9. Start the cluster (``-vvv`` will produce verbose diagnostic output - you can use zero to four v's):

::

	elasticluster -vvv start azure-gridengine

If all goes well, first you'll see global resources created and then the nodes being brought up. Then elasticluster will try to ssh to 
each node - this typically fails for awhile, as the nodes finish booting up, and then it succeeds. When all the nodes have been contacted, the Ansible 
provisioning step will start. This installs the normal gridengine setup that comes with elasticluster - nothing's been modified for Azure. Finally, 
elasticluster will print a "your cluster is ready!" message.

On occasion, something will go wrong during the Ansible provisioning phase, which follows the creation of the cluster itself (i.e. the 
virtual machines, storage accounts, cloud services, and virtual network). In these cases, at the end of the output there will usually be 
a "Your cluster is not ready!" message. If the last saved state of the cluster includes the correct addresses (ip:port) for the vms, 
there's no need to destroy and restart from scratch. Instead, you can re-run the Ansible phase with this command:

::

	elasticluster -vvv setup azure-gridengine

10. Contacting the cluster: this command should establish an interactive ssh connection with the head (frontend) node.

::

	elasticluster ssh azure-gridengine

11. Other supported elasticluster commands: ``list``, ``list-nodes``, and ``list-templates``.


12. Tearing down the cluster: this will permanently destroy all Azure resources, and stop Azure charges from accruing.

::

	elasticluster -vvv stop azure-gridengine

13. Troubleshooting:

Occasionally, Azure will start a VM, but it will stay in an unreachable state. In the Azure console, such a VM will show a status 
of "provisioning failed". It will never respond to connection attempts. Elasticluster tries and fails to contact the VM until the 
configured time (600 seconds, hardcoded in ``cluster.py`` as ``startup_timeout``) has elapsed. Then it will try to delete the VM (which usually 
succeeds) and will continue on with whatever VMs 
remain. (But if the failed node was the only frontend node, the cluster won't be much use, and you'll probably want to stop it.)

If a cluster is in an unusable state, perhaps because of errors on startup or shutdown, and can't be stopped cleanly with the 
elasticluster ``stop`` command, you might need to clean up Azure resources as well as local files to prevent errors on the next start 
(and to prevent unwanted Azure charges). Here are the steps:

1. Find your elasticluster storage directory. By default, this is ``~/.elasticluster/storage``. You might have set it to something else, either 
by using the ``-s {path}`` option on the elasticluster command line, or by setting
::

	[storage]
	storage_path = {path}
	
in your config file.

2. From the storage directory, delete all files whose names contain your cluster name, or the base_name specified in your config. For example:
::

	rm ~/.elasticluster/storage/*azure-gridengine*
	rm ~/.elasticluster/storage/*test1234*
	
3. Log into the Azure management console (https://manage.windowsazure.com) and look for resources left over from your cluster. Proceed in 
this order:

	a. Cloud services. When you delete a cloud service, choose the "delete the cloud service and its deployments" option so that the virtual
	machines in the cloud service get deleted too.

	b. Storage accounts. You might need to wait awhile after deleting a virtual machine before you can successfully delete the storage account that
	was used to host the OS hard drive for that VM. To speed this up, go to "Virtual Machines", then "Disks", and try to delete any disks shown.
	Once these are gone, you should be able to delete the storage account.

	c. Networks. Again, it may take a few minutes after deleting other resources before you can delete a network.

14. Additional config settings:

The Azure provider automatically decides how many storage accounts and how many cloud services to create, based on the number of nodes being
requested. (The constants VMS_PER_CLOUD_SERVICE and VMS_PER_STORAGE_ACCOUNT control these calculations.) However, you can override these values
by setting n_cloud_services and/or n_storage_accounts in the [cluster] section of the config file. For clusters of 50 or more VMs, you may find
that creating more cloud services and storage accounts improves speed of cluster starting, stopping, and usage.

You can also provide the subscription_file setting, which allows you to provide more than one Azure subscription in an external file. This
feature is experimental at this time and should not be necessary for clusters of fewer than 100 nodes.
