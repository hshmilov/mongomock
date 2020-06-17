import calendar
import io
import logging
import re
import threading
from datetime import datetime, timedelta
from typing import Tuple, List
import json

import gridfs
import pymongo
from apscheduler.triggers.cron import CronTrigger
from bson import ObjectId
from dateutil import tz
from dateutil.relativedelta import relativedelta
from flask import (jsonify,
                   request, make_response)
from urllib3.util.url import parse_url
from werkzeug.wrappers import Response

from axonius.consts import report_consts
from axonius.consts.gui_consts import (EXEC_REPORT_EMAIL_CONTENT,
                                       EXEC_REPORT_FILE_NAME,
                                       EXEC_REPORT_GENERATE_PDF_THREAD_ID,
                                       EXEC_REPORT_THREAD_ID,
                                       LAST_UPDATED_FIELD, UPDATED_BY_FIELD)
from axonius.consts.plugin_consts import (GUI_PLUGIN_NAME)
from axonius.consts.report_consts import (ACTIONS_FAILURE_FIELD, ACTIONS_MAIN_FIELD,
                                          ACTIONS_POST_FIELD,
                                          ACTIONS_SUCCESS_FIELD)
from axonius.logging.audit_helper import AuditCategory, AuditAction
from axonius.plugin_base import EntityType, return_error
from axonius.utils.axonius_query_language import parse_filter
from axonius.utils.datetime import next_weekday
from axonius.utils.gui_helpers import (get_connected_user_id,
                                       find_filter_by_name, paginated,
                                       filtered, sorted_endpoint)
from axonius.utils.threading import run_and_forget
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.filter_utils import filter_archived
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.routes.reports.report_generator import ReportGenerator

# pylint: disable=import-error,no-member,no-self-use,too-many-branches,too-many-statements,invalid-name

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules('reports')
class Reports:

    def _get_reports(self, limit, mongo_filter, mongo_sort, skip):
        sort = []
        for field, direction in mongo_sort.items():
            if field in [ACTIONS_MAIN_FIELD, ACTIONS_SUCCESS_FIELD, ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD]:
                field = f'actions.{field}'
            sort.append((field, direction))
        if not sort:
            sort.append((LAST_UPDATED_FIELD, pymongo.DESCENDING))

        def beautify_report(report):
            beautify_object = {
                '_id': report['_id'],
                'name': report['name'],
                LAST_UPDATED_FIELD: report.get(LAST_UPDATED_FIELD),
                UPDATED_BY_FIELD: report.get(UPDATED_BY_FIELD),
                report_consts.LAST_GENERATED_FIELD: report.get(report_consts.LAST_GENERATED_FIELD)
            }
            if report.get('add_scheduling'):
                beautify_object['period'] = report.get('period').capitalize()
                if report.get('mail_properties'):
                    beautify_object['mailSubject'] = report.get('mail_properties').get('mailSubject')
            return beautify_db_entry(beautify_object)

        reports_collection = self.reports_config_collection
        result = [beautify_report(enforcement) for enforcement in reports_collection.find(
            mongo_filter).sort(sort).skip(skip).limit(limit)]
        return result

    def _generate_and_schedule_report(self, report):
        run_and_forget(lambda: self._generate_and_save_report(report))
        if report.get('period'):
            self._schedule_exec_report(report)

    @paginated()
    @filtered()
    @sorted_endpoint()
    @gui_route_logged_in(methods=['GET'])
    def get_reports(self, limit, skip, mongo_filter, mongo_sort):
        """
        GET results in list of all currently configured enforcements, with their query id they were created with

        :return:
        """
        return jsonify(self._get_reports(limit, mongo_filter, mongo_sort, skip))

    @gui_route_logged_in(methods=['PUT'])
    def add_reports(self):
        """
        PUT Send report_service a new enforcement to be configured

        :return:
        """

        report_to_add = request.get_json()
        reports_collection = self.reports_config_collection
        report_name = report_to_add['name'] = report_to_add['name'].strip()

        if re.match(r'^[\w@.\s-]*$', report_name) is None:
            return f'Report name can only contain letters, numbers and the characters: @,_.-', 400

        if len(report_name) > 50:
            return 'Report name cannot exceed 50 characters.', 400

        report = reports_collection.find_one({
            'name': report_name
        })
        if report:
            return 'Report name already taken by another report', 400

        if not self.is_axonius_user():
            report_to_add['user_id'] = get_connected_user_id()
            report_to_add[LAST_UPDATED_FIELD] = datetime.now()
            report_to_add[UPDATED_BY_FIELD] = get_connected_user_id()
        upsert_result = self._upsert_report_config(report_to_add['name'], report_to_add, False)
        report_to_add['uuid'] = str(upsert_result)
        self._generate_and_schedule_report(report_to_add)
        return jsonify(report_to_add), 201

    @gui_route_logged_in(methods=['DELETE'], activity_params=['count'])
    def delete_reports(self):
        return self._delete_report_configs(self.get_request_data_as_object()), 200

    @filtered()
    @gui_route_logged_in('count')
    def reports_count(self, mongo_filter):
        reports_collection = self.reports_config_collection
        return jsonify(reports_collection.count_documents(mongo_filter))

    def _is_restricted_by_role(self, report_to_check):
        spaces = report_to_check.get('spaces', [])
        for space_id in spaces:
            space = self._dashboard_spaces_collection.find_one({
                '_id': ObjectId(space_id)
            })
            # in case the space was deleted we allow the view because no data available
            if space:
                user_role = str(self.get_user_role_id())
                space_roles = space.get('roles', [])
                space_access = space.get('public', True)
                if not space_access and user_role not in space_roles:
                    return True
        return False

    @gui_route_logged_in('<report_id>', methods=['GET'])
    def get_report_by_id(self, report_id):
        """
        :param report_id:
        :return:
        """
        reports_collection = self.reports_config_collection
        report = reports_collection.find_one({
            '_id': ObjectId(report_id)
        }, {
            LAST_UPDATED_FIELD: 0,
            UPDATED_BY_FIELD: 0,
            'user_id': 0
        })
        if not report:
            return return_error(f'Report with id {report_id} was not found', 400)

        if not self.is_admin_user() and self._is_restricted_by_role(report):
            return make_response('Report restricted')

        return jsonify(beautify_db_entry(report))

    @gui_route_logged_in('<report_id>', methods=['POST'])
    def update_report_by_id(self, report_id):

        report_to_update = request.get_json(silent=True)
        if not self.is_axonius_user():
            report_to_update[LAST_UPDATED_FIELD] = datetime.now()
            report_to_update[UPDATED_BY_FIELD] = get_connected_user_id()

        self._upsert_report_config(report_to_update['name'], report_to_update, True)
        self._generate_and_schedule_report(report_to_update)

        return jsonify(report_to_update), 200

    def generate_new_reports_offline(self):
        """
        Generates a new version of the report as a PDF file and saves it to the db
        (this method is NOT an endpoint)

        :return: "Success" if successful, error if there is an error
        """

        logger.info('Rendering Reports.')
        reports = self.reports_config_collection.find()
        for report in reports:
            try:
                self._generate_and_save_report(report)
            except Exception:
                logger.exception(f'error generating pdf for the report {report["name"]}')
        return 'Success'

    def _generate_and_save_report(self, report):
        # generate_report() renders the report html
        generated_date = datetime.now(tz.tzlocal())
        report_html, attachments = self.generate_report(generated_date, report)

        exec_report_generate_pdf_thread_id = EXEC_REPORT_GENERATE_PDF_THREAD_ID.format(report['name'])
        exec_report_generate_pdf_job = self._job_scheduler.get_job(exec_report_generate_pdf_thread_id)
        # If job doesn't exist generate it
        if exec_report_generate_pdf_job is None:
            self._job_scheduler.add_job(func=self._convert_to_pdf_and_save_report,
                                        kwargs={'report': report,
                                                'report_html': report_html,
                                                'generated_date': generated_date,
                                                'attachments': attachments},
                                        trigger='date',
                                        next_run_time=datetime.now(),
                                        name=exec_report_generate_pdf_thread_id,
                                        id=exec_report_generate_pdf_thread_id,
                                        max_instances=1,
                                        coalesce=True)
        else:
            self._job_scheduler.reschedule_job(exec_report_generate_pdf_thread_id, next_run_time=datetime.now())

    def _convert_to_pdf_and_save_report(self, report, report_html, generated_date, attachments):
        # Writes the report pdf to a file-like object and use seek() to point to the beginning of the stream
        name = report['name']
        try:
            with io.BytesIO() as report_data:
                report_html.write_pdf(report_data)
                report_data.seek(0)
                # Uploads the report to the db and returns a uuid to retrieve it
                uuid = self._upload_report(report_data, report)
                logger.info(f'Report was saved to the grif fs db uuid: {uuid}')
                # Stores the uuid in the db in the "reports" collection

                attachment_uuids = []
                for attachment in attachments:
                    with io.BytesIO() as attachment_data:
                        attachment_data.write(attachment['stream'].getvalue().encode('utf-8'))
                        attachment_data.seek(0)
                        attachment_uuid = self._upload_attachment(attachment['name'], attachment_data)
                        attachment_uuids.append(attachment_uuid)

                filename = 'most_recent_{}'.format(name)
                self._get_collection('reports').replace_one(
                    {
                        'filename': filename
                    },
                    {
                        'uuid': uuid,
                        'filename': filename,
                        'time': datetime.now(),
                        'attachments': attachment_uuids
                    },
                    upsert=True
                )
                logger.info(f'Report was saved to the mongo db to "reports" collection filename: {filename}')

                report[report_consts.LAST_GENERATED_FIELD] = generated_date
                self._upsert_report_config(name, report, False)
                logger.info(f'Report was saved to the mongo db to "report_configs" collection name: {name}')
        except Exception:
            logger.exception(f'Exception with report {name}')

    def _upload_report(self, report, report_metadata) -> str:
        """
        Uploads the latest report PDF to the db
        :param report: report data
        :return:
        """
        if not report:
            return return_error('Report must exist', 401)
        report_name = 'most_recent_{}'.format(report_metadata['name'])

        # First, need to delete the old report
        self._delete_last_report(report_name)

        db_connection = self._get_db_connection()
        fs = gridfs.GridFS(db_connection[GUI_PLUGIN_NAME])
        written_file_id = fs.put(report, filename=report_name)
        logger.info('Report successfully placed in the db')
        return str(written_file_id)

    def _upload_attachment(self, attachment_name: str, attachment_stream: object) -> str:
        """
        Uploads an attachment for a report to the db
        :param attachment_name: attachment name
        :param attachment_stream: attachment stream
        :return: the attachment object id
        """
        if not attachment_name:
            return return_error('Attachment must exist', 401)

        db_connection = self._get_db_connection()
        fs = gridfs.GridFS(db_connection[GUI_PLUGIN_NAME])
        written_file_id = fs.put(attachment_stream,
                                 filename=attachment_name)
        logger.info('Attachment successfully placed in the db')
        return str(written_file_id)

    def _delete_last_report(self, report_name):
        """
        Deletes the last version of the report pdf to avoid having too many saved versions
        :return:
        """
        report_collection = self._get_collection('reports')
        most_recent_report = report_collection.find_one({'filename': report_name})
        if most_recent_report is not None:
            fs = gridfs.GridFS(self._get_db_connection()[GUI_PLUGIN_NAME])
            attachments = most_recent_report.get('attachments')
            if attachments is not None:
                for attachment_uuid in attachments:
                    logger.info(f'DELETE attachment: {attachment_uuid}')
                    fs.delete(ObjectId(attachment_uuid))
            uuid = most_recent_report.get('uuid')
            if uuid is not None:
                logger.info(f'DELETE: {uuid}')
                fs.delete(ObjectId(uuid))

    @gui_route_logged_in('<report_id>/pdf')
    def export_report(self, report_id):
        """
        Gets definition of report from DB for the dynamic content.
        Gets all the needed data for both pre-defined and dynamic content definitions.
        Sends the complete data to the report generator to be composed to one document and generated as a pdf file.

        If background report generation setting is turned off, the report will be generated here, as well.

        TBD Should receive ID of the report to export (once there will be an option to save many report definitions)
        :return:
        """
        report_name, report_data, attachments_data = self._get_executive_report_and_attachments(report_id)
        response = Response(report_data, mimetype='application/pdf', direct_passthrough=True)
        self.log_activity_user(AuditCategory.Reports, AuditAction.Download, {
            'name': report_name
        })
        return response

    def _get_executive_report_and_attachments(self, report_id) -> Tuple[str, object, List[object]]:
        """
        Opens the report pdf and attachment csv's from the db,
        save them in a temp files and return their path
        :param name: a report name string
        :return: A tuple of the report pdf path and a list of attachments paths
         """
        report_config = self.reports_config_collection.find_one({'_id': ObjectId(report_id)})
        name = report_config.get('name', '') if report_config else ''
        report = self._get_collection('reports').find_one({'filename': f'most_recent_{name}'})
        logger.info(f'exporting report "{name}"')
        if not report:
            logger.info(f'exporting report "{name}" failed - most recent report was not found')
            raise Exception('The report is being generated or '
                            'there was a problem with generating the report')

        logger.info(f'exporting report "{name}" succeeded. most recent report found')
        uuid = report['uuid']
        report_path = f'axonius-{name}_{datetime.now()}.pdf'
        logger.info(f'report_path: {report_path}')
        db_connection = self._get_db_connection()

        attachments_data = []
        gridfs_connection = gridfs.GridFS(db_connection[GUI_PLUGIN_NAME])
        attachments = report.get('attachments')
        if attachments:
            for attachment_uuid in attachments:
                try:
                    attachment = gridfs_connection.get(ObjectId(attachment_uuid))
                    attachments_data.append({
                        'name': attachment.name,
                        'content': attachment
                    })
                except Exception:
                    logger.error(f'failed to retrieve attachment {attachment_uuid}')
        report_data = gridfs_connection.get(ObjectId(uuid))
        return name, report_data, attachments_data

    def generate_report(self, generated_date, report):
        """
        Generates the report and returns html.
        :return: the generated report file path.
        """
        logger.info('Starting to generate report')
        try:
            generator_params = {}
            space_ids = report.get('spaces') or []
            generator_params['dashboard'] = self._get_dashboard(space_ids=space_ids, exclude_personal=True)
            generator_params['adapters'] = self._get_adapter_data(report['adapters']) if report.get('adapters') \
                else None
            generator_params['default_sort'] = self._system_settings['defaultSort']
            generator_params['saved_view_count_func'] = self._get_entity_count
            generator_params['spaces'] = self._dashboard_spaces_collection.find(filter_archived())
            system_config = self.system_collection.find_one({'type': 'server'}) or {}
            server_name = str(self._saml_login.get('axonius_external_url') or '').strip()
            if server_name:
                server_name = parse_url(server_name).host
            else:
                server_name = system_config.get('server_name', 'localhost')
            logger.info(f'All data for report gathered - about to generate for server {server_name}')
            return ReportGenerator(report,
                                   generator_params,
                                   'gui/templates/report/',
                                   host=server_name).render_html(generated_date)
        except Exception as e:
            logging.exception(e)
        return None

    def _get_adapter_data(self, adapters):
        """
        Get the definition of the adapters to include in the report. For each adapter, get the views defined for it
        and execute each one, according to its entity, to get the amount of results for it.

        :return:
        """

        def get_adapters_data():
            for adapter in adapters:
                if not adapter.get('name'):
                    continue

                views = []
                for query in adapter.get('views', []):
                    if not query.get('name') or not query.get('entity'):
                        continue
                    entity = EntityType(query['entity'])
                    view_filter = find_filter_by_name(entity, query['name'])
                    if view_filter:
                        query_filter = view_filter['query']['filter']
                        view_parsed = parse_filter(query_filter)
                        views.append({
                            **query,
                            'count': self._entity_db_map[entity].count_documents(view_parsed)
                        })
                adapter_clients_report = {}
                adapter_unique_name = ''
                try:
                    # Exception thrown if adapter is down or report missing, and section will appear with views only
                    adapter_unique_name = self.get_plugin_unique_name(adapter['name'])
                    adapter_reports_db = self._get_db_connection()[adapter_unique_name]
                    found_report = adapter_reports_db['report'].find_one({'name': 'report'}) or {}
                    adapter_clients_report = found_report.get('data', {})
                except Exception:
                    logger.exception(f'Error contacting the report db for adapter {adapter_unique_name} {adapter}')

                yield {'name': adapter['title'], 'queries': views, 'views': adapter_clients_report}

        return list(get_adapters_data())

    @gui_route_logged_in('send_email', methods=['POST'])
    def test_exec_report(self):
        try:
            report = self.get_request_data_as_object()
            self._send_report_thread(report=report)
            return ''
        except Exception as e:
            logger.exception('Failed sending test report by email.')
            return return_error(f'Problem testing report by email: {repr(e)}', 400)

    def _get_exec_report_settings(self, exec_reports_settings_collection):
        settings_objects = exec_reports_settings_collection.find(
            {'period': {'$exists': True}, 'mail_properties': {'$exists': True}})
        return settings_objects

    def _schedule_exec_report(self, exec_report_data):
        logger.info('rescheduling exec_reports')
        time_period = exec_report_data.get('period')
        time_period_config = exec_report_data.get('period_config')
        current_date = datetime.now()
        next_run_time = current_date

        next_run_hour = 8
        next_run_minute = 0
        week_day = 0
        monthly_day = 1

        if time_period_config:
            send_time = time_period_config.get('send_time')
            send_time_parts = send_time.split(':')
            next_run_hour = int(send_time_parts[0])
            next_run_minute = int(send_time_parts[1])
            week_day = int(time_period_config.get('week_day'))
            monthly_day = int(time_period_config.get('monthly_day'))

            utc_time_diff = int((datetime.now() - datetime.utcnow()).total_seconds() / 3600)
            next_run_hour += utc_time_diff
            if next_run_hour > 23:
                next_run_hour -= 24
            elif next_run_hour < 0:
                next_run_hour += 24

        next_run_time = next_run_time.utcnow()

        if time_period == 'weekly':
            if week_day < next_run_time.weekday() or (week_day == next_run_time.weekday() and
                                                      next_run_time.replace(hour=next_run_hour, minute=next_run_minute,
                                                                            second=0) < next_run_time):
                # Get next week's selected week day if it has passed this week
                next_run_time = next_weekday(current_date, week_day)
            else:
                # Get next day of the the current week
                day_of_month_diff = week_day - current_date.weekday()
                next_run_time += timedelta(days=day_of_month_diff)
            next_run_time = next_run_time.replace(hour=next_run_hour, minute=next_run_minute, second=0)
            new_interval_triggger = CronTrigger(year='*', month='*', week='*',
                                                day_of_week=week_day, hour=next_run_hour,
                                                minute=next_run_minute, second=0)
        elif time_period == 'monthly':
            if monthly_day < current_date.day or (monthly_day == current_date.day and
                                                  next_run_time.replace(hour=next_run_hour,
                                                                        minute=next_run_minute,
                                                                        second=0) < next_run_time):
                # ￿Go to next month if the selected day of the month has passed
                next_run_time = current_date + relativedelta(months=+1)

            next_run_time = next_run_time.replace(day=(28 if monthly_day == 29 else monthly_day),
                                                  hour=next_run_hour, minute=next_run_minute, second=0)
            # 29 means the end of the month
            if monthly_day == 29:
                last_month_day = calendar.monthrange(next_run_time.year, next_run_time.month)[1]
                next_run_time.replace(day=last_month_day)
                monthly_day = 'last'
            new_interval_triggger = CronTrigger(year='*', month='1-12',
                                                day=monthly_day, hour=next_run_hour,
                                                minute=next_run_minute, second=0)
        elif time_period == 'daily':
            if next_run_time.replace(hour=next_run_hour, minute=next_run_minute, second=0) < next_run_time:
                # sets it for tomorrow if the selected time has passed
                next_run_time = current_date + relativedelta(days=+1)
            next_run_time = next_run_time.replace(hour=next_run_hour, minute=next_run_minute, second=0)
            new_interval_triggger = CronTrigger(year='*', month='*', week='*',
                                                day_of_week='0-4', hour=next_run_hour,
                                                minute=next_run_minute, second=0)
        else:
            raise ValueError('period have to be in (\'daily\', \'monthly\', \'weekly\').')

        exec_report_thread_id = EXEC_REPORT_THREAD_ID.format(exec_report_data['name'])
        exec_report_job = self._job_scheduler.get_job(exec_report_thread_id)

        logger.info(f'Next report send time: {next_run_time}')

        # If job doesn't exist generate it
        if exec_report_job is None:
            self._job_scheduler.add_job(func=self._send_report_thread_logged,
                                        kwargs={'report': exec_report_data},
                                        trigger=new_interval_triggger,
                                        next_run_time=next_run_time,
                                        name=exec_report_thread_id,
                                        id=exec_report_thread_id,
                                        max_instances=1)
        else:
            exec_report_job.modify(func=self._send_report_thread_logged,
                                   kwargs={'report': exec_report_data},
                                   next_run_time=next_run_time)
            self._job_scheduler.reschedule_job(exec_report_thread_id, trigger=new_interval_triggger)

        logger.info(f'Scheduling an exec_report sending for {next_run_time} and period of {time_period}.')
        return 'Scheduled next run.'

    def _send_report_thread_logged(self, report):
        self._send_report_thread(report)
        self.log_activity(AuditCategory.Reports, AuditAction.Trigger, {
            'name': report.get('name', '')
        })

    def _upsert_report_config(self, name, report_data, clear_generated_report) -> ObjectId:
        if clear_generated_report:
            report_data[report_consts.LAST_GENERATED_FIELD] = None

        result = self.reports_config_collection.find_one_and_update({
            'name': name,
            'archived': {
                '$ne': True
            }
        }, {
            '$set': report_data
        }, projection={
            '_id': True
        }, upsert=True, return_document=pymongo.ReturnDocument.AFTER)
        return result['_id']

    def _delete_report_configs(self, reports):
        reports_collection = self.reports_config_collection
        reports['ids'] = [ObjectId(id) for id in reports['ids']]
        ids = self.get_selected_ids(reports_collection, reports, {})
        for report_id in ids:
            existed_report = reports_collection.find_one_and_delete({
                'archived': {
                    '$ne': True
                },
                '_id': ObjectId(report_id)
            }, projection={
                'name': 1
            })

            if existed_report is None:
                logger.info(f'Report with id {report_id} does not exists')
                return return_error('Report does not exist')
            name = existed_report['name']
            exec_report_thread_id = EXEC_REPORT_THREAD_ID.format(name)
            exec_report_job = self._job_scheduler.get_job(exec_report_thread_id)
            if exec_report_job:
                exec_report_job.remove()
            logger.info(f'Deleted report {name} id: {report_id}')
        return json.dumps({
            'count': str(len(ids))
        })

    def _send_report_thread(self, report):
        if self.trial_expired():
            logger.error('Report email not sent - system trial has expired')
            return
        if self.contract_expired():
            logger.error('Report email not sent - system contract has expired')
            return
        report_name = report['name']
        logger.info(f'_send_report_thread for the "{report_name}" report started')
        lock = self.exec_report_locks[report_name] if self.exec_report_locks.get(report_name) else threading.RLock()
        self.exec_report_locks[report_name] = lock
        with lock:
            _, report_data, attachments_data = self._get_executive_report_and_attachments(report['uuid'])
            if self.mail_sender:
                try:
                    mail_properties = report['mail_properties']
                    subject = mail_properties.get('mailSubject')
                    logger.info(mail_properties)
                    if mail_properties.get('emailList'):
                        email = self.mail_sender.new_email(subject,
                                                           mail_properties.get('emailList', []),
                                                           cc_recipients=mail_properties.get('emailListCC', []))
                        email.add_pdf(EXEC_REPORT_FILE_NAME.format(report_name), report_data.read())

                        for attachment_data in attachments_data:
                            email.add_attachment(attachment_data['name'], attachment_data['content'].read(),
                                                 'text/csv')
                        email.send(mail_properties.get('mailMessage',
                                                       EXEC_REPORT_EMAIL_CONTENT).replace('\n', '\n<br>'))
                        self.reports_config_collection.update_one({
                            'name': report_name,
                            'archived': {
                                '$ne': True
                            }
                        }, {
                            '$set': {
                                report_consts.LAST_TRIGGERED_FIELD: datetime.now()
                            }
                        })
                        logger.info(f'The "{report_name}" report was sent')
                except Exception:
                    logger.info(f'Failed to send an Email for the "{report_name}" report')
                    raise
            else:
                logger.info('Email cannot be sent because no email server is configured')
                raise RuntimeWarning('No email server configured')
        logger.info(f'_send_report_thread for the "{report_name}" report ended')
