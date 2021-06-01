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

"""PyAMS_elastic.query module

This module defines Elasticsearch query class.
"""

__docformat__ = 'restructuredtext'

import inspect
from functools import wraps

from elasticsearch_dsl import A, Q, Search

from pyams_elastic.mixin import ElasticMixin
from pyams_elastic.result import ElasticResult


ARBITRARILY_LARGE_SIZE = 10000


def filters(f):  # pylint: disable=invalid-name
    """Query filters appender

    A convenience decorator to wrap query methods that are adding filters. To
    use, simply make a method that returns a filter dict in elasticsearch's
    JSON object format.
    """
    @wraps(f)
    def wrapped(self, *args, **kwargs):
        val = f(self, *args, **kwargs)
        if self.query is None:
            self.query = val
        else:
            self.query &= val
        return self
    return wrapped


def sorting(f):  # pylint: disable=invalid-name
    """Update current search sort order"""
    @wraps(f)
    def wrapped(self, *args, **kwargs):
        val = f(self, *args, **kwargs)
        self.sorts.append(val)
        return self
    return wrapped


def bucket(f):  # pylint: disable=invalid-name
    """Update query aggregates"""
    @wraps(f)
    def wrapped(self, name, *args, **kwargs):
        val = f(self, name, *args, **kwargs)
        self.dsl.aggs.bucket(name, val)
        return self
    return wrapped


class ElasticQuery:
    """
    Wrapper around Elasticsearch-DSL Search object
    """

    def __init__(self, client, classes=None, query=None):
        self.client = client
        self.dsl = Search(using=client.es,
                          index=client.index)
        if isinstance(query, str):
            self.query = Q('simple_query_string', **{'query': query})
        else:
            self.query = query
        if classes:
            docs_types = [
                cls.get_document_type()
                if inspect.isclass(cls) and issubclass(cls, ElasticMixin) else cls
                for cls in classes
            ]
            docs_types_filter = \
                Q('terms', **{'document_type': docs_types}) | \
                Q('terms', **{'document_type.keyword': docs_types})
            self.filter(docs_types_filter)
        self.sorts = []
        self.aggs = []
        self._start = None
        self._size = None

    @filters
    def ids(self, values):  # pylint: disable=no-self-use
        """Add filter documents on IDs"""
        if not isinstance(values, (list, tuple, set)):
            values = {values}
        return Q('ids', **{'values': list(map(str, values))})

    @filters
    def match_all_query(self):  # pylint: disable=no-self-use
        """Static method to return a filter which will match everything"""
        return Q('match_all')

    @filters
    def text_query(self, phrase, fields=None):  # pylint: disable=no-self-use
        """Static method to return a filter matching a text query"""
        query = {'query': phrase}
        if fields:
            query['fields'] = fields
        return Q('multi_match', **query)

    @filters
    def filter(self, query):  # pylint: disable=no-self-use,redefined-builtin
        """Add custom query to filters"""
        return query

    @filters
    def match(self, term, value, **kwargs):  # pylint: disable=no-self-use
        """Add match filter"""
        query = {'query': value}
        query.update(kwargs)
        return Q('match', **{term: query})

    @filters
    def filter_term(self, term, value, boost=1.0):  # pylint: disable=no-self-use
        """Add term filter"""
        return Q('term', **{term: {'value': value, 'boost': boost}})

    @filters
    def filter_terms(self, term, values, boost=1.0):  # pylint: disable=no-self-use
        """Add terms filters"""
        return Q('terms', **{term: values, 'boost': boost})

    @filters
    def filter_value_upper(self, term, upper):  # pylint: disable=no-self-use
        """Filter documents for which term is lower or equal to *upper*"""
        return Q('range', **{term: {'to': upper, 'include_upper': True}})

    @filters
    def filter_value_lower(self, term, lower):  # pylint: disable=no-self-use
        """Filter documents for which term is higher or equal to *lower*"""
        return Q('range', **{term: {'from': lower, 'include_lower': True}})

    @sorting
    def order_by(self, key, desc=False, **kwargs):  # pylint: disable=no-self-use
        """Sort results on given fields in ascending order, unless if *desc* is True"""
        order = {'order': 'desc' if desc else 'asc'}
        order.update(kwargs)
        return {key: order}

    def offset(self, n):  # pylint: disable=invalid-name
        """Start results at document ``n``"""
        if self._start is not None:
            raise ValueError('This query already has an offset applied.')
        self._start = n
        return self
    start = offset

    def limit(self, n):  # pylint: disable=invalid-name
        """Limit results at document ``n``"""
        if self._size is not None:
            raise ValueError('This query already has a limit applied.')
        self._size = n
        return self
    size = limit

    @bucket
    def add_term_aggregate(self, name, field, **kwargs):
        # pylint: disable=no-self-use,unused-argument
        """Add simple term aggregate"""
        return A('terms', field=field, **kwargs)

    @bucket
    def add_range_aggregate(self, name, field, ranges, **kwargs):
        # pylint: disable=no-self-use,unused-argument
        """Add range aggregate"""
        return A('range', field=field, ranges=ranges, **kwargs)

    def add_term_suggester(self, name, field, text):  # pylint: disable=no-self-use
        """Add term suggester"""
        self.dsl = self.dsl.suggest(name, text, term={'field': field})
        return self

    def search(self, start=0, size=ARBITRARILY_LARGE_SIZE, fields=None):
        """Start search"""
        if not self.query:
            self.query = self.match_all_query()
        query = self.dsl.query(self.query)

        if self.sorts:
            query = query.sort(*self.sorts)

        q_start = self._start or 0
        q_size = self._size or ARBITRARILY_LARGE_SIZE

        if start is not None:
            q_start = q_start + start
        if size is not None:
            q_size = max(0,
                         size if q_size is None else min(size, q_size - q_start))

        if q_start:
            q_size = min(q_size, ARBITRARILY_LARGE_SIZE - q_start)

        if q_start:
            query = query.extra(from_=q_start)
        if q_size:
            query = query.extra(size=q_size)

        if fields:
            query = query.source(fields)

        return query.execute()

    def execute(self, start=None, size=None, fields=None):
        """Execute this query and return a result set."""
        return ElasticResult(self.search(start=start, size=size, fields=fields))

    def count(self):
        """Return search total results"""
        res = self.search(size=0)
        return res.hits.total.value
