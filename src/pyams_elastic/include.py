#
# Copyright (c) 2015-2019 Thierry Florac <tflorac AT ulthar.net>
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

"""PyAMS elastic.include module

This module is used for Pyramid integration
"""

__docformat__ = 'restructuredtext'

from pyramid.settings import asbool

from pyams_elastic.client import ElasticClient
from pyams_elastic.interfaces import IElasticClient


def client_from_config(settings, prefix='pyams_elastic.'):
    """
    Instantiate and configure an Elasticsearch from settings.

    In typical Pyramid usage, you shouldn't use this directly: instead, just
    include ``pyams_elastic`` and use the :py:func:`get_client` function to get
    access to the shared :py:class:`.client.ElasticClient` instance.
    """
    return ElasticClient(
        servers=settings.get(prefix + 'servers', ['elasticsearch:9200']),
        index=settings[prefix + 'index'],
        timeout=settings.get(prefix + 'timeout', 10.0),
        timeout_retries=int(settings.get(prefix + 'timeout_retry', 0)),
        use_transaction=asbool(settings.get(prefix + 'use_transaction', True)),
        disable_indexing=settings.get(prefix + 'disable_indexing', False))


def get_client(request):
    """
    Get the registered Elasticsearch client. The supplied argument can be
    either a ``Request`` instance or a ``Registry``.
    """
    registry = request.registry
    return registry.queryUtility(IElasticClient)


def include_package(config):
    """Pyramid package include"""

    # add translations
    config.add_translation_dirs('pyams_elastic:locales')

    # add request methods
    config.add_request_method(get_client, 'elastic_client', reify=True)

    # initialize Elasticsearch client
    registry = config.registry
    settings = registry.settings
    if settings.get('pyams_elastic.index'):
        client = client_from_config(settings)
        if asbool(settings.get('pyams_elastic.ensure_index_on_start')):
            client.ensure_index()
        registry.registerUtility(client, IElasticClient)

    # package scan
    ignored = []
    try:
        import pyams_zmi  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError:
        ignored.append('pyams_elastic.zmi')
        ignored.append('pyams_elastic.task.zmi')

    try:
        import pyams_scheduler  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError:
        ignored.append('pyams_elastic.task')

    config.scan(ignore=ignored)
