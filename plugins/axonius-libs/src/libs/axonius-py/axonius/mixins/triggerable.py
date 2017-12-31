import concurrent.futures
from abc import ABC, abstractmethod
from enum import Enum, auto
from threading import Lock

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
        self.__trigger_lock = Lock()
        self.__state = {}
        # this executor executes the trigger function
        self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.__last_error = ""

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Triggerable"]

    @abstractmethod
    def _triggered(self, job_name: str, post_json: dict):
        """
        This is called when the plugin is triggered
        :return:
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
        return jsonify({
            "state": state['state'].value,
            "last_error": state['last_error']
        })

    @add_rule('trigger/<job_name>', methods=['POST'])
    def trigger(self, job_name):
        with self.__trigger_lock:
            job_state = self.__state.setdefault(job_name,
                                                {
                                                    'state': TriggerStates.Idle,
                                                    'last_error': "No Error"
                                                }
                                                )
            if job_state['state'] != TriggerStates.Idle:
                return return_error("Plugin is not at rest", 412)
            job_state['state'] = TriggerStates.Triggered
            promise = Promise(
                functools.partial(run_in_executor_helper,
                                  self.__executor,
                                  functools.partial(self._triggered, job_name, request.get_json(silent=True))))

            def on_success(*args):
                job_state['state'] = TriggerStates.Idle
                self.logger.info("Successfully triggered")

            def on_failed(err):
                # if failed, restore to 'Disabled'
                self.logger.error(f"Failed triggering up: {err}")
                job_state['last_error'] = str(repr(err))
                job_state['state'] = TriggerStates.Idle

            promise.then(did_fulfill=on_success,
                         did_reject=on_failed)
            return ""
