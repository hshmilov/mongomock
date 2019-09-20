"""
AdapterExceptions.py: Exceptions common for all adapters, those should be respected by other parts of the system.
"""


class AdapterException(Exception):
    pass


class CredentialErrorException(AdapterException):
    pass


class ClientConnectionException(AdapterException):
    """
    Exception to be thrown from specific adapter when they are unable to connect to a client, according to given config.
    """


class ClientConnectionAlreadyConnected(ClientConnectionException):
    """
    Exception to be thrown from specific adapter when they are unable to connect to a client, according to given config.
    """


class TagDeviceError(AdapterException):
    """
    Exception to be thrown if tagging a device failed.
    """


class GetDevicesError(AdapterException):
    """
    Exception to be thrown if getting devices failed.
    """


class ParseDevicesError(AdapterException):
    """
    Exception to be thrown if getting devices failed.
    """


class NoIpFoundError(AdapterException):
    pass
