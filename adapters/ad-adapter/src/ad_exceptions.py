"""
The purpose of this file is to export the ActiveDirectoryAdapter exceptions.
"""

__author__ = 'Ofir Yefet'


class AdException(Exception):
    def __init__(self, message=""):
        super().__init__(message)


class LdapException(AdException):
    def __init__(self, message=""):
        super().__init__(message)


class NoClientError(AdException):
    def __init__(self, message="Couldn't find client for execution"):
        super().__init__(message)


class IpResolveError(AdException):
    def __init__(self, message=""):
        super().__init__(message)
