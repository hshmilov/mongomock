class GotoassistException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class GotoassistNotConnected(GotoassistException):
    pass


class GotoassistAlreadyConnected(GotoassistException):
    pass


class GotoassistConnectionError(GotoassistException):
    pass


class GotoassistRequestException(GotoassistException):
    pass
