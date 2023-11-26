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

"""PyAMS_elastic.tests.data module

This module is used to create test data.
"""

__docformat__ = 'restructuredtext'

from hashlib import sha1

from sqlalchemy import Column, ForeignKey, orm, types
from sqlalchemy.orm import declarative_base
from zope.interface import provider

from pyams_elastic.interfaces import IElasticMapping
from pyams_elastic.mixin import ESField, ESKeyword, ESMapping, ESText, ElasticMixin


Base = declarative_base()


@provider(IElasticMapping)
class Genre(Base, ElasticMixin):

    __tablename__ = 'genres'

    id = Column(types.String(40), primary_key=True)
    title = Column(types.Unicode(40))

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.id = sha1(self.title.encode('utf-8')).hexdigest()

    @classmethod
    def elastic_mapping(cls):
        return ESMapping(
            # analyzer='content',
            properties=ESMapping(
                ESKeyword('document_type'),
                ESText('title')))


@provider(IElasticMapping)
class Movie(Base, ElasticMixin):

    __tablename__ = 'movies'

    id = Column(types.String(40), primary_key=True)
    title = Column(types.Unicode(40))
    director = Column(types.Unicode(40))
    year = Column(types.Integer)
    rating = Column(types.Numeric)
    genre_id = Column(None, ForeignKey('genres.id'))

    genre = orm.relationship('Genre')

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.id = sha1(self.title.encode('utf-8')).hexdigest()

    @property
    def genre_title(self):
        return self.genre and self.genre.title or ''

    @classmethod
    def elastic_mapping(cls):
        return ESMapping(
            properties=ESMapping(
                ESKeyword('document_type'),
                ESText('title'),
                ESText('director'),
                ESField('year'),
                ESField('rating'),
                ESKeyword('genre_title')))


class Unindexed(Base):
    # Does not inherit from ElasticMixin.

    __tablename__ = 'unindexed'

    id = Column(types.Integer, primary_key=True)


def get_data():
    mystery = Genre(title='Mystery')
    comedy = Genre(title='Comedy')
    action = Genre(title='Action')
    drama = Genre(title='Drama')

    genres = [mystery, comedy, action, drama]

    movies = [
        Movie(
            title='To Catch a Thief',
            director='Alfred Hitchcock',
            year=1955,
            rating=7.5,
            genre=mystery,
            genre_id=mystery.id,
        ),
        Movie(
            title='Vertigo',
            director='Alfred Hitchcock',
            year=1958,
            rating=8.5,
            genre=mystery,
            genre_id=mystery.id,
        ),
        Movie(
            title='North by Northwest',
            director='Alfred Hitchcock',
            year=1959,
            rating=8.5,
            genre=mystery,
            genre_id=mystery.id,
        ),
        Movie(
            title='Destination Tokyo',
            director='Delmer Daves',
            year=1943,
            rating=7.1,
            genre=action,
            genre_id=action.id,
        ),
        Movie(
            title='Annie Hall',
            director='Woody Allen',
            year=1977,
            rating=8.2,
            genre=comedy,
            genre_id=comedy.id,
        ),
        Movie(
            title='Sleeper',
            director='Woody Allen',
            year=1973,
            rating=7.3,
            genre=comedy,
            genre_id=comedy.id,
        ),
        Movie(
            title='Captain Blood',
            director='Michael Curtiz',
            year=1935,
            rating=7.8,
            genre=action,
            genre_id=action.id,
        ),
        Movie(
            title='Metropolis',
            director='Fritz Lang',
            year=1927,
            rating=8.4,
            genre=drama,
            genre_id=drama.id,
        )]
    return genres, movies
