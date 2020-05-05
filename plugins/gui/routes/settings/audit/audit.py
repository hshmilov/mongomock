import codecs
import re
from datetime import datetime
import logging
import csv
import io

import pymongo
from flask import (jsonify, make_response)

from axonius.consts.gui_consts import FILE_NAME_TIMESTAMP_FORMAT
from axonius.utils.gui_helpers import (paginated, search_filter)
from axonius.utils.serial_csv.constants import DTFMT
from gui.logic.db_helpers import translate_user_id_to_details
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in

# pylint: disable=no-member,inconsistent-return-statements

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('audit')
class Audit:

    @paginated()
    @search_filter()
    @gui_route_logged_in()
    def get_audit(self, limit: int, skip: int, search: str):
        if not search:
            limited_activity_logs = self._fetch_audit().skip(skip).limit(limit)
            return jsonify([self._format_activity(activity) for activity in limited_activity_logs])

        return jsonify(self._get_activities_formatted_filtered(search)[skip:(skip + limit)])

    def _fetch_audit(self):
        return self._audit_collection.find().sort([('timestamp', pymongo.DESCENDING)])

    def _format_activity(self, activity: dict, format_date=False) -> dict:
        """
        Format each activity field to a human readable string

        :param activity: Activity data in format {<field_name>: <field_value>}
        :param fields_format: map base fields to pretty names
        :return:
        """
        def _get_date_from_timestamp(activity: dict):
            timestamp = activity.get('timestamp')
            if not timestamp:
                return ''
            return timestamp.strftime(DTFMT) if format_date else str(timestamp)

        def _get_user_from_id(activity: dict):
            user_id = activity.get('user')
            if not user_id:
                return ''
            user_info = translate_user_id_to_details(user_id)
            if not user_info:
                return ''
            return f'{user_info.source}/{user_info.username}'

        def _get_category_action(activity: dict):
            return f'{activity["category"]}.{activity["action"]}'

        def _get_label(code: str):
            return self._get_labels().get(f'audit.{code}', code)

        def _get_message_from_activity(activity):
            template = _get_label(f'{_get_category_action(activity)}.template')
            if not activity.get('params'):
                return re.sub(r' {\w+}', '', template)
            return template.format(**activity['params'])

        audit_field_to_processor = {
            'type': lambda activity: activity.get('type', ''),
            'date': _get_date_from_timestamp,
            'user': _get_user_from_id,
            'action': lambda activity: _get_label(_get_category_action(activity)),
            'category': lambda activity: _get_label(activity.get('category', '')),
            'message': _get_message_from_activity
        }
        return {
            field: processor(activity)
            for field, processor in audit_field_to_processor.items()
        }

    def _get_activities_formatted_filtered(self, search, format_date=False):
        search = search.lower().strip()
        matching_activities = []
        for activity in self._fetch_audit():
            formatted_activity = self._format_activity(activity, format_date)
            stringified_activity = ','.join(formatted_activity.values()).lower()
            if search in stringified_activity:
                matching_activities.append(formatted_activity)

        return matching_activities

    @search_filter()
    @gui_route_logged_in('count')
    def get_audit_count(self, search):
        """
        :return: filtered users collection size (without axonius users)
        """
        if not search:
            return jsonify(self._audit_collection.count_documents({}))

        return jsonify(len(self._get_activities_formatted_filtered(search)))

    @search_filter()
    @gui_route_logged_in('csv')
    def get_audit_csv(self, search):
        csv_audit_data = self._get_activities_formatted_filtered(search, format_date=True)
        csv_string = io.StringIO()
        dw = csv.DictWriter(csv_string, ['type', 'date', 'user', 'action', 'category', 'message'])
        dw.writeheader()
        dw.writerows(csv_audit_data)

        response = make_response((codecs.BOM_UTF8 * 2) + csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        response.headers['Content-Disposition'] = f'attachment; filename=axonius_activity_logs_{timestamp}.csv'
        response.headers['Content-type'] = 'text/csv'
        return response
