========================================================================
Testing ElastiCluster + Azure
========================================================================

.. This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information


Dave Steinkraus / Trevor Eberl 6/29/2015
Updated Dave Steinkraus 9/23/2016

This document, and the Azure provider for ElastiCluster, are works in progress. Expect changes.

Notes about this version: The basis for this code is ElastiCluster 1.3.dev0, cloned from https://github.com/gc3-uzh-ch/elasticluster (master) on 9/22/16.
This version of ElastiCluster installs Ansible version 2.1.1.0.

In this guide, we'll walk through all the steps to:

	- set up a Linux machine to run a test version of ElastiCluster that supports Microsoft Azure; 
	- start an Azure compute cluster and provision it to run Slurm (or gridengine, if you prefer); 
	- communicate with the cluster; and 
	- tear down the cluster.

1. Set up a client environment for running ElastiCluster. This has been tested on Ubuntu 16.04 LTS. On a new machine, install prerequisites:

::

	sudo apt-get update
	sudo apt-get install git python-pip python-dev build-essential \
		libssl-dev libffi-dev nodejs-legacy
	sudo apt-get install npm -y
	sudo apt-get install libxml2-dev libxslt1-dev
    sudo pip install --upgrade httplib2
    sudo pip install --upgrade stevedore
	# running in a virtual Python environment is strongly advised!
	sudo apt-get install python-virtualenv
	sudo pip install virtualenvwrapper

2. Create and enter a virtual Python environment:

::

	mkdir ~/.virtualenvs
	export WORKON_HOME=~/.virtualenvs
	source /usr/local/bin/virtualenvwrapper.sh
	mkvirtualenv elasticluster
	workon elasticluster
	cdvirtualenv
	# note that the following command will make the wrapper commands (workon, etc.) available in the future:
	# echo "source /usr/local/bin/virtualenvwrapper.sh" >> $HOME/.bashrc

3. Install elasticluster:

::

	git clone https://github.com/bobd00/elasticluster.git
	cd elasticluster
	git checkout azure_support_part2
	pip install -e .

Note that this will install the latest Microsoft Azure SDK for Python (for more information see: https://github.com/Azure/azure-sdk-for-python/).

4. Confirm ElastiCluster is ready to run:

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

6. You'll need a keypair to access the virtual machines during provisioning, and later via ssh. For now, 
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


8. Edit the ElastiCluster config file. (The default is ``~/.elasticluster/config``. You can optionally specify a different file/path on the 
ElastiCluster command line.) You can start by copying the file ``azure-sample-config`` from the same directory as this README to 
``~/.elasticluster/config`` on your computer. You'll need to edit the items marked ``**** CHANGE ****``.

For the certificate, specify the .pem file created in step 5 (e.g. ``/home/my_user_name/.ssh/managementCert.pem``).

For user_key_private, specify the .key file created in step 7 (e.g. ``/home/my_user_name/.ssh/managementCert.key``). For user_key_public, specify 
the same .pem file you used for the certificate entry.

Set the basename to a meaningful string of between 3 and 15 characters, digits and lowercase letters ONLY. All Azure resources created will 
include this string.

9. Start the cluster (``-vvv`` will produce verbose diagnostic output - you can use zero to four v's):

::

	elasticluster -vvv start azure-slurm

If all goes well, first you'll see global resources created and then the nodes being brought up. Then ElastiCluster will try to ssh to 
each node - this typically fails for awhile, as the nodes finish booting up, and then it succeeds. When all the nodes have been contacted, the Ansible 
provisioning step will start. This installs the normal Slurm setup that comes with ElastiCluster - nothing's been modified for Azure. Finally, 
ElastiCluster will print a "your cluster is ready!" message.

On occasion, something will go wrong during the Ansible provisioning phase, which follows the creation of the cluster itself (i.e. the 
virtual machines, storage accounts, cloud services, and virtual network). In these cases, at the end of the output there will usually be 
a "Your cluster is not ready!" message. If the last saved state of the cluster includes the correct addresses (ip:port) for the vms, 
there's no need to destroy and restart from scratch. Instead, you can re-run the Ansible phase with this command:

::

	elasticluster -vvv setup azure-slurm

10. Contacting the cluster: this command should establish an interactive ssh connection with the head (frontend) node.

::

	elasticluster ssh azure-slurm

11. Other supported ElastiCluster commands: ``list``, ``list-nodes``, and ``list-templates``.


12. Tearing down the cluster: this will permanently destroy all Azure resources, and stop Azure charges from accruing.
(At the end of a successful teardown, there will be no files left for the cluster in your storage directory, which 
by default is ``~/.elasticluster/storage``.)

::

	elasticluster -vvv stop azure-slurm

13. Troubleshooting:

Occasionally, Azure will start a VM, but it will stay in an unreachable state. In the Azure console, such a VM will show a status 
of "provisioning failed". It will never respond to connection attempts. ElastiCluster tries and fails to contact the VM until the 
configured time (600 seconds, hardcoded in ``cluster.py`` as ``startup_timeout``) has elapsed. Then it will try to delete the VM (which usually 
succeeds) and will continue on with whatever VMs 
remain. (But if the failed node was the only frontend node, the cluster won't be much use, and you'll probably want to stop it.)

If a cluster is in an unusable state, perhaps because of errors on startup or shutdown, and can't be stopped cleanly with the 
ElastiCluster ``stop`` command, you might need to clean up Azure resources as well as local files to prevent errors on the next start 
(and to prevent unwanted Azure charges). Here are the steps:

1. Find your ElastiCluster storage directory. By default, this is ``~/.elasticluster/storage``. You might have set it to something else,  
by using the ``-s {path}`` option on the ElastiCluster command line.

2. From the storage directory, delete all files whose names contain your cluster name, or the base_name specified in your config. For example:
::

	rm ~/.elasticluster/storage/*azure-slurm*
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
