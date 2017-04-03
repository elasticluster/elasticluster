#! /usr/bin/env python
#
"""
Test the `Node` class from the `elasticluster.cluster` module.
"""
#
#   Copyright (C) 2017 University of Zurich
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

from __future__ import absolute_import

# this is needed to get logging info in `py.test` when something fails
import logging
logging.basicConfig()

# stdlib imports
from tempfile import NamedTemporaryFile

# 3rd-party imports
from mock import MagicMock, patch
import pytest
from pytest import raises

# ElastiCluster imports
from elasticluster.cluster import Cluster, Node
from elasticluster.exceptions import ClusterError
from elasticluster.repository import PickleRepository
from elasticluster.utils import Struct

# local test imports
from _helpers.config import make_cluster


__author__ = (', '.join([
    'Nicolas Baer <nicolas.baer@uzh.ch>',
    'Riccardo Murri <riccardo.murri@gmail.com>',
]))


@pytest.fixture
def node():
    with NamedTemporaryFile() as tmp:
        node = Node(  # pylint: disable=redefined-outer-name
            name='test',
            cluster_name='cluster',
            kind='frontend',
            cloud_provider=MagicMock(),
            user_key_public=tmp.name,
            user_key_private=tmp.name,
            user_key_name='key',
            image_user='user',
            security_group='secgroup',
            image_id='ami-000000',
            flavor='m1.tiny',
            image_userdata=None)
        yield node


def test_start(node):
    """
    Test `Node.start()`
    """
    INSTANCE_ID = 'test-id'

    cloud_provider = node._cloud_provider
    cloud_provider.start_instance.return_value = INSTANCE_ID

    node.start()

    cloud_provider.start_instance.assert_called_once_with(
        node.user_key_name,
        node.user_key_public,
        node.user_key_private,
        node.security_group,
        node.flavor,
        node.image_id,
        node.image_userdata,
        username=node.image_user,
        node_name=("{0}-{1}".format(node.cluster_name, node.name)))
    assert node.instance_id == INSTANCE_ID


def test_stop(node):
    """
    Test `Node.stop()`
    """
    INSTANCE_ID = 'test-id'
    node.instance_id = INSTANCE_ID

    node.stop()

    node._cloud_provider.stop_instance.assert_called_once_with(INSTANCE_ID)


def test_stop_with_no_id(node):
    """
    Test `Node.stop()` when the node has ID ``None``
    """
    node.instance_id = None

    node.stop()

    assert node._cloud_provider.stop_instance.call_count == 0


def test_is_alive(node):
    """
    Test `Node.is_alive()`
    """
    # check without having any knowlegde of the node (e.g. instance id)
    assert not node.is_alive()

    # check with knowledge and cloud provider and mock ip update
    INSTANCE_ID = "test-id"
    node.instance_id = INSTANCE_ID

    provider = node._cloud_provider
    provider.is_instance_running.return_value = True
    provider.get_ips.return_value = ['127.0.0.1', '127.0.0.1']

    assert node.is_alive()

    provider.is_instance_running.assert_called_once_with(INSTANCE_ID)


def test_connect(node):
    """
    Connect to node
    """
    # check without any ips set on the host
    assert node.connect() is None

    # check with mocking the ssh connection
    with patch('elasticluster.cluster.paramiko.SSHClient') as ssh_mock:
        ssh_mock.connect.return_value = True
        node.connect()


def test_update_ips(node):
    """
    Update node ip address
    """
    # check without any ip addresses set
    INSTANCE_ID = "test-id"
    node.instance_id = INSTANCE_ID
    provider = node._cloud_provider

    ips = ['127.0.0.1', '127.0.0.2']
    node.ips = ips
    provider.get_ips.return_value = ips

    node.update_ips()

    assert node.ips == ips
    provider.get_ips.assert_called_once_with(INSTANCE_ID)


def test_dict_mixin(node):
    """Check that the node class can be seen as dictionary"""
    # Setup node with dummy values
    INSTANCE_ID = "test-id"
    node.instance_id = INSTANCE_ID
    ips = ['127.0.0.1', '127.0.0.2']
    node.ips = ips

    node_as_dict = dict(node)

    assert node_as_dict['instance_id'] == INSTANCE_ID
    assert node_as_dict['ips'] == ips

    with pytest.raises(KeyError):
        # pylint: disable=pointless-statement
        node_as_dict['_cloud_provider']
    assert node['_cloud_provider'] == node._cloud_provider


if __name__ == "__main__":
    pytest.main(['-v', __file__])
