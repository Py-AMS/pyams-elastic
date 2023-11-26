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

"""PyAMS_elastic.task module

This module defines a PyAMS_scheduler task which can be used to schedule
Elasticsearch queries, and send notifications on (un)expected values.
"""

import json
import sys
import traceback

from elasticsearch import helpers
from elasticsearch.exceptions import TransportError
from zope.schema.fieldproperty import FieldProperty

from pyams_elastic.client import ElasticClient
from pyams_utils.dict import DotDict
from pyams_elastic.task.interfaces import IElasticReindexTask, IElasticReindexTaskInfo, \
    IElasticTask
from pyams_scheduler.interfaces.task import TASK_STATUS_ERROR, TASK_STATUS_FAIL, TASK_STATUS_OK
from pyams_scheduler.task import Task
from pyams_utils.factory import factory_config
from pyams_utils.text import render_text


__docformat__ = 'restructuredtext'

from pyams_elastic import _  # pylint: disable=ungrouped-imports


@factory_config(IElasticTask)
class ElasticTask(Task):
    """Elasticsearch task

    This task is used to execute an Elasticsearch search query; you can specify the
    number of records which are expected (a simple number or a range), and an error status
    is returned if a query is returning more or less items.
    """

    label = _("Elasticsearch query")
    icon_class = 'fab fa-searchengin'

    connection = FieldProperty(IElasticTask['connection'])
    query = FieldProperty(IElasticTask['query'])
    expected_results = FieldProperty(IElasticTask['expected_results'])
    log_fields = FieldProperty(IElasticTask['log_fields'])

    def run(self, report, **kwargs):  # pylint: disable=unused-argument,too-many-locals,too-many-branches
        """Run Elasticsearch query task"""
        try:  # pylint: disable=too-many-nested-blocks
            client = ElasticClient(using=self.connection,
                                   use_transaction=False)
            try:
                report.write('Elasticsearch query output\n'
                             '==========================\n')
                query = json.loads(render_text(self.query))
                results = client.es.search(index=self.connection.index, **query)
                hits = DotDict(results['hits'])
                expected = self.expected_results
                total = hits.total
                if isinstance(total, DotDict):
                    total = total.value
                report.write(f" - expected results: {expected or '--'}\n")
                report.write(f" - total results: {total}\n")
                report.write(f" - query results: {len(hits.hits)}\n")
                report.write('==========================\n')
                if expected:
                    if '-' in expected:
                        mini, maxi = map(int, expected.split('-'))
                    else:
                        mini = maxi = int(expected)
                    if not mini <= total <= maxi:
                        if self.log_fields:
                            for hit in hits.hits:
                                result = hit['_source']
                                for field in self.log_fields:
                                    record = result
                                    try:
                                        for attribute in field.split('.'):
                                            record = record[attribute]
                                        report.write(f' - {field}: {record}\n')
                                    except KeyError:
                                        report.write(f' - {field}: no value\n')
                                report.write('==========================\n')
                        return TASK_STATUS_ERROR, results
                    return TASK_STATUS_OK, results
                return TASK_STATUS_ERROR, results
            finally:
                client.close()
        except TransportError:
            etype, value, tb = sys.exc_info()  # pylint: disable=invalid-name
            report.write('\n\n'
                         'An Elasticsearch error occurred\n'
                         '===============================\n')
            report.write(''.join(traceback.format_exception(etype, value, tb)))
            return TASK_STATUS_FAIL, None


@factory_config(IElasticReindexTask)
class ElasticReindexTask(Task):
    """Elasticsearch re-indexer task

    This task can be used to extract results of an Elasticsearch index to create documents
    into another index; original ID and timestamp, if any, are left unmodified. You can also
    specify the set of attributes which will be transferred into the new index, and you can rename
    these attributes.

    If an attribute is a string containing a serialized JSON object, it will be deserialized
    and contained attributes will be used as new properties of documents created in the new
    index.
    """

    label = _("Elasticsearch re-indexer")
    icon_class = 'fas fa-code-merge'

    source_connection = FieldProperty(IElasticReindexTask['source_connection'])
    source_query = FieldProperty(IElasticReindexTask['source_query'])
    source_fields = FieldProperty(IElasticReindexTask['source_fields'])
    page_size = FieldProperty(IElasticReindexTask['page_size'])
    target_connection = FieldProperty(IElasticReindexTask['target_connection'])

    def get_source_fields(self):
        """Source fields getter"""
        for field in self.source_fields:
            if '=' in field:
                target, source = field.split('=')
                yield source
            else:
                yield field

    def get_hits(self, results):
        """Internal hits iterator getter"""
        for hit in results.hits.hits:
            target_value = {}
            for field in self.source_fields:
                if '=' in field:
                    target_field, source_field = field.split('=')
                else:
                    target_field = source_field = field
                source_value = hit._source
                for attr in source_field.split('.'):
                    try:
                        source_value = source_value[attr]
                    except KeyError:
                        break
                try:
                    target_value[target_field] = json.loads(source_value)
                except (TypeError, json.JSONDecodeError):
                    target_value[target_field] = source_value
            yield {
                '_id': hit._id,
                '_source': target_value
            }

    def run(self, report, **kwargs):  # pylint: disable=unused-argument,too-many-locals,too-many-branches
        """Run Elasticsearch re-indexer query task"""
        try:  # pylint: disable=too-many-nested-blocks
            source = ElasticClient(using=self.source_connection,
                                   use_transaction=False)
            target = ElasticClient(using=self.target_connection,
                                   use_transaction=False)
            try:
                report.write('Elasticsearch query output\n'
                             '==========================\n')
                report.write(f' - source index: {source.index}\n')
                report.write(f' - target index: {target.index}\n\n')
                source_query = json.loads(render_text(self.source_query))
                source_query['_source'] = list(self.get_source_fields())
                source_query['size'] = self.page_size
                if 'sort' not in source_query:
                    source_query['sort'] = ['_score', '@timestamp']
                source_count = 0
                index_count = 0
                has_more_results = True
                last_sort = None
                while has_more_results:
                    if last_sort:
                        source_query['search_after'] = last_sort
                    results = DotDict(source.es.search(index=self.source_connection.index,
                                                       **source_query))
                    source_count += len(results.hits.hits)
                    actions, errors = helpers.bulk(target.es, self.get_hits(results),
                                                   index=target.index,
                                                   stats_only=False,
                                                   raise_on_error=False)
                    has_more_results = len(results.hits.hits) >= self.page_size
                    if has_more_results:
                        last_sort = results.hits.hits[-1].sort
                    index_count += actions
                    for error in errors:
                        report.write(f' - indexing error: {error}\n')
                report.write(f' - total source records: {source_count}\n')
                report.write(f' - total re-indexed records: {index_count}\n\n')
                return TASK_STATUS_OK, (source_count, index_count)
            finally:
                source.close()
                target.close()
        except TransportError:
            etype, value, tb = sys.exc_info()  # pylint: disable=invalid-name
            report.write('\n\n'
                         'An Elasticsearch error occurred\n'
                         '===============================\n')
            report.write(''.join(traceback.format_exception(etype, value, tb)))
            return TASK_STATUS_FAIL, None
