class CarbonblackResponseException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class CarbonblackResponseNotConnected(CarbonblackResponseException):
    pass


class CarbonblackResponseAlreadyConnected(CarbonblackResponseException):
    pass


class CarbonblackResponseConnectionError(CarbonblackResponseException):
    pass


class CarbonblackResponseRequestException(CarbonblackResponseException):
    pass
