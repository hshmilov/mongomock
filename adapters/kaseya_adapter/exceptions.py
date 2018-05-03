class KaseyaException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class KaseyaNotConnected(KaseyaException):
    pass


class KaseyaAlreadyConnected(KaseyaException):
    pass


class KaseyaConnectionError(KaseyaException):
    pass


class KaseyaRequestException(KaseyaException):
    pass
