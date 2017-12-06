"""
AdapterExceptions.py: Exceptions common for all adapters, those should be respected by other parts of the system
"""


class AdapterException(Exception):
    pass


class CredentialErrorException(AdapterException):
    pass


class ClientConnectionException(AdapterException):
    """
    Exception to be thrown from specific adapter when they are unable to connect to a client, according to given config
    """
    pass


class ClientSaveException(AdapterException):
    """
    Exception to be thrown if there was a problem with saving the client to the adapters DB
    """
