"""
The purpose of this file is to export the ActiveDirectoryPlugin exceptions.
"""

__author__ = 'Ofir Yefet'


class AdException(Exception):
    def __init__(self, message=""):
        super().__init__(message)


class SqliteException(AdException):
    def __init__(self, message=""):
        super().__init__(message)


class LdapException(AdException):
    def __init__(self, message=""):
        super().__init__(message)
