# Standard modules
import concurrent.futures
import threading
import datetime
from deepdiff import DeepDiff
from bson.objectid import ObjectId
from axonius.mixins.triggerable import Triggerable

# pip modules
from flask import jsonify, json

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.utils.files import get_local_config_file


class WatchService(PluginBase, Triggerable):
    def __init__(self, *args, **kwargs):
        """ This service is responsible for alerting users in several ways and cases when a
                        watched query result changes. """

        # Initialize the watcher threads, get the DB credentials and set the default sampling rate.
        def _parse_mongo_id(watch):
            watch['_id'] = str(watch['_id'])
            return watch

        super().__init__(get_local_config_file(__file__), *args, **kwargs)

        # Loading watch resources from db (If any exist).
        self._watched_queries = {str(watch['query']): _parse_mongo_id(watch)
                                 for watch in self._get_collection('watches').find()}

        # Set's a sample rate to check the saved queries.
        self._watch_check_lock = threading.RLock()

        self._activate('execute')

    def _triggered(self, job_name: str, post_json: dict, *args):
        if job_name != 'execute':
            self.logger.error(f"Got bad trigger request for non-existent job: {job_name}")
            return return_error("Got bad trigger request for non-existent job", 400)
        else:
            return self._check_watches()

    @add_rule("watch/<watch_id>", methods=['GET', 'DELETE', 'POST'])
    def watch_by_id(self, watch_id):
        """The specific rest watch endpoint.

        Gets, Deletes and edits (currently deletes and creates again with same ID) specific watch by ID.

        :return: Correct HTTP response.
        """
        try:
            if self.get_method() == 'GET':
                requested_watch = self._get_collection('watches').find_one({'_id': ObjectId(watch_id)})
                return jsonify(requested_watch) if requested_watch is not None else return_error('A watch with that id was not found.', 404)
            elif self.get_method() == 'DELETE':
                return self._remove_watch(watch_id)
            elif self.get_method() == 'POST':
                watch_data = self.get_request_data_as_object()
                delete_response = self._remove_watch(watch_id)
                if delete_response[1] == 404:
                    return return_error('A watch with that ID was not found.', 404)
                watch_data['_id'] = watch_id
                self._add_watch(watch_data)
                return '', 200

        except ValueError:
            message = 'Expected JSON, got something else...'
            self.logger.exception(message)
            return return_error(message, 400)

    @add_rule("watch", methods=['PUT', 'GET', 'DELETE'])
    def watch(self):
        """The Rest watch endpoint.

        Creates and deletes the watch resources as well as gets a list of all of them.

        While creating a new watch resource a parameter named "criteria" should be included.
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
                return self._add_watch(self.get_request_data_as_object())
            elif self.get_method() == 'GET':
                return jsonify(self._watched_queries.values())
            elif self.get_method() == 'DELETE':
                return self._remove_watch(self.get_request_data_as_object())
        except ValueError:
            message = 'Expected JSON, got something else...'
            self.logger.exception(message)
            return return_error(message, 400)

    def _add_watch(self, watch_data):
        """Adds a watch on a query.

        Creates a watch resource which is a query on our device_db that the user or a plugin wants to be notified when
        it's result changes (criteria should indicate whether to notify in
        only a specific change to the results or any).
        :param dict watch_data: The query to watch (as a valid mongo query) and criteria.
        :return: Correct HTTP response.
        """
        # Checks if requested query isn't already watched.
        try:
            if json.dumps(watch_data['query']) not in self._watched_queries.keys() and \
                    len([current_watch for current_watch in self._watched_queries.keys()
                         if len(DeepDiff(current_watch, watch_data['query'], ignore_order=True)) == 0]) == 0:

                current_query_result = self.get_query_results(watch_data['query'])
                if current_query_result is None:
                    return return_error('Aggregator is down, please try again later.', 404)

                watch_resource = {'watch_time': datetime.datetime.now(), 'criteria': int(watch_data['criteria']),
                                  'alert_types': watch_data['alert_types'],
                                  'result': current_query_result,
                                  'query': json.dumps(watch_data['query']),
                                  'retrigger': watch_data['retrigger'],
                                  'triggered': 0,
                                  'name': watch_data['name'],
                                  'severity': watch_data['severity']
                                  }

                if '_id' in watch_data:
                    watch_resource['_id'] = ObjectId(watch_data['_id'])

                # Adds the query to the local watch dict
                self._watched_queries[json.dumps(
                    watch_data['query'])] = watch_resource

                # Pushes the resource to the db.
                insert_result = self._get_collection('watches').insert_one(watch_resource)
                self._watched_queries[json.dumps(
                    watch_data['query'])]['_id'] = str(insert_result.inserted_id)
                self.logger.info('Added query to watch list')
                return str(insert_result.inserted_id), 201

            return return_error('An existing watch on a query as been requested', 409)

        except KeyError as e:
            message = 'The query watch request is missing data. Details: {0}'.format(str(e))
            self.logger.exception(message)
            return return_error(message, 400)
        except TypeError as e:
            message = 'The mongo query was invalid. Details: {0}'.format(str(e))
            self.logger.exception(message)
            return return_error(message, 400)

    def _remove_watch(self, watch_data):
        """Delete a watch resource if it exists.

        :param watch_data: The watched query to delete
        :return: Correct HTTP response.
        """
        if isinstance(watch_data, dict):
            delete_result = self._get_collection('watches').delete_one(
                {'query': json.dumps(watch_data['query'])})
            try:
                del self._watched_queries[json.dumps(watch_data['query'])]
                if delete_result.deleted_count == 0:
                    self.logger.info(
                        'Successfully deleted a watch that existed only in-memory (not on the DB.')

                self.logger.info('Removed query from watch.')
                return '', 200
            except KeyError:
                if delete_result != 0:
                    self.logger.info(
                        'Deleted a watch that only existed on the DB.')

                return return_error('Attempted to delete un existing watch.', 404)
        elif isinstance(watch_data, str):
            delete_result = self._get_collection('watches').delete_one(
                {'_id': ObjectId(watch_data)})
            deleted = False
            for current_query in self._watched_queries.keys():
                if self._watched_queries[current_query]['_id'] == watch_data:
                    del self._watched_queries[current_query]
                    deleted = True
                    break

            if deleted and delete_result.deleted_count == 0:
                self.logger.info(
                    'Successfully deleted a watch that existed only in-memory (not on the DB.')
            elif not deleted and delete_result.deleted_count != 0:
                self.logger.info(
                    'Deleted a watch that only existed on the DB.')

                return return_error('Attempted to delete un existing watch.', 404)
            elif not deleted and delete_result.deleted_count == 0:
                self.logger.info(
                    'Attempted to delete un existing watch.')
                return return_error('Attempted to delete un existing watch.', 404)

            self.logger.info('Removed query from watch.')
            return '', 200

    def get_query_results(self, query):
        """Gets a query's results from the aggregator devices_db.

        :param query: The query to use.
        :return: The results of the query.
        """
        return list(self._get_collection('devices_db', db_name=AGGREGATOR_PLUGIN_NAME).find(query))

    def _check_watches(self):
        """Function for monitoring other threads activity.

        This function should run in a different thread. It runs forever and monitors the other watch threads.
        If a new query will be watched, this function will create a new thread for it.
        Currently the sampling rate is hard coded for 60 seconds.
        """
        try:
            with self._watch_check_lock:
                for query_string, current_query in self._watched_queries.items():
                    with concurrent.futures.ThreadPoolExecutor() as executor:

                        future_for_watch_checks = {executor.submit(
                            self._check_current_query_result, query_string): current_query for query_string, current_query in self._watched_queries.items()}

                        for future in concurrent.futures.as_completed(future_for_watch_checks):
                            self.logger.info(f'{future_for_watch_checks[future]} finished checking watch.')
        except Exception:
            self.logger.exception("Failed to check watches.")
            return return_error("Failed to check watches.")
        return ''

    def _check_current_query_result(self, query):
        """Function for getting all devices from specific adapter periodically.

        This function should be called in a different thread. It will periodically run a watched query
        on the device_db, check if the result is different from the saved results and notify if needed.

        Repeated errors from this function could be a race condition of a deleted watch.

        :param str query: The watched query to sample.
        :param str saved_result: The saved results from the query at time of watch.
        :param int criteria: Should be -1,0 or 1 to identify in which case the user wants to be notified.
        """

        def _trigger_watch():

            alert_types = self._watched_queries[query]['alert_types']
            if retrigger or self._watched_queries[query]['triggered'] == 0:
                self._watched_queries[query]['triggered'] += 1
                for alert in alert_types:
                    if alert['type'] == 'notification':
                        self.create_notification(alert['title'], '{0}. {1}'.format(alert['message'],
                                                                                   'Num of Triggers is {0}'.format(
                                                                                       self._watched_queries[query][
                                                                                           'triggered']), 'alert'),
                                                 severity_type=self._watched_queries[query]['severity'])
                        self.logger.info(
                            'Watch triggered on query: {0}'.format(str(query)))

        try:
            current_result = self.get_query_results(json.loads(query))
            if current_result is None:
                self.logger.info("Skipping watch trigger because there's no aggregator.")
                return
            saved_result = self._watched_queries[query]['result']
            criteria = self._watched_queries[query]['criteria']
            retrigger = self._watched_queries[query]['retrigger']

            if current_result != saved_result:
                if criteria == 0:
                    _trigger_watch()
                if (criteria > 0 and len(saved_result) - len(current_result) < 0) or (
                        criteria < 0 and len(saved_result) - len(current_result) > 0):
                    _trigger_watch()

                if retrigger:
                    self._watched_queries[query]['result'] = current_result

        except Exception as e:
            self.logger.exception(
                "Thread {0} encountered error: {1}. Repeated errors like this could be a race condition of a deleted watch.".format(
                    threading.current_thread(), str(e)))
            raise

    @property
    def plugin_subtype(self):
        return "Post-Correlation"
