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
from functools import wraps
from pprint import pformat

import transaction as zope_transaction
from elasticsearch import Elasticsearch, NotFoundError
from persistent import Persistent
from transaction.interfaces import ISavepointDataManager
from zope.component import getAdapters
from zope.interface import implementer
from zope.schema.fieldproperty import FieldProperty

from pyams_elastic.docdict import DotDict
from pyams_elastic.interfaces import IElasticClient, IElasticClientInfo, IElasticMapping, \
    IElasticMappingExtension
from pyams_elastic.query import ElasticQuery
from pyams_utils.factory import factory_config


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

STATUS_ACTIVE = 'active'
STATUS_CHANGED = 'changed'


_CLIENT_STATE = {}


class ElasticSavepoint:
    """Elasticsearch savepoint"""

    def __init__(self, dm):
        self.dm = dm  # pylint: disable=invalid-name
        self.saved = dm.client.uncommitted.copy()

    def rollback(self):
        """Savepoint rollback"""
        self.dm.client.uncommitted = self.saved.copy()


@implementer(ISavepointDataManager)
class ElasticDataManager:
    """Elasticsearch data manager"""

    def __init__(self, client, transaction_manager):
        self.client = client
        self.transaction_manager = transaction_manager
        t = transaction_manager.get()  # pylint: disable=invalid-name
        t.join(self)
        _CLIENT_STATE[id(client)] = STATUS_ACTIVE
        self._reset()

    def _reset(self):
        """Data manager reset"""
        LOGGER.debug('_reset(%s)', self)
        self.client.uncommitted = []

    def _finish(self):
        """Data manager finish"""
        LOGGER.debug('_finish(%s)', self)
        client = self.client
        del _CLIENT_STATE[id(client)]

    def abort(self, transaction):  # pylint: disable=unused-argument
        """Transaction abort"""
        LOGGER.debug('abort(%s)', self)
        self._reset()
        self._finish()

    def tpc_begin(self, transaction):  # pylint: disable=unused-argument
        """Begin two-phases commit"""
        LOGGER.debug('tpc_begin(%s)', self)

    def commit(self, transaction):  # pylint: disable=unused-argument
        """Transaction commit"""
        LOGGER.debug('commit(%s)', self)

    def tpc_vote(self, transaction):  # pylint: disable=unused-argument
        """Two-phases commit vote"""
        LOGGER.debug('tpc_vote(%s)', self)
        # XXX: Ideally, we'd try to check the uncommitted queue and make sure
        # everything looked ok. Not sure how we can do that, though.

    def tpc_finish(self, transaction):  # pylint: disable=unused-argument
        """Two-phases commit finish"""
        # Actually persist the uncommitted queue.
        LOGGER.debug('tpc_finish(%s)', self)
        LOGGER.warning("running: %r", self.client.uncommitted)
        for cmd, args, kwargs in self.client.uncommitted:
            kwargs['immediate'] = True
            getattr(self.client, cmd)(*args, **kwargs)
        self._reset()
        self._finish()

    def tpc_abort(self, transaction):  # pylint: disable=unused-argument
        """Two-phases commit abort"""
        LOGGER.debug('tpc_abort()')
        self._reset()
        self._finish()

    def sortKey(self):  # pylint: disable=invalid-name
        """Data manager sort key getter"""
        # NOTE: Ideally, we want this to sort *after* database-oriented data
        # managers, like the SQLAlchemy one. The double tilde should get us
        # to the end.
        return '~~elasticsearch' + str(id(self))

    def savepoint(self):
        """Savepoint getter"""
        return ElasticSavepoint(self)


def join_transaction(client, transaction_manager):
    """Join current transaction"""
    client_id = id(client)
    existing_state = _CLIENT_STATE.get(client_id, None)
    if existing_state is None:
        LOGGER.warning('client %s not found, setting up new data manager',
                       client_id)
        ElasticDataManager(client, transaction_manager)
    else:
        LOGGER.warning('client %s found, using existing data manager',
                       client_id)
        _CLIENT_STATE[client_id] = STATUS_CHANGED


def transactional(f):  # pylint: disable=invalid-name
    """Transactional functions wrapper"""

    @wraps(f)
    def transactional_inner(client, *args, **kwargs):
        """Inner transaction wrapper"""
        immediate = kwargs.pop('immediate', None)
        if client.use_transaction:
            if immediate:
                return f(client, *args, **kwargs)
            LOGGER.debug('enqueueing action: %s: %r, %r', f.__name__, args, kwargs)
            join_transaction(client, client.transaction_manager)
            client.uncommitted.append((f.__name__, args, kwargs))
            return None
        return f(client, *args, **kwargs)
    return transactional_inner


@factory_config(IElasticClientInfo)
@implementer(IElasticClientInfo)
class ElasticClientInfo(Persistent):
    """Elasticsearch client connection info"""

    servers = FieldProperty(IElasticClientInfo['servers'])
    use_ssl = FieldProperty(IElasticClientInfo['use_ssl'])
    verify_certs = FieldProperty(IElasticClientInfo['verify_certs'])
    index = FieldProperty(IElasticClientInfo['index'])
    timeout = FieldProperty(IElasticClientInfo['timeout'])
    timeout_retries = FieldProperty(IElasticClientInfo['timeout_retries'])

    def __init__(self, data=None):  # pylint: disable=unused-argument
        super().__init__()

    def open(self):
        """Open Elasticsearch client"""
        return Elasticsearch(self.servers,  # pylint: disable=invalid-name
                             use_ssl=self.use_ssl,
                             verify_certs=self.verify_certs,
                             timeout=self.timeout,
                             retry_on_timeout=self.timeout_retries > 0,
                             max_retries=self.timeout_retries)


@implementer(IElasticClient)
class ElasticClient:
    """
    A handle for interacting with the Elasticsearch backend.
    """

    def __init__(self, servers=None, index=None, using=None,
                 auth=None,
                 use_ssl=False,
                 verify_certs=True,
                 timeout=10.0,
                 timeout_retries=0,
                 disable_indexing=False,
                 use_transaction=True,
                 transaction_manager=zope_transaction.manager):
        # pylint: disable=too-many-arguments,unused-argument
        assert servers or using, "You must provide servers or connection info!"
        self.disable_indexing = disable_indexing
        self.use_transaction = use_transaction
        self.transaction_manager = transaction_manager
        if using is not None:
            self.index = using.index
            self.es = using.open()  # pylint: disable=invalid-name
        else:
            self.index = index
            self.es = Elasticsearch(servers,  # pylint: disable=invalid-name
                                    auth=auth,
                                    use_ssl=use_ssl,
                                    verify_certs=verify_certs,
                                    timeout=timeout,
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
        exists = self.es.indices.exists(self.index)
        if recreate or not exists:
            if exists:
                self.es.indices.delete(self.index)
            self.es.indices.create(self.index,
                                   body=dict(settings=settings or CREATE_INDEX_SETTINGS))

    def delete_index(self):
        """
        Delete the index on the ES server.
        """
        self.es.indices.delete(self.index)

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
            for cls in base_class._decl_class_registry.values():  # pylint: disable=protected-access
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

        kwargs = dict(index=self.index, body=doc, id=id)
        if '__pipeline__' in doc:
            kwargs['pipeline'] = doc.pop('__pipeline__')
        self.es.index(**kwargs)

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
