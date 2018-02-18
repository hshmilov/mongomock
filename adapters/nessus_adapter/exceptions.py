class NessusException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class NessusNotConnected(NessusException):
    """
    Use on an attempt to make a request, when connection is not established
    """


class NessusAlreadyConnected(NessusException):
    """
    Use on an attempt to connect, while adapter is already connected
    """
    pass


class NessusCredentialMissing(NessusException):
    """
    Use on an attempt to connect without one of required credentials
    """
    pass


class NessusConnectionError(NessusException):
    """
    Use on failure of a valid attempt to connect
    """
    pass


class NessusRequestError(NessusException):
    """
    Use on failure of a valid attempt to request from an established connection
    """
