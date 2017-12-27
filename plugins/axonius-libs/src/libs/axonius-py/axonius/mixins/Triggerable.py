import concurrent.futures
from abc import ABC, abstractmethod
from enum import Enum, auto
from threading import Lock

import functools

from flask import jsonify, request
from promise import Promise

from axonius.mixins.Feature import Feature
from axonius.PluginBase import add_rule, return_error
from axonius.ThreadingUtils import run_in_executor_helper


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
        self.__state = TriggerStates.Idle
        # this executor executes the trigger function
        self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.__last_error = ""

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Triggerable"]

    @abstractmethod
    def _triggered(self, post_json):
        """
        This is called when the plugin is triggered
        :return:
        """
        pass

    @add_rule('trigger_state')
    def get_trigger_activatable_state(self):
        """
        Get whether plugin state and last error.
        :return:
        """
        return jsonify({
            "State": self.__state.value,
            "LastError": self.__last_error
        })

    @add_rule('trigger', methods=['POST'])
    def trigger(self):
        with self.__trigger_lock:
            if self.__state != TriggerStates.Idle:
                return return_error("Plugin is not at rest", 412)
            self.__state = TriggerStates.Triggered
            promise = Promise(
                functools.partial(run_in_executor_helper,
                                  self.__executor,
                                  functools.partial(self._triggered, request.get_json(silent=True))))

            def on_success(*args):
                self.__state = TriggerStates.Idle
                self.logger.info("Successfully triggered")

            def on_failed(err):
                # if failed, restore to 'Disabled'
                self.logger.error(f"Failed triggering up: {err}")
                self.__last_error = str(repr(err))
                self.__state = TriggerStates.Idle

            promise.then(did_fulfill=on_success,
                         did_reject=on_failed)
            return ""
