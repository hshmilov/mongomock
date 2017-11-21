"""
The purpose of this file is to export the Core exceptions.
"""

__author__ = 'Ofir Yefet'


class CoreException(Exception):
    def __init__(self, message=""):
        super().__init__(message)


class PluginNotFoundError(CoreException):
    def __init__(self, message=""):
        super().__init__(message)
