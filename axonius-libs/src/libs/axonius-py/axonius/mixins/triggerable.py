import functools
import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from threading import RLock

from axonius.thread_stopper import stoppable, StopThreadException

from axonius.mixins.feature import Feature
from axonius.plugin_base import add_rule, return_error
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
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

    """
    Plugin was triggered and haven't finished working yet
    """
    Triggered = auto()
    """
    Plugin finished the last trigger, or wasn't triggered at all, 
    """
    Scheduled = auto()
    """
    The trigger is disabled.
    """
    Disabled = auto()


class Triggerable(Feature, ABC):
    """
    Defined a plugin that may be "triggered" to do something
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__trigger_lock = RLock()
        self.__state = {}
        # this executor executes the trigger function
        self.__executor = LoggedThreadPoolExecutor(max_workers=20)
        self.__last_error = ""
        self._default_activity = False

    def trigger_activate_if_needed(self):
        docs = self._get_collection("config").find({'trigger_activate_job': {'$exists': 1}})
        for doc in docs:
            job_name = doc['trigger_activate_job']
            job_state = doc['trigger_activate_state']
            logger.info(f'Trigger activate job {job_name}: state is {job_state}')
            if job_state is True:
                self._activate(job_name)

    def __trigger_activate_save_to_db(self):
        """
        Saves the state into the db.
        :return:
        """

        for job_name, state in self.__state.items():
            self._get_collection('config').update(
                {'trigger_activate_job': job_name},
                {
                    'trigger_activate_job': job_name,
                    'trigger_activate_state': bool(state.get('active', False))
                },
                upsert=True
            )

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Triggerable"]

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
            raise Exception("Stopped")

    @add_rule('trigger_state/<job_name>')
    def get_trigger_activatable_state(self, job_name: str):
        """
        Get whether plugin state and last error.
        :return:
        """
        if job_name != 'execute':
            state = self.__state.get(job_name)
            if state is None:
                return return_error("Job name not found", 404)
        else:
            state = self._get_state_or_default(job_name)

        with state['lock']:
            state_name = TriggerStates.Disabled.name

            if state['triggered']:
                state_name = TriggerStates.Triggered.name
            elif state['active']:
                state_name = TriggerStates.Scheduled.name

            return jsonify({
                # normalize states to Triggered and Scheduled
                "state": state_name,
                "last_error": state['last_error']
            })

    @add_rule('trigger_activate/<job_name>', methods=['POST'])
    def activate(self, job_name):
        """
        Activate the trigger job.
        :param job_name: the job to activate.
        :return:
        """
        return self._activate(job_name)

    def _activate(self, job_name):
        """
        Activate the trigger job.
        :param job_name: the job to activate.
        :return:
        """
        job_state = self._get_state_or_default(job_name)
        # Flipping current active state.
        job_state['active'] = True
        logger.info(f'Trigger job {job_name} has been activated.')
        self.__trigger_activate_save_to_db()
        return ''

    @add_rule('trigger_deactivate/<job_name>', methods=['POST'])
    def deactivate(self, job_name):
        """
        Deactivate the trigger job.
        :param job_name: the job to Deactivate.
        :return:
        """
        return self._deactivate(job_name)

    def _deactivate(self, job_name):
        """
        Deactivate the trigger job.
        :param job_name: the job to Deactivate.
        :return:
        """
        job_state = self._get_state_or_default(job_name)
        # Flipping current active state.
        job_state['active'] = False
        logger.info(f'Trigger job {job_name} has been deactivated.')
        return ''

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
                                           'promise': None,
                                           'active': self._default_activity,
                                           'last_error': "",
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
        logger.info(f"Triggered {job_name} " +
                    ('blocking' if blocking else 'unblocked') + " with " +
                    ('prioritized' if priority else 'unprioritized') +
                    f" from {self.get_caller_plugin_name()}")
        return self._trigger(job_name, blocking, priority)

    def _trigger(self, job_name, blocking=True, priority=False):
        if priority:
            self._triggered_facade(job_name, request.get_json(silent=True))
            return ''

        with self.__trigger_lock:
            job_state = self._get_state_or_default(job_name)

        # having a lock per job allows more efficient parallelization
        with job_state['lock']:
            self.__perform_trigger(job_name, job_state)

        if blocking:
            if job_state['promise']:
                Promise.wait(job_state['promise'])
        return ''

    def __perform_trigger(self, job_name, job_state):
        """
        Actually perform the job, assumes locks
        :return:
        """
        if job_state['scheduled']:
            # it's already triggered and scheduled
            return ''

        if not job_state['active']:
            return ''
            # return return_error(f"{job_name} trigger is disabled.", 403)

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
                logger.info("Successfully triggered")
                return arg

        def on_failed(err):
            with job_state['lock']:
                logger.error(f'Failed triggering up: {err}')
                job_state['last_error'] = str(repr(err))
                if not job_state['scheduled']:
                    job_state['triggered'] = False
                job_state['scheduled'] = False
                return err

        to_run = functools.partial(self._triggered_facade, job_name, request.get_json(silent=True))
        if job_state['triggered']:
            job_state['scheduled'] = True
            job_state['promise'] = job_state['promise'].then(to_run)

        else:
            job_state['triggered'] = True
            job_state['promise'] = Promise(functools.partial(run_in_executor_helper,
                                                             self.__executor,
                                                             to_run))
        job_state['promise'].then(did_fulfill=on_success,
                                  did_reject=on_failed)
