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

"""PyAMS_elastic.tests.test_result module

Elasticsearch query result test class.
"""

__docformat__ = 'restructuredtext'

from unittest import TestCase

from pyams_elastic.result import ElasticResult, ElasticResultRecord


sample_record1 = {
    '_score': 0.85,
    '_id': 1234,
    '_type': 'Thing',
    '_source': {
        'name': 'Grue',
        'color': 'Dark'
    }
}


sample_record2 = {
    '_score': 0.62,
    '_id': 1249,
    '_type': 'Thing',
    '_source': {
        'name': 'Widget',
        'color': 'Red'
    }
}


sample_result = {
    '_shards': {
        'failed': 0,
        'successful': 2,
        'total': 2
    },
    'hits': {
        'hits': [
            sample_record1,
            sample_record2,
        ],
        'max_score': 0.85,
        'total': 2
    },
    'suggest': {
        'check1': [
            {
                'text': 'sdlr',
                'length': 4,
                'options': [
                    {'text': 'sldr',
                     'freq': 35,
                     'score': 0.75},
                    {'text': 'sale',
                     'freq': 94,
                     'score': 0.5},
                ],
                'offset': 0,
            }
        ]
    },
    'timed_out': False,
    'took': 1
}


class TestResult(TestCase):
    """Result test case"""

    def _make_result(self):  # pylint: disable=no-self-use
        """Create result"""
        return ElasticResult(sample_result)

    def test_result_repr(self):
        """Test result output"""
        result = self._make_result()
        self.assertIn('total:2', repr(result))


class TestResultRecord(TestCase):
    """Result record test case"""

    def _make_record(self):  # pylint: disable=no-self-use
        """Create record"""
        return ElasticResultRecord(sample_record1)

    def test_record_repr(self):
        """Test record output"""
        record = self._make_record()
        s = repr(record)  # pylint: disable=invalid-name
        self.assertIn('Thing', s)
        self.assertIn('1234', s)

    def test_record_getitem(self):
        """Test record item getter"""
        record = self._make_record()
        self.assertEqual(record['_type'], 'Thing')

    def test_record_attr_source(self):
        """Test record source attribute"""
        record = self._make_record()
        self.assertEqual(record.name, 'Grue')

    def test_record_attr_raw(self):
        """Test record raw attribute"""
        record = self._make_record()
        self.assertEqual(record._id, 1234)  # pylint: disable=protected-access

    def test_record_attr_nonexistent(self):
        """Test record missing attribute"""
        record = self._make_record()
        with self.assertRaises(AttributeError):
            record.nonexistent  # pylint: disable=pointless-statement

    def test_record_contains(self):
        """Test record container"""
        record = self._make_record()
        self.assertIn('_score', record)
        self.assertNotIn('foo', record)
