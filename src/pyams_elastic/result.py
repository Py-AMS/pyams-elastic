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

"""PyAMS_elastic.result module

This module defines Elasticsearch results management classes.
"""

__docformat__ = 'restructuredtext'

from pyams_utils.dict import DotDict


class ElasticResultRecord:
    """
    Wrapper for an Elasticsearch result record. Provides access to the indexed
    document, ES result data (like score), and the mapped object.
    """
    def __init__(self, raw):
        self.raw = DotDict(raw)

    def __repr__(self):
        return '<{} score:{} id:{} type:{}>'.format(self.__class__.__name__,
                                                    getattr(self, '_score', '-'),
                                                    self._id,
                                                    self._type)

    def __getitem__(self, key):
        return self.raw[key]

    def __contains__(self, key):
        return key in self.raw

    def __getattr__(self, key):
        source = self.raw.get('_source', {})
        fields = self.raw.get('fields', {})
        if key in source:
            return source[key]
        if key in fields:
            return fields[key]
        if key in self.raw:
            return self.raw[key]
        raise AttributeError('{!r} object has no attribute {!r}'.format(self.__class__.__name__,
                                                                        key))


class ElasticResult:
    """
    Wrapper for an Elasticsearch result set. Provides access to the documents,
    result aggregate data (like total count), facets and aggregations.

    Iterate over this object to yield document records, which are instances of
    :py:class:`ElasticResultRecord`.
    """
    def __init__(self, raw):
        self.raw = raw

    def __iter__(self):
        return iter(self.raw)

    def __repr__(self):
        return '<%s total:%s>' % (self.__class__.__name__, self.total)

    @property
    def total(self):
        """
        Return the total number of docs which would have been matched by this
        query. Note that this is not necessarily the same as the number of
        document result records associated with this object, because the query
        may have a start / size applied.
        """
        return self.raw['hits']['total']

    @property
    def facets(self):
        """
        Return the facets returned by this search query.
        """
        return self.raw.facets

    @property
    def aggregations(self):
        """
        Return aggregations returned by this search query
        """
        return self.raw.aggregations

    @property
    def suggests(self):
        """
        Return suggestions returned by this search query
        """
        return self.raw.suggest
