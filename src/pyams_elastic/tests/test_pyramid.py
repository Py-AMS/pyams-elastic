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

"""PyAMS_elastic.tests.test_pyramid module

Pyramid integration tests.
"""

__docformat__ = 'restructuredtext'

from datetime import datetime
from unittest import TestCase
from urllib.parse import urlencode

from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPFound
from pyramid.threadlocal import RequestContext
from sqlalchemy import Column, types
from sqlalchemy.orm import declarative_base
from webtest import TestApp

from pyams_elastic.client import ElasticClient, ElasticClientInfo
from pyams_elastic.include import get_client
from pyams_elastic.mixin import ESKeyword, ESMapping, ESText, ElasticMixin
from pyams_utils.request import check_request

Base = declarative_base()


class Todo(Base, ElasticMixin):

    __tablename__ = 'todos'

    id = Column(types.Integer, primary_key=True)
    description = Column(types.Unicode(40))

    @classmethod
    def elastic_mapping(cls):
        return ESMapping(
            # analyzer='content',
            properties=ESMapping(
                ESKeyword('document_type'),
                ESText('description')))


def index_view(request):
    es_client = get_client(request)
    es_client.refresh()
    result = es_client.query(Todo).execute()
    return {
        'todos': [rec.to_dict() for rec in result],
        'count': result.total.value
    }


def add_view(request):
    es_client = get_client(request)
    for s in request.params['description'].split(', '):
        todo = Todo(description=s)
        es_client.index_object(todo)
    if request.params.get('fail_after_index'):
        raise RuntimeError('fail!')
    return HTTPFound(location=request.route_url('index'))


def make_app():
    settings = {
        'pyams_elastic.index': 'pyams_elastic_tests_app',
        'pyams_elastic.servers': ['http://elasticsearch:9200'],
    }
    config = Configurator(settings=settings)
    config.include('pyramid_tm')
    config.include('cornice')
    config.include('pyams_utils')
    config.include('pyams_elastic')

    config.add_route('index', '/')
    config.add_view(index_view, route_name='index', renderer='json')

    config.add_route('add', '/add')
    config.add_view(add_view, route_name='add')

    es_client = get_client(config)
    es_client.ensure_index(recreate=True)

    sample = Todo(description='Example to-do item')
    es_client.index_object(sample, immediate=True)

    return config.make_wsgi_app()


class PyramidTestLayer:

    @classmethod
    def setUp(cls):
        cls.app = TestApp(make_app())

    @classmethod
    def tearDown(cls):
        client = get_client(cls.app.app)
        client.delete_index()


class TestPyramid(TestCase):

    layer = PyramidTestLayer

    @classmethod
    def setUpClass(cls):
        cls.layer.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.layer.tearDown()

    @property
    def app(self):
        return self.layer.app

    def test_index(self):
        resp = self.app.get('/')
        resp.mustcontain('Example')

    def test_add_successful(self):
        params = urlencode({
            'description': 'Zygomorphic',
        })
        self.app.get('/add?' + params, status=302)
        # Check that new todo is now in the index.
        resp = self.app.get('/')
        resp.mustcontain('Zygomorphic')

    def test_add_fail(self):
        params = urlencode({
            'description': 'Nucleoplasm',
            'fail_after_index': True,
        })
        with self.assertRaises(RuntimeError):
            self.app.get('/add?' + params)

        resp = self.app.get('/')
        # Check that new todo is *not* in the index.
        self.assertNotIn('Nucleoplasm', resp.body.decode('utf8'))

    def test_add_alternate(self):
        params = urlencode({
            'description': 'Banana',
        })
        self.app.get('/add?' + params, status=302)
        resp = self.app.get('/')
        resp.mustcontain('Banana')

        params = urlencode({
            'description': 'Apple',
            'fail_after_index': 1,
        })
        with self.assertRaises(RuntimeError):
            self.app.get('/add?' + params)
        resp = self.app.get('/')
        self.assertNotIn('Apple', resp.body.decode('utf8'))

        params = urlencode({
            'description': 'Kiwi, Pineapple, Cherry',
        })
        self.app.get('/add?' + params, status=302)
        resp = self.app.get('/')
        resp.mustcontain('Kiwi')

    def test_client_with_dynamic_index_name(self):
        info = ElasticClientInfo()
        info.servers = ['http://elasticsearch:9200']
        info.index = 'pyams_elastic_tests_${{now:%Y-%m-%d}}'
        request = check_request(registry=self.app.app.registry)
        with RequestContext(request):
            client = ElasticClient(using=info,
                                   use_transaction=False)
            today = datetime.utcnow().date().strftime('%Y-%m-%d')
            self.assertTrue(client.index.endswith(today))
            client = ElasticClient(servers=info.servers,
                                   index=info.index,
                                   use_transaction=False)
            self.assertTrue(client.index.endswith(today))
