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

"""PyAMS_elastic.tests.test_task module

This module provides unit tests for PyAMS scheduler task for Elasticsearch.
"""

__docformat__ = 'restructuredtext'

import json
from io import StringIO
from unittest import TestCase

from zope.interface import Invalid
from zope.schema._bootstrapinterfaces import WrongType

from pyams_elastic.client import ElasticClient, ElasticClientInfo
from pyams_utils.dict import DotDict
from pyams_elastic.task import ElasticReindexTask, ElasticTask
from pyams_elastic.task.interfaces import IElasticTaskInfo
from pyams_elastic.tests.data import Base, get_data
from pyams_scheduler.interfaces.task import TASK_STATUS_ERROR, TASK_STATUS_FAIL, TASK_STATUS_OK


class TestElasticTask(TestCase):

    def test_schema(self):
        task = ElasticTask()
        IElasticTaskInfo.validateInvariants(task)

    def test_schema_with_zero_value(self):
        task = ElasticTask()
        with self.assertRaises(WrongType):
            task.expected_results = 0

    def test_schema_with_wrong_value(self):
        task = ElasticTask()
        with self.assertRaises(WrongType):
            task.expected_results = -10

    def test_schema_with_int_value(self):
        task = ElasticTask()
        task.expected_results = '10'
        IElasticTaskInfo.validateInvariants(task)

    def test_schema_with_negative_value(self):
        task = ElasticTask()
        task.expected_results = '-10'
        with self.assertRaises(Invalid):
            IElasticTaskInfo.validateInvariants(task)

    def test_schema_with_range(self):
        task = ElasticTask()
        task.expected_results = '0-10'
        IElasticTaskInfo.validateInvariants(task)

    def test_schema_with_bad_range(self):
        task = ElasticTask()
        task.expected_results = '10-0'
        with self.assertRaises(Invalid):
            IElasticTaskInfo.validateInvariants(task)

    def test_task(self):
        client = ElasticClient(servers=['http://elasticsearch:9200'],
                               index='pyams_elastic_tests',
                               use_transaction=False)
        client.ensure_index(recreate=True)
        client.ensure_all_mappings(Base)
        genres, movies = get_data()
        client.index_objects(genres)
        client.index_objects(movies)
        client.refresh()

        task_info = ElasticClientInfo()
        task_info.servers = ['http://elasticsearch:9200']
        task_info.index = 'pyams_elastic_tests'
        task = ElasticTask()
        task.connection = task_info
        task.query = '''{
            "query": {
                "bool": {
                    "filter": {
                        "term": {
                            "year": 1977
                        }
                    }
                }
            },
            "size": 10,
            "_source": [
                "title",
                "document_type"
            ]
        }'''
        task.expected_results = '8'
        task.log_fields = ['title', 'missing.field']

        # check for failure
        task_info.servers = ['http://unknown_hostname:9200']
        report = StringIO()
        status, results = task.run(report)
        self.assertEqual(status, TASK_STATUS_FAIL)
        self.assertEqual(results, None)
        report.close()

        # check for error
        task_info.servers = ['http://elasticsearch:9200']

        report = StringIO()
        status, results = task.run(report)
        self.assertEqual(status, TASK_STATUS_ERROR)

        report.seek(0)
        output = report.getvalue()
        self.assertIn("expected results: 8", output)
        self.assertIn("query results: 1", output)
        report.close()

        # check for undefined results
        task.expected_results = None
        task.log_fields = ['title', 'missing.field']
        report = StringIO()
        status, results = task.run(report)
        self.assertEqual(status, TASK_STATUS_ERROR)

        report.seek(0)
        output = report.getvalue()
        self.assertIn("expected results: --", output)
        self.assertIn("query results: 1", output)
        report.close()

        # check for OK
        task.expected_results = '1'
        task.log_fields = ['title', 'missing.field']
        report = StringIO()
        status, results = task.run(report)
        self.assertEqual(status, TASK_STATUS_OK)

        report.seek(0)
        output = report.getvalue()
        self.assertIn("expected results: 1", output)
        self.assertIn("query results: 1", output)
        report.close()

        # check for range
        task.expected_results = '0-1'
        task.log_fields = ['title', 'missing.other']
        report = StringIO()
        status, results = task.run(report)
        self.assertEqual(status, TASK_STATUS_OK)

        report.seek(0)
        output = report.getvalue()
        self.assertIn("expected results: 0-1", output)
        self.assertIn("query results: 1", output)
        report.close()

        client.delete_index()
        client.close()

    def test_reindex_task(self):
        src_client = ElasticClient(servers=['http://elasticsearch:9200'],
                                   index='pyams_elastic_tests',
                                   use_transaction=False)
        src_client.ensure_index(recreate=True)
        src_client.ensure_all_mappings(Base)
        genres, movies = get_data()
        src_client.index_objects(genres)
        src_client.index_objects(movies)
        src_client.refresh()

        trg_client = ElasticClient(servers=['http://elasticsearch:9200'],
                                   index='pyams_elastic_parser_tests',
                                   use_transaction=False)

        task_source_info = ElasticClientInfo()
        task_source_info.servers = ['http://elasticsearch:9200']
        task_source_info.index = 'pyams_elastic_tests'

        task_target_info = ElasticClientInfo()
        task_target_info.servers = ['http://elasticsearch:9200']
        task_target_info.index = 'pyams_elastic_parser_tests'

        task = ElasticReindexTask()
        task.source_connection = task_source_info
        task.source_query = '''{
            "query": {
                "bool": {
                    "must": {
                        "range": {
                            "rating": {
                                "gte": 7
                            }
                        }
                    }
                }
            },
            "size": 100,
            "sort": ["_score", "year"],
            "_source": [
                "title",
                "document_type"
            ]
        }'''
        task.page_size = 3
        task.source_fields = [
            'year',
            'rating',
            'new_title=title'
        ]
        task.target_connection = task_target_info

        # check for source failure
        task_source_info.servers = ['http://unknown_hostname:9200']
        report = StringIO()
        status, results = task.run(report)
        self.assertEqual(status, TASK_STATUS_FAIL)
        self.assertEqual(results, None)
        report.close()

        # check for target failure
        task_source_info.servers = ['http://elasticsearch:9200']
        task_target_info.servers = ['http://unknown_hostname:9200']
        report = StringIO()
        status, results = task.run(report)
        self.assertEqual(status, TASK_STATUS_FAIL)
        self.assertEqual(results, None)
        report.close()

        # # check for reindex OK
        task_target_info.servers = ['http://elasticsearch:9200']

        report = StringIO()
        status, results = task.run(report)
        report.seek(0)
        output = report.getvalue()
        self.assertEqual(status, TASK_STATUS_OK)
        self.assertEqual(results, (8, 8))
        self.assertIn("total source records: 8", output)
        self.assertIn("total re-indexed records: 8", output)
        self.assertTrue(trg_client.es.indices.exists(index=trg_client.index))

        trg_client.refresh()
        query = {'query': json.loads(task.source_query).get('query')}
        count = DotDict(trg_client.es.count(index=trg_client.index, body=query))
        self.assertEqual(count.count, 8)

        # check for saved document ID
        query = json.loads(task.source_query)
        es_src_results = DotDict(src_client.es.search(index=src_client.index, **query))
        src_element = es_src_results.hits.hits[0]
        trg_element = DotDict(trg_client.es.get(id=src_element._id,
                                                index=trg_client.index))
        self.assertIsNotNone(trg_element)
        self.assertEqual(trg_element._id, src_element._id)

        # check for updated document fields
        trg_element = DotDict(trg_client.es.get(id=src_element._id,
                                                index=trg_client.index))
        self.assertEqual(trg_element._source.new_title, src_element._source.title)
        self.assertFalse('director' in trg_element._source)

        src_client.delete_index()
        src_client.close()
        trg_client.delete_index()
        trg_client.close()
