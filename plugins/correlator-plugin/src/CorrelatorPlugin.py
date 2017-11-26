"""
CorrelatorPlugin.py: A Plugin for the devices correlation process
"""
import threading
from enum import Enum, auto

from datetime import datetime
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import jsonify

from axonius.PluginBase import PluginBase, add_rule, return_error
from CorrelatorEngine import CorrelatorEngine, WarningResult, CorrelationResult


class CorrelatorStates(Enum):
    def _generate_next_value_(name, *args):
        return f"Correlation{name}"

    """
    Correlation is scheduled to run in the near future, i.e. correlation is "active"
    """
    Scheduled = auto()
    """
    Correlation isn't running and isn't scheduled, unless requested, correlations won't run
    """
    Disabled = auto()
    """
    Correlation is taking place right now
    """
    InProgress = auto()


class CorrelatorPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)

        # this lock makes sure correlation won't happen concurrently
        self._correlation_lock = threading.RLock()

        # if this plugin is scheduled to run correlations this will be the scheduler instance
        self._correlation_scheduler = None

        executor = self.request_action

        def get_remote_plugin_correlation_cmds(plugin_name):
            return self.request_remote_plugin('correlation_cmds', plugin_name).json()

        def parse_correlation_results(plugin_unique_name, results):
            return self.request_remote_plugin('parse_correlation_results', plugin_unique_name, 'post',
                                              json=results).json()

        self._correlation_engine = CorrelatorEngine(self.logger, executor, get_remote_plugin_correlation_cmds,
                                                    parse_correlation_results)

    @add_rule('start')
    def start_scheduling(self):
        """
        Start the scheduler
        :return:
        """
        if self._correlation_scheduler is not None:
            return return_error("Correlation is already scheduled")

        executors = {'default': ThreadPoolExecutor(1)}
        self._correlation_scheduler = BackgroundScheduler(executors=executors)
        self._correlation_scheduler.add_job(func=self._correlate,
                                            trigger=IntervalTrigger(minutes=5),
                                            next_run_time=datetime.now(),
                                            name='correlation',
                                            id='correlation',
                                            max_instances=1)
        self._correlation_scheduler.start()

        return ""

    @add_rule('stop')
    def stop_scheduling(self):
        """
        Stop the scheduler
        :return:
        """
        self._correlation_scheduler.shutdown()
        self._correlation_scheduler = None
        return ""

    @add_rule('state')
    def get_state(self):
        """
        Get whether correlation is taking place, scheduled, or not scheduled.
        :return:
        """
        if self._correlation_lock.acquire(False):
            if self._correlation_scheduler is None:
                state = CorrelatorStates.Disabled
            else:
                state = CorrelatorStates.Scheduled
            self._correlation_lock.release()
        else:
            state = CorrelatorStates.InProgress
        return jsonify(state.value)

    @add_rule('correlate', methods=['POST'])
    def correlate(self):
        """
        Correlate across the whole DB, returns any errors as-is.
        This should be used for "debugging purposes" or manual correlation (if needed for any reason)
        with the benefit that any errors will be easily returned to the caller.
        :return:
        """
        try:
            self._correlate()
        except Exception as e:
            return return_error(f"Fatal error during correlations: {e}")
        return ""

    def _correlate(self):
        """
        Correlate across the whole DB
        :return:
        """
        with self._correlation_lock:
            with self._get_db_connection(True) as db:
                aggregator_db = db[self.get_plugin_by_name('aggregator', verify_single=True)['plugin_unique_name']]
                all_devices = list(aggregator_db['devices_db'].find())
                for result in self._correlation_engine.correlate(all_devices):
                    if isinstance(result, WarningResult):
                        self.create_notification(result.title, result.content, result.notification_type)

                    if isinstance(result, CorrelationResult):
                        self.request_remote_plugin('plugin_push', 'aggregator', 'post', json={
                            "plugin_type": "Plugin",
                            "data": result.data,
                            "associated_adapter_devices": dict(result.associated_adapter_devices),
                            "association_type": "Link"
                        })
