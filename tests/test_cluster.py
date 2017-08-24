#! /usr/bin/env python
#
#   Copyright (C) 2013-2017 University of Zurich
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# pylint: disable=missing-docstring

from __future__ import absolute_import

# this is needed to get logging info in `py.test` when something fails
import logging
logging.basicConfig()

# 3rd-party imports
from mock import MagicMock, patch
import pytest
from pytest import raises

# ElastiCluster imports
from elasticluster.exceptions import ClusterError

# local test imports
from _helpers.config import make_cluster
from _helpers.environ import clean_os_environ_openstack


__author__ = (', '.join([
    'Nicolas Baer <nicolas.baer@uzh.ch>',
    'Riccardo Murri <riccardo.murri@gmail.com>',
]))



def test_add_node(tmpdir):
    """
    Add node and let ElastiCluster choose the name.
    """
    clean_os_environ_openstack()
    cluster = make_cluster(tmpdir)
    size = len(cluster.nodes['compute'])
    cluster.add_node("compute", 'image_id', 'image_user', 'flavor',
                     'security_group')
    assert (size + 1) == len(cluster.nodes['compute'])
    new_node = cluster.nodes['compute'][2]
    assert new_node.kind == 'compute'
    assert new_node.name == 'compute003'


def test_add_node_with_custom_name(tmpdir):
    """
    Add node with a given name.
    """
    cluster = make_cluster(tmpdir)
    name = "test-node"
    size = len(cluster.nodes['compute'])
    cluster.add_node("compute", 'image_id', 'image_user', 'flavor',
                     'security_group', image_userdata="", name=name)
    assert (size + 1) == len(cluster.nodes['compute'])
    assert (cluster.nodes['compute'][-1].name) == name


def test_remove_node(tmpdir):
    """
    Remove node
    """
    cluster = make_cluster(tmpdir)
    size = len(cluster.nodes['compute'])
    cluster.remove_node(cluster.nodes['compute'][1])
    assert (size - 1) == len(cluster.nodes['compute'])


def test_start(tmpdir):
    """
    Start cluster
    """
    cloud_provider = MagicMock()
    cloud_provider.start_instance.return_value = u'test-id'
    cloud_provider.get_ips.return_value = ['127.0.0.1']
    cloud_provider.is_instance_running.return_value = True

    cluster = make_cluster(tmpdir, template='example_ec2', cloud=cloud_provider)
    cluster.repository = MagicMock()
    cluster.repository.storage_path = '/unused/path'

    with patch('paramiko.SSHClient'):
        cluster.start()

    cluster.repository.save_or_update.assert_called_with(cluster)

    for node in cluster.get_all_nodes():
        assert node.instance_id == u'test-id'
        assert node.ips == ['127.0.0.1']


def test_check_cluster_size_ok(tmpdir):
    cluster = make_cluster(tmpdir)

    assert len(cluster.nodes["frontend"]) == 1
    assert len(cluster.nodes["compute"]) == 2

    # pylint: disable=protected-access
    cluster._check_cluster_size({'frontend':1, 'compute':1})


def test_check_cluster_size_fail(tmpdir):
    cluster = make_cluster(tmpdir)

    assert len(cluster.nodes["frontend"]) == 1
    assert len(cluster.nodes["compute"]) == 2

    # pylint: disable=protected-access
    with raises(ClusterError):
        cluster._check_cluster_size({'frontend':1, 'compute':5})

    with raises(ClusterError):
        cluster._check_cluster_size({'frontend':3, 'compute':1})


def test_get_all_nodes(tmpdir):
    """
    Check that `Cluster.get_all_nodes()` returns all nodes in the cluster.
    """
    cluster = make_cluster(tmpdir)
    all_nodes = cluster.get_all_nodes()
    assert len(all_nodes) == 3
    assert len([node for node in all_nodes if node.name.startswith('frontend')]) == 1
    assert len([node for node in all_nodes if node.name.startswith('compute')]) == 2


def test_stop(tmpdir):
    """
    Test `Cluster.stop()`
    """
    cloud_provider = MagicMock()
    cloud_provider.start_instance.return_value = u'test-id'
    cloud_provider.get_ips.return_value = ('127.0.0.1', '127.0.0.1')
    states = [
        # pylint: disable=bad-whitespace
        True,  True,  True,  True,  True,
        False, False, False, False, False
    ]
    def is_running(instance_id):  # pylint: disable=unused-argument,missing-docstring
        return states.pop()
    cloud_provider.is_instance_running.side_effect = is_running

    cluster = make_cluster(tmpdir, cloud=cloud_provider)

    for node in cluster.get_all_nodes():
        node.instance_id = u'test-id'

    cluster.repository = MagicMock()
    cluster.repository.storage_path = '/unused/path'

    cluster.stop()

    cloud_provider.stop_instance.assert_called_with(u'test-id')
    cluster.repository.delete.assert_called_once_with(cluster)


def test_get_ssh_to_node_with_class(tmpdir):
    """
    Get frontend node
    """
    cluster = make_cluster(tmpdir)
    cluster.ssh_to = 'frontend'
    frontend = cluster.get_ssh_to_node()
    assert cluster.nodes['frontend'][0] == frontend


def test_get_ssh_to_node_with_nodename(tmpdir):
    """
    Get frontend node
    """
    cluster = make_cluster(tmpdir)
    cluster.ssh_to = 'frontend001'
    frontend = cluster.get_ssh_to_node()
    assert frontend.name == 'frontend001'


def test_get_ssh_to_node_with_defaults(tmpdir):
    """
    Get frontend node
    """
    cluster = make_cluster(tmpdir)
    cluster.ssh_to = None
    frontend = cluster.get_ssh_to_node()
    assert cluster.nodes['frontend'][0] == frontend


def test_setup(tmpdir):
    """
    Setup the nodes of a cluster
    """
    # pylint: disable=protected-access
    cluster = make_cluster(tmpdir)
    setup_provider = MagicMock()
    setup_provider.setup_cluster.return_value = True
    cluster._setup_provider = setup_provider

    cluster.setup()

    setup_provider.setup_cluster.assert_called_once_with(cluster, tuple())


def test_update(tmpdir):
    cloud_provider = MagicMock()
    ip_addr = '127.0.0.1'
    cloud_provider.get_ips.return_value = (ip_addr, ip_addr)

    storage = MagicMock()

    cluster = make_cluster(tmpdir, cloud=cloud_provider)
    cluster.repository = storage

    with patch('paramiko.SSHClient'):
        cluster.update()

    for node in cluster.get_all_nodes():
        assert ip_addr == node.ips[0]


def test_dict_mixin(tmpdir):
    """Check that instances of the `Cluster` class can be recast as Python dictionary."""
    cluster = make_cluster(tmpdir, template='example_ec2')

    # add an attribute and test later if it's exported
    cluster.ssh_to = "misc"

    cluster_as_dict = dict(cluster)
    assert cluster_as_dict['template'] == 'example_ec2'
    assert cluster_as_dict['template'] == cluster_as_dict['name']
    assert 'misc_nodes' in cluster_as_dict['extra']
    # FIXME: why on earth are node numbers converted to string?
    assert cluster_as_dict['extra']['misc_nodes'] == '10'
    assert cluster_as_dict['ssh_to'] == 'misc'
    assert cluster_as_dict['nodes'].keys() == cluster.nodes.keys()

    # non-public attrs should not be exported
    with raises(KeyError):
        # pylint: disable=pointless-statement
        cluster_as_dict['_cloud_provider']
    # pylint: disable=protected-access
    assert cluster['_cloud_provider'] == cluster._cloud_provider


if __name__ == "__main__":
    pytest.main(['-v', __file__])
