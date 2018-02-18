class SentinelOneException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class SentinelOneNotConnected(SentinelOneException):
    pass


class SentinelOneAlreadyConnected(SentinelOneException):
    pass


class SentinelOneConnectionError(SentinelOneException):
    pass


class SentinelOneRequestException(SentinelOneException):
    pass
