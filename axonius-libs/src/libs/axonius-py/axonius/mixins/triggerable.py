import functools
import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from threading import RLock

from axonius.mixins.feature import Feature
from axonius.plugin_base import add_rule
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.thread_stopper import StopThreadException, stoppable
from axonius.utils.threading import run_in_executor_helper
from flask import jsonify, request
from promise import Promise

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


class Triggerable(Feature, ABC):
    """
    Defined a plugin that may be 'triggered' to do something
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__trigger_lock = RLock()
        self.__state = {}
        # this executor executes the trigger function
        self.__executor = LoggedThreadPoolExecutor(max_workers=20)
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

    @stoppable
    def _triggered_facade(self, *args, **kwargs):
        try:
            return self._triggered(*args, **kwargs)
        except StopThreadException:
            # promises can't accept a StopThreadException
            raise Exception('Stopped')

    def _get_state(self, job_name: str):
        """
        See get_triggerable_state
        :param job_name:
        :return:
        """
        with self.__trigger_lock:
            state = self._get_state_or_default(job_name).copy()

        if state['triggered']:
            state_name = TriggerStates.Triggered.name
        else:
            state_name = TriggerStates.Scheduled.name

        return {
            # normalize states to Triggered and Scheduled
            'state': state_name,
            'last_error': state['last_error']
        }

    @add_rule('trigger_state/<job_name>')
    def get_triggerable_state(self, job_name: str):
        """
        Get whether plugin state and last error.
        :return:
        """
        return jsonify(self._get_state(job_name))

    def _get_state_or_default(self, job_name):
        """
        Get's either the current state or a default if it doesn't exist.
        :param job_name: the job to get state of.
        :return:
        """
        return self.__state.setdefault(job_name,
                                       {
                                           'triggered': False,
                                           'scheduled': False,
                                           'cancel_scheduled': False,
                                           'promise': None,
                                           'last_error': '',
                                           'lock': RLock()
                                       }
                                       )

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
        logger.info(f'Triggered {job_name} ' +
                    ('blocking' if blocking else 'unblocked') + ' with ' +
                    ('prioritized' if priority else 'unprioritized') +
                    f' from {self.get_caller_plugin_name()}')
        return self._trigger(job_name, blocking, priority, request.get_json(silent=True))

    @add_rule('wait/<job_name>', methods=['GET'])
    def wait_for_job(self, job_name):
        """
        If a certain job is running, this waits for it to finish, and returns the last return value
        :param job_name: The job to wait for
        """
        logger.info(f'Waiting for {job_name} from {self.get_caller_plugin_name()}')
        with self.__trigger_lock:
            job_state = self._get_state_or_default(job_name)

        promise = job_state['promise']
        if promise:
            Promise.wait(promise)
            if promise.is_rejected:
                logger.error(f'Exception on wait: {promise.value}', exc_info=promise.value)
                return 'Error has occurred', 500
            return promise.value or ''
        return ''

    def _trigger(self, job_name='execute', blocking=True, priority=False, post_json=None):
        if priority:
            return self._triggered_facade(job_name, post_json) or ''

        with self.__trigger_lock:
            job_state = self._get_state_or_default(job_name)

        # having a lock per job allows more efficient parallelization
        with job_state['lock']:
            self.__perform_trigger(job_name, job_state, post_json)

        if blocking:
            promise = job_state['promise']
            if promise:
                Promise.wait(promise)
                if promise.is_rejected:
                    logger.error(f'Exception on wait: {promise.value}', exc_info=promise.value)
                    return 'Error has occurred', 500
                return promise.value or ''
        return ''

    def __perform_trigger(self, job_name, job_state, post_json=None):
        """
        Actually perform the job, assumes locks
        :return:
        """
        if job_state['scheduled']:
            logger.info(f'job is already scheduled, {job_state}')
            return ''
        job_state['cancel_scheduled'] = False

        # If a plugin was triggered and then triggered again.
        # This is good for cases when a single trigger is enough but an event may happen while
        # a trigger is taking place and it can't be assured that the current trigger will respond to that event.
        #
        # For example, adding a client to an adapter will trigger the aggregator to aggregate that specific adapter.
        # If another client is then quickly added, another trigger will be issued.
        # In this case, it's difficult to know if the current trigger will or will not fetch that client,
        # so another trigger will be scheduled.
        def on_success(arg):
            with job_state['lock']:
                if not job_state['scheduled']:
                    job_state['triggered'] = False
                job_state['scheduled'] = False
                logger.info('Successfully triggered')
                return arg

        def on_failed(err):
            with job_state['lock']:
                logger.error(f'Failed triggering up: {err}')
                job_state['last_error'] = str(repr(err))
                if not job_state['scheduled']:
                    job_state['triggered'] = False
                job_state['scheduled'] = False
                return err

        def to_run(*args, **kwargs):
            with job_state['lock']:
                is_to_be_canceled = job_state['cancel_scheduled']
                job_state['cancel_scheduled'] = False

            if not is_to_be_canceled:
                return self._triggered_facade(job_name, post_json, *args, **kwargs)

        if job_state['triggered']:
            job_state['scheduled'] = True
            job_state['promise'] = job_state['promise'].then(lambda x: Promise(functools.partial(run_in_executor_helper,
                                                                                                 self.__executor,
                                                                                                 to_run)))

        else:
            job_state['triggered'] = True
            job_state['promise'] = Promise(functools.partial(run_in_executor_helper,
                                                             self.__executor,
                                                             to_run))
        job_state['promise'] = job_state['promise'].then(did_fulfill=on_success,
                                                         did_reject=on_failed)

    def _unschedule(self, job_name: str = 'execute'):
        """
        In case you want to cancel a scheduled job and doesn't allow any new scheduled jobs until
        the current job finishes
        :param job_name: the job to schedule, e.g. 'execute'
        """
        with self.__trigger_lock:
            job_state = self._get_state_or_default(job_name)

        with job_state['lock']:
            if not job_state['triggered']:
                return  # not running - nothing to cancel
            job_state['scheduled'] = True
            job_state['cancel_scheduled'] = True

    def _restore_to_running_state(self, job_name: str = 'execute'):
        """
        Sometimes the thread responsible on running your trigger messes up
        This might mean that your state will always be `running` or some sort
        :param job_name: the job to restore to default
        """
        with self.__trigger_lock:
            old_state = self.__state.pop(job_name, None)
        if old_state:
            logger.warning(f'Restored triggered on {old_state}')
