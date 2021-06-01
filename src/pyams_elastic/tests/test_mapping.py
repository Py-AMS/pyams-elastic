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

"""PyAMS_elastic.tests.test_mapping module

Small module used to test mappings.
"""

__docformat__ = 'restructuredtext'

from unittest import TestCase

from pyramid.config import Configurator
from sqlalchemy import Column, types

from pyams_elastic.interfaces import IElasticMappingExtension
from pyams_elastic.mixin import ESField, ESMapping, ESObject, ESText, ElasticMixin
from pyams_elastic.tests.data import Base, Movie
from pyams_utils.adapter import adapter_config


class Actor(Base, ElasticMixin):
    """Simple movie extension mapping"""

    __tablename__ = 'actors'

    id = Column(types.String(40), primary_key=True)
    name = Column(types.Unicode(40))
    birth_date = Column(types.Date())

    @classmethod
    def elastic_mapping(cls):
        return ESMapping(
            properties=ESMapping(
                actor=ESObject(
                    'actor',
                    properties=ESMapping(
                        ESText('name'),
                        ESField('birth_date')
                    )
                )
            )
        )


class TestMapping(TestCase):

    def test_base_mapping(self):
        mapping = Movie.elastic_mapping()
        self.assertIn('document_type', mapping.properties)
        self.assertEqual(mapping.properties['document_type'].parts['type'], 'keyword')

    def test_mapping_update(self):
        movie_mapping = Movie.elastic_mapping()
        actor_mapping = Actor.elastic_mapping()
        movie_mapping.update(actor_mapping)
        self.assertIn('document_type', movie_mapping.properties)
        self.assertIn('actor', movie_mapping.properties)
        self.assertIn('birth_date', movie_mapping.properties['actor'].properties)
