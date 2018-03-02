class MinervaException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class MinervaNotConnected(MinervaException):
    pass


class MinervaAlreadyConnected(MinervaException):
    pass


class MinervaConnectionError(MinervaException):
    pass


class MinervaRequestException(MinervaException):
    pass
