import logging
from collections import namedtuple

logger = logging.getLogger(f'axonius.{__name__}')
SessionTimeoutTuple = namedtuple('SessionTimeoutTuple', ['read_timeout', 'recv_timeout'])
DEFAULT_TIMEOUT = SessionTimeoutTuple(5, 300)


def get_default_timeout():
    try:
        # We have to import this here, since this file gets imported from pluginbase itself, so we have to not
        # be recursive.
        from axonius.plugin_base import PluginBase
        return SessionTimeoutTuple(*PluginBase.Instance._configured_session_timeout)  # pylint: disable=protected-access
    except Exception:
        logger.exception(f'Can not get default timeout')
    return DEFAULT_TIMEOUT
