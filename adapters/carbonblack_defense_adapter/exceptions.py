class CarbonblackDefenseException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class CarbonblackDefenseNotConnected(CarbonblackDefenseException):
    pass


class CarbonblackDefenseAlreadyConnected(CarbonblackDefenseException):
    pass


class CarbonblackDefenseConnectionError(CarbonblackDefenseException):
    pass


class CarbonblackDefenseRequestException(CarbonblackDefenseException):
    pass
