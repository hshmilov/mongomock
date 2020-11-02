"""
PluginExceptions.py: Exceptions common for all plugins, to notify other parts of the system there is a plugin-level problem
"""


class PluginException(Exception):
    pass


class PhaseExecutionException(PluginException):
    """
    Exception to be thrown from phase service when an exception is raised during one of the research phases.
    """
    pass


class PluginNotFoundException(PluginException):
    """
    To be used for shouting about a plugin that is expected to be registered but not returned when calling /register
    """
    pass


class SessionInvalid(Exception):
    """
    To be used anytime a session is expected to have a user logged in, but it is
    """
    pass


class InvalidRequestException(Exception):
    """
    To be used anytime a an invalid request is sent
    """
    pass
