class SecdoException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class SecdoNotConnected(SecdoException):
    pass


class SecdoAlreadyConnected(SecdoException):
    pass


class SecdoConnectionError(SecdoException):
    pass


class SecdoRequestException(SecdoException):
    pass
