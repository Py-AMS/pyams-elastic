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

"""PyAMS_elastic.tests.test_dotdict module

This module is used to test DotDict class.
"""

__docformat__ = 'restructuredtext'

from unittest import TestCase

from pyams_elastic.docdict import DotDict


class TestDotDict(TestCase):
    """DotDict class test case"""

    def test_empty(self):
        """Test empty dict"""
        dd = DotDict()  # pylint: disable=invalid-name
        self.assertEqual(len(dd), 0)

    def test_get(self):
        """Test getter"""
        dd = DotDict({'a': 42,  # pylint: disable=invalid-name
                      'b': 'hello'})
        self.assertEqual(dd['b'], 'hello')
        self.assertEqual(dd.b, 'hello')

    def test_recursive(self):
        """Test recursion"""
        dd = DotDict({'a': 42,  # pylint: disable=invalid-name
                      'b': {'one': 1,
                            'two': 2,
                            'three': 3}})
        self.assertEqual(dd['b']['two'], 2)
        self.assertEqual(dd.b.two, 2)

    def test_recursive_list(self):
        """Test recursive list"""
        dd = DotDict({  # pylint: disable=invalid-name
            'organization': 'Avengers',
            'members': [
                {'id': 1, 'name': 'Bruce Banner'},
                {'id': 2, 'name': 'Tony Stark'},
                {'id': 3, 'name': 'Steve Rogers'},
                {'id': 4, 'name': 'Natasha Romanoff'}
            ]
        })
        self.assertEqual(dd.members[1].name, 'Tony Stark')

    def test_set(self):
        """Test setter"""
        dd = DotDict({'a': 4,  # pylint: disable=invalid-name
                      'b': 9})
        dd.c = 16
        self.assertEqual(dd.c, 16)
        self.assertEqual(dd['c'], 16)

    def test_del(self):
        """Test deletion"""
        dd = DotDict({'a': 123,  # pylint: disable=invalid-name
                      'b': 456})
        del dd.b
        self.assertEqual(dict(dd), {'a': 123})

    def test_repr(self):
        """Test repr"""
        dd = DotDict({'a': 1})  # pylint: disable=invalid-name
        self.assertEqual(repr(dd), "<DotDict({'a': 1})>")
