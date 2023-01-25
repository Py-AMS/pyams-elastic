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

"""PyAMS_elastic.task.zmi module

This module provides management components for Elasticsearch tasks.
"""

from zope.interface import Interface, alsoProvides, implementer

from pyams_elastic.client import ElasticClientInfo
from pyams_elastic.interfaces import IElasticClientInfo
from pyams_elastic.task import ElasticReindexTask, ElasticTask, IElasticReindexTaskInfo
from pyams_elastic.task.interfaces import IElasticReindexTask, IElasticTask, IElasticTaskInfo
from pyams_form.ajax import ajax_form_config
from pyams_form.field import Fields
from pyams_form.group import GroupManager
from pyams_form.interfaces import IObjectFactory
from pyams_form.interfaces.form import IForm, IInnerTabForm
from pyams_form.interfaces.widget import IObjectWidget
from pyams_form.subform import InnerAddForm, InnerEditForm
from pyams_layer.interfaces import IFormLayer, IPyAMSLayer
from pyams_scheduler.interfaces import IScheduler, MANAGE_TASKS_PERMISSION
from pyams_scheduler.zmi import SchedulerTasksTable
from pyams_scheduler.task.zmi import BaseTaskAddForm, BaseTaskEditForm
from pyams_skin.viewlet.menu import MenuItem
from pyams_utils.adapter import adapter_config
from pyams_utils.factory import get_interface_name
from pyams_utils.interfaces.data import IObjectData
from pyams_viewlet.viewlet import viewlet_config
from pyams_zmi.interfaces import IAdminLayer
from pyams_zmi.interfaces.viewlet import IContextAddingsViewletManager


__docformat__ = 'restructuredtext'

from pyams_elastic import _  # pylint: disable=ungrouped-imports


@adapter_config(name=get_interface_name(IElasticClientInfo),
                required=(Interface, IFormLayer, IForm, IObjectWidget),
                provides=IObjectFactory)
def elastic_connection_factory(*args, **kwargs):  # pylint: disable=unused-argument
    """Elasticsearch connection object factory"""
    return ElasticClientInfo


#
# Base Elasticsearch task
#

class IElasticTaskForm(IForm):
    """Elasticsearch task form marker interface"""


@implementer(IElasticTaskForm)
class ElasticTaskFormInfo(GroupManager):
    """Elasticsearch task form info"""

    title = _("Elasticsearch task settings")
    fields = Fields(IElasticTaskInfo)

    def update_widgets(self, prefix=None):
        """Widgets update method"""
        super().update_widgets(prefix)  # pylint: disable=no-member
        query = self.widgets.get('query')  # pylint: disable=no-member
        if query is not None:
            query.add_class('height-100')
            query.widget_css_class = 'editor height-300px'
            query.object_data = {
                'ams-filename': 'query.json'
            }
            alsoProvides(query, IObjectData)
        fields = self.widgets.get('log_fields')  # pylint: disable=no-member
        if fields is not None:
            fields.rows = 5


@viewlet_config(name='add-elastic-task.menu',
                context=IScheduler, layer=IAdminLayer, view=SchedulerTasksTable,
                manager=IContextAddingsViewletManager, weight=110,
                permission=MANAGE_TASKS_PERMISSION)
class ElasticTaskAddMenu(MenuItem):
    """Elasticsearch task add menu"""

    label = _("Add Elasticsearch query...")
    href = 'add-elastic-task.html'
    modal_target = True


@ajax_form_config(name='add-elastic-task.html',
                  context=IScheduler, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class ElasticTaskAddForm(BaseTaskAddForm):
    """Elasticsearch task add form"""

    modal_class = 'modal-xl'

    content_factory = IElasticTask
    content_label = ElasticTask.label


@adapter_config(name='elastic-task-info.form',
                required=(IScheduler, IAdminLayer, ElasticTaskAddForm),
                provides=IInnerTabForm)
class ElasticTaskAddFormInfo(ElasticTaskFormInfo, InnerAddForm):
    """Elasticsearch task add form info"""


@ajax_form_config(name='properties.html',
                  context=IElasticTask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class ElasticTaskEditForm(BaseTaskEditForm):
    """Elasticsearch task edit form"""

    modal_class = 'modal-xl'


@adapter_config(name='elastic-task-info.form',
                required=(IElasticTask, IAdminLayer, ElasticTaskEditForm),
                provides=IInnerTabForm)
class ElasticTaskEditFormInfo(ElasticTaskFormInfo, InnerEditForm):
    """Elasticsearch task edit form info"""


#
# Elasticsearch reindex task
#

class IElasticReindexTaskForm(IForm):
    """Elasticsearch reindex task form marker interface"""


@implementer(IElasticReindexTaskForm)
class ElasticReindexTaskFormInfo(GroupManager):
    """Elasticsearch reindex task form info"""

    title = _("Elasticsearch reindex task settings")
    fields = Fields(IElasticReindexTaskInfo)

    def update_widgets(self, prefix=None):
        """Widgets update method"""
        super().update_widgets(prefix)  # pylint: disable=no-member
        query = self.widgets.get('source_query')  # pylint: disable=no-member
        if query is not None:
            query.add_class('height-100')
            query.widget_css_class = 'editor height-300px'
            query.object_data = {
                'ams-filename': 'query.json'
            }
            alsoProvides(query, IObjectData)
        fields = self.widgets.get('source_fields')  # pylint: disable=no-member
        if fields is not None:
            fields.rows = 5


@viewlet_config(name='add-elastic-reindex-task.menu',
                context=IScheduler, layer=IAdminLayer, view=SchedulerTasksTable,
                manager=IContextAddingsViewletManager, weight=115,
                permission=MANAGE_TASKS_PERMISSION)
class ElasticReindexTaskAddMenu(MenuItem):
    """Elasticsearch reindex task add menu"""

    label = _("Add Elasticsearch reindex...")
    href = 'add-elastic-reindex-task.html'
    modal_target = True


@ajax_form_config(name='add-elastic-reindex-task.html',
                  context=IScheduler, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class ElasticReindexTaskAddForm(BaseTaskAddForm):
    """Elasticsearch reindex task add form"""

    modal_class = 'modal-xl'

    content_factory = IElasticReindexTask
    content_label = ElasticReindexTask.label


@adapter_config(name='elastic-reindex-task-info.form',
                required=(IScheduler, IAdminLayer, ElasticReindexTaskAddForm),
                provides=IInnerTabForm)
class ElasticReindexTaskAddFormInfo(ElasticReindexTaskFormInfo, InnerAddForm):
    """Elasticsearch reindex task add form info"""


@ajax_form_config(name='properties.html',
                  context=IElasticReindexTask, layer=IPyAMSLayer,
                  permission=MANAGE_TASKS_PERMISSION)
class ElasticReindexTaskEditForm(BaseTaskEditForm):
    """Elasticsearch reindex task edit form"""

    modal_class = 'modal-xl'


@adapter_config(name='elastic-reindex-task-info.form',
                required=(IElasticReindexTask, IAdminLayer, ElasticReindexTaskEditForm),
                provides=IInnerTabForm)
class ElasticReindexTaskEditFormInfo(ElasticReindexTaskFormInfo, InnerEditForm):
    """Elasticsearch reindex task edit form info"""
