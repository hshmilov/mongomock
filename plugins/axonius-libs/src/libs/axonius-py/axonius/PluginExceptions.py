"""
PluginExceptions.py: Exceptions common for all plugins, to notify other parts of the system there is a plugin-level problem
"""


class PluginException(Exception):
    pass


class PluginNotFoundException(PluginException):
    """
    To be used for shouting about a plugin that is expected to be registered but not returned when calling /register
    """
    pass
