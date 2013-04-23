elasticluster
=============
elasticluster aims to provide a user-friendly command line tool to create, manage and setup computing clusters hosted on OpenStack or Amazon's Elastic Compute Cloud (EC2). It's main goal is to get your cluster up and running with just a few commands.  
  
*This project is an effort of the [Grid Computing Competence Center](http://www.gc3.uzh.ch/) at the [University of Zurich](http://www.uzh.ch) licensed under GNU General Public License 3.*

Features:
==========
elasticluster is in ongoing development and offers the following features at the current state:
* Simple configuration file to define cluster templates
* Create and start multiple clusters / instances
* Automated cluster setup
    * [SLURM](https://computing.llnl.gov/linux/slurm/)
    * Grid Engine
    * Ganglia
* Grow and shrink a cluster
* Stop and destroy a cluster

Getting Started:
===============
It's quite easy to install elasticluster using pypi: 
```shell
pip install elasticluster
```
If you want to install elasticluster from source you have to **install ansible first**:
```shell
pip install ansible
python setup.py install
```

## Configuration
After the software is installed you'll need to create a configuration file. You'll find a configuration template along with its description [here](docs/config.template.ini). When running elasticluster the first time it will copy the configuration template to `~/.elasticluster/config.cfg`. The following shows a basic configuration to connect to OpenStack, please consider the template for details and further options:
```
[cloud/mycloud]
provider=ec2_boto
ec2_url=http://myopenstack.com:8773/services/Cloud
ec2_access_key=my-openstack-key
ec2_secret_key=my-openstack-secret
ec2_region=nova

[login/mylogin]
image_user=ubuntu
image_user_sudo=root
image_sudo=True
user_key_name=my-key-name
user_key_private=~/.ssh/id_rsa
user_key_public=~/.ssh/id_rsa.pub

[cluster/mycluster]
cloud=mycloud
login=mylogin
setup_provider=ansible
security_group=no-access
image=Ubuntu
flavor=m1.tiny
frontend=1
compute=2
image_userdata=

[setup/ansible]
provider=ansible
playbook_path=%(ansible_pb_dir)s/site.yml
frontend_groups=slurm_master, gridengine_master
compute_groups=slurm_clients, gridengine_clients
```
*elasticluster will look for a config.cfg in the following directory by default: `~/.elasticluster/config.cfg` you can easily specify a different path with `elasticluster -c /path/to/config.cfg` at each execution*
  
## Start your cluster
The start command will do the following tasks:  
1. Start the instances on your cloud provider  
2. Setup the instances with the configured setup  
3. Print information about how to connect to the frontend node

Since your done with the configuration you can start your first cluster with elasticluster:
```shell
elasticluster start mycluster
```
Considering the `cluster/mycluster` section in the configuration file, this command will create 1 frontend node and 2 compute nodes based on the given specifications above.  
It's also possible to start a different cluster with the given configuration:
```shell
elasticluster start mycluster --name mycluster2 --compute-nodes 10
```
This will start a cluster (recognized by the name mycluster2) with 10 compute nodes and configure it as specified in the config section of `cluster/mycluster`.  

The started clusters will be automatically configured with the given frontend_groups and compute_groups in the `setup/ansible` section of the configuration file. In this example elasticluster will configure your cluster with slurm and gridengine.  

## List your clusters
The following command will show you all clusters managed with elasticluster:
```shell
elasticluster list
```

## List all nodes of your cluster
To list all nodes within your cluster `mycluster2` you can call:
```shell
elasticluster list-nodes mycluster2
```

## Grow your cluster
Growing your cluster by a certain number of nodes works out of the box:
```shell
elasticluster resize mycluster2 +10
```
This will start 10 new compute nodes on your cloud and setup the nodes with the given configuration (as described in the start your cluster section above).

## Shrink your cluster
**Shrinking your cluster will destroy the last started instance(s) of your cluster. At the moment there is no implementation to determine suited node(s) to destroy. Please use this functionality with caution, if you even consider to use it!**
```shell
elasticluster resize mycluster2 -1
```
This will remove 1 compute node from your cluster.
## Stop your cluster
If you want to stop your cluster you can use the following command:
```shell
elasticluster stop mycluster2
```
This will destory all instances that correspond to the cluster `mycluster2`. The same works for the cluster `mycluster`.














