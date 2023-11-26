#
# Copyright (c) 2015-2021 Thierry Florac <tflorac AT ulthar.net>
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

"""PyAMS_elastic.tests.test_client module

This module provides a few unit tests about Elasticsearch client.
"""

from unittest import TestCase

from pyams_elastic.client import ElasticClient, ElasticClientInfo


__docformat__ = 'restructuredtext'


class TestClient(TestCase):

    def test_client_without_argument(self):
        with self.assertRaises(AssertionError) as context:
            client = ElasticClient()
        self.assertIn("You must provide servers or connection info!", str(context.exception))

    def test_client_with_servers(self):
        client = ElasticClient(servers=['http://elasticsearch:9200'],
                               index='pyams_elastic_tests',
                               use_transaction=False)
        with client as es:
            ping = es.ping(pretty=True)
            self.assertTrue(ping)
            info = es.info()
            self.assertIn('cluster_name', info)

    def test_client_with_info(self):
        info = ElasticClientInfo()
        info.servers = ['http://elasticsearch:9200']
        info.index = 'pyams_elastic_tests'
        client = ElasticClient(using=info,
                               use_transaction=False)
        with client as es:
            ping = es.ping(pretty=True)
            self.assertTrue(ping)
            info = es.info()
            self.assertIn('cluster_name', info)
