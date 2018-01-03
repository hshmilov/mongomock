import concurrent.futures
from abc import ABC, abstractmethod
from enum import Enum, auto
from threading import RLock

import functools

from flask import jsonify, request
from promise import Promise

from axonius.mixins.feature import Feature
from axonius.plugin_base import add_rule, return_error
from axonius.threading_utils import run_in_executor_helper


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
    Plugin finished the last trigger, or wasn't triggered at all
    """
    Idle = auto()


class Triggerable(Feature, ABC):
    """
    Defined a plugin that may be "triggered" to do something
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__trigger_lock = RLock()
        self.__state = {}
        # this executor executes the trigger function
        self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self.__last_error = ""

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
        state = self.__state.get(job_name)
        if state is None:
            return return_error("Job name not found", 404)

        with state['lock']:
            return jsonify({
                # normalize states to Triggered and Idle
                "state": TriggerStates.Triggered.value if state['triggered'] else TriggerStates.Idle.value,
                "last_error": state['last_error']
            })

    @add_rule('trigger/<job_name>', methods=['POST'])
    def trigger(self, job_name):
        with self.__trigger_lock:
            job_state = self.__state.setdefault(job_name,
                                                {
                                                    'triggered': False,
                                                    'scheduled': False,
                                                    'promise': None,
                                                    'last_error': "",
                                                    'lock': RLock()
                                                }
                                                )

        # having a lock per job allows more efficient parallelization
        with job_state['lock']:
            if job_state['scheduled']:
                # it's already triggered and scheduled
                return ""

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

            to_run = functools.partial(self._triggered, job_name, request.get_json(silent=True))

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
            return ""
