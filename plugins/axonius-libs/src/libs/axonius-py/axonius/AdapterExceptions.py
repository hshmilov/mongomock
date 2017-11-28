"""
AdapterExceptions.py: Exceptions common for all adapters, those should be respected by other parts of the system
"""


class AdapterException(Exception):
    pass


class CredentialErrorException(AdapterException):
    pass
