import logging
logger = logging.getLogger(f"axonius.{__name__}")
# Standard modules
import concurrent.futures
import threading
import datetime

from bson.objectid import ObjectId
from axonius.mixins.triggerable import Triggerable

# pip modules
from flask import jsonify, json

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME, PLUGIN_UNIQUE_NAME
from axonius.consts import report_consts
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.utils.files import get_local_config_file
from axonius.parsing_utils import parse_filter


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
            report_query = self._get_collection('reports').find({'query': report_data['query']})

            if report_query.count() == 0:
                current_query_result = self.get_query_results(report_data['query'])
                if current_query_result is None:
                    return return_error('Aggregator is down, please try again later.', 404)

                report_resource = {'report_creation_time': datetime.datetime.now(),
                                   'triggers': report_data['triggers'],
                                   'actions': report_data['actions'],
                                   'result': current_query_result,
                                   'query': json.dumps(report_data['query']),
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

            return return_error('An existing reports on a query as been requested', 409)

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
        delete_query = {'query': json.dumps(report_data['query'])} if isinstance(report_data, dict) else {
            '_id': ObjectId(report_data)}

        delete_result = self._get_collection('reports').delete_one(delete_query)

        if delete_result.deleted_count == 0:
            logger.error('Attempted to delete an non-existing report.')
            return return_error('Attempted to delete non-existing reports.', 404)

        logger.info('Removed query from reports.')
        return '', 200

    def get_query_results(self, query):
        """Gets a query's results from the aggregator devices_db_view.

        :param query: The query to use.
        :return: The results of the query.
        """
        return list(self._get_collection('devices_db_view', db_name=AGGREGATOR_PLUGIN_NAME).find(parse_filter(query)))

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
                    executor.submit(self._check_current_query_result, report_data): report_data['query'] for report_data
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

    def _handle_action_send_emails(self, report_data, triggered, trigger_data, current_num_of_devices,
                                   action_data=None):
        """ Sends an email to the list of e-mails

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        :param action_data: List of email addresses to send to.
        """
        self.send_email(report_consts.REPORT_TITLE.format(query_name=report_data['name']),
                        action_data,
                        report_consts.REPORT_CONTENT_HTML.format(query_name=report_data['name'],
                                                                 num_of_triggers=report_data['triggered'],
                                                                 trigger_message=self._parse_action_content(
                                                                     report_data['triggers'], triggered),
                                                                 num_of_current_devices=current_num_of_devices),
                        report_data['severity'])

    def _handle_action_create_notification(self, report_data, triggered, trigger_data, current_num_of_devices,
                                           action_data=None):
        """ Sends an email to the list of e-mails

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        :param action_data: None.
        """
        self.create_notification(report_consts.REPORT_TITLE.format(query_name=report_data['name']),
                                 report_consts.REPORT_CONTENT.format(query_name=report_data['name'],
                                                                     num_of_triggers=report_data['triggered'],
                                                                     trigger_message=self._parse_action_content(
                                                                         report_data['triggers'], triggered),
                                                                     num_of_current_devices=current_num_of_devices),
                                 report_data['severity'])

    def _handle_action_tag_device(self, report_data, triggered, trigger_data, current_num_of_devices, action_data=None):
        """ Sends an email to the list of e-mails

        :param dict report_data: The report settings.
        :param set triggered: triggered triggers set.
        :param trigger_data: The results difference.
        :param action_data: List of email addresses to send to.
        """
        device_collection = self._get_collection('devices_db', db_name=AGGREGATOR_PLUGIN_NAME)
        devices = [device_collection.find_one({'internal_axon_id': device[1]['internal_axon_id']})['adapters'][0]
                   for device in
                   trigger_data]
        devices = [(device[PLUGIN_UNIQUE_NAME], device['data']['id'])
                   for device in devices]

        self.add_many_labels_to_entity(devices, labels=[action_data])

    def _parse_action_content(self, triggers_data, triggered_triggers):
        """ Creates a readable message for the different actions.

        :param dict triggers_data: The data of this trigger event.
        :param set triggered_triggers: The actually triggered triggers.
        :return:
        """
        if report_consts.Triggers.Increase.name in triggered_triggers:
            return f'shown an Increase for the specified saved query.'

        if report_consts.Triggers.Above.name in triggered_triggers:
            return f'shown an increase of above {triggers_data[report_consts.Triggers.Above.name.lower()]} for the specified saved query.'

        if report_consts.Triggers.Decrease.name in triggered_triggers:
            return f'shown a decrease for the specified saved query.'

        if report_consts.Triggers.Below.name in triggered_triggers:
            return f'shown a decrease of below {triggers_data[report_consts.Triggers.Above.name.lower()]} for the specified saved query.'

        if report_consts.Triggers.No_Change.name in triggered_triggers:
            return f'stayed the same.'

    def _check_current_query_result(self, report_data):
        """This function checks if a specific report should be generated.

        This function checks the reports triggers and executes the actions if needed.

        :param dict report_data: All the report information.
        """

        def _diff(current_result, old_result):
            diff = list()
            for result in current_result:
                any_result_match = False
                for current_adapter_data in result['adapters_data']:
                    # The reason for the "list(current_adapter_data.values())[0]['id']" is because
                    # For some reason we currently keep a list of dicts in "adapters_data" with a key of adapter name
                    # For each correlated adapter...
                    if any(list(current_adapter_data.values())[0]['id'] == list(adapter_data.values())[0]['id'] for
                           current_device in old_result for adapter_data in current_device['adapters_data']):
                        any_result_match = True
                        break
                if not any_result_match:
                    diff.append((report_consts.Triggers.Increase.name, result))

            for result in old_result:
                any_result_match = False
                for old_adapter_data in result['adapters_data']:
                    # Same as above...
                    if any(list(old_adapter_data.values())[0]['id'] == list(adapter_data.values())[0]['id'] for
                           current_device in current_result for adapter_data in current_device['adapters_data']):
                        any_result_match = True
                        break
                if not any_result_match:
                    diff.append((report_consts.Triggers.Decrease.name, result))
            return diff

        def _trigger_watch(triggers, result_difference):
            if report_data['retrigger'] or report_data['triggered'] == 0:
                report_data['triggered'] += 1
                for action in report_data['actions']:
                    getattr(self, f"_handle_action_{action['type']}")(
                        report_data, triggers, result_difference, len(current_result), action.get('data'))
                self.update_report(report_data)

        try:
            current_result = self.get_query_results(json.loads(report_data['query']))
            if current_result is None:
                logger.info("Skipping reports trigger because there were no current results.")
                return
            retrigger = report_data['retrigger']
            # DeepDiff(report_data['result'], current_result, ignore_order=True)
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
