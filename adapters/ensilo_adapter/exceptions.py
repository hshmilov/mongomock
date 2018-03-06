class EnsiloException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class EnsiloNotConnected(EnsiloException):
    pass


class EnsiloAlreadyConnected(EnsiloException):
    pass


class EnsiloConnectionError(EnsiloException):
    pass


class EnsiloRequestException(EnsiloException):
    pass
