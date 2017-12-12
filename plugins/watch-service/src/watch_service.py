# Standard modules
import threading
import time
import datetime

# pip modules
import os
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import jsonify, json

from axonius.PluginBase import PluginBase, add_rule, return_error


class WatchService(PluginBase):
    def __init__(self, *args, **kwargs):
        """
        Initializes the watcher threads, gets the DB credentials and sets the default sampling rate.
        """
        super().__init__(*args, **kwargs)

        self._scheduler = None
        aggregator_data = self.get_plugin_by_name('aggregator')

        self._device_collection_location = self.get_aggregator(aggregator_data)

        # Loading watch resources from db (If any exist).
        self._watched_queries = {
            str(watch['query']): watch for watch in self._get_collection('watches').find()}

        # Set's a sample rate to check the saved queries.
        self._default_query_sample_rate = 10

        # Starts the watch manager thread.
        self._start_managing_thread()

    def get_aggregator(self, aggregator_data):
        if aggregator_data is None:
            self.logger.error('No Aggregator found.')
            return None
        else:
            return aggregator_data['plugin_unique_name']

    @add_rule("trigger_watches", methods=['GET'])
    def run_jobs(self):
        if self._scheduler is not None:
            for job in self._scheduler.get_jobs():
                job.modify(next_run_time=datetime.datetime.now())
            self._scheduler.wakeup()
        return '', 200

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
            self.logger.error(message)
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
            if json.dumps(watch_data['query']) not in self._watched_queries.keys():
                current_query_result = self.get_query_results(watch_data['query'])

                if current_query_result is None:
                    return return_error('Aggregator is down, please try again later.', 404)
                watch_resource = {'watch_time': datetime.datetime.now(), 'criteria': int(watch_data['criteria']),
                                  'alert_types': watch_data['alert_types'],
                                  'result': current_query_result,
                                  'query_sample_rate': self._default_query_sample_rate,
                                  'query': json.dumps(watch_data['query']),
                                  'retrigger': watch_data['retrigger'],
                                  'triggered': 0}

                # Adds the query to the local watch dict
                self._watched_queries[json.dumps(
                    watch_data['query'])] = watch_resource

                # Pushes the resource to the db.
                self._get_collection('watches').insert_one(watch_resource)

                self.logger.info('Added query to watch list')
                return 'CREATED', 201

            return return_error('An existing watch on a query as been requested', 409)

        except KeyError:
            message = 'The query watch request is missing data.'
            self.logger.error(message)
            return return_error(message, 400)
        except TypeError:
            message = 'The mongo query was invalid.'
            self.logger.error(message)
            return return_error(message, 400)

    def _remove_watch(self, watch_data):
        """Delete a watch resource if it exists.

        :param watch_data: The watched query to delete
        :return: Correct HTTP response.
        """
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

    def get_query_results(self, query):
        """Gets a query's results from the aggregator devices_db.

        :param query: The query to use.
        :return: The results of the query.
        """
        if self._device_collection_location is None:
            aggregator_data = self.get_plugin_by_name('aggregator')
            self._device_collection_location = self.get_aggregator(aggregator_data)

        if self._device_collection_location is not None:
            return list(self._get_collection('devices_db', db_name=self._device_collection_location).find(query))
        else:
            return None

    def _start_managing_thread(self):
        """
        Starts watching.
        """
        if self._scheduler is None:
            executors = {'default': ThreadPoolExecutor(10)}
            self._scheduler = BackgroundScheduler(executors=executors)
            self._scheduler.add_job(func=self._watch_thread_manager,
                                    trigger=IntervalTrigger(seconds=60),
                                    next_run_time=datetime.datetime.now(),
                                    name='watch_thread_manager',
                                    id='watch_thread_manager',
                                    max_instances=1)
            self._scheduler.start()

        else:
            raise RuntimeError("Already running")

    def _watch_thread_manager(self):
        """Function for monitoring other threads activity.

        This function should run in a different thread. It runs forever and monitors the other watch threads.
        If a new query will be watched, this function will create a new thread for it.
        Currently the sampling rate is hard coded for 60 seconds.
        """
        try:
            # let's add jobs for all adapters
            for query_string, current_query in self._watched_queries.items():

                if self._scheduler.get_job(query_string):
                    # We already have a running thread for this adapter
                    continue

                sample_rate = current_query['query_sample_rate']
                self._scheduler.add_job(func=self._check_current_query_result,
                                        trigger=IntervalTrigger(
                                            seconds=sample_rate),
                                        next_run_time=datetime.datetime.now(),
                                        kwargs={
                                            'query': current_query['query']},
                                        name="Fetching job for query={}".format(
                                            query_string),
                                        id=query_string,
                                        max_instances=1)

            for job in self._scheduler.get_jobs():
                if job.id not in self._watched_queries.keys() and job.id != 'watch_thread_manager':
                    # this means that the adapter has disconnected, so we stop fetching it
                    job.remove()

        except Exception as e:
            self.logger.critical('Managing thread got exception, '
                                 'must restart aggregator manually. Exception: {0}'.format(str(e)))
            os._exit(1)

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
                                                                                           'triggered']), 'alert'))
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
            self.logger.error(
                "Thread {0} encountered error: {1}. Repeated errors like this could be a race condition of a deleted watch.".format(
                    threading.current_thread(), str(e)))
            raise
