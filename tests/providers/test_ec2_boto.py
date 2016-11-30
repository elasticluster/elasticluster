#! /usr/bin/env python
#
#   Copyright (C) 2013, 2016 S3IT, University of Zurich
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
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'

import os
import tempfile
import unittest

from mock import MagicMock, PropertyMock

from elasticluster.exceptions import (
    KeypairError,
    InstanceError,
    InstanceNotFoundError,
    SecurityGroupError,
    SubnetError,
    ImageError
)
from elasticluster.providers.ec2_boto import BotoCloudProvider

import pytest


class TestBotoCloudProvider(unittest.TestCase):

    def _create_provider(self):
        return BotoCloudProvider("https://hobbes.gc3.uzh.ch/", "nova", "a-key",
                                 "s-key")

    def test_start_instance(self):
        """
        BotoCloudProvider: start instance
        """
        # keypairs
        key_content_prv = """-----BEGIN RSA PRIVATE KEY-----
            MIIEogIBAAKCAQEAnviAyqIZ9J/hYHwsR0a5wo6aFn5N+lyOn+sMgFKz13CXqKzN
            TwtQru4WbteizrltGoNDtN8M128agrqvBABVjtk165vFVJYrjWewPPA/Mu3FqYKG
            AiZWL19wAviCpt5to16RP1f7+96ernm0oo0mRNSN6PP4/FdZRwSi22QU2BqwY2ft
            XmgrzwTVRUulTjsREyLi+ajjJ6QoBlLeUx8XbUb9BjbYhdCIJ4YiYLG4I46XrmoX
            uRZEZjfomnIVdnTfRtW7rDwQYX+Sk4FXZJs2CFiramkbH0KFJYU67XA/0qj4TNwl
            th8HDPwcX2vqE/AdrdliXe3mP86yO5Vk7J4C3wIDAQABAoIBAB6kF273P7l+95n5
            VS+H2lY91kVvougW3wbD72zsg+2KrjC83fXWYH7XNUu4FJFz/CuYEXzTYU5FA/8e
            rI1A4zzdcR8wryBWsZ5X1gho5kWSvv6lQd84NHR9GMH51HUFemx61dQ3yUIK7tsC
            ambKfg3WSmQUYnGBBJxDsIBJEht0+6dWwwUcZyXuCtY2sXb0G6jYguWayXiwMMN8
            UoDUnIc9zMHoqdl7fpWDfXbEkzwrPn0DTJcrw16wybpod/pLxTgiIAcAOZnMABsa
            +vnpsPSoihB4EF9qrNylIYKuOjkGe6he8TKQMmXBeGJEJry6bQYplZKXLrNcku6q
            gz/sDAECgYEA0aW208IWSrXzvh0MtRDMHjQrJ/8ELyoIVR+4CC2zLHMUL2G1YT0u
            BTKpI8TlDhqggxbrczxD74WkR0whQRkrIHWF68Wkbu+FgDYJeaiV7IVd31mGTaPo
            ZvjY/d8TBNd3LQvBtBeIJCkJrVHThtycTDydgM5gOm57LfUJycKZpJ8CgYEAwh5u
            529CjY4El1BsLbvxPyIBDtZfp8K4+jkv33H2wL75fbgs689qvPpVZTCXchXuWdCw
            i6HHlGG1WB8XjM9ZpMxMkPjoW7Bx2IDpZQMZqDpQ6bcGISZ/UhG4HHjjNfhsjS66
            6y9XZMvfqidxnl//eeGd5I57+Rnkp+DH4P3uucECgYB3C2BbslQyLEux4pD6qAUg
            CYOP/JEFrxp4K8C2dCzPyrDljtgN1U2yiefddcqTTa9jgLpF/yyccAiuq54edwo0
            LkfTb7FFhSELgqOyv3YSjlCVqSJIKBCpmBivX+JO14LGw2xEtTALSHpEPricVd0y
            tSDCqW2fAGlV2VSriqLwBQKBgB1V3Ay9k6EwxSDY1oBS1rJjwSUs4GfJ1Yp6+fEa
            l9+o/KszGhbI0aidbCpOnZRwHAUWtJdla3PREEaw7C4rZ7Cv7yI5e2Pf1lSRprPN
            NCNoLLIlJpf76WHNq7Uhz7RoRn9PgI/qJ5rj9HkSXOlCOKmCnwnbPoD2mMeGAK7P
            sTQBAoGAQ9+hCFWTQ3VpAx8m+gLyjbcVctrbDwMq7VGydDhpD6a295SKKJkUu8nl
            1Y6lf5LN0tI7CSo/wP5iBML7BYU5ctil2XBHQLK4fCOFO0jqFUyYu+UARiJCcGtM
            fQXPnL3okAfeLdQJKKf1hjeIkNxiOXDAJZ23h6q+X2L5FVu3qCA=
            -----END RSA PRIVATE KEY-----"""
        key_content_pub = ('ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCe+IDKohn0n+'
           'FgfCxHRrnCjpoWfk36XI6f6wyAUrPXcJeorM1PC1Cu7hZu16LOuW0ag0O03wzXbxq'
           'Cuq8EAFWO2TXrm8VUliuNZ7A88D8y7cWpgoYCJlYvX3AC+IKm3m2jXpE/V/v73p6'
           'uebSijSZE1I3o8/j8V1lHBKLbZBTYGrBjZ+1eaCvPBNVFS6VOOxETIuL5qOMnpCg'
           'GUt5THxdtRv0GNtiF0IgnhiJgsbgjjpeuahe5FkRmN+iachV2dN9G1busPBBhf5K'
           'TgVdkmzYIWKtqaRsfQoUlhTrtcD/SqPhM3CW2HwcM/Bxfa+oT8B2t2WJd7eY/zrI'
           '7lWTsngLf test@elasticluster')
        fingerprint = '29:fd:a2:35:2e:18:18:68:c4:4a:86:6c:e1:08:ec:7c'

        (key_file_prv, key_prv) = tempfile.mkstemp()
        key_file_prv = os.fdopen(key_file_prv, 'w+')
        key_file_prv.write(key_content_prv)
        key_file_prv.close()

        (key_file_pub, key_pub) = tempfile.mkstemp()
        key_file_pub = os.fdopen(key_file_pub, 'w+')
        key_file_pub.write(key_content_pub)
        key_file_pub.close()
        key_name = "key"

        try:
            provider = self._create_provider()
            con = MagicMock()
            provider._ec2_connection = con

            # key mock
            mock_key = MagicMock()
            type(mock_key).name = key_name
            type(mock_key).fingerprint =  fingerprint

            con.get_all_key_pairs.return_value = [mock_key]

            # security group mock
            security_group = "test-security-group"
            msecurity_group = MagicMock()
            type(msecurity_group).name = security_group
            con.get_all_security_groups.return_value = [msecurity_group]

            image_id = "image-id"
            flavor = "m1.tiny"
            image_userdata = ""

            provider.start_instance(key_name, key_pub, key_prv,
                                    security_group, flavor, image_id,
                                    image_userdata)

            con.run_instances.assert_called_once_with(image_id,
                    key_name=key_name, security_groups=[security_group],
                    instance_type=flavor, user_data=image_userdata,
                    network_interfaces=None, instance_profile_name=None)


        except:
            # cleanup
            os.unlink(key_prv)
            os.unlink(key_pub)
            raise
        os.unlink(key_prv)
        os.unlink(key_pub)

    def test_stop_instance(self):
        """
        BotoCloudProvider: stop instance
        """
        instance = MagicMock()
        instance_id = "test-id"

        provider = self._create_provider()
        provider._instances[instance_id] = instance

        provider.stop_instance(instance_id)

        instance.terminate.assert_called_once_with()


    def test_get_ips(self):
        """
        BotoCloudProvider: get ip addresses for given instance
        """
        ip_private = "127.0.0.1"
        ip_public = "127.0.0.1"

        instance_id = "test-id"
        instance = MagicMock()
        mock_ip_public = PropertyMock(return_value=ip_public)
        mock_ip_private = PropertyMock(return_value=ip_private)
        type(instance).private_ip_address = mock_ip_private
        type(instance).ip_address = mock_ip_public

        provider = self._create_provider()
        provider._instances[instance_id] = instance

        ips = provider.get_ips(instance_id)

        # get_ips() returns list of *unique* IPs
        assert ips == list(set([ip_private, ip_public]))


    def test_is_instance_running(self):
        """
        BotoCloudProvider: check if instance is running
        """
        # mock a running instance
        instance_id = "test-id"
        instance = MagicMock()
        instance.update.return_value = "running"

        # mock a not running instance
        nr_instance_id = "test-not-running"
        nr_instance = MagicMock()
        nr_instance.update.return_value = "not sure"

        provider = self._create_provider()
        provider._instances[instance_id] = instance
        provider._instances[nr_instance_id] = nr_instance

        assert provider.is_instance_running(instance_id)
        assert not provider.is_instance_running(nr_instance_id)



    def test_load_instance(self):
        """
        BotoCloudProvider: load an instance
        """
        # check instance which does not exist :)
        con = MagicMock()
        provider = self._create_provider()
        provider._ec2_connection = con
        with pytest.raises(InstanceNotFoundError):
            provider._load_instance("not-existing")

        # check instance already fetched
        instance_present = MagicMock()
        instance_present_id = "already-there"
        provider._instances[instance_present_id] = instance_present

        i = provider._load_instance(instance_present_id)
        assert i == instance_present

        # check instance fetched by boto
        instance_boto = MagicMock()
        instance_boto_id = "boto-instance"
        type(instance_boto).id = PropertyMock(return_value=instance_boto_id)
        res = MagicMock()
        type(res).instances = PropertyMock(return_value=[instance_boto])

        con.get_all_reservations.return_value = [res]

        i = provider._load_instance(instance_boto_id)
        assert i == instance_boto

        # check cached instance (example from above boto-instance)
        con.reset_mock()
        del provider._instances[instance_boto_id]
        i = provider._load_instance(instance_boto_id)

        assert i == instance_boto
        # ensure that the instance has been cached
        assert con.get_all_instances.call_count == 0

    def test_check_security_group(self):
        """
        BotoCloudProvider: check security group
        """
        provider = self._create_provider()
        provider._vpc = 'vpc-c0ffee'
        con = MagicMock()
        provider._ec2_connection = con

        # security group that does not exist
        con.get_all_security_groups.return_value = []
        with pytest.raises(SecurityGroupError):
            provider._check_security_group("not-existing")

        group = MagicMock()
        type(group).name = PropertyMock(return_value="key-exists")
        type(group).id = PropertyMock(return_value="id-exists")
        con.get_all_security_groups.return_value = [group]
        with pytest.raises(SecurityGroupError):
            provider._check_security_group("not-existing")

        # security group that exists
        provider._check_security_group("key-exists")
        provider._check_security_group("id-exists")

        group2 = MagicMock()
        type(group2).name = PropertyMock(return_value="key-exists")
        type(group2).id = PropertyMock(return_value="id-exists2")
        con.get_all_security_groups.return_value = [group, group2]

        # VPC and security groups with the same name
        with pytest.raises(SecurityGroupError):
            provider._check_security_group("key-exists")

    def test_check_subnet(self):
        """
        BotoCloudProvider: check subnet IDs
        """
        provider = self._create_provider()
        con = MagicMock()
        provider._ec2_connection = con
        vpc = MagicMock()
        provider._vpc_connection = vpc

        # subnet that does not exist
        vpc.get_all_subnets.return_value = []
        with pytest.raises(SubnetError):
            provider._check_subnet("not-existing")

        subnet = MagicMock()
        type(subnet).tags = PropertyMock(return_value={"Name": "key-exists"})
        type(subnet).id = PropertyMock(return_value="id-exists")
        vpc.get_all_subnets.return_value = [subnet]
        with pytest.raises(SubnetError):
            provider._check_subnet("not-existing")

        # subnet that exists, by name or by key
        provider._check_subnet("key-exists")
        provider._check_subnet("id-exists")

        subnet2 = MagicMock()
        type(subnet2).tags = PropertyMock(return_value={"Name": "key-exists"})
        type(subnet2).id = PropertyMock(return_value="id-exists2")
        vpc.get_all_subnets.return_value = [subnet, subnet2]

        # subnets with the same name
        with pytest.raises(SubnetError):
            provider._check_subnet("key-exists")

    def test_find_image_id(self):
        """
        BotoCloudProvider: find image by id
        """
        name = "test-name"
        image_id = "test-id"

        image = MagicMock()
        type(image).name = PropertyMock(return_value=name)
        type(image).id = PropertyMock(return_value=image_id)

        con = MagicMock()
        con.get_all_images.return_value = [image]

        provider = self._create_provider()
        provider._ec2_connection = con

        assert provider._find_image_id(name) == image_id
        assert provider._find_image_id(image_id) == image_id

        with pytest.raises(ImageError):
            provider._find_image_id("not-existing")




    def _check_keypair_helper(self, key_content_prv, key_content_pub,
                              fingerprint, key_exists=True, host="hobbes"):
        (key_file_prv, key_prv) = tempfile.mkstemp()
        key_file_prv = os.fdopen(key_file_prv, 'w+')
        key_file_prv.write(key_content_prv)
        key_file_prv.close()

        (key_file_pub, key_pub) = tempfile.mkstemp()
        key_file_pub = os.fdopen(key_file_pub, 'w+')
        key_file_pub.write(key_content_pub)
        key_file_pub.close()

        provider = self._create_provider()
        key_name = "test-key"

        connection = MagicMock()
        if key_exists:
            key_result = MagicMock()
            key_result.name = key_name
            key_result.fingerprint = fingerprint
            key_results = [key_result]
            connection.get_all_key_pairs.return_value = key_results
        provider._ec2_connection = connection
        provider._ec2host = host

        try:
            provider._check_keypair(key_name, key_pub, key_prv)
            os.unlink(key_prv)
            os.unlink(key_pub)
        except:
            os.unlink(key_prv)
            os.unlink(key_pub)
            raise



    def test_check_keypair_rsa(self):
        """
        Keypair error handling for RSA
        """
        # create temporary rsa key
        key_content_prv = """-----BEGIN RSA PRIVATE KEY-----
            MIIEogIBAAKCAQEAnviAyqIZ9J/hYHwsR0a5wo6aFn5N+lyOn+sMgFKz13CXqKzN
            TwtQru4WbteizrltGoNDtN8M128agrqvBABVjtk165vFVJYrjWewPPA/Mu3FqYKG
            AiZWL19wAviCpt5to16RP1f7+96ernm0oo0mRNSN6PP4/FdZRwSi22QU2BqwY2ft
            XmgrzwTVRUulTjsREyLi+ajjJ6QoBlLeUx8XbUb9BjbYhdCIJ4YiYLG4I46XrmoX
            uRZEZjfomnIVdnTfRtW7rDwQYX+Sk4FXZJs2CFiramkbH0KFJYU67XA/0qj4TNwl
            th8HDPwcX2vqE/AdrdliXe3mP86yO5Vk7J4C3wIDAQABAoIBAB6kF273P7l+95n5
            VS+H2lY91kVvougW3wbD72zsg+2KrjC83fXWYH7XNUu4FJFz/CuYEXzTYU5FA/8e
            rI1A4zzdcR8wryBWsZ5X1gho5kWSvv6lQd84NHR9GMH51HUFemx61dQ3yUIK7tsC
            ambKfg3WSmQUYnGBBJxDsIBJEht0+6dWwwUcZyXuCtY2sXb0G6jYguWayXiwMMN8
            UoDUnIc9zMHoqdl7fpWDfXbEkzwrPn0DTJcrw16wybpod/pLxTgiIAcAOZnMABsa
            +vnpsPSoihB4EF9qrNylIYKuOjkGe6he8TKQMmXBeGJEJry6bQYplZKXLrNcku6q
            gz/sDAECgYEA0aW208IWSrXzvh0MtRDMHjQrJ/8ELyoIVR+4CC2zLHMUL2G1YT0u
            BTKpI8TlDhqggxbrczxD74WkR0whQRkrIHWF68Wkbu+FgDYJeaiV7IVd31mGTaPo
            ZvjY/d8TBNd3LQvBtBeIJCkJrVHThtycTDydgM5gOm57LfUJycKZpJ8CgYEAwh5u
            529CjY4El1BsLbvxPyIBDtZfp8K4+jkv33H2wL75fbgs689qvPpVZTCXchXuWdCw
            i6HHlGG1WB8XjM9ZpMxMkPjoW7Bx2IDpZQMZqDpQ6bcGISZ/UhG4HHjjNfhsjS66
            6y9XZMvfqidxnl//eeGd5I57+Rnkp+DH4P3uucECgYB3C2BbslQyLEux4pD6qAUg
            CYOP/JEFrxp4K8C2dCzPyrDljtgN1U2yiefddcqTTa9jgLpF/yyccAiuq54edwo0
            LkfTb7FFhSELgqOyv3YSjlCVqSJIKBCpmBivX+JO14LGw2xEtTALSHpEPricVd0y
            tSDCqW2fAGlV2VSriqLwBQKBgB1V3Ay9k6EwxSDY1oBS1rJjwSUs4GfJ1Yp6+fEa
            l9+o/KszGhbI0aidbCpOnZRwHAUWtJdla3PREEaw7C4rZ7Cv7yI5e2Pf1lSRprPN
            NCNoLLIlJpf76WHNq7Uhz7RoRn9PgI/qJ5rj9HkSXOlCOKmCnwnbPoD2mMeGAK7P
            sTQBAoGAQ9+hCFWTQ3VpAx8m+gLyjbcVctrbDwMq7VGydDhpD6a295SKKJkUu8nl
            1Y6lf5LN0tI7CSo/wP5iBML7BYU5ctil2XBHQLK4fCOFO0jqFUyYu+UARiJCcGtM
            fQXPnL3okAfeLdQJKKf1hjeIkNxiOXDAJZ23h6q+X2L5FVu3qCA=
            -----END RSA PRIVATE KEY-----"""

        key_content_pub = ('ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCe+IDKohn0n+'
           'FgfCxHRrnCjpoWfk36XI6f6wyAUrPXcJeorM1PC1Cu7hZu16LOuW0ag0O03wzXbxq'
           'Cuq8EAFWO2TXrm8VUliuNZ7A88D8y7cWpgoYCJlYvX3AC+IKm3m2jXpE/V/v73p6'
           'uebSijSZE1I3o8/j8V1lHBKLbZBTYGrBjZ+1eaCvPBNVFS6VOOxETIuL5qOMnpCg'
           'GUt5THxdtRv0GNtiF0IgnhiJgsbgjjpeuahe5FkRmN+iachV2dN9G1busPBBhf5K'
           'TgVdkmzYIWKtqaRsfQoUlhTrtcD/SqPhM3CW2HwcM/Bxfa+oT8B2t2WJd7eY/zrI'
           '7lWTsngLf test@elasticluster')

        fingerprint = '29:fd:a2:35:2e:18:18:68:c4:4a:86:6c:e1:08:ec:7c'

        # checking a valid keypair that exists
        self._check_keypair_helper(key_content_prv, key_content_pub,
                                   fingerprint)

        # checking keypair with wrong fingerprint
        with pytest.raises(KeypairError):
            self._check_keypair_helper(key_content_prv, key_content_pub,
                                        "wrong-fingerprint")


    def test_check_keypair_dsa(self):
        """
        Keypair error handling for DSA
        """
        # create temporary rsa key
        key_content_prv = """-----BEGIN DSA PRIVATE KEY-----
            MIIBvAIBAAKBgQC9xEaNsXNre+EKxmWZDjpNrN6YmsHao4bPX3u06wkqy9cuopni
            XQV8mgPi3f7lSSZE7InqCC30TilNnN1biqyX35GHkmemPmwP9aSULGIiI0e5EyGR
            zA8Zq796tgRTjY5QMcSyyPzunq9+z9vFFaghnnI7DUJpGwX5oG4g/ivNJQIVAOF8
            5GphTgaEVaxpMRKUHJYN6YjTAoGAeMDA+pzIG3+KS0wwf8TKI559WMxiSANAwu1s
            vvZZDowaMEx5z0yQ8Y1vGdy93jcakJIZnDqHuZzF7ym52+CyMRDeOFMi/D/UyRnb
            Ela4KfYll78aAVIju+ldgwFTwfU6Mp8fKNeQnLalsqiV5mo9ACQaZS48cZXJoYXX
            Z3vThN8CgYEAsOB6hxMwGWSYhdPOy6t50qedR3lWcQsS2SOafjzNEH6O/6f89V1a
            DzTDnhI6GPMIX4gWiA4E11aCGDPhiu0th5XUPJAQdhvjdjxdAYzkm+C/Z0l3XmAG
            5ApiTlNDpCQGpXCbCIoJkWNQlz7W5Wq/l38FA1JJRsMWb9+DwHC94R4CFQCY+6x3
            hjBpunK4slADrzWBALjSTw==
            -----END DSA PRIVATE KEY-----"""

        key_content_pub = ('ssh-dss AAAAB3NzaC1kc3MAAACBAL3ERo2xc2t74QrGZZkO'
                            'Ok2s3piawdqjhs9fe7TrCSrL1y6imeJdBXyaA+Ld/uVJJkT'
                            'sieoILfROKU2c3VuKrJffkYeSZ6Y+bA/1pJQsYiIjR7kTIZ'
                            'HMDxmrv3q2BFONjlAxxLLI/O6er37P28UVqCGecjsNQmkbB'
                            'fmgbiD+K80lAAAAFQDhfORqYU4GhFWsaTESlByWDemI0wAA'
                            'AIB4wMD6nMgbf4pLTDB/xMojnn1YzGJIA0DC7Wy+9lkOjBo'
                            'wTHnPTJDxjW8Z3L3eNxqQkhmcOoe5nMXvKbnb4LIxEN44Uy'
                            'L8P9TJGdsSVrgp9iWXvxoBUiO76V2DAVPB9Toynx8o15Cct'
                            'qWyqJXmaj0AJBplLjxxlcmhhddne9OE3wAAAIEAsOB6hxMw'
                            'GWSYhdPOy6t50qedR3lWcQsS2SOafjzNEH6O/6f89V1aDzT'
                            'DnhI6GPMIX4gWiA4E11aCGDPhiu0th5XUPJAQdhvjdjxdAY'
                            'zkm+C/Z0l3XmAG5ApiTlNDpCQGpXCbCIoJkWNQlz7W5Wq/l'
                            '38FA1JJRsMWb9+DwHC94R4= test@elasticluster')

        fingerprint = '4d:74:5c:a7:4d:ba:d9:5b:c7:b4:a7:30:18:89:67:bc'

        # check valid dsa key
        self._check_keypair_helper(key_content_prv, key_content_pub,
                                   fingerprint, key_exists=True)

        # amazon does not allow dsa keys
        with pytest.raises(KeypairError):
            self._check_keypair_helper(key_content_prv, key_content_pub,
                        fingerprint, key_exists=False, host="us.amazon.com")
