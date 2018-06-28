import logging

logger = logging.getLogger(f"axonius.{__name__}")
# Standard modules
import concurrent.futures
from collections import Iterable
import threading
import datetime
from bson.objectid import ObjectId
from flask import jsonify

from axonius.entities import EntityType
from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME, PLUGIN_UNIQUE_NAME, GUI_SYSTEM_CONFIG_COLLECTION, \
    GUI_NAME
from axonius.consts import report_consts
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.thread_stopper import stoppable
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_filter


class ReportsService(PluginBase, Triggerable):
    def __init__(self, *args, **kwargs):
        """ This service is responsible for alerting users in several ways and cases when a
                        report query result changes. """

        super().__init__(get_local_config_file(__file__), *args, **kwargs)

        # Set's a sample rate to check the saved queries.
        self._report_check_lock = threading.RLock()

        self._activate('execute')

    def _triggered(self, job_name: str, post_json: dict, *args):
        if job_name != 'execute':
            logger.error(f"Got bad trigger request for non-existent job: {job_name}")
            return return_error("Got bad trigger request for non-existent job", 400)
        else:
            return self._create_reports()

    @add_rule("reports/<report_id>", methods=['GET', 'DELETE', 'POST'])
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
            elif self.get_method() == 'DELETE':
                return self._remove_report(report_id)
            elif self.get_method() == 'POST':
                report_data = self.get_request_data_as_object()
                delete_response = self._remove_report(report_id)
                if delete_response[1] == 404:
                    return return_error('A reports with that ID was not found.', 404)
                report_data['_id'] = report_id
                self._add_report(report_data)
                return '', 200

        except ValueError:
            message = 'Expected JSON, got something else...'
            logger.exception(message)
            return return_error(message, 400)

    @add_rule("reports", methods=['PUT', 'GET', 'DELETE'])
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
            elif self.get_method() == 'GET':
                return jsonify(self._get_collection('reports').find())
            elif self.get_method() == 'DELETE':
                return self._remove_report(self.get_request_data_as_object())
        except ValueError:
            message = 'Expected JSON, got something else...'
            logger.exception(message)
            return return_error(message, 400)

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

            report_resource = {'report_creation_time': datetime.datetime.now(),
                               'triggers': report_data['triggers'],
                               'actions': report_data['actions'],
                               'result': current_query_result,
                               'view': report_data['view'],
                               'view_entity': report_data['viewEntity'],
                               'retrigger': report_data['retrigger'],
                               'triggered': 0,
                               'name': report_data['name'],
                               'severity': report_data['severity']
                               }

            if '_id' in report_data:
                report_resource['_id'] = ObjectId(report_data['_id'])

            # Pushes the resource to the db.
            insert_result = self._get_collection('reports').insert_one(report_resource)
            logger.info('Added query to reports list')
            return str(insert_result.inserted_id), 201
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

    def get_view_results(self, view_name: str, view_entity: EntityType) -> list:
        """Gets a query's results from the aggregator devices_db.

        :param view_name: The query name.
        :param view_entity: The query entity type name.
        :return: The results of the query.
        """
        query = self.gui.entity_query_views_db_map[view_entity].find_one({'name': view_name})
        if query is None:
            raise ValueError(f'Missing query "{view_name}"')
        parsed_query_filter = parse_filter(query['view']['query']['filter'])

        # Projection to get only the needed data to differentiate between results.
        return list(self._entity_views_db_map[view_entity].find(parsed_query_filter, {'specific_data.data.id': 1}))

    def update_report(self, report_data):
        """update a report data.

        :param report_data: The report to update and it's data.
        """
        self._get_collection('reports').replace_one({'_id': report_data['_id']}, report_data, upsert=True)

    def _create_reports(self):
        """Checks and generate reports if needed.

        This function runs thread for each report it needs to check and/or generate.
        """
        with self._report_check_lock:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_for_report_checks = {
                    executor.submit(self._check_current_query_result, report_data): report_data['view'] for report_data
                    in self._get_collection('reports').find()}

                for future in concurrent.futures.as_completed(future_for_report_checks):
                    try:
                        future.result()
                        logger.info(f'{future_for_report_checks[future]} finished checking reports.')
                    except Exception:
                        logger.exception("Failed to check report generation.")

        return ''

    def _check_triggers(self, result_difference, above, below):
        """ Checks what did actually triggered against the saved and current results.

        :param result_difference: The result difference.
        :param above: The trigger increased above value
        :param below: The trigger decreased below value.
        :return: A set of triggered trigger names.
        """
        applied_triggers = set()

        # If there was change
        if len(result_difference) > 0:
            increased_by = 0
            decreased_by = 0
            for diff_type, device in result_difference:
                if diff_type == report_consts.Triggers.Increase.name:
                    increased_by += 1
                else:
                    decreased_by += 1

            if increased_by > 0:
                if int(above) > 0:
                    if increased_by >= int(above):
                        # If Increased above
                        applied_triggers.add(report_consts.Triggers.Above.name)
                else:
                    # If Increase
                    applied_triggers.add(report_consts.Triggers.Increase.name)
            elif decreased_by > 0:
                if int(below) > 0:
                    if decreased_by > int(below):
                        # If Increased above
                        applied_triggers.add(report_consts.Triggers.Below.name)
                else:
                    # If Decrease
                    applied_triggers.add(report_consts.Triggers.Decrease.name)
        else:
            applied_triggers.add(report_consts.Triggers.No_Change.name)

        return applied_triggers

    def _parse_triggers(self, triggers):
        """ Goes over the report trigger settings and creates a set of requested trigger names.

        :param dict triggers: The report trigger settings.
        :return:
        """
        required_triggers = set()

        if triggers['increase']:
            required_triggers.add(report_consts.Triggers.Increase.name)

        if int(triggers['above']) > 0:
            required_triggers.remove(report_consts.Triggers.Increase.name)
            required_triggers.add(report_consts.Triggers.Above.name)

        if triggers['decrease']:
            required_triggers.add(report_consts.Triggers.Decrease.name)

        if int(triggers['below']) > 0:
            required_triggers.remove(report_consts.Triggers.Decrease.name)
            required_triggers.add(report_consts.Triggers.Below.name)

        if triggers['no_change']:
            required_triggers.add(report_consts.Triggers.No_Change.name)

        return required_triggers

    def _generate_query_link(self, entity_type, view_name):
        # Getting system config from the gui.
        system_config = self._get_collection(GUI_SYSTEM_CONFIG_COLLECTION,
                                             self.get_plugin_by_name(GUI_NAME)[PLUGIN_UNIQUE_NAME]).find_one(
            {'type': 'server'}) or {}
        return f"https://{system_config.get('server_name', 'localhost')}/{entity_type}?view={view_name}"

    def _handle_action_create_service_now_computer(self, report_data, triggered, trigger_data, current_num_of_devices,
                                                   action_data=None):
        current_result = self.get_view_results(report_data['view'], EntityType(report_data['view_entity']))
        if current_result is None:
            logger.info("Skipping reports trigger because there were no current results.")
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
                    mac_address_raw = data_from_adapter.get('network_interfaces', [{'ip': []}])[0].get('mac')
                if ip_address_raw is None:
                    ip_address_raw = data_from_adapter.get('network_interfaces', [{'ip': []}])[0].get('ips', [None])[0]
                if serial_number_raw is None:
                    serial_number_raw = data_from_adapter.get('device_serial')
                if manufacturer_raw is None:
                    manufacturer_raw = data_from_adapter.get('device_manufacturer')
            # Make sure that we have name
            if name_raw is None:
                if asset_name_raw is None:
                    continue
                else:
                    # If we don't have hostname we use asset name
                    name_raw = asset_name_raw
            self.create_service_now_computer(name=name_raw,
                                             mac_address=mac_address_raw,
                                             ip_address=ip_address_raw,
                                             manufacturer=manufacturer_raw,
                                             os=os_raw,
                                             serial_number=serial_number_raw)

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
                                                          trigger_message=self._parse_action_content(
                                                              report_data['triggers'], triggered),
                                                          num_of_current_devices=current_num_of_devices,
                                                          old_results_num_of_devices=len(report_data['result']),
                                                          query_link=self._generate_query_link(
                                                              report_data['view_entity'],
                                                              report_data['view']))
        self.create_service_now_incident(report_data['name'], log_message,
                                         report_consts.SERVICE_NOW_SEVERITY.get(report_data['severity'], report_consts.SERVICE_NOW_SEVERITY['error']))

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
                                                          trigger_message=self._parse_action_content(
                                                              report_data['triggers'], triggered),
                                                          num_of_current_devices=current_num_of_devices,
                                                          old_results_num_of_devices=len(report_data['result']),
                                                          query_link=self._generate_query_link(
                                                              report_data['view_entity'],
                                                              report_data['view'])).replace('\n', ' ')
        self.send_syslog_message(log_message, report_data['severity'])

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
            mail_sender.new_email(report_consts.REPORT_TITLE.format(name=report_data['name'], query=report_data['view']), action_data) \
                .send(report_consts.REPORT_CONTENT_HTML.format(
                    name=report_data['name'], query=report_data['view'], num_of_triggers=report_data['triggered'],
                    trigger_message=self._parse_action_content(report_data['triggers'], triggered),
                    num_of_current_devices=current_num_of_devices, severity=report_data['severity'],
                    old_results_num_of_devices=len(report_data['result']),
                    query_link=self._generate_query_link(report_data['view_entity'], report_data['view'])))
        else:
            logger.info("Email cannot be sent because no email server is configured")

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
                                                                     trigger_message=self._parse_action_content(
                                                                         report_data['triggers'], triggered),
                                                                     num_of_current_devices=current_num_of_devices,
                                                                     old_results_num_of_devices=len(
                                                                         report_data['result']),
                                                                     query_link=self._generate_query_link(
                                                                         report_data['view_entity'],
                                                                         report_data['view'])),
                                 report_data['severity'])

    def _handle_action_tag_entities(self, report_data, triggered, trigger_data, current_num_of_devices,
                                    action_data=None):
        """ Sends an email to the list of e-mails

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        :param action_data: List of email addresses to send to.
        """
        entity_db = f"{report_data['view_entity']}_db_view"
        entities_collection = self._get_collection(entity_db, db_name=AGGREGATOR_PLUGIN_NAME)

        entities = [
            entities_collection.find_one({'internal_axon_id': entity[1]['internal_axon_id']})['specific_data'][0]
            for entity in trigger_data]
        entities = [(entity[PLUGIN_UNIQUE_NAME], entity['data']['id']) for entity in entities]

        self.add_many_labels_to_entity(report_data['view_entity'], entities, [action_data])

    def _parse_action_content(self, triggers_data, triggered_triggers):
        """ Creates a readable message for the different actions.

        :param dict triggers_data: The data of this trigger event.
        :param set triggered_triggers: The actually triggered triggers.
        :return:
        """
        if report_consts.Triggers.Increase.name in triggered_triggers:
            return f'shown an Increase for the specified saved query'

        if report_consts.Triggers.Above.name in triggered_triggers:
            return f'shown an increase of above {triggers_data[report_consts.Triggers.Above.name.lower()]} for the specified saved query'

        if report_consts.Triggers.Decrease.name in triggered_triggers:
            return f'shown a decrease for the specified saved query'

        if report_consts.Triggers.Below.name in triggered_triggers:
            return f'shown a decrease of below {triggers_data[report_consts.Triggers.Above.name.lower()]} for the specified saved query'

        if report_consts.Triggers.No_Change.name in triggered_triggers:
            return f'stayed the same'

    @stoppable
    def _check_current_query_result(self, report_data):
        """This function checks if a specific report should be generated.

        This function checks the reports triggers and executes the actions if needed.

        :param dict report_data: All the report information.
        """

        def _diff(current_result, old_result):
            diff = list()
            for result in current_result:
                any_result_match = False
                for current_adapter_data in result['specific_data']:
                    if any(current_adapter_data['data']['id'] == adapter_data['data']['id'] for
                           current_device in old_result for adapter_data in current_device['specific_data']):
                        any_result_match = True
                        break
                if not any_result_match:
                    diff.append((report_consts.Triggers.Increase.name, result))

            for result in old_result:
                any_result_match = False
                for old_adapter_data in result['specific_data']:
                    if any(old_adapter_data['data']['id'] == adapter_data['data']['id'] for
                           current_device in current_result for adapter_data in current_device['specific_data']):
                        any_result_match = True
                        break
                if not any_result_match:
                    diff.append((report_consts.Triggers.Decrease.name, result))
            return diff

        def _trigger_watch(triggers, result_difference):
            if report_data['retrigger'] or report_data['triggered'] == 0:
                report_data['triggered'] += 1
                for action in report_data['actions']:
                    try:
                        # get the action function to run.
                        current_action_handle = getattr(self, f"_handle_action_{action['type']}")
                        current_action_handle(report_data, triggers, result_difference,
                                              len(current_result), action.get('data'))
                    except Exception:
                        logger.exception(
                            f'Error performing action {action} with parameters '
                            f'{report_data, triggers, result_difference} '
                            f'{(len(current_result) if isinstance(current_result, Iterable) else current_result)}')
                self.update_report(report_data)

        try:
            current_result = self.get_view_results(report_data['view'], EntityType(report_data['view_entity']))
            if current_result is None:
                logger.info("Skipping reports trigger because there were no current results.")
                return
            retrigger = report_data['retrigger']

            if 'result' not in report_data:
                # If this is the first time we are running this report (the 'result' is not set), set it for next time
                # this happens after axonius system upgrade (where we only save the report and not the result, since
                # it is going to change completely anyway...)
                self._get_collection('reports').update_one({"_id": report_data['_id']},
                                                           {"$set": {"result": current_result}})
                return

            result_difference = _diff(current_result, report_data['result'])
            # Checks to see what was triggered against the requested trigger list.
            intersection = self._check_triggers(result_difference,
                                                report_data['triggers']['above'],
                                                report_data['triggers']['below']) & self._parse_triggers(
                report_data['triggers'])
            if len(intersection) > 0:

                _trigger_watch(intersection, result_difference)

                if retrigger:
                    report_data['result'] = current_result
                    self.update_report(report_data)

        except Exception as e:
            logger.exception(
                "Thread {0} encountered error: {1}. Repeated errors like this could be a race condition of a deleted reports.".format(
                    threading.current_thread(), str(e)))
            raise

    @property
    def plugin_subtype(self):
        return "Post-Correlation"
