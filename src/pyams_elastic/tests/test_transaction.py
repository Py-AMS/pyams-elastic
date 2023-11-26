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

"""PyAMS_elastic.tests.test_transaction module

This module is used to test transaction integration.
"""

__docformat__ = 'restructuredtext'

from unittest import TestCase

import transaction
from sqlalchemy import Column, types
from sqlalchemy.orm import declarative_base

from pyams_elastic.client import ElasticClient
from pyams_elastic.mixin import ESKeyword, ESMapping, ESText, ElasticMixin


Base = declarative_base()


class Todo(Base, ElasticMixin):

    __tablename__ = 'todos'

    id = Column(types.Integer, primary_key=True)
    description = Column(types.Unicode(40))

    @classmethod
    def elastic_mapping(cls):
        return ESMapping(
            # analyzer='content',
            properties=ESMapping(
                ESKeyword('document_type'),
                ESText('description')))


class TestClient(TestCase):

    def setUp(self):
        self.client = ElasticClient(servers=['http://elasticsearch:9200'],
                                    index='pyams_elastic_tests_txn',
                                    use_transaction=True)
        self.client.ensure_index(recreate=True)
        self.client.ensure_all_mappings(Base, recreate=True)

    def tearDown(self):
        self.client.delete_index()
        self.client.close()

    def test_index_and_delete_document(self):
        todo = Todo(id=42, description='Finish exhaustive test suite')

        with transaction.manager:
            self.client.index_object(todo)
        self.client.flush(force=True)
        self.client.refresh()

        # Search for this document and make sure it exists.
        q = self.client.query(Todo, query='exhaustive')
        result = q.execute()
        todos = [doc.description for doc in result]
        self.assertIn('Finish exhaustive test suite', todos)

        with transaction.manager:
            self.client.delete_object(todo)

        self.client.flush(force=True)
        self.client.refresh()

        # Search for this document and make sure it DOES NOT exist.
        q = self.client.query(Todo, query='exhaustive')
        result = q.execute()
        todos = [doc.description for doc in result]
        self.assertNotIn('Finish exhaustive test suite', todos)
