#! /usr/bin/env python
#
#   Copyright (C) 2013 GC3, University of Zurich
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
from elasticluster.exceptions import KeypairError

__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'

import os
import tempfile
import unittest

from mock import MagicMock

from elasticluster.providers.ec2_boto import BotoCloudProvider


class TestBotoCloudProvider(unittest.TestCase):

    def _create_provider(self):
        return BotoCloudProvider("http://test.os.com", "nova", "a-key",
                                 "s-key")

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
        provider._connection = connection
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
        '''
        Keypair error handling for RSA
        '''
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
        with self.assertRaises(KeypairError):
            self._check_keypair_helper(key_content_prv, key_content_pub,
                                        "wrong-fingerprint")


    def test_check_keypair_dsa(self):
        '''
        Keypair error handling for DSA
        '''
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
        with self.assertRaises(KeypairError):
            self._check_keypair_helper(key_content_prv, key_content_pub,
                        fingerprint, key_exists=False, host="us.amazon.com")








