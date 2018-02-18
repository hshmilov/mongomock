class SccmException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class SccmNotConnected(SccmException):
    pass


class SccmAlreadyConnected(SccmException):
    pass


class SccmConnectionError(SccmException):
    pass


class SccmRequestException(SccmException):
    pass
