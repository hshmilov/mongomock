class CarbonblackException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class CarbonblackNotConnected(CarbonblackException):
    pass


class CarbonblackAlreadyConnected(CarbonblackException):
    pass


class CarbonblackConnectionError(CarbonblackException):
    pass


class CarbonblackRequestException(CarbonblackException):
    pass
