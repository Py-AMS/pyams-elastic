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

"""PyAMS_elastic.client module

This module defines the main Elasticsearch client class.
"""

__docformat__ = 'restructuredtext'

import logging
from pprint import pformat

import transaction
from elasticsearch import Elasticsearch, NotFoundError
from persistent import Persistent
from zope.component import getAdapters
from zope.interface import implementer
from zope.schema.fieldproperty import FieldProperty

from pyams_elastic.interfaces import IElasticClient, IElasticClientInfo, IElasticMapping, \
    IElasticMappingExtension
from pyams_elastic.query import ElasticQuery
from pyams_utils.dict import DotDict
from pyams_utils.factory import factory_config
from pyams_utils.text import render_text
from pyams_utils.transaction import TransactionClient, transactional

LOGGER = logging.getLogger('PyAMS (elastic)')


ANALYZER_SETTINGS = {
    "analysis": {
        "filter": {
            "snowball": {
                "type": "snowball",
                "language": "English"
            },
        },

        "analyzer": {
            "lowercase": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase"]
            },

            "email": {
                "type": "custom",
                "tokenizer": "uax_url_email",
                "filter": ["lowercase"]
            },

            "content": {
                "type": "custom",
                "tokenizer": "standard",
                "char_filter": ["html_strip"],
                "filter": ["lowercase", "stop", "snowball"]
            }
        }
    }
}


CREATE_INDEX_SETTINGS = ANALYZER_SETTINGS.copy()
CREATE_INDEX_SETTINGS.update({
    "index": {
        "number_of_shards": 2,
        "number_of_replicas": 0
    },
})


@factory_config(IElasticClientInfo)
@implementer(IElasticClientInfo)
class ElasticClientInfo(Persistent):
    """Elasticsearch client connection info"""

    servers = FieldProperty(IElasticClientInfo['servers'])
    cloud_id = FieldProperty(IElasticClientInfo['cloud_id'])
    api_key = FieldProperty(IElasticClientInfo['api_key'])
    basic_auth = FieldProperty(IElasticClientInfo['basic_auth'])
    bearer_auth = FieldProperty(IElasticClientInfo['bearer_auth'])
    verify_certs = FieldProperty(IElasticClientInfo['verify_certs'])
    ca_certs = FieldProperty(IElasticClientInfo['ca_certs'])
    client_cert = FieldProperty(IElasticClientInfo['client_cert'])
    client_key = FieldProperty(IElasticClientInfo['client_key'])
    index = FieldProperty(IElasticClientInfo['index'])
    timeout = FieldProperty(IElasticClientInfo['timeout'])
    timeout_retries = FieldProperty(IElasticClientInfo['timeout_retries'])

    def open(self):
        """Open Elasticsearch client"""
        api_key = self.api_key
        if api_key and (':' in api_key):
            api_key = api_key.split(':', 1)
        basic_auth = self.basic_auth
        if basic_auth:
            basic_auth = basic_auth.split(':', 1)
        return Elasticsearch(self.servers,  # pylint: disable=invalid-name
                             cloud_id=self.cloud_id,
                             api_key=api_key,
                             basic_auth=basic_auth,
                             bearer_auth=self.bearer_auth,
                             verify_certs=self.verify_certs,
                             ca_certs=self.ca_certs,
                             client_cert=self.client_cert,
                             client_key=self.client_key,
                             request_timeout=self.timeout,
                             retry_on_timeout=self.timeout_retries > 0,
                             max_retries=self.timeout_retries)


@implementer(IElasticClient)
class ElasticClient(TransactionClient):
    """A handle for interacting with the Elasticsearch backend"""

    def __init__(self,
                 servers=None,
                 index=None,
                 using=None,
                 cloud_id=None,
                 api_key=None,
                 basic_auth=None,
                 bearer_auth=None,
                 verify_certs=True,
                 ca_certs=None,
                 client_cert=None,
                 client_key=None,
                 timeout=10.0,
                 timeout_retries=0,
                 disable_indexing=False,
                 use_transaction=True,
                 transaction_manager=transaction.manager):
        # pylint: disable=too-many-arguments,unused-argument
        super().__init__(use_transaction, transaction_manager)
        assert servers or using, "You must provide servers or connection info!"
        self.disable_indexing = disable_indexing
        if using is not None:
            self.index = render_text(using.index)
            self.es = using.open()  # pylint: disable=invalid-name
        else:
            self.index = render_text(index)
            self.es = Elasticsearch(servers,  # pylint: disable=invalid-name
                                    cloud_id=cloud_id,
                                    api_key=api_key,
                                    basic_auth=basic_auth,
                                    bearer_auth=bearer_auth,
                                    verify_certs=verify_certs,
                                    ca_certs=ca_certs,
                                    client_cert=client_cert,
                                    client_key=client_key,
                                    request_timeout=timeout,
                                    retry_on_timeout=timeout_retries > 0,
                                    max_retries=timeout_retries)

    def close(self):
        """Close Elasticsearch client"""
        self.es.close()

    def __enter__(self):
        return self.es

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.es.close()

    def ensure_index(self, recreate=False, settings=None):
        """
        Ensure that the index exists on the ES server, and has up-to-date
        settings.
        """
        exists = self.es.indices.exists(index=self.index)
        if recreate or not exists:
            if exists:
                self.es.indices.delete(index=self.index)
            self.es.indices.create(index=self.index,
                                   **dict(settings=settings or CREATE_INDEX_SETTINGS))

    def delete_index(self):
        """
        Delete the index on the ES server.
        """
        self.es.indices.delete(index=self.index)

    def get_mappings(self):  # pylint: disable=unused-argument
        """
        Return the object mappings currently used by ES.
        """
        raw = self.es.indices.get_mapping(index=self.index)
        return raw[self.index]['mappings']

    def ensure_mapping(self, cls, recreate=False):
        """
        Put an explicit mapping for the given class if it doesn't already
        exist.
        """
        doc_mapping = cls.elastic_mapping()
        doc_mapping = dict(doc_mapping)

        LOGGER.debug('Putting mapping: \n%s', pformat(doc_mapping))
        mappings = self.get_mappings()
        if (not mappings) or recreate:
            self.es.indices.put_mapping(index=self.index,
                                        body=doc_mapping)

    def ensure_all_mappings(self, base_class, recreate=False):
        """
        Initialize explicit mappings for all subclasses of the specified
        SQLAlchemy declarative base class.
        """
        doc_mapping = self.get_mappings()
        if (not doc_mapping) or recreate:
            doc_mapping = {}
            for cls in base_class.registry._class_registry.values():  # pylint: disable=protected-access
                if not IElasticMapping.providedBy(cls):
                    continue
                cls_mapping = dict(cls.elastic_mapping())
                if cls_mapping:
                    for _name, extension in getAdapters((cls,), IElasticMappingExtension):
                        cls_mapping.update(extension.elastic_mapping())
                    doc_mapping.update(cls_mapping)
            LOGGER.debug('Putting mapping: \n%s', pformat(doc_mapping))
            self.es.indices.put_mapping(index=self.index,
                                        body=doc_mapping)

    def index_objects(self, objects):
        """
        Add multiple objects to the index.
        """
        for obj in objects:
            self.index_object(obj)

    def index_object(self, obj, **kw):
        """
        Add or update the indexed document for an object.
        """
        doc = obj.elastic_document()
        doc_id = doc.pop("_id")

        LOGGER.debug('Indexing object:\n%s', pformat(doc))
        LOGGER.debug('ID is %r', doc_id)

        self.index_document(id=doc_id, doc=doc, **kw)

    @transactional
    def index_document(self, id, doc):  # pylint: disable=invalid-name,redefined-builtin
        """
        Add or update the indexed document from a raw document source (not an
        object).
        """
        if self.disable_indexing:
            return

        kwargs = dict(index=self.index, document=doc, id=id)
        if '__pipeline__' in doc:
            kwargs['pipeline'] = doc.pop('__pipeline__')
        self.es.index(**kwargs)

    def update_object(self, obj, attrs, **kw):
        """
        Update an indexed object with partial properties. You have to provide a list of
        original Elasticsearch document attributes which will be updated
        """
        doc = obj.elastic_document()
        doc_id = doc.pop("_id")
        for key in list(doc.keys()):
            if key not in attrs:
                doc.pop(key)

        LOGGER.debug('Updating object:\n%s', pformat(doc))
        LOGGER.debug('ID is %r', doc_id)

        return self.update_document(id=doc_id, doc=doc, **kw)

    @transactional
    def update_document(self, id, doc=None, script=None, safe=False, **kw):  # pylint: disable=invalid-name,redefined-builtin
        """
        Update an indexed document with new properties.
        """
        assert doc or script, "doc and script arguments can't both be null"
        if self.disable_indexing:
            return

        body = {'script': script} if script else {'doc': doc}
        body.update(kw)
        kwargs = dict(index=self.index, id=id)
        kwargs.update(body)
        try:
            result = self.es.update(**kwargs)
            return result.get('result'), DotDict(result.get('get', {}).get('_source'))
        except NotFoundError:
            if not safe:
                raise
            return 'notfound', None

    def delete_object(self, obj, safe=False, **kw):
        """
        Delete the indexed document for an object.
        """
        doc = obj.elastic_document()
        doc_id = doc.pop("_id")

        self.delete_document(id=doc_id, safe=safe, **kw)

    @transactional
    def delete_document(self, id, safe=False):  # pylint: disable=invalid-name,redefined-builtin
        """
        Delete the indexed document based on a raw document source (not an
        object).
        """
        if self.disable_indexing:
            return

        kwargs = dict(index=self.index, id=id)
        try:
            self.es.delete(**kwargs)
        except NotFoundError:
            if not safe:
                raise

    def flush(self, force=True):
        """
        Flush indices data
        """
        self.es.indices.flush(index=self.index, force=force)  # pylint: disable=unexpected-keyword-arg

    def get(self, obj):
        """
        Retrieve the ES source document for a given object or (document type,
        id) pair.
        """
        if isinstance(obj, (list, tuple)):
            _doc_type, doc_id = obj
        else:
            doc_id = obj.id

        kwargs = dict(index=self.index, id=doc_id)
        r = self.es.get(**kwargs)  # pylint: disable=invalid-name
        return DotDict(r['_source'])

    def refresh(self):
        """Refresh the ES index."""
        self.es.indices.refresh(index=self.index)

    def query(self, *classes, **kw):
        """
        Return an ElasticQuery against the specified class.
        """
        cls = kw.pop('cls', ElasticQuery)
        return cls(client=self, classes=classes, **kw)
