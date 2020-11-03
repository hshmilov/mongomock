import codecs
import re
from datetime import datetime
import logging
import csv
import io

import pymongo
from flask import (jsonify, make_response)

from axonius.consts.gui_consts import FILE_NAME_TIMESTAMP_FORMAT
from axonius.utils.gui_helpers import (paginated, search_filter, historical_range)
from axonius.utils.serial_csv.constants import DTFMT
from gui.logic.db_helpers import translate_user_id_to_details
from gui.logic.filter_utils import filter_by_date_range
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in
from gui.routes.labels.labels_catalog import LABELS_CATALOG
# pylint: disable=no-self-use,no-member,inconsistent-return-statements

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('audit')
class Audit:

    @paginated()
    @search_filter()
    @historical_range()
    @gui_route_logged_in()
    def get_audit(self, limit: int, skip: int, search: str, from_date: datetime, to_date: datetime):
        """
        path: /api/settings/audit
        """
        if not search:
            limited_activity_logs = self._fetch_audit(from_date, to_date).skip(skip).limit(limit)
            return jsonify([self._format_activity(activity) for activity in limited_activity_logs])

        return jsonify(self._get_activities_formatted_filtered(search, from_date, to_date, skip, limit))

    def _fetch_audit(self, from_date: datetime, to_date: datetime):
        audit_filter = {}
        if from_date and to_date:
            audit_filter = filter_by_date_range(from_date, to_date)
        return self.common.audit_collection.find(filter=audit_filter).sort([('timestamp', pymongo.DESCENDING)])

    def _count_audit(self, from_date: datetime, to_date: datetime):
        audit_filter = {}
        if from_date and to_date:
            audit_filter = filter_by_date_range(from_date, to_date)
        return self.common.audit_collection.count_documents(audit_filter)

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
            return timestamp.strftime(DTFMT) if format_date else timestamp

        def _get_user_from_id(activity: dict):
            user_id = activity.get('user')
            if not user_id:
                return ''
            user_info = translate_user_id_to_details(user_id)
            if not user_info:
                return ''
            return f'{user_info.source}/{user_info.user_name}'

        def _get_category_action(activity: dict):
            return f'{activity["category"]}.{activity["action"]}'

        def _get_label(code: str):
            return LABELS_CATALOG.get(f'audit.{code}', code)

        def _get_message_from_activity(activity):
            try:
                template = _get_label(f'{_get_category_action(activity)}.template')
                activity_params = activity['params'] or {}
                for match in re.finditer(r'\{(\w+)\}', template):
                    template = re.sub(match.group(0), activity_params.get(match.group(1), ''), template)
                return template
            except Exception:
                logger.warning(f'Fatal Error processing audit message activity {activity} ')

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

    def _get_activities_formatted_filtered(self, search,
                                           from_date: datetime, to_date: datetime,
                                           skip: int = 0, limit: int = -1,
                                           format_date=False):
        """
        Fetch the activities from the db, in given date range
        Format each one, so it has pretty strings
        Check if given search term is anywhere in the resulting activity
        Check if the activity is in the range of given skip and limit

        :return: Formatted activities, logged within given date range,
                 containing the given search term, between the skip and limit
        """
        search = search.lower().strip()
        matching_activities = []
        match_count = 0
        for activity in self._fetch_audit(from_date, to_date):
            if len(matching_activities) == limit:
                break

            formatted_activity = self._format_activity(activity, format_date)
            stringified_activity = ','.join([value for value
                                             in formatted_activity.values() if isinstance(value, str)]).lower()
            if search in stringified_activity:
                if match_count >= skip:
                    matching_activities.append(formatted_activity)
                match_count += 1

        return matching_activities

    @search_filter()
    @historical_range()
    @gui_route_logged_in('count')
    def get_audit_count(self, search, from_date: datetime, to_date: datetime):
        """
        path: /api/settings/audit/count

        :return: filtered users collection size (without axonius users)
        """
        if not search:
            return jsonify(self._count_audit(from_date, to_date))

        return jsonify(len(self._get_activities_formatted_filtered(search, from_date, to_date)))

    @search_filter()
    @historical_range()
    @gui_route_logged_in('csv')
    def get_audit_csv(self, search, from_date: datetime, to_date: datetime):
        """
        path: /api/settings/audit/csv
        """
        csv_audit_data = self._get_activities_formatted_filtered(search, from_date, to_date, format_date=True)
        csv_string = io.StringIO()
        dw = csv.DictWriter(csv_string, ['type', 'date', 'user', 'action', 'category', 'message'])
        dw.writeheader()
        dw.writerows(csv_audit_data)

        response = make_response((codecs.BOM_UTF8 * 2) + csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        response.headers['Content-Disposition'] = f'attachment; filename=axonius_activity_logs_{timestamp}.csv'
        response.headers['Content-type'] = 'text/csv'
        return response
