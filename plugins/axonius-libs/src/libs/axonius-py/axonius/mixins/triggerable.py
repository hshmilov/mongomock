from abc import ABC, abstractmethod
from enum import Enum, auto
from threading import RLock

from flask import jsonify, request

from axonius.mixins.feature import Feature
from axonius.plugin_base import add_rule, return_error
from axonius.thread_pool_executor import LoggedThreadPoolExecutor


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
        self.__executor = LoggedThreadPoolExecutor(self.logger, max_workers=20)
        self.__last_error = ""
        self._default_activity = False

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
        self.logger.info(f'Trigger job {job_name} has been activated.')
        return ''

    @add_rule('trigger_deactivate/<job_name>', methods=['POST'])
    def deactivate(self, job_name):
        """
        Deactivate the trigger job.
        :param job_name: the job to Deactivate.
        :return:
        """
        self._deactivate(job_name)

    def _deactivate(self, job_name):
        """
        Deactivate the trigger job.
        :param job_name: the job to Deactivate.
        :return:
        """
        job_state = self._get_state_or_default(job_name)
        # Flipping current active state.
        job_state['active'] = False
        self.logger.info(f'Trigger job {job_name} has been deactivated.')
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
        with self.__trigger_lock:
            job_state = self._get_state_or_default(job_name)

        # having a lock per job allows more efficient parallelization
        with job_state['lock']:
            if job_state['scheduled']:
                # it's already triggered and scheduled
                return ""

            if not job_state['active']:
                return ""
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
                    self.logger.info("Successfully triggered")
                    return arg

            def on_failed(err):
                with job_state['lock']:
                    self.logger.error(f"Failed triggering up: {err}")
                    job_state['last_error'] = str(repr(err))
                    if not job_state['scheduled']:
                        job_state['triggered'] = False
                    job_state['scheduled'] = False
                    return err

            if job_state['triggered']:
                job_state['scheduled'] = True
            else:
                job_state['triggered'] = True

            trigger_response = "Didn't run yet"
            try:
                trigger_response = self._triggered(job_name, request.get_json(silent=True))
                on_success(trigger_response)
            except Exception as err:
                self.logger.exception(f'An exception was raised while triggering job: {job_name}')
                on_failed(err)
                raise

            return trigger_response
