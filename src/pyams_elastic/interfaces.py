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

"""PyAMS elastic.interfaces module

This module defines mail package interfaces.
"""

from zope.interface import Interface
from zope.schema import Bool, Float, Int, TextLine

from pyams_utils.schema import TextLineListField

from pyams_elastic import _


class IElasticClientInfo(Interface):
    """Elasticsearch client information interface"""

    servers = TextLineListField(title=_("Servers"),
                                description=_("Newline separated list of Elasticsearch servers "
                                              "URLs"),
                                required=True,
                                default=['elasticsearch:9200'])

    use_ssl = Bool(title=_("Use SSL?"),
                   description=_("If 'yes', use SSL for HTTP connection"),
                   required=True,
                   default=False)

    verify_certs = Bool(title=_("Verify certificates?"),
                        description=_("If 'no', SSL certificates will not be verified"),
                        required=True,
                        default=True)

    ca_certs = TextLine(title=_("CA certificates"),
                        description=_("Path to certificates of certification authority"),
                        required=False)

    client_cert = TextLine(title=_("Client certificate"),
                           description=_("Path to PEM file containing client certificate"),
                           required=False)

    client_key = TextLine(title=_("Client key"),
                          description=_("Path to PEM file containing client key, if not "
                                        "included with client certificate"),
                          required=False)

    index = TextLine(title=_("Index name"),
                     description=_("Elasticsearch index name or pattern"),
                     required=True)

    timeout = Float(title=_("Timeout"),
                    description=_("Request timeout, in seconds"),
                    required=True,
                    default=10.0)

    timeout_retries = Int(title=_("Timeout retries"),
                          description=_("You can define the number of retries which can be done "
                                        "if a timeout occurs; setting this to 0 disable retries"),
                          required=False,
                          default=0)


class IElasticClient(IElasticClientInfo):
    """Elasticsearch client marker interface"""


class IElasticMapping(Interface):
    """Elasticsearch mapping interface"""

    def elastic_mapping(self):
        """Elasticsearch mapping getter

        This must be defined as a class method!
        """


class IElasticMappingExtension(IElasticMapping):
    """Elasticsearch mapping extension interface

    This interface defines an extension to an existing mapping interface.
    """
