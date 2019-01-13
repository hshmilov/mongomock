import functools
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from enum import Enum, auto
from threading import RLock

from namedlist import namedlist, FACTORY

from axonius.mixins.feature import Feature
from axonius.plugin_base import add_rule
from flask import jsonify, request
from promise import Promise

from axonius.utils.threading import run_in_thread_helper, ReusableThread

logger = logging.getLogger(f'axonius.{__name__}')


class TriggerStates(Enum):
    """
    Defines the state of a triggerable plugin
    """

    def _generate_next_value_(name, *args):
        return name

    # Plugin was triggered and haven't finished working yet
    Triggered = auto()

    # Plugin finished the last trigger, or wasn't triggered at all,
    Scheduled = auto()


JobState = namedlist('JobState',
                     [
                         ('triggered', False),
                         ('scheduled', False),
                         ('promise', None),
                         ('last_error', ''),
                         ('lock', FACTORY(RLock)),
                         ('thread', FACTORY(ReusableThread)),
                         ('last_started_time', None),
                     ]
                     )


def _on_job_continue(job_state: JobState, last_error: str):
    if not job_state.scheduled:
        job_state.triggered = False
        # Why bother removing the reference to 'promise'?
        # This references is not allowing for the gc to clean everything that is referenced from the promise,
        # thus it blocks the GC from cleaning the stacktrace (or something like that) and thus some things, among
        # the iterators described in
        # https://axonius.atlassian.net/browse/AX-2996
        # will not be freed until the next call to triggerable and a GC run, and they should be cleaned now,
        # otherwise the system will lock up.
        # The reason this is safe is that job_state.promise is only used if job_state.triggered = True,
        # and clearly, job_state.promise = False after the line executed above.
        job_state.promise = None
    job_state.scheduled = False
    job_state.last_error = last_error


class Triggerable(Feature, ABC):
    """
    Defined a plugin that may be 'triggered' to do something
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__state = defaultdict(JobState)
        self.__last_error = ''

    @classmethod
    def specific_supported_features(cls) -> list:
        return ['Triggerable']

    @abstractmethod
    def _triggered(self, job_name: str, post_json: dict, *args):
        """
        This is called when the plugin is triggered
        :param job_name: the name of the job to run, the guarantees made are on a job_name basis
        :param post_json: additional JSON data received from post
        :return: ignored
        """
        pass

    def _stopped(self, job_name: str):
        """
        This is called when the plugin is stopped.
        If you want to be notified, override this
        :param job_name: the name of the job stopped
        """
        pass

    def _get_state(self, job_name: str):
        """
        See get_triggerable_state
        :param job_name:
        :return:
        """
        state = self.__state[job_name]

        if state.triggered:
            state_name = TriggerStates.Triggered.name
        else:
            state_name = TriggerStates.Scheduled.name

        return {
            # normalize states to Triggered and Scheduled
            'state': state_name,
            'last_error': state.last_error
        }

    @add_rule('trigger_state/<job_name>')
    def get_triggerable_state(self, job_name: str):
        """
        Get whether plugin state and last error.
        :return:
        """
        return jsonify(self._get_state(job_name))

    @add_rule('trigger/<job_name>', methods=['POST'])
    def trigger(self, job_name):
        """
        Trigger a job.
        :param job_name: the job to trigger.
        """
        # if ?blocking=True/False is passed than this request will wait until the trigger has completed
        blocking = request.args.get('blocking', 'True') == 'True'
        # if ?priority=True than this request will run immediately, ignoring any internal lock mechanism
        # use with caution!
        # priority assumes blocking
        priority = request.args.get('priority', 'False') == 'True'
        message = f'Triggered {job_name} ' + ('blocking' if blocking else 'unblocked') + ' with ' + \
                  ('prioritized' if priority else 'unprioritized') + f' from {self.get_caller_plugin_name()}'
        if blocking:
            logger.debug(message)
        else:
            logger.info(message)
        return self._trigger(job_name, blocking, priority, request.get_json(silent=True))

    @add_rule('wait/<job_name>', methods=['GET'])
    def wait_for_job(self, job_name):
        """
        If a certain job is running, this waits for it to finish, and returns the last return value
        :param job_name: The job to wait for
        """
        logger.info(f'Waiting for {job_name} from {self.get_caller_plugin_name()}')
        job_state = self.__state[job_name]

        promise = job_state.promise
        if promise:
            Promise.wait(promise)
            if promise.is_rejected or isinstance(promise.value, Exception):
                logger.error(f'Exception on wait: {promise.value}', exc_info=promise.value)
                return 'Error has occurred', 500
            return promise.value or ''
        return ''

    def __perform_stop_job(self, job_name, job_state):
        """
        Stops job_state
        """
        logger.info(f'Stopping job {job_name}')
        if job_state.triggered:
            logger.info(f'Job state: {job_state}')
            job_state.thread.terminate_thread()
            promise = job_state.promise
            if promise:
                job_state.promise = None
                promise.do_reject(Exception('Stopped manually exception'))
            job_state.scheduled = False
            job_state.triggered = False
            job_state.last_error = 'Stopped manually'
            self._stopped(job_name)

    @add_rule('stop/<job_name>', methods=['POST'])
    def stop_job(self, job_name):
        job_state = self.__state[job_name]
        with job_state.lock:
            self.__perform_stop_job(job_name, job_state)
        return ''

    @add_rule('stop_all', methods=['POST'])
    def stop_all_jobs(self):
        for job_name, job_state in self.__state.items():
            with job_state.lock:
                self.__perform_stop_job(job_name, job_state)
        return ''

    def _trigger(self, job_name='execute', blocking=True, priority=False, post_json=None):
        if priority:
            res = self._triggered(job_name, post_json) or ''
            return res

        job_state = self.__state[job_name]

        # having a lock per job allows more efficient parallelization
        with job_state.lock:
            promise = self.__perform_trigger(job_name, job_state, post_json)

        if blocking:
            Promise.wait(promise)
            if promise.is_rejected or isinstance(promise.value, Exception):
                logger.error(f'Exception on wait: {promise.value}', exc_info=promise.value)
                return 'Error has occurred', 500
            return promise.value or ''
        return ''

    def __perform_trigger(self, job_name, job_state, post_json=None):
        """
        Actually perform the job, assumes locks
        :return:
        """
        if job_state.scheduled:
            logger.info(f'job is already scheduled, {job_state}')
            return job_state.promise

        # If a plugin was triggered and then triggered again.
        # This is good for cases when a single trigger is enough but an event may happen while
        # a trigger is taking place and it can't be assured that the current trigger will respond to that event.
        #
        # For example, adding a client to an adapter will trigger the aggregator to aggregate that specific adapter.
        # If another client is then quickly added, another trigger will be issued.
        # In this case, it's difficult to know if the current trigger will or will not fetch that client,
        # so another trigger will be scheduled.
        def on_success(arg):
            with job_state.lock:
                _on_job_continue(job_state, 'Ran OK')
                logger.info('Successfully triggered')
                return arg

        def on_failed(err):
            with job_state.lock:
                _on_job_continue(job_state, str(repr(err)))
                logger.error(f'Failed triggering up: {err}', exc_info=err)
                return err

        def to_run(*args, **kwargs):
            with job_state.lock:
                if not job_state.promise:
                    return
                job_state.last_started_time = datetime.now()
            return self._triggered(job_name, post_json, *args, **kwargs)

        if job_state.triggered:
            job_state.scheduled = True
            job_state.promise = job_state.promise.then(lambda x: Promise(functools.partial(run_in_thread_helper,
                                                                                           job_state.thread,
                                                                                           to_run)))

        else:
            job_state.triggered = True
            job_state.promise = Promise(functools.partial(run_in_thread_helper,
                                                          job_state.thread,
                                                          to_run))
        job_state.promise = job_state.promise.then(did_fulfill=on_success,
                                                   did_reject=on_failed)
        return job_state.promise
