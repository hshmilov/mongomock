from abc import ABC, abstractmethod
from enum import Enum, auto
from threading import Lock

from flask import jsonify

from axonius.PluginBase import add_rule


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


class Activatable(ABC):
    """
    Defines common methods and api for plugins that can be "started" and "stopped", say, like the Aggregator.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._activation_lock = Lock()

    @add_rule('start')
    def start_scheduling(self):
        """
        Start scheduling
        :return:
        """
        with self._activation_lock:
            return self._start()

    @add_rule('stop')
    def stop_scheduling(self):
        """
        Stop scheduling
        :return:
        """
        with self._activation_lock:
            return self._stop()

    @add_rule('state')
    def get_activatable_state(self):
        """
        Get whether plugin work is taking place, scheduled, or not scheduled.
        :return:
        """
        with self._activation_lock:
            state = self._get_activatable_state()
            assert isinstance(state, ActiveStates)
            return jsonify(state.value)

    @abstractmethod
    def _start(self):
        """
        Called when scheduling should start
        Might be called even if scheduling is already taking place
        :return:
        """
        pass

    @abstractmethod
    def _stop(self):
        """
        Called when scheduling should stop
        Might be called even if scheduling is not taking place
        :return:
        """
        pass

    @abstractmethod
    def _get_activatable_state(self) -> ActiveStates:
        """
        Returns the state of the task
        :return: ActiveStates
        """
        pass
