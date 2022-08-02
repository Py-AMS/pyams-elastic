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

import sys
import traceback

from elasticsearch import ElasticsearchException
from zope.schema.fieldproperty import FieldProperty

from pyams_elastic.client import ElasticClient
from pyams_elastic.docdict import DotDict
from pyams_elastic.task.interfaces import IElasticTask
from pyams_scheduler.interfaces.task import TASK_STATUS_ERROR, TASK_STATUS_FAIL, TASK_STATUS_OK
from pyams_scheduler.task import Task
from pyams_utils.factory import factory_config


__docformat__ = 'restructuredtext'

from pyams_elastic import _  # pylint: disable=ungrouped-imports


@factory_config(IElasticTask)
class ElasticTask(Task):
    """Elasticsearch task"""

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
                results = client.es.search(body=self.query,
                                           index=self.connection.index)
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
        except ElasticsearchException:
            etype, value, tb = sys.exc_info()  # pylint: disable=invalid-name
            report.write('\n\n'
                         'An Elasticsearch error occurred\n'
                         '===============================\n')
            report.write(''.join(traceback.format_exception(etype, value, tb)))
            return TASK_STATUS_FAIL, None
