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

import re

from pyramid.settings import asbool, aslist

from pyams_elastic.client import ElasticClient
from pyams_elastic.interfaces import IElasticClient

__docformat__ = 'restructuredtext'


def client_from_config(settings, prefix='pyams_elastic.', **kwargs):
    """
    Instantiate and configure an Elasticsearch from settings.

    In typical Pyramid usage, you shouldn't use this directly: instead, just
    include ``pyams_elastic`` and use the :py:func:`get_client` function to get
    access to the shared :py:class:`.client.ElasticClient` instance (which is also
    available using *request.elastic_client* notation).

    When creating a client manually, you can provide additional settings; these arguments
    will override settings defined into configuration file.
    """

    def get_setting(name, default=None):
        """Get setting from arguments or configuration file"""
        return kwargs.get(name, settings.get(f'{prefix}{name}', default))

    api_key = get_setting('api_key')
    if api_key and (':' in api_key):
        api_key = api_key.split(':', 1)
    basic_auth = get_setting('basic_auth')
    if basic_auth:
        basic_auth = basic_auth.split(':', 1)

    return ElasticClient(
        servers=aslist(get_setting('servers')),
        cloud_id=get_setting('cloud_id'),
        api_key=api_key,
        basic_auth=basic_auth,
        bearer_auth=get_setting('bearer_auth'),
        verify_certs=asbool(get_setting('verify_certs', True)),
        ca_certs=get_setting('ca_certs'),
        client_cert=get_setting('client_cert'),
        client_key=get_setting('client_key'),
        index=get_setting('index'),
        timeout=float(get_setting('timeout', 10.0)),
        timeout_retries=int(get_setting('timeout_retries', 0)),
        use_transaction=asbool(get_setting('use_transaction', True)),
        disable_indexing=asbool(get_setting('disable_indexing', False)))


def get_client(context):
    """
    Get the registered Elasticsearch client. The provided context argument can be
    either a ``Request`` instance or a ``Registry``.
    """
    try:
        registry = context.registry
    except AttributeError:
        registry = context
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
        ignored.append(re.compile(r'pyams_elastic\..*\.zmi\.?.*').search)

    try:
        import pyams_scheduler  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError:
        ignored.append('pyams_elastic.task')

    config.scan(ignore=ignored)
