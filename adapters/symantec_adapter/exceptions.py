class SymantecException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class SymantecNotConnected(SymantecException):
    pass


class SymantecAlreadyConnected(SymantecException):
    pass


class SymantecConnectionError(SymantecException):
    pass


class SymantecRequestException(SymantecException):
    pass
