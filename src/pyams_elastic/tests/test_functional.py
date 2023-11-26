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

"""PyAMS_elastic.tests.test_functional module

This module provides tests cases for Elasticsearch client.
"""

__docformat__ = 'restructuredtext'

import unittest
from unittest import TestCase

from elasticsearch import NotFoundError
from elasticsearch_dsl.query import MatchAll

from pyams_elastic.client import ElasticClient
from pyams_elastic.tests.data import Base, Genre, Movie, get_data


class ClientTestLayer:
    """Base test layer"""

    @classmethod
    def setUp(cls):
        cls.client = ElasticClient(servers=['http://elasticsearch:9200'],
                                   index='pyams_elastic_tests',
                                   use_transaction=False)
        if cls.client.es.indices.exists(index=cls.client.index):
            cls.client.delete_index()

    @classmethod
    def tearDown(cls):
        cls.client.delete_index()
        cls.client.close()


class TestClient(TestCase):
    """Elasticsearch client test"""

    layer = ClientTestLayer

    @classmethod
    def setUpClass(cls):
        cls.layer.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.layer.tearDown()

    @property
    def client(self):
        return self.layer.client

    def test_ensure_index(self):
        """Test for index creation"""
        # First ensure it with no args.
        self.client.ensure_index()
        # Recreate.
        self.client.ensure_index(recreate=True)
        # Delete explicitly.
        self.client.delete_index()
        # One more time.
        self.client.ensure_index(recreate=True)

    def test_ensure_mapping_recreate(self):
        """Test mapping creation"""
        # First create.
        self.client.ensure_mapping(Movie)
        # Recreate.
        self.client.ensure_mapping(Movie, recreate=True)

    def test_ensure_all_mappings(self):
        """Test all mappings creation"""
        self.client.ensure_index(recreate=True)
        self.client.ensure_all_mappings(Base)

    def test_get_mappings(self):
        """Test get mappings"""
        mapping = self.client.get_mappings()
        self.assertEqual(mapping['properties']['title'],
                         {'type': 'text'})
        self.assertIn('director', mapping['properties'])

    def test_disable_indexing(self):
        """Test disabled indexing"""
        self.client.ensure_index(recreate=True)

        self.client.disable_indexing = True
        genre = Genre(title='Procedural Electronica')
        self.client.index_object(genre)

        num = self.client.query(Genre, query='Electronica').count()
        self.assertEqual(num, 0)

        self.client.delete_object(genre)
        self.client.disable_indexing = False

    def test_index_and_delete_document(self):
        """Test index and delete document"""
        doc = dict(document_type='Answer',
                   question='What is the ultimate question?')
        doc_id = 42

        self.client.index_document(id=doc_id,
                                   doc=doc)
        self.client.refresh()

        query = self.client.query().ids(doc_id)
        self.assertEqual(query.count(), 1)

        self.client.delete_document(id=doc_id)
        self.client.refresh()

        query = self.client.query().ids(doc_id)
        self.assertEqual(query.count(), 0)

    def test_index_and_delete_object(self):
        genre = Genre(title='Sci-Fi Romance')
        self.client.index_object(genre)
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Romance')
        self.assertEqual(query.count(), 1)

        self.client.delete_object(genre)
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Romance')
        self.assertEqual(query.count(), 0)

    def test_object_update(self):
        genre = Genre(title='Sci-Fi Romance')
        self.client.index_object(genre)
        self.client.refresh()

        genre.title = 'Sci-Fi Fantasy'
        self.client.update_object(genre, ['title'])
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Fantasy')
        self.assertEqual(query.count(), 1)

        self.client.delete_object(genre)
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Fantasy')
        self.assertEqual(query.count(), 0)

    def test_document_update(self):
        genre = Genre(title='Sci-Fi Romance')
        self.client.index_object(genre)
        self.client.refresh()

        genre.title = 'Sci-Fi Fantasy'
        self.client.update_document(genre.id, {
            'title': genre.title
        })
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Fantasy')
        self.assertEqual(query.count(), 1)

        self.client.delete_object(genre)
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Fantasy')
        self.assertEqual(query.count(), 0)

    def test_update_with_script(self):
        genre = Genre(title='Sci-Fi Romance')
        self.client.index_object(genre)
        self.client.refresh()

        genre.title = 'Sci-Fi Fantasy'
        result, data = self.client.update_document(genre.id, script={
            'source': "ctx._source.title = params.title",
            'params': {
                'title': genre.title
            }
        })
        self.assertEqual(result, 'updated')

        self.client.delete_object(genre)
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Romance')
        self.assertEqual(query.count(), 0)
        query = self.client.query(Genre).match('title', 'Sci-Fi Fantasy')
        self.assertEqual(query.count(), 0)

    def test_update_with_args(self):
        genre = Genre(title='Sci-Fi Romance')
        self.client.index_object(genre)
        self.client.refresh()

        genre.title = 'Sci-Fi Fantasy'
        result, data = self.client.update_document(genre.id, {
            'title': genre.title
        }, _source=['title'])
        self.assertEqual(result, 'updated')
        self.assertEqual(data.title, 'Sci-Fi Fantasy')

        self.client.delete_object(genre)
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Romance')
        self.assertEqual(query.count(), 0)
        query = self.client.query(Genre).match('title', 'Sci-Fi Fantasy')
        self.assertEqual(query.count(), 0)

    def test_noop_update(self):
        genre = Genre(title='Sci-Fi Romance')
        self.client.index_object(genre)
        self.client.refresh()

        result, data = self.client.update_document(genre.id, {
            'title': genre.title
        }, _source=['title'])
        self.assertEqual(result, 'noop')
        self.assertEqual(data.title, 'Sci-Fi Romance')

        self.client.delete_object(genre)
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Romance')
        self.assertEqual(query.count(), 0)

    def test_force_update(self):
        genre = Genre(title='Sci-Fi Romance')
        self.client.index_object(genre)
        self.client.refresh()

        result, data = self.client.update_document(genre.id, {
            'title': genre.title
        }, detect_noop=False, _source=['title'])
        self.assertEqual(result, 'updated')
        self.assertEqual(data.title, 'Sci-Fi Romance')

        self.client.delete_object(genre)
        self.client.refresh()

        query = self.client.query(Genre).match('title', 'Sci-Fi Romance')
        self.assertEqual(query.count(), 0)

    def test_update_nonexisting_document(self):
        with self.assertRaises(NotFoundError):
            self.client.update_document(id=888, doc={
                'title': "Missing document"
            })

    def test_update_nonexisting_document_safe(self):
        result, data = self.client.update_document(id=888, doc={
            'title': "Missing document"
        }, safe=True)
        self.assertEqual(result, 'notfound')

    def test_delete_nonexistent_document(self):
        with self.assertRaises(NotFoundError):
            self.client.delete_document(id=1337)

    def test_delete_nonexistent_document_safe(self):
        self.client.delete_document(id=888,
                                    safe=True)

    def test_delete_nonexistent_object(self):
        genre = Genre(title='Geriatric Philosophy')
        with self.assertRaises(NotFoundError):
            self.client.delete_object(genre)

    def test_delete_nonexistent_object_safe(self):
        genre = Genre(title='Geriatric Philosophy')
        self.client.delete_object(genre, safe=True)


class QueryTestLayer:

    @classmethod
    def setUp(cls):
        cls.client = ElasticClient(servers=['http://elasticsearch:9200'],
                                   index='pyams_elastic_tests',
                                   use_transaction=False)
        cls.client.ensure_index(recreate=True)
        cls.client.ensure_all_mappings(Base, recreate=True)

        cls.genres, cls.movies = get_data()

        cls.client.index_objects(cls.genres)
        cls.client.index_objects(cls.movies)
        cls.client.refresh()

    @classmethod
    def tearDown(cls):
        cls.client.delete_index()
        cls.client.close()


class TestQuery(TestCase):

    layer = QueryTestLayer

    @classmethod
    def setUpClass(cls):
        cls.layer.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.layer.tearDown()

    @property
    def client(self):
        return self.layer.client

    def test_match_all(self):
        q = self.client.query(Movie)
        result = q.match_all_query().execute()
        self.assertEqual(result.total.value, 8)

    def test_query_all(self):
        result = self.client.query(Movie).execute()
        self.assertEqual(result.total.value, 8)

        records = list(result)
        titles = [rec.title for rec in records]
        self.assertIn('Metropolis', titles)

    def test_text_query(self):
        q = self.client.query(Movie)
        result = q.text_query('allen').execute()
        self.assertEqual(result.total.value, 2)

        records = list(result)
        titles = [rec.title for rec in records]
        self.assertSequenceEqual(titles, ['Annie Hall', 'Sleeper'])

    def test_text_query_with_fields(self):
        q = self.client.query(Movie)
        result = q.text_query('curtiz', fields=['director']).execute()
        self.assertEqual(result.total.value, 1)

        q = self.client.query(Movie)
        result = q.text_query('curtiz', fields=['title', 'director']).execute()
        self.assertEqual(result.total.value, 1)

        q = self.client.query(Movie)
        result = q.text_query('curtiz', fields=['title']).execute()
        self.assertEqual(result.total.value, 0)

    def test_sorted(self):
        result = self.client.query(Movie).order_by('year', desc=True).execute()
        self.assertEqual(result.total.value, 8)

        records = list(result)
        self.assertEqual(records[0].title, 'Annie Hall')
        self.assertEqual(records[0].meta.score, None)

    def test_keyword(self):
        q = self.client.query(Movie, query='hitchcock')
        result = q.execute()
        self.assertEqual(result.total.value, 3)

        records = list(result)
        titles = [rec.title for rec in records]
        self.assertIn('To Catch a Thief', titles)

    def test_filter_year_lower(self):
        q = self.client.query(Movie)
        # Movies made after 1960.
        q = q.filter_value_lower('year', 1960)
        result = q.execute()
        self.assertEqual(result.total.value, 2)

        records = list(result)
        titles = [rec.title for rec in records]
        self.assertEqual(['Annie Hall', 'Sleeper'], sorted(titles))

    def test_filter_rating_upper(self):
        q = self.client.query(Movie)
        q = q.filter_value_upper('rating', 7.5)
        result = q.execute()
        self.assertEqual(result.total.value, 3)

        records = list(result)
        titles = [rec.title for rec in records]
        self.assertIn('Destination Tokyo', titles)

    def test_filter_term_int(self):
        q = self.client.query(Movie).\
            filter_term('year', 1927)
        result = q.execute()
        self.assertEqual(result.total.value, 1)

        records = list(result)
        titles = [rec.title for rec in records]
        self.assertIn('Metropolis', titles)

    def test_filter_terms_int(self):
        q = self.client.query(Movie).\
            filter_terms('year', [1927, 1958])
        result = q.execute()
        self.assertEqual(result.total.value, 2)

        records = list(result)
        titles = set(rec.title for rec in records)
        self.assertEqual({'Metropolis', 'Vertigo'}, titles)

    def test_offset(self):
        q = self.client.query(Movie).order_by('year').offset(4)
        result = q.execute()
        self.assertEqual(result.total.value, 8)

        records = list(result)
        self.assertEqual(len(records), 4)
        self.assertEqual(records[0].title, 'Vertigo')

    def test_offset_with_start(self):
        # If you apply .execute(start=N) on a query that already has limit M,
        # the 'start position' actually used should be M+N.
        q = self.client.query(Movie).order_by('year').offset(2)
        result = q.execute(start=2)
        # XXX How should this behave?
        self.assertEqual(result.total.value, 8)

        records = list(result)
        self.assertEqual(len(records), 4)
        self.assertEqual(records[0].title, 'Vertigo')

    def test_offset_twice(self):
        q = self.client.query(Movie).order_by('year').offset(4)
        with self.assertRaises(ValueError):
            q.offset(7)

    def test_limit(self):
        q = self.client.query(Movie).order_by('year').limit(3)
        result = q.execute()
        self.assertEqual(result.total.value, 8)

        records = list(result)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].title, 'Metropolis')

    def test_limit_with_size(self):
        q = self.client.query(Movie).order_by('year').limit(6)
        result = q.execute(size=3)
        # XXX How should this behave?
        self.assertEqual(result.total.value, 8)

        records = list(result)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].title, 'Metropolis')

    def test_limit_twice(self):
        q = self.client.query(Movie).order_by('year').limit(3)
        with self.assertRaises(ValueError):
            q.limit(5)

    def test_count(self):
        q = self.client.query(Movie)
        self.assertEqual(q.count(), 8)

    def test_get_tuple(self):
        genre = Genre(title='Mystery')
        record = self.client.get(('Genre', genre.id))
        self.assertEqual(record.title, 'Mystery')

    def test_get_object(self):
        genre = Genre(title='Mystery')
        record = self.client.get(genre)
        self.assertEqual(record.title, 'Mystery')

    def test_add_range_aggregate(self):
        q = self.client.query(Movie). \
            add_range_aggregate(name='era_hist',
                                field='year',
                                ranges=[
                                    {"to": 1950},
                                    {"from": 1950, "to": 1970},
                                    {"from": 1970, "to": 1990},
                                    {"from": 1990}
                                ])

        result = q.execute()
        aggregations = result.aggregations
        self.assertEqual('era_hist' in aggregations, True)
        histogram = aggregations['era_hist']

        self.assertEqual(len(histogram), 4)
        self.assertEqual(histogram[1]['from'], 1950)
        self.assertEqual(histogram[1]['to'], 1970)
        self.assertEqual(histogram[1]['doc_count'], 3)

    def test_add_term_aggregate(self):
        q = self.client.query(Movie).\
            add_term_aggregate(name='genre_hist',
                               field='genre_title',
                               size=3)

        result = q.execute()
        aggregations = result.aggregations
        self.assertEqual('genre_hist' in aggregations, True)
        histogram = aggregations['genre_hist']

        self.assertEqual(len(histogram), 3)
        self.assertEqual(histogram[0]['doc_count'], 3)
        self.assertEqual(histogram[0]['key'], 'Mystery')

    def test_raw_query(self):
        raw_query = MatchAll()
        q = self.client.query(Movie, query=raw_query)
        result = q.execute()
        self.assertEqual(result.total.value, 8)

    def test_query_fields(self):
        q = self.client.query(Movie, query='hitchcock')
        result = q.execute(fields=['title'])
        self.assertEqual(result.total.value, 3)

        records = list(result)
        titles = [rec.title for rec in records]
        self.assertIn('To Catch a Thief', titles)

    def test_add_term_suggester(self):
        q = self.client.query(Movie).\
            add_term_suggester('suggest1',
                               field='title',
                               text='vrtigo')

        result = q.execute()
        self.assertIn('suggest1', result.suggests)
        suggest = result.suggests['suggest1']
        options = suggest[0].options
        self.assertGreater(len(options), 0)
        self.assertEqual(options[0].text, 'vertigo')


if __name__ == '__main__':
    unittest.main()
