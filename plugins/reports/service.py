# Standard modules
import concurrent.futures
import datetime
import logging
import threading
from collections import Iterable

from bson.objectid import ObjectId
from flask import jsonify

from axonius.consts import report_consts
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME, GUI_NAME,
                                          GUI_SYSTEM_CONFIG_COLLECTION,
                                          PLUGIN_UNIQUE_NAME)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.entities import EntityType
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.thread_stopper import stoppable
from axonius.utils import gui_helpers
from axonius.utils.files import get_local_config_file
from axonius.utils.json import to_json
from axonius.utils.parsing import parse_filter

logger = logging.getLogger(f'axonius.{__name__}')


def query_result_sort_by_id(result: list) -> dict:
    """ Re order query result to dict with id as key.
        Note that multiple ids may point to the same entity """
    ret = {}
    for r in result:
        for specific_data in r['specific_data']:
            ret[specific_data['data']['id']] = r
    return ret


def query_result_diff_by_id(result_by_id1: dict, result_by_id2: dict) -> list:
    """ Get difference between (sorted by id) query result1 and result2.
        We only add unique entities because the result dict may have multiple
        ids that point to the same entity """

    diff = []
    for id_ in result_by_id1.keys() - result_by_id2.keys():
        if result_by_id1[id_] not in diff:
            diff.append(result_by_id1[id_])
    return diff


def query_result_diff(current_result: list, last_result: list)-> dict:
    """ get the current query result and last query result and create and returns
        a dict "diff_dict" that store the added entities and the removed entities """

    diff_dict = {diff_type: [] for diff_type in report_consts.TRIGGERS_DIFF_TYPES}
    current_result = query_result_sort_by_id(current_result)
    last_result = query_result_sort_by_id(last_result)

    diff_dict['added'] = query_result_diff_by_id(current_result, last_result)
    diff_dict['removed'] = query_result_diff_by_id(last_result, current_result)

    return diff_dict


class ReportsService(PluginBase, Triggerable):
    def __init__(self, *args, **kwargs):
        """ This service is responsible for alerting users in several ways and cases when a
                        report query result changes. """

        super().__init__(get_local_config_file(__file__), *args, **kwargs)

        self._actions = {
            'create_service_now_computer': self._handle_action_create_service_now_computer,
            'fresh_service_incident': self._handle_action_create_fresh_service_incident,
            'create_service_now_incident': self._handle_action_create_service_now_incident,
            'carbonblack_isolate': self._handle_action_carbonblack_isolate,
            'carbonblack_unisolate': self._handle_action_carbonblack_unisolate,
            'notify_syslog': self._handle_action_notify_syslog,
            'send_emails': self._handle_action_send_emails,
            'create_notification': self._handle_action_create_notification,
            'tag_all_entities': self._handle_action_tag_all_entities,
            'tag_entities': self._handle_action_tag_entities,
        }

    def _triggered(self, job_name: str, post_json: dict, *args):
        if job_name != 'execute':
            logger.error(f'Got bad trigger request for non-existent job: {job_name}')
            return return_error('Got bad trigger request for non-existent job', 400)
        return self._handle_reports()

    @add_rule('reports/<report_id>', methods=['GET', 'DELETE', 'POST'])
    def report_by_id(self, report_id):
        """The specific rest reports endpoint.

        Gets, Deletes and edits (currently deletes and creates again with same ID) specific reports by ID.

        :return: Correct HTTP response.
        """
        try:
            if self.get_method() == 'GET':
                requested_report = self._get_collection('reports').find_one({'_id': ObjectId(report_id)})
                return jsonify(requested_report) if requested_report is not None else return_error(
                    'A reports with that id was not found.', 404)
            if self.get_method() == 'DELETE':
                return self._remove_report(report_id)
            if self.get_method() == 'POST':
                report_data = self.get_request_data_as_object()
                report_data['last_triggered'] = self._get_collection('reports').find_one(
                    {'_id': ObjectId(report_data['id'])}).get('last_triggered', None)
                delete_response = self._remove_report(report_id)
                if delete_response[1] == 404:
                    return return_error('A reports with that ID was not found.', 404)
                report_data['_id'] = report_id
                self._add_report(report_data)
                return '', 200
            raise ValueError
        except ValueError:
            message = 'Expected JSON, got something else...'
            logger.exception(message)
            return return_error(message, 400)

    @add_rule('reports', methods=['PUT', 'GET', 'DELETE'])
    def report(self):
        """The Rest reports endpoint.

        Creates and deletes the reports resources as well as gets a list of all of them.

        While creating a new reports resource a parameter named "criteria" should be included.
        The criteria should be -1,0 or 1 to identify in which case the user/plugin wants to be notified:
        -1 - If the query results in less devices only.
        0 - Any change in the results.
        1 - If the qurey results in more devices than the original.

        Another expected parameter is "retrigger" which should signify if the user wants to be notified more then once
        if the result changes.

        Also
        :return: Correct HTTP response.
        """
        try:
            if self.get_method() == 'PUT':
                return self._add_report(self.get_request_data_as_object())
            if self.get_method() == 'GET':
                return jsonify(self._get_collection('reports').find())
            if self.get_method() == 'DELETE':
                return self._remove_report(self.get_request_data_as_object())
            raise ValueError
        except ValueError:
            message = 'Expected JSON, got something else...'
            logger.exception(message)
            return return_error(message, 400)

    @staticmethod
    def _get_trigger_description(report_data_triggers, triggers):
        """ Creates a readable message for the different actions.

        :param dict report_data_triggers: The data of this trigger event. example it my be {'above': '3'}
        :param set triggers: The actually triggered triggers. it may be ['above']
        :return:
        """
        first_trigger = triggers[0]
        first_trigger_data = report_data_triggers.get(first_trigger, '')
        return report_consts.TRIGGERS_TO_DESCRIPTION[first_trigger].format(first_trigger_data)

    @staticmethod
    def validate_triggers(report_data):
        """ check that the given triggers in report_data are valid.
            raise ValueError if not """
        for trigger_key, trigger_value in report_data['triggers'].items():
            if trigger_key not in report_consts.TRIGGERS_DEFAULT_VALUES:
                raise ValueError(f'Invalid trigger "{trigger_key}" provided')
            if not isinstance(trigger_value, type(report_consts.TRIGGERS_DEFAULT_VALUES[trigger_key])):
                raise ValueError(f'Invalid value for trigger "{trigger_key}"')

    def _add_report(self, report_data):
        """Adds a reports on a query.

        Creates a reports resource which is a query on our device_db that the user or a plugin wants to be notified when
        it's result changes (criteria should indicate whether to notify in
        only a specific change to the results or any).
        :param dict report_data: The query to reports (as a valid mongo query) and criteria.
        :return: Correct HTTP response.
        """
        # Checks if requested query isn't already watched.
        try:
            current_query_result = self.get_view_results(report_data['view'], EntityType(report_data['viewEntity']))
            if current_query_result is None:
                return return_error('Aggregator is down, please try again later.', 404)

            self.validate_triggers(report_data)

            report_resource = {'report_creation_time': datetime.datetime.now(),
                               'triggers': report_data['triggers'],
                               'actions': report_data['actions'],
                               'result': current_query_result,
                               'view': report_data['view'],
                               'view_entity': report_data['viewEntity'],
                               'retrigger': report_data['retrigger'],
                               'triggered': 0,
                               'name': report_data['name'],
                               'severity': report_data['severity'],
                               'period': report_data['period'],
                               'last_triggered': report_data.get('last_triggered', None)
                               }

            if '_id' in report_data:
                report_resource['_id'] = ObjectId(report_data['_id'])

            # Pushes the resource to the db.
            insert_result = self._get_collection('reports').insert_one(report_resource)
            logger.info('Added query to reports list')
            return str(insert_result.inserted_id), 201
        except ValueError as e:
            message = str(e)
            logger.exception(message)
            return return_error(message, 400)
        except KeyError as e:
            message = 'The query reports request is missing data. Details: {0}'.format(str(e))
            logger.exception(message)
            return return_error(message, 400)
        except TypeError as e:
            message = 'The mongo query was invalid. Details: {0}'.format(str(e))
            logger.exception(message)
            return return_error(message, 400)

    def _remove_report(self, report_data):
        """Delete a reports resource if it exists.

        :param report_data: The report query to delete
        :return: Correct HTTP response.
        """
        if isinstance(report_data, list):
            report_ids = [ObjectId(report_id) for report_id in report_data]
            delete_result = self._get_collection('reports').delete_many({'_id': {'$in': report_ids}})
        elif isinstance(report_data, str):
            delete_result = self._get_collection('reports').delete_one({'_id': ObjectId(report_data)})
        else:
            logger.error('Request to DELETE with unexpected data - not string (id) or list (of ids)')
            return return_error('Request to DELETE with unexpected data - not string (id) or list (of ids)', 400)

        if delete_result.deleted_count == 0:
            logger.error('Attempted to delete a non-existing report.')
            return return_error('Attempted to delete non-existing reports.', 404)

        logger.info('Removed query from reports.')
        return '', 200

    def get_view_results(self, view_name: str, view_entity: EntityType, projection=None) -> list:
        """Gets a query's results from the aggregator devices_db.

        :param view_name: The query name.
        :param view_entity: The query entity type name.
        :return: The results of the query.
        """
        if projection is None:
            projection = {'specific_data.data.id': 1}
        query = self.gui_dbs.entity_query_views_db_map[view_entity].find_one({'name': view_name})
        if query is None:
            raise ValueError(f'Missing query "{view_name}"')
        parsed_query_filter = parse_filter(query['view']['query']['filter'])

        # Projection to get only the needed data to differentiate between results.
        return list(self._entity_views_db_map[view_entity].find(parsed_query_filter, projection))

    def update_report(self, report_data):
        """update a report data.

        :param report_data: The report to update and it's data.
        """
        self._get_collection('reports').replace_one({'_id': report_data['_id']}, report_data, upsert=True)

    def _handle_reports(self):
        """
            For each report that was added to the system,
            if triggered execute it action (for example push notification) .
            This function runs thread for each report handle.
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_for_report_checks = {
                executor.submit(self._handle_report, report_data): report_data['view']
                for report_data in self._get_collection('reports').find()}

            for future in concurrent.futures.as_completed(future_for_report_checks):
                try:
                    future.result()
                    logger.info(f'{future_for_report_checks[future]} finished checking reports.')
                except Exception:
                    logger.exception('Failed to check report generation.')

        return ''

    @staticmethod
    def _get_triggered_reports(current_result, diff_dict, requested_triggers):
        """
        get the actual list of reports that was triggered this cycle

        :param diff_dict: dict that represent the changes between last cycle and this one.
        :param requested_triggers: the user defined triggers
        :return: A set of triggered trigger names.
        """
        triggers = requested_triggers
        triggered = list()

        # If there was change
        if triggers.get('every_discovery'):
            triggered.append('every_discovery')

        if triggers.get('new_entities') and diff_dict['added']:
            triggered.append('new_entities')

        if triggers.get('previous_entities') and diff_dict['removed']:
            triggered.append('previous_entities')

        if triggers.get('above') and len(current_result) > triggers.get('above'):
            triggered.append('above')

        if triggers.get('below') and len(current_result) < triggers.get('below'):
            triggered.append('below')

        return triggered

    def _generate_query_link(self, entity_type, view_name):
        # Getting system config from the gui.
        system_config = self._get_collection(GUI_SYSTEM_CONFIG_COLLECTION, GUI_NAME).find_one({'type': 'server'}) or {}
        return 'https://{}/{}?view={}'.format(
            system_config.get('server_name', 'localhost'), entity_type, view_name)

    def _handle_action_create_service_now_computer(self, report_data, triggered, trigger_data, current_num_of_devices,
                                                   action_data=None):
        service_now_projection = {'adapters': 1,
                                  'specific_data.data.hostname': 1,
                                  'specific_data.data.name': 1,
                                  'specific_data.data.os.type': 1,
                                  'specific_data.data.device_serial': 1,
                                  'specific_data.data.device_manufacturer': 1,
                                  'specific_data.data.network_interfaces.mac': 1,
                                  'specific_data.data.network_interfaces.ips': 1}
        current_result = self.get_view_results(report_data['view'], EntityType(report_data['view_entity']),
                                               projection=service_now_projection)
        if current_result is None:
            logger.info('Skipping reports trigger because there were no current results.')
            return

        for entry in current_result:
            name_raw = None
            asset_name_raw = None
            mac_address_raw = None
            ip_address_raw = None
            manufacturer_raw = None
            serial_number_raw = None
            os_raw = None
            if 'service_now_adapter' in entry['adapters']:
                # It is already ServiceNow adapter
                continue
            for from_adapter in entry['specific_data']:
                data_from_adapter = from_adapter['data']
                if name_raw is None:
                    name_raw = data_from_adapter.get('hostname')
                if asset_name_raw is None:
                    asset_name_raw = data_from_adapter.get('name')
                if os_raw is None:
                    os_raw = data_from_adapter.get('os', {}).get('type')
                if mac_address_raw is None:
                    mac_address_raw = data_from_adapter.get('network_interfaces', [{'ips': []}])[0].get('mac')
                if ip_address_raw is None:
                    ip_address_raw = data_from_adapter.get('network_interfaces', [{'ips': []}])[0].get('ips', [None])[0]
                if serial_number_raw is None:
                    serial_number_raw = data_from_adapter.get('device_serial')
                if manufacturer_raw is None:
                    manufacturer_raw = data_from_adapter.get('device_manufacturer')
            # Make sure that we have name
            if name_raw is None and asset_name_raw is None:
                continue

            # If we don't have hostname we use asset name
            name_raw = name_raw if name_raw else asset_name_raw

            self.create_service_now_computer(name=name_raw,
                                             mac_address=mac_address_raw,
                                             ip_address=ip_address_raw,
                                             manufacturer=manufacturer_raw,
                                             os=os_raw,
                                             serial_number=serial_number_raw)

    def _handle_action_create_fresh_service_incident(self, report_data, triggered, trigger_data, current_num_of_devices,
                                                     action_data=None):

        # create an html of the description
        description = report_consts.REPORT_CONTENT
        description = description.format(name=report_data['name'],
                                         query=report_data['view'],
                                         num_of_triggers=report_data['triggered'],
                                         trigger_message=self._get_trigger_description(report_data['triggers'],
                                                                                       triggered),
                                         num_of_current_devices=current_num_of_devices,
                                         old_results_num_of_devices=len(report_data['result']),
                                         query_link=self._generate_query_link(report_data['view_entity'],
                                                                              report_data['view']))

        logger.info(f'Print the report data: {report_data}')

        # pass into fresh service the name of the alert, the html of the description and the priority
        self.create_fresh_service_incident(subject=report_data.get('name'), description=description, email=action_data,
                                           priority=report_consts.FRESH_SERVICE_PRIORITY.get('medium'))

    def _handle_action_create_service_now_incident(self, report_data, triggered, trigger_data, current_num_of_devices,
                                                   action_data=None):
        """ Create an incident in our ServiceNow acount
        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        :param action_data: List of email addresses to send to.
        """
        log_message = report_consts.REPORT_CONTENT.format(name=report_data['name'],
                                                          query=report_data['view'],
                                                          num_of_triggers=report_data['triggered'],
                                                          trigger_message=self._get_trigger_description(
                                                              report_data['triggers'], triggered),
                                                          num_of_current_devices=current_num_of_devices,
                                                          old_results_num_of_devices=len(report_data['result']),
                                                          query_link=self._generate_query_link(
                                                              report_data['view_entity'],
                                                              report_data['view']))
        self.create_service_now_incident(report_data['name'], log_message,
                                         report_consts.SERVICE_NOW_SEVERITY.get(report_data['severity'],
                                                                                report_consts.SERVICE_NOW_SEVERITY[
                                                                                    'error']))

    def _carbon_black_action(self, action, report_data):
        cb_projection = {'adapters': 1,
                         'specific_data.client_used': 1,
                         'specific_data.data.id': 1,
                         'specific_data.plugin_name': 1}
        current_result = self.get_view_results(report_data['view'], EntityType(report_data['view_entity']),
                                               projection=cb_projection)
        if current_result is None:
            logger.info('Skipping reports trigger because there were no current results.')
            return
        for entry in current_result:
            if 'carbonblack_response_adapter' not in entry['adapters']:
                # It is not CB Response adapter
                continue
            for adapter_data in entry['specific_data']:
                if adapter_data['plugin_name'] == 'carbonblack_response_adapter':
                    device_id = adapter_data['data']['id']
                    client_id = adapter_data['client_used']
                    cb_response_dict = dict()
                    cb_response_dict['device_id'] = device_id
                    cb_response_dict['client_id'] = client_id
                    self.request_remote_plugin(action, 'carbonblack_response_adapter', 'post', json=cb_response_dict)

    def _handle_action_carbonblack_isolate(self, report_data, triggered, trigger_data, current_num_of_devices,
                                           action_data=None):
        """ Isolate a CarbonBlack response device

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        """
        self._carbon_black_action('isolate_device', report_data)

    def _handle_action_carbonblack_unisolate(self, report_data, triggered, trigger_data, current_num_of_devices,
                                             action_data=None):
        """ Unisolate a CarbonBlack response device

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        """
        self._carbon_black_action('unisolate_device', report_data)

    def _handle_action_notify_syslog(self, report_data, triggered, trigger_data, current_num_of_devices,
                                     action_data=None):
        """ Sends an email to the list of e-mails

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        :param action_data: List of email addresses to send to.
        """
        log_message = report_consts.REPORT_CONTENT.format(name=report_data['name'],
                                                          query=report_data['view'],
                                                          num_of_triggers=report_data['triggered'],
                                                          trigger_message=self._get_trigger_description(
                                                              report_data['triggers'], triggered),
                                                          num_of_current_devices=current_num_of_devices,
                                                          old_results_num_of_devices=len(report_data['result']),
                                                          query_link=self._generate_query_link(
                                                              report_data['view_entity'],
                                                              report_data['view'])).replace('\n', ' ')
        # Check if send device data is checked.
        if not action_data:
            self.send_syslog_message(log_message, report_data['severity'])
        else:
            query = self.gui_dbs.entity_query_views_db_map[EntityType(report_data['view_entity'])].find_one({
                'name': report_data['view']})
            parsed_query_filter = parse_filter(query['view']['query']['filter'])
            field_list = query['view'].get('fields', [])
            all_gui_entities = gui_helpers.get_entities(None, None, parsed_query_filter,
                                                        gui_helpers.get_sort(query['view']),
                                                        {field: 1 for field in field_list},
                                                        EntityType(report_data['view_entity']))

            for entity in all_gui_entities:
                entity['alert_name'] = report_data['name']
                self.send_syslog_message(to_json(entity), report_data['severity'])

    def _handle_action_send_emails(self, report_data, triggered, trigger_data, current_num_of_devices,
                                   action_data=None):
        """ Sends an email to the list of e-mails

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        :param action_data: List of email addresses to send to.
        """
        mail_sender = self.mail_sender
        if mail_sender:
            email = mail_sender.new_email(
                report_consts.REPORT_TITLE.format(name=report_data['name'], query=report_data['view']),
                action_data.get('emailList', []))

            if action_data.get('sendDeviceCSV', False):
                query = self.gui_dbs.entity_query_views_db_map[EntityType(report_data['view_entity'])].find_one({
                    'name': report_data['view']})
                parsed_query_filter = parse_filter(query['view']['query']['filter'])
                field_list = query['view'].get('fields', [])
                with self._get_db_connection() as db_connection:
                    csv_string = gui_helpers.get_csv(parsed_query_filter,
                                                     gui_helpers.get_sort(query['view']),
                                                     {field: 1 for field in field_list},
                                                     db_connection,
                                                     EntityType(report_data['view_entity']))

                email.add_attachment('Axonius Entity Data.csv', csv_string.getvalue().encode('utf-8'), 'text/csv')

            email.send(report_consts.REPORT_CONTENT_HTML.format(
                name=report_data['name'], query=report_data['view'], num_of_triggers=report_data['triggered'],
                trigger_message=self._get_trigger_description(report_data['triggers'], triggered),
                num_of_current_devices=current_num_of_devices, severity=report_data['severity'],
                old_results_num_of_devices=len(report_data['result']),
                query_link=self._generate_query_link(report_data['view_entity'], report_data['view'])))
        else:
            logger.info('Email cannot be sent because no email server is configured')

    def _handle_action_create_notification(self, report_data, triggered, trigger_data, current_num_of_devices,
                                           action_data=None):
        """ Sends an email to the list of e-mails

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        :param action_data: None.
        """
        self.create_notification(report_consts.REPORT_TITLE.format(name=report_data['name'], query=report_data['view']),
                                 report_consts.REPORT_CONTENT.format(name=report_data['name'],
                                                                     query=report_data['view'],
                                                                     num_of_triggers=report_data['triggered'],
                                                                     trigger_message=self._get_trigger_description(
                                                                         report_data['triggers'], triggered),
                                                                     num_of_current_devices=current_num_of_devices,
                                                                     old_results_num_of_devices=len(
                                                                         report_data['result']),
                                                                     query_link=self._generate_query_link(
                                                                         report_data['view_entity'],
                                                                         report_data['view'])),
                                 report_data['severity'])

    def _handle_action_tag_all_entities(self, report_data, triggered, trigger_data, current_num_of_devices,
                                        action_data=None):
        tag_projection = {'specific_data.data.id': 1,
                          'specific_data.plugin_unique_name': 1}
        current_result = self.get_view_results(report_data['view'], EntityType(report_data['view_entity']),
                                               projection=tag_projection)
        if current_result is None:
            logger.info('Skipping reports trigger because there were no current results.')
            return
        entities = []
        for entity in current_result:
            for adapter_data in entity['specific_data']:
                entities.append((adapter_data[PLUGIN_UNIQUE_NAME], adapter_data['data']['id']))
        self.add_many_labels_to_entity(EntityType(report_data['view_entity']), entities, [action_data])

    def _handle_action_tag_entities(self, report_data, triggered, trigger_data, current_num_of_devices,
                                    action_data=None):
        """ Sends an email to the list of e-mails

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        :param action_data: List of email addresses to send to.
        """
        entity_db = f'{report_data["view_entity"]}_db_view'
        entities_collection = self._get_collection(entity_db, db_name=AGGREGATOR_PLUGIN_NAME)

        entities = []
        for entity in trigger_data['added']:
            db_entity = entities_collection.find_one({'_id': ObjectId(entity['_id'])})
            if db_entity is not None:
                for adapter_data in db_entity['specific_data']:
                    entities.append((adapter_data[PLUGIN_UNIQUE_NAME], adapter_data['data']['id']))
            else:
                logger.warning(f'Couldn\'t find entity to tag. {entity}')

        self.add_many_labels_to_entity(EntityType(report_data['view_entity']), entities, [action_data])

    def _call_actions(self, report_data, triggers, result_difference,  current_result):
        if report_data['retrigger'] or report_data['triggered'] == 0:
            report_data['triggered'] += 1
            for action in report_data['actions']:
                try:
                    # get the action function to run.
                    current_action_handle = self._actions[action['type']]
                    current_action_handle(report_data, triggers, result_difference,
                                          len(current_result), action.get('data'))
                except Exception as e:
                    logger.exception(
                        f'Error - {e} - performing action {action} with parameters '
                        f'{report_data, triggers, result_difference} '
                        f'{(len(current_result) if isinstance(current_result, Iterable) else current_result)}')
            self.update_report(report_data)

    @stoppable
    def _handle_report(self, report_data):
        """
        Check if report that was added to the system is triggered,
        and execute it action (for example push notification).
        :param dict report_data: the report data that the user added.
        """
        try:
            report_period = report_data.get('period', 'all')
            if report_period != 'all':
                if 'last_triggered' in report_data and report_data['last_triggered'] is not None:
                    if report_period == 'weekly' and report_data['last_triggered'] + datetime.timedelta(
                            days=7) >= datetime.datetime.now():
                        return
                    if report_period == 'daily' and report_data['last_triggered'] + datetime.timedelta(
                            days=1) >= datetime.datetime.now():
                        return

            current_query_result = self.get_view_results(report_data['view'], EntityType(report_data['view_entity']))
            if current_query_result is None:
                logger.info('Skipping reports trigger because there were no current results.')
                return
            retrigger = report_data['retrigger']

            if 'result' not in report_data:
                # If this is the first time we are running this report (the 'result' is not set), set it for next time
                # this happens after axonius system upgrade (where we only save the report and not the result, since
                # it is going to change completely anyway...)
                self._get_collection('reports').update_one({'_id': report_data['_id']},
                                                           {'$set': {'result': current_query_result}})
                return

            last_query_result = report_data['result']
            # Get the difference from last cycle
            query_difference = query_result_diff(current_query_result, last_query_result)

            # Get the actual report triggered list
            triggered = self._get_triggered_reports(current_query_result, query_difference,
                                                    report_data['triggers'])
            logger.debug(f'Triggered with {triggered}, requested {report_data["triggers"]}'
                         f'query_diffrence = {query_difference}'
                         f'current_query_result = {current_query_result}')
            if triggered:
                self._call_actions(report_data, triggered, query_difference, current_query_result)

                # Update last triggered.
                report_data['last_triggered'] = datetime.datetime.now()

                if retrigger:
                    report_data['result'] = current_query_result
                    self.update_report(report_data)

        except Exception as e:
            error_message = 'Thread {0} encountered error: {1}.'\
                'Repeated errors like this could be a race condition of a deleted reports.'.format(
                    threading.current_thread(), str(e))
            logger.exception(error_message)
            raise

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PostCorrelation
