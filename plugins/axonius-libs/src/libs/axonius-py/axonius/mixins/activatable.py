from abc import ABC, abstractmethod
from enum import Enum, auto
from threading import RLock

import functools
from flask import jsonify
from promise import Promise

from axonius.plugin_base import add_rule
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.threading_utils import run_in_executor_helper
from axonius.mixins.feature import Feature


class ActiveStates(Enum):
    """
    Defines the state of an activatable plugin.
    At a specific point in time, it may be disabled, doing work, or not disabled and will do work in some point in the
    future.
    """

    def _generate_next_value_(name, *args):
        return name

    """
    Plugin is scheduled to run in the near future, i.e. is "active"
    """
    Scheduled = auto()
    """
    Plugin isn't running and isn't scheduled
    """
    Disabled = auto()
    """
    Plugin work is taking place right now
    """
    InProgress = auto()
    """
    Plugin is in the process of starting up (e.g. after calling /start)
    """
    StartingUp = auto()
    """
    Plugin is in the process of shutting down (e.g. after calling /stop)
    """
    ShuttingDown = auto()


class Activatable(Feature, ABC):
    """
    Defines common methods and api for plugins that can be "started" and "stopped", say, like the Aggregator.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__activation_lock = RLock()

        # this executor starts and closes the activatable
        self.__executor = LoggedThreadPoolExecutor(self.logger, max_workers=1)

        # this is used internally for startup and shutdown logic
        self.__shutdown_startup_state = ActiveStates.Disabled
        self.__last_error = ""

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Activatable"]

    @add_rule('start')
    def start_scheduling(self):
        """
        Start scheduling
        :return:
        """
        return self.start_activatable()

    @add_rule('stop')
    def stop_scheduling(self):
        """
        Stop scheduling
        :return:
        """
        return self.stop_activatable()

    @add_rule('state')
    def get_activatable_state(self):
        """
        Get whether plugin state and last error.
        :return:
        """
        return jsonify({
            "State": self._get_activatable_state().value,
            "LastError": self.__last_error
        })

    def _get_activatable_state(self):
        """
        Get whether plugin work is taking place, scheduled, or not scheduled.
        :return:
        """
        with self.__activation_lock:
            current_state = self.__shutdown_startup_state
            if current_state != ActiveStates.Scheduled:
                return current_state
            if self._is_work_in_progress():
                return ActiveStates.InProgress
            return ActiveStates.Scheduled

    def _set_activation_state(self, new_state):
        """
        Internally used
        :type new_state: ActiveState
        :return: None
        """
        with self.__activation_lock:
            self.__shutdown_startup_state = new_state

    def start_activatable(self):
        with self.__activation_lock:
            # test of anomalies
            if self.__shutdown_startup_state == ActiveStates.StartingUp:
                return return_error("Startup is already in progress", 412)
            if self.__shutdown_startup_state == ActiveStates.ShuttingDown:
                return return_error("Shutdown in progress", 412)
            if self.__shutdown_startup_state == ActiveStates.Scheduled:
                return return_error("Plugin was already started", 412)

            # verify we're not in a weird state
            assert self.__shutdown_startup_state == ActiveStates.Disabled

            # starting up began
            self.__shutdown_startup_state = ActiveStates.StartingUp
            self.logger.info("Starting up")

            promise = Promise(
                functools.partial(run_in_executor_helper,
                                  self.__executor,
                                  self._start_activatable))

            def on_success(*args):
                self._set_activation_state(ActiveStates.Scheduled)
                self.logger.info("Successfully started")

            def on_failed(err):
                # if failed, restore to 'Disabled'
                self.logger.error(f"Failed starting up: {err}")
                self.__last_error = str(repr(err))
                self._set_activation_state(ActiveStates.Disabled)

            promise.then(did_fulfill=on_success,
                         did_reject=on_failed)
            return ""

    def stop_activatable(self):
        with self.__activation_lock:
            # test of anomalies
            if self.__shutdown_startup_state == ActiveStates.StartingUp:
                return return_error("Startup is already in progress", 412)
            if self.__shutdown_startup_state == ActiveStates.ShuttingDown:
                return return_error("Shutdown in progress", 412)
            if self.__shutdown_startup_state == ActiveStates.Disabled:
                return return_error("Plugin is already stopped", 412)

            # verify we're not in a weird state
            assert self.__shutdown_startup_state == ActiveStates.Scheduled

            # shutting down began
            self.__shutdown_startup_state = ActiveStates.ShuttingDown
            self.logger.info("Shutting down")

            promise = Promise(
                functools.partial(run_in_executor_helper,
                                  self.__executor,
                                  self._stop_activatable))

            def on_success(*args):
                self._set_activation_state(ActiveStates.Disabled)
                self.logger.info("Successfully stopped")

            def on_failed(err):
                # if failed, restore to 'Scheduled'
                self.logger.error(f"Failed shutting down: {err}")
                self.__last_error = str(repr(err))
                self._set_activation_state(ActiveStates.Scheduled)

            promise.then(did_fulfill=on_success,
                         did_reject=on_failed)
            return ""

    @abstractmethod
    def _start_activatable(self):
        """
        Called when scheduling should start.
        Might be called even if scheduling is already taking place, or if stopped.
        Make sure your method returns only after all "starting up" logic is complete
        and your instance is internally in an "available" state.
        This is promised to be called only once and only when the plugin is not in "starting up" or "shutting down"
        and not "started".
        :return:
        """
        pass

    @abstractmethod
    def _stop_activatable(self):
        """
        Called when scheduling should stop
        Might be called even if scheduling is already taking place, or if stopped.
        Make sure your method returns only after all "shutting down" logic is complete
        and your instance is internally in an "not scheduling and not running" state
        This is promised to be called only once and only when the plugin is not in "starting up" or "shutting down"
        and not "stopped".
        This means this may be called when action is taking place or just scheduled.
        :return:
        """
        pass

    @abstractmethod
    def _is_work_in_progress(self) -> bool:
        """
        This is only called when the process was previously started with /start and not stopped using /stop
        Returns if some work is currently taking place (True) or if the plugin is in standby (False)
        :return: bool
        """
        pass
