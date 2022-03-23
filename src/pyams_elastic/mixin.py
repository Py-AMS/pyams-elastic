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

"""PyAMS_elastic.mixin module

This module provides mixin class which can be used to define classes of documents
which can be easily indexed and searched.
"""

import copy

__docformat__ = 'restructuredtext'


class ElasticMixin:
    """
    Mixin for SQLAlchemy classes that use ESMapping.
    """

    @classmethod
    def elastic_mapping(cls):
        """
        Return an ES mapping for the current class. Should basically be some
        form of ``return ESMapping(...)``.
        """
        raise NotImplementedError("ES classes must define a mapping")

    def elastic_document(self):
        """Apply the class ES mapping to the current instance."""
        return self.elastic_mapping()(self)

    @classmethod
    def get_document_type(cls):
        """
        Return a string keyword matching document type
        """
        return cls.__name__

    @property
    def document_type(self):
        """Document type getter"""
        return self.__class__.get_document_type()


class ESMapping:
    """
    ESMapping defines a tree-like DSL for building Elasticsearch mappings.

    Calling dict(es_mapping_object) produces an Elasticsearch mapping
    definition appropriate for pyes.

    Applying an ESMapping to another object returns an Elasticsearch document.
    """

    def __init__(self, *args, **kwargs):
        self.filter = kwargs.pop("filter", None)
        self.name = kwargs.pop("name", None)
        self.attr = kwargs.pop("attr", None)

        # Automatically map the id field
        self.parts = {
            "_id": ESField("_id", attr="id")
        }

        # Map implicit args
        for arg in args:
            self.parts[arg.name] = arg

        # Map explicit kwargs
        for key, value in kwargs.items():  # pylint: disable=invalid-name
            if isinstance(value, dict):
                value, value.parts = ESMapping(), value  # pylint: disable=invalid-name
            if isinstance(value, ESMapping):
                value.name = key
            self.parts[key] = value

    def __iter__(self):
        for key, value in self.parts.items():  # pylint: disable=invalid-name
            if isinstance(value, ESMapping):
                value = dict(value)  # pylint: disable=invalid-name
            if value:
                yield key, value

    iteritems = __iter__
    items = __iter__

    def __contains__(self, key):
        return key in self.parts

    def __getitem__(self, key):
        return self.parts[key]

    def __setitem__(self, key, value):  # pylint: disable=invalid-name
        self.parts[key] = value

    def update(self, mapping):  # pylint: disable=invalid-name
        """
        Return a copy of the current mapping merged with the properties of
        another mapping. *update* merges just one level of hierarchy and uses
        simple assignment below that.
        """
        def is_mapping(src):
            return hasattr(src, "parts") and src.parts

        def merge_once(map1, map2):
            for key, value in map2.parts.items():
                if key in map1 and is_mapping(map1[key]) and is_mapping(value):
                    map1[key].parts.update(value.parts)
                else:
                    map1[key] = value
            return map1

        return merge_once(copy.copy(self), copy.copy(mapping))

    @property
    def properties(self):
        """
        Return the dictionary {name: property, ...} describing the top-level
        properties in this mapping, or None if this mapping is a leaf.
        """
        props = self.parts.get("properties")
        if props:
            return props.parts
        return None

    def __call__(self, instance):
        """
        Apply this mapping to an instance to return a document.

        Returns a dictionary {name: value, ...}.
        """
        if self.attr or self.name:
            instance = getattr(instance, self.attr or self.name)
        if self.filter:
            instance = self.filter(instance)
        if self.properties is None:
            return instance
        return dict((key, value(instance)) for key, value in self.properties.items())


class ESProp(ESMapping):
    """A leaf property."""

    # pylint: disable=redefined-builtin,super-init-not-called
    def __init__(self, name, filter=None, attr=None, **kwargs):
        self.name = name
        self.attr = attr
        self.filter = filter
        self.parts = kwargs


class ESField(ESProp):
    """
    A leaf property that doesn't emit a mapping definition.

    This behavior is useful if you want to allow Elasticsearch to
    automatically construct an appropriate mapping while indexing.
    """

    def __iter__(self):
        return iter(())


class ESText(ESProp):
    """A string text property"""

    def __init__(self, name, **kwargs):
        ESProp.__init__(self, name, type="text", **kwargs)


class ESKeyword(ESProp):
    """A keyword text property"""

    def __init__(self, name, **kwargs):
        ESProp.__init__(self, name, type="keyword", **kwargs)


class ESObject(ESProp):
    """An object property"""

    def __init__(self, name, **kwargs):
        ESProp.__init__(self, name, type="object", **kwargs)
