class BigfixException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class BigfixNotConnected(BigfixException):
    pass


class BigfixAlreadyConnected(BigfixException):
    pass


class BigfixConnectionError(BigfixException):
    pass


class BigfixRequestException(BigfixException):
    pass
