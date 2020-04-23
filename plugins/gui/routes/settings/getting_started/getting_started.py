import logging
from datetime import datetime

import pymongo
from flask import (jsonify)

from axonius.consts.metric_consts import GettingStartedMetric
from axonius.logging.audit_helper import (AuditCategory, AuditAction)
from axonius.logging.metric_helper import log_metric
from axonius.utils.gui_helpers import get_connected_user_id
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in

# pylint: disable=no-member

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('getting_started')
class GettingStarted:

    @gui_route_logged_in(methods=['GET'], enforce_permissions=False)
    def get_getting_started_data(self):
        """
        Fetch the Getting Started checklist state from db
        """
        data = self._get_collection('getting_started').find_one({})
        return jsonify(data)

    @gui_route_logged_in('completion', methods=['POST'], enforce_permissions=False)
    def getting_started_set_milestone_completion(self):
        """
        Check an item in the Getting Started checklist as done.
        """
        milestone_name = self.get_request_data_as_object().get('milestoneName', '')

        result = self._get_collection('getting_started').find_one_and_update({}, {
            '$set': {
                'milestones.$[element].completed': True,
                'milestones.$[element].user_id': get_connected_user_id(),
                'milestones.$[element].completionDate': datetime.now()
            }
        }, array_filters=[{'element.name': milestone_name}], return_document=pymongo.ReturnDocument.AFTER)

        milestones_len = len(result['milestones'])
        progress = len([item for item in result['milestones'] if item['completed']])
        progress_formatted_str = f'{progress} of {milestones_len}'

        details = [{'name': item.get('name', 'name not found'), 'completed': item.get('completed', False)} for item
                   in result.get('milestones', []) if item]

        log_metric(logger, GettingStartedMetric.COMPLETION_STATE,
                   metric_value=milestone_name,
                   details=details,
                   progress=progress_formatted_str)

        completed_milestone = next(milestone for milestone in result['milestones']
                                   if milestone.get('name', '') == milestone_name)
        if completed_milestone:
            self.log_activity_user(AuditCategory.GettingStarted, AuditAction.CompletePhase, {
                'phase': completed_milestone.get('title')
            })
        if milestones_len == progress:
            self.log_activity_user(AuditCategory.GettingStarted, AuditAction.Complete)
        return ''

    @gui_route_logged_in(methods=['POST'])
    def getting_started_update_settings(self):
        """
        Update the value of the checklist autoOpen setting.
        """
        settings = self.get_request_data_as_object().get('settings', {})
        auto_open = settings.get('autoOpen', False)

        self._get_collection('getting_started').update_one({}, {
            '$set': {
                'settings.autoOpen': auto_open
            }
        })

        log_metric(logger, GettingStartedMetric.AUTO_OPEN_SETTING, metric_value=auto_open)

        return ''
