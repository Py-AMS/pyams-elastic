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

from io import StringIO
from unittest import TestCase

from zope.interface import Invalid
from zope.schema._bootstrapinterfaces import WrongType

from pyams_elastic.client import ElasticClient, ElasticClientInfo
from pyams_elastic.task import ElasticTask
from pyams_elastic.task.interfaces import IElasticTaskInfo
from pyams_elastic.tests.data import Base, get_data
from pyams_scheduler.interfaces.task import TASK_STATUS_ERROR, TASK_STATUS_OK


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
        client = ElasticClient(servers=['elasticsearch:9200'],
                               index='pyams_elastic_tests',
                               use_transaction=False)
        client.ensure_index(recreate=True)
        client.ensure_all_mappings(Base)
        genres, movies = get_data()
        client.index_objects(genres)
        client.index_objects(movies)
        client.refresh()

        task_info = ElasticClientInfo()
        task_info.servers = ['elasticsearch:9200']
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

        # check for error
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
