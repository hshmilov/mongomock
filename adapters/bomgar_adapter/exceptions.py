class BomgarException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class BomgarNotConnected(BomgarException):
    pass


class BomgarAlreadyConnected(BomgarException):
    pass


class BomgarConnectionError(BomgarException):
    pass


class BomgarRequestException(BomgarException):
    pass
